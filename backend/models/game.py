from pydantic import BaseModel
from typing import Literal


class ValidationResult(BaseModel):
    valid: bool
    explanation: str
    movie_id: int | None = None
    movie_title: str | None = None
    movie_year: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None
    from_actor_found: bool = False
    to_actor_found: bool = False


class Actor(BaseModel):
    name: str
    id: int
    profile_url: str | None = None


class MovieStep(BaseModel):
    type: Literal["movie"]
    title: str
    id: int
    year: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None


class ActorStep(BaseModel):
    type: Literal["actor"]
    name: str
    id: int
    profile_url: str | None = None


class Move(BaseModel):
    from_actor: str
    movie: str
    to_actor: str
    movie_id: int | None = None
    movie_title: str | None = None
    movie_year: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None


class GameState(BaseModel):
    id: str
    start_actor: Actor
    end_actor: Actor
    difficulty: str
    min_moves: int
    current_actor: Actor
    moves: list[Move]
    status: Literal["in_progress", "won"]
    created_at: str | None = None


class NewGameResponse(BaseModel):
    game_id: str
    start_actor: Actor
    end_actor: Actor
    difficulty: str
    min_moves: int


class MoveRequest(BaseModel):
    movie: str
    next_actor: str


class MoveResponse(BaseModel):
    valid: bool
    explanation: str
    movie_id: int | None = None
    movie_title: str | None = None
    movie_year: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None
    game_status: Literal["in_progress", "won"]
    current_actor: Actor
