"""
Validation Agent: verifies that two actors both appeared in a named movie.

Uses direct TMDb lookups and fuzzy string matching. Falls back to an LLM
call (via reusable-llm-provider) when fuzzy matching cannot resolve a name,
e.g. nicknames like "Larry" for "Laurence".
"""

import logging
from langsmith import traceable, get_current_run_tree
from art_graph.cinema_data_providers.tmdb.client import TMDbClient
from ..matching import find_actor_in_cast, ActorMatch
from ..models.game import Confidence, ValidationResult

logger = logging.getLogger(__name__)


LLM_NAME_MATCH_PROMPT = (
    "You are matching a player-typed actor name against a movie cast list.\n"
    "The player is playing a cinema connections game where they name actors\n"
    "and movies to build a chain. They may use nicknames, abbreviations,\n"
    "or informal names (e.g. 'Larry' for 'Laurence', 'Dick' for 'Richard').\n\n"
    "Cast list:\n{cast_names}\n\n"
    'Player typed: "{query}"\n\n'
    "If the player clearly means one of the cast members, return a JSON object:\n"
    '  {{"matched_name": "Exact Name From Cast List"}}\n'
    "If no cast member matches, return:\n"
    '  {{"matched_name": null}}\n\n'
    "Return ONLY the JSON object, nothing else."
)


@traceable(run_type="tool", name="llm_name_match")
def _llm_name_match(llm, query: str, cast_names: list[str]) -> ActorMatch | None:
    """Ask the LLM to resolve a name that fuzzy matching could not."""
    prompt = LLM_NAME_MATCH_PROMPT.format(
        cast_names="\n".join(f"- {n}" for n in cast_names),
        query=query,
    )
    try:
        result = llm.invoke_json(prompt)
    except Exception:
        logger.warning("LLM name match failed for %r", query, exc_info=True)
        return None

    matched = result.get("matched_name") if isinstance(result, dict) else None
    if matched and matched in cast_names:
        return ActorMatch(matched_name=matched)
    return None


@traceable(run_type="tool", name="resolve_actor")
def _resolve_actor(query: str, cast_names: list[str], llm=None) -> ActorMatch | None:
    """Try fuzzy matching first, then LLM fallback if available."""
    match = find_actor_in_cast(query, cast_names)
    if match is not None:
        return match
    if llm is not None:
        return _llm_name_match(llm, query, cast_names)
    logger.warning(
        "Fuzzy matching failed for %r and no LLM fallback is available", query
    )
    rt = get_current_run_tree()
    if rt:
        rt.metadata["llm_fallback_skipped"] = True
        rt.metadata["unresolved_query"] = query
    return None


@traceable(run_type="chain", name="validate_move")
async def validate_move(
    tmdb: TMDbClient,
    from_actor: str,
    movie_title: str,
    to_actor: str,
    llm=None,
) -> ValidationResult:
    """
    Verify that from_actor and to_actor both appeared in movie_title.

    1. Search TMDb for the movie (TMDb handles fuzzy title matching).
    2. Fetch the cast list.
    3. Fuzzy-match both actor names against the cast.
    4. If fuzzy matching fails and an LLM provider is available, try LLM fallback.
    """
    movie = await tmdb.search_movie(movie_title)
    if not movie:
        return ValidationResult(
            valid=False,
            explanation=f"Movie '{movie_title}' not found on TMDb.",
            confidence=Confidence.high,
        )

    cast = await tmdb.get_movie_cast(movie.id)
    cast_names = [c.name for c in cast]

    from_match = _resolve_actor(from_actor, cast_names, llm)
    to_match = _resolve_actor(to_actor, cast_names, llm)

    valid = from_match is not None and to_match is not None

    if valid:
        explanation = (
            f"{from_match.matched_name} and {to_match.matched_name} "
            f"both appear in {movie.title} ({movie.year})."
        )
    else:
        missing = []
        if from_match is None:
            missing.append(from_actor)
        if to_match is None:
            missing.append(to_actor)
        explanation = (
            f"{' and '.join(missing)} not found in the cast of "
            f"{movie.title} ({movie.year})."
        )

    return ValidationResult(
        valid=valid,
        explanation=explanation,
        confidence=Confidence.high,
        movie_id=movie.id,
        movie_title=movie.title,
        movie_year=movie.year,
        poster_url=movie.poster_url,
        backdrop_url=movie.backdrop_url,
        from_actor_found=from_match is not None,
        to_actor_found=to_match is not None,
        from_actor_name=from_match.matched_name if from_match else None,
        to_actor_name=to_match.matched_name if to_match else None,
    )
