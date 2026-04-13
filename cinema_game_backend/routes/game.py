import uuid
from fastapi import APIRouter, HTTPException
from langsmith import traceable, get_current_run_tree
from ..models.game import (
    NewGameResponse,
    MoveRequest,
    MoveResponse,
    UndoResponse,
    GameState,
    Actor,
    Move,
)
from ..agents.puzzle_agent import generate_puzzle
from ..agents.validation_agent import validate_move
from ..tools.tmdb import tmdb
from ..database import save_game, load_game, update_game

router = APIRouter(prefix="/game", tags=["game"])


async def _resolve_actor(name: str, fallback_id: int = 0) -> dict:
    """Look up an actor by name and return their TMDb ID + canonical name."""
    person = await tmdb.search_person(name)
    if person:
        return {"name": person.name, "id": person.id, "profile_url": person.profile_url}
    return {"name": name, "id": fallback_id, "profile_url": None}


def _reached_end(next_actor_id: int, next_actor_name: str, end_actor: dict) -> bool:
    """
    Win condition: compare by TMDb ID when available, fall back to normalised name.
    Handles typos and name variants (e.g. 'Brad Pitt' vs 'William Bradley Pitt').
    """
    end_id = end_actor.get("id", 0)
    if next_actor_id and end_id and next_actor_id == end_id:
        return True
    # Normalised name fallback (strips extra whitespace, case-insensitive)
    return next_actor_name.strip().lower() == end_actor["name"].strip().lower()


@router.post("/new", response_model=NewGameResponse)
@traceable(run_type="chain", name="new_game")
async def new_game(difficulty: str = "medium"):
    if difficulty not in ("easy", "medium", "hard"):
        raise HTTPException(
            status_code=400, detail="difficulty must be easy, medium, or hard"
        )

    puzzle = await generate_puzzle(difficulty)

    game_id = str(uuid.uuid4())
    rt = get_current_run_tree()
    if rt:
        rt.metadata.update({"game_id": game_id, "difficulty": difficulty})

    game = {
        "id": game_id,
        "start_actor": puzzle["start_actor"],
        "end_actor": puzzle["end_actor"],
        "difficulty": puzzle["difficulty"],
        "known_solution": puzzle["known_solution"],
        "moves": [],
        "current_actor": puzzle["start_actor"],
        "status": "in_progress",
        "strikes": 0,
    }
    save_game(game)

    return NewGameResponse(
        game_id=game_id,
        start_actor=Actor(**puzzle["start_actor"]),
        end_actor=Actor(**puzzle["end_actor"]),
        difficulty=puzzle["difficulty"],
        min_moves=puzzle["min_moves"],
    )


@router.post("/{game_id}/move", response_model=MoveResponse)
@traceable(run_type="chain", name="make_move")
async def make_move(game_id: str, body: MoveRequest):
    game = load_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game["status"] != "in_progress":
        raise HTTPException(status_code=400, detail="Game is already over")

    from_actor = game["current_actor"]["name"]

    rt = get_current_run_tree()
    if rt:
        rt.metadata.update(
            {
                "game_id": game_id,
                "difficulty": game["difficulty"],
                "from_actor": from_actor,
            }
        )

    result = await validate_move(
        from_actor,
        body.movie,
        body.next_actor,
        langsmith_extra={"metadata": {"game_id": game_id}},
    )

    if not result.valid:
        strikes = game.get("strikes", 0) + 1
        new_status = "lost" if strikes >= 3 else "in_progress"
        update_game(game_id, game["moves"], game["current_actor"], new_status, strikes)
        return MoveResponse(
            valid=False,
            explanation=result.explanation,
            game_status=new_status,
            current_actor=Actor(**game["current_actor"]),
            strikes=strikes,
        )

    # Resolve the next actor's TMDb ID for accurate win detection
    new_actor = await _resolve_actor(body.next_actor)

    # Record the move with the canonical TMDb title
    move = Move(
        from_actor=from_actor,
        movie=result.movie_title or body.movie,
        to_actor=new_actor["name"],
        movie_id=result.movie_id,
        movie_title=result.movie_title,
        movie_year=result.movie_year,
        poster_url=result.poster_url,
        backdrop_url=result.backdrop_url,
    )
    game["moves"].append(move.model_dump())

    # Win check: ID-first, name fallback
    reached = _reached_end(new_actor["id"], new_actor["name"], game["end_actor"])
    new_status = "won" if reached else "in_progress"

    strikes = game.get("strikes", 0)
    update_game(game_id, game["moves"], new_actor, new_status, strikes)

    return MoveResponse(
        valid=True,
        explanation=result.explanation,
        movie_id=result.movie_id,
        movie_title=result.movie_title,
        movie_year=result.movie_year,
        poster_url=result.poster_url,
        backdrop_url=result.backdrop_url,
        game_status=new_status,
        current_actor=Actor(**new_actor),
        strikes=strikes,
    )


@router.delete("/{game_id}/move", response_model=UndoResponse)
async def undo_move(game_id: str):
    game = load_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game["status"] != "in_progress":
        raise HTTPException(status_code=400, detail="Game is already over")
    if not game["moves"]:
        raise HTTPException(status_code=400, detail="No moves to undo")

    last_move = game["moves"].pop()
    restored_actor = await _resolve_actor(
        last_move["from_actor"],
        fallback_id=game["start_actor"]["id"] if not game["moves"] else 0,
    )
    strikes = game.get("strikes", 0)
    update_game(game_id, game["moves"], restored_actor, "in_progress", strikes)

    return UndoResponse(
        current_actor=Actor(**restored_actor),
        moves=[Move(**m) for m in game["moves"]],
        strikes=strikes,
        game_status="in_progress",
    )


@router.get("/{game_id}", response_model=GameState)
async def get_game(game_id: str):
    game = load_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    return GameState(
        id=game["id"],
        start_actor=Actor(**game["start_actor"]),
        end_actor=Actor(**game["end_actor"]),
        difficulty=game["difficulty"],
        min_moves=len([s for s in game["known_solution"] if s["type"] == "movie"]),
        current_actor=Actor(**game["current_actor"]),
        moves=[Move(**m) for m in game["moves"]],
        status=game["status"],
        strikes=game.get("strikes", 0),
        created_at=game.get("created_at"),
    )
