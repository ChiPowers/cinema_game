import httpx
from ..config import TMDB_API_KEY, TMDB_BASE_URL, TMDB_IMAGE_BASE, TMDB_BACKDROP_BASE
from ..models.tmdb import TmdbCastMember, TmdbMovie, TmdbPerson


class TMDbClient:
    def __init__(self):
        self.key = TMDB_API_KEY
        self.base = TMDB_BASE_URL

    def _img(self, path: str | None, base: str = TMDB_IMAGE_BASE) -> str | None:
        return f"{base}{path}" if path else None

    async def _get(self, path: str, params: dict = {}) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base}{path}",
                params={"api_key": self.key, **params},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

    async def search_person(self, name: str) -> TmdbPerson | None:
        data = await self._get("/search/person", {"query": name})
        results = data.get("results", [])
        if not results:
            return None
        p = results[0]
        return TmdbPerson(
            id=p["id"],
            name=p["name"],
            popularity=p.get("popularity", 0),
            profile_url=self._img(p.get("profile_path")),
            known_for=[m.get("title", m.get("name", "")) for m in p.get("known_for", [])],
        )

    async def get_person_movies(self, person_id: int, limit: int = 20) -> list[TmdbMovie]:
        data = await self._get(f"/person/{person_id}/movie_credits")
        cast = data.get("cast", [])
        cast.sort(key=lambda x: x.get("popularity", 0), reverse=True)
        return [
            TmdbMovie(
                id=m["id"],
                title=m["title"],
                year=(m.get("release_date") or "")[:4] or None,
                popularity=m.get("popularity", 0),
                poster_url=self._img(m.get("poster_path")),
                backdrop_url=self._img(m.get("backdrop_path"), TMDB_BACKDROP_BASE),
            )
            for m in cast[:limit]
        ]

    async def search_movie(self, title: str, year: int | None = None) -> TmdbMovie | None:
        params = {"query": title}
        if year:
            params["year"] = year
        data = await self._get("/search/movie", params)
        results = data.get("results", [])
        if not results:
            return None
        m = results[0]
        return TmdbMovie(
            id=m["id"],
            title=m["title"],
            year=(m.get("release_date") or "")[:4] or None,
            poster_url=self._img(m.get("poster_path")),
            backdrop_url=self._img(m.get("backdrop_path"), TMDB_BACKDROP_BASE),
        )

    async def get_movie_cast(self, movie_id: int) -> list[TmdbCastMember]:
        data = await self._get(f"/movie/{movie_id}/credits")
        return [
            TmdbCastMember(
                id=c["id"],
                name=c["name"],
                character=c.get("character", ""),
                order=c.get("order", 999),
                profile_url=self._img(c.get("profile_path")),
            )
            for c in data.get("cast", [])
        ]

    async def get_person_details(self, person_id: int) -> TmdbPerson | None:
        try:
            data = await self._get(f"/person/{person_id}")
            return TmdbPerson(
                id=data["id"],
                name=data["name"],
                popularity=data.get("popularity", 0),
                profile_url=self._img(data.get("profile_path")),
            )
        except Exception:
            return None

    async def get_popular_people(self, page: int = 1) -> list[TmdbPerson]:
        data = await self._get("/person/popular", {"page": page})
        return [
            TmdbPerson(
                id=p["id"],
                name=p["name"],
                popularity=p.get("popularity", 0),
                profile_url=self._img(p.get("profile_path")),
                known_for=[m.get("title", m.get("name", "")) for m in p.get("known_for", [])],
            )
            for p in data.get("results", [])
        ]


tmdb = TMDbClient()
