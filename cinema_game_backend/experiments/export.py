"""Export game sessions from the database into RecordedGame models."""

from ..database import load_game, list_games
from ..models.experiment import (
    ExpectedSuccess,
    RecordedMove,
    RecordedGame,
)


def list_game_ids(limit: int | None = None) -> list[dict]:
    """List recent games in the database with summary info.

    Returns a list of dicts with keys: game_id, difficulty, start_actor,
    end_actor, status, moves, created_at.
    """
    games = list_games(limit=limit)
    return [
        {
            "game_id": g["id"],
            "difficulty": g["difficulty"],
            "start_actor": g["start_actor"]["name"],
            "end_actor": g["end_actor"]["name"],
            "status": g["status"],
            "moves": len(g["moves"]),
            "created_at": g.get("created_at"),
        }
        for g in games
    ]


def export_game(game_id: str) -> RecordedGame:
    """Load a game from the database and return it as a RecordedGame.

    Only valid (accepted) moves are stored in the database, so every
    move in the returned RecordedGame has an ExpectedSuccess outcome.
    """
    game = load_game(game_id)
    if game is None:
        raise ValueError(f"Game not found: {game_id}")

    moves = []
    for m in game["moves"]:
        expected = ExpectedSuccess(
            movie_id=m["movie_id"],
            movie_title=m["movie_title"],
            actor_id=m.get("to_actor_id"),
            actor_name=m["to_actor"],
        )
        moves.append(
            RecordedMove(movie=m["movie"], actor=m["to_actor"], expected=expected)
        )

    return RecordedGame(
        start_actor=game["start_actor"]["name"],
        start_actor_id=game["start_actor"]["id"],
        end_actor=game["end_actor"]["name"],
        moves=moves,
    )
