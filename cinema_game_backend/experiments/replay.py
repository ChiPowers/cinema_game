"""Replay recorded games through validate_move and compare against expected outcomes."""

from dataclasses import dataclass
from art_graph.cinema_data_providers.tmdb.client import TMDbClient
from ..agents.validation_agent import validate_move
from ..models.experiment import RecordedGame, RecordedMove, ExpectedSuccess


@dataclass
class MoveResult:
    """Result of replaying a single move."""

    move: RecordedMove
    actual_valid: bool
    expected_valid: bool
    passed: bool
    detail: str


async def replay_move(
    tmdb: TMDbClient,
    from_actor: str,
    move: RecordedMove,
    from_actor_id: int,
    llm=None,
) -> MoveResult:
    """Replay a single move and compare against the expected outcome."""
    result = await validate_move(
        tmdb, from_actor, move.movie, move.actor, from_actor_id=from_actor_id, llm=llm
    )

    expected_valid = move.expected.valid
    passed = result.valid == expected_valid

    if passed and result.valid and isinstance(move.expected, ExpectedSuccess):
        # Valid move — also check that the resolved IDs and names match.
        if result.movie_id != move.expected.movie_id:
            passed = False
            detail = (
                f"Movie ID mismatch: expected {move.expected.movie_id}, "
                f"got {result.movie_id}"
            )
        elif result.to_actor_name != move.expected.actor_name:
            passed = False
            detail = (
                f"Actor name mismatch: expected {move.expected.actor_name!r}, "
                f"got {result.to_actor_name!r}"
            )
        else:
            detail = "ok"
    elif passed:
        detail = "ok"
    elif result.valid and not expected_valid:
        detail = f"Expected failure but move was accepted: {result.explanation}"
    else:
        detail = f"Expected success but move was rejected: {result.explanation}"

    return MoveResult(
        move=move,
        actual_valid=result.valid,
        expected_valid=expected_valid,
        passed=passed,
        detail=detail,
    )


async def replay_game(
    tmdb: TMDbClient,
    game: RecordedGame,
    llm=None,
) -> list[MoveResult]:
    """Replay all moves in a recorded game sequentially.

    Each move uses the previous move's expected actor as the from_actor,
    mirroring how the game advances through the chain.
    """
    results = []
    current_actor = game.start_actor
    current_actor_id = game.start_actor_id

    for move in game.moves:
        result = await replay_move(
            tmdb, current_actor, move, from_actor_id=current_actor_id, llm=llm
        )
        results.append(result)

        # Advance the chain only if the move was expected to succeed.
        if isinstance(move.expected, ExpectedSuccess):
            current_actor = move.expected.actor_name
            current_actor_id = move.expected.actor_id

    return results
