"""Models for recorded game sessions used in regression testing."""

from pydantic import BaseModel


class ExpectedSuccess(BaseModel):
    """Expected outcome for a valid move."""

    valid: bool = True
    movie_id: int
    movie_title: str
    actor_id: int | None = None
    actor_name: str


class ExpectedFailure(BaseModel):
    """Expected outcome for an invalid move."""

    valid: bool = False


class RecordedMove(BaseModel):
    """A single player move: a movie and actor expressed as raw strings."""

    movie: str
    actor: str
    expected: ExpectedSuccess | ExpectedFailure


class RecordedGame(BaseModel):
    """A complete recorded game session for regression testing."""

    start_actor: str
    start_actor_id: int | None = None
    end_actor: str
    moves: list[RecordedMove]
