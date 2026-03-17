"""
Puzzle Agent: generates a new cinema connections puzzle via random walk on TMDb data.
Guarantees a valid solution by construction (the walk IS the solution).
No LLM needed here — pure TMDb API calls.
"""

import random
import asyncio
from tools.tmdb import tmdb
from config import DIFFICULTY_HOPS, MIN_ACTOR_POPULARITY


async def _pick_popular_actor(min_popularity: float) -> dict:
    """Pick a random actor from TMDb's popular people list above a popularity threshold."""
    page = random.randint(1, 5)
    people = await tmdb.get_popular_people(page=page)
    eligible = [p for p in people if p["popularity"] >= min_popularity]
    if not eligible:
        eligible = people
    return random.choice(eligible)


async def _random_walk(
    start_actor: dict,
    hops: int,
    min_popularity: float,
    no_repeat_movies: bool = False,
) -> list[dict] | None:
    """
    Build a path of length `hops` via random walk:
      actor → movie → actor → movie → actor ...

    Returns an ordered list of step dicts, or None if the walk dead-ends.
    Each step: {"type": "actor"|"movie", ...}

    When no_repeat_movies=True, the same movie cannot appear twice in the path.
    """
    path = [
        {
            "type": "actor",
            "name": start_actor["name"],
            "id": start_actor["id"],
            "profile_url": start_actor.get("profile_url"),
        }
    ]
    current_actor_id = start_actor["id"]
    used_movie_ids: set[int] = set()

    for hop in range(hops):
        # Get movies for current actor, sorted by popularity
        movies = await tmdb.get_person_movies(current_actor_id, limit=20)
        movies = [m for m in movies if m.get("popularity", 0) > 5] or movies

        # Exclude already-used movies when required
        if no_repeat_movies:
            movies = [m for m in movies if m["id"] not in used_movie_ids]

        if not movies:
            return None

        movie = random.choice(movies[:10])
        used_movie_ids.add(movie["id"])

        path.append(
            {
                "type": "movie",
                "title": movie["title"],
                "id": movie["id"],
                "year": movie.get("year"),
                "poster_url": movie.get("poster_url"),
                "backdrop_url": movie.get("backdrop_url"),
            }
        )

        # Get cast, excluding current actor
        cast = await tmdb.get_movie_cast(movie["id"])
        cast = [c for c in cast if c["id"] != current_actor_id]
        if not cast:
            return None

        is_last_hop = hop == hops - 1
        if is_last_hop:
            # Prefer end actor above the popularity floor; fall back to most popular available.
            scored = []
            for candidate in cast[:20]:
                person = await tmdb.get_person_details(candidate["id"])
                pop = person.get("popularity", 0) if person else 0
                scored.append({**candidate, "popularity": pop})
                if len(scored) >= 10:
                    break

            eligible = [c for c in scored if c["popularity"] >= min_popularity]
            if eligible:
                next_actor = random.choice(eligible)
            elif scored:
                next_actor = max(scored, key=lambda c: c["popularity"])
            else:
                return None
        else:
            # Intermediate hops: top billing is a good popularity proxy
            next_actor = random.choice(cast[:15])

        path.append(
            {
                "type": "actor",
                "name": next_actor["name"],
                "id": next_actor["id"],
                "profile_url": next_actor.get("profile_url"),
            }
        )
        current_actor_id = next_actor["id"]

    return path


async def generate_puzzle(difficulty: str = "medium") -> dict:
    """
    Generate a puzzle for the given difficulty tier.
    Returns: start_actor, end_actor, difficulty, min_moves, known_solution.

    Hop counts:
      easy:   exactly 2 hops, no movie repeated
      medium: 3–5 hops (random)
      hard:   6–8 hops (random)
    """
    hop_range = DIFFICULTY_HOPS.get(difficulty, (3, 5))
    hops = random.randint(*hop_range)
    min_pop = MIN_ACTOR_POPULARITY.get(difficulty, 4)
    no_repeat = difficulty == "easy"

    for _ in range(10):
        start_actor = await _pick_popular_actor(min_pop)
        path = await _random_walk(
            start_actor, hops, min_pop, no_repeat_movies=no_repeat
        )
        if path and len(path) >= 3:
            break
    else:
        raise RuntimeError(
            f"Failed to generate a valid {difficulty} puzzle after 10 attempts."
        )

    start = path[0]
    end = path[-1]

    return {
        "start_actor": {
            "name": start["name"],
            "id": start["id"],
            "profile_url": start.get("profile_url"),
        },
        "end_actor": {
            "name": end["name"],
            "id": end["id"],
            "profile_url": end.get("profile_url"),
        },
        "difficulty": difficulty,
        "min_moves": hops,
        "known_solution": path,
    }
