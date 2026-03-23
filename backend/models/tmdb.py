from pydantic import BaseModel


class TmdbPerson(BaseModel):
    id: int
    name: str
    popularity: float = 0.0
    profile_url: str | None = None
    known_for: list[str] = []


class TmdbMovie(BaseModel):
    id: int
    title: str
    year: str | None = None
    popularity: float = 0.0
    poster_url: str | None = None
    backdrop_url: str | None = None


class TmdbCastMember(BaseModel):
    id: int
    name: str
    character: str = ""
    order: int = 999
    profile_url: str | None = None
