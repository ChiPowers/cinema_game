"""
Puzzle Agent: generates a new cinema connections puzzle via random walk on TMDb data.
Guarantees a valid solution by construction (the walk IS the solution).
No LLM needed here — pure TMDb API calls.
"""

import random
import asyncio
from langsmith import traceable
from ..tools.tmdb import tmdb
from ..config import DIFFICULTY_HOPS, MIN_ACTOR_POPULARITY


async def _has_short_path(start_id: int, end_id: int, max_hops: int) -> bool:
    """
    Returns True if a path of <= max_hops exists between start and end actors.
    Checks up to 2 hops (practical API-cost limit).

    1-hop: the two actors share a movie directly.
    2-hop: the two actors share a common co-star.
    """
    start_movies, end_movies = await asyncio.gather(
        tmdb.get_person_movies(start_id, limit=15),
        tmdb.get_person_movies(end_id, limit=15),
    )

    start_movie_ids = {m.id for m in start_movies}
    end_movie_ids = {m.id for m in end_movies}

    # 1-hop check
    if start_movie_ids & end_movie_ids:
        return True

    if max_hops < 2:
        return False

    # 2-hop check: fetch casts for top 15 movies of each actor in parallel
    top_start = [m.id for m in start_movies[:15]]
    top_end = [m.id for m in end_movies[:15]]

    start_casts, end_casts = await asyncio.gather(
        asyncio.gather(*[tmdb.get_movie_cast(mid) for mid in top_start]),
        asyncio.gather(*[tmdb.get_movie_cast(mid) for mid in top_end]),
    )

    start_costars = {c.id for cast in start_casts for c in cast if c.id != start_id}

    for cast in end_casts:
        for c in cast:
            if c.id != end_id and c.id in start_costars:
                return True

    return False


async def _pick_popular_actor(min_popularity: float):
    """Pick a random actor from TMDb's popular people list above a popularity threshold."""
    page = random.randint(1, 5)
    people = await tmdb.get_popular_people(page=page)
    eligible = [p for p in people if p.popularity >= min_popularity]
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
            "name": start_actor.name,
            "id": start_actor.id,
            "profile_url": start_actor.profile_url,
        }
    ]
    current_actor_id = start_actor.id
    used_movie_ids: set[int] = set()

    for hop in range(hops):
        # Get movies for current actor, sorted by popularity
        movies = await tmdb.get_person_movies(current_actor_id, limit=20)
        movies = [m for m in movies if m.popularity > 5] or movies

        # Exclude already-used movies when required
        if no_repeat_movies:
            movies = [m for m in movies if m.id not in used_movie_ids]

        if not movies:
            return None

        movie = random.choice(movies[:10])
        used_movie_ids.add(movie.id)

        path.append(
            {
                "type": "movie",
                "title": movie.title,
                "id": movie.id,
                "year": movie.year,
                "poster_url": movie.poster_url,
                "backdrop_url": movie.backdrop_url,
            }
        )

        # Get cast, excluding current actor
        cast = await tmdb.get_movie_cast(movie.id)
        cast = [c for c in cast if c.id != current_actor_id]
        if not cast:
            return None

        is_last_hop = hop == hops - 1
        if is_last_hop:
            # Prefer end actor above the popularity floor; fall back to most popular available.
            scored = []
            for candidate in cast[:20]:
                person = await tmdb.get_person_details(candidate.id)
                pop = person.popularity if person else 0
                scored.append((candidate, pop))
                if len(scored) >= 10:
                    break

            eligible = [c for c, pop in scored if pop >= min_popularity]
            if eligible:
                next_actor = random.choice(eligible)
            elif scored:
                next_actor = max(scored, key=lambda x: x[1])[0]
            else:
                return None
        else:
            # Intermediate hops: top billing is a good popularity proxy
            next_actor = random.choice(cast[:15])

        path.append(
            {
                "type": "actor",
                "name": next_actor.name,
                "id": next_actor.id,
                "profile_url": next_actor.profile_url,
            }
        )
        current_actor_id = next_actor.id

    return path


@traceable(run_type="chain", name="generate_puzzle")
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
    # Reject puzzles where a shortcut shorter than the intended minimum exists.
    # We check up to 2 hops regardless of difficulty (API cost limit).
    shortcut_threshold = min(hop_range[0] - 1, 2)

    for _ in range(15):
        start_actor = await _pick_popular_actor(min_pop)
        path = await _random_walk(
            start_actor, hops, min_pop, no_repeat_movies=no_repeat
        )
        if not path or len(path) < 3:
            continue
        if await _has_short_path(path[0]["id"], path[-1]["id"], shortcut_threshold):
            continue
        break
    else:
        raise RuntimeError(
            f"Failed to generate a valid {difficulty} puzzle after 15 attempts."
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
