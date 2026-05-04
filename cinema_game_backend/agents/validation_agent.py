"""
Validation Agent: verifies that two actors both appeared in a named movie.

Fast path: pre-fetches movie + cast from TMDb (cache-friendly), asks Claude
to reason over the provided data in a single LLM call. Falls back to the full
agentic loop when fast-path confidence is low or the pre-fetch fails.
"""

import json
import logging
import re
from langsmith import traceable, trace
from art_graph.cinema_data_providers.tmdb.client import TMDbClient
from .base import run_agent, _call_llm_once
from ..models.game import Confidence, ValidationResult
from ..tools.definitions import ALL_TOOLS

logger = logging.getLogger(__name__)


FAST_PATH_SYSTEM = """You are a movie cast validator for a cinema connections game.

You will be given a movie's TMDb metadata and its full cast list. Your job is to
determine whether two named actors both appear in that cast, using fuzzy matching
for typos, name variants, partial names, and abbreviations.

Rate your confidence:
- high: both actors clearly match (or clearly don't match) entries in the cast list
- medium: you matched with minor name variation, abbreviation, or last-name-only
- low: significant ambiguity — the cast list may be for the wrong film, an actor
  is not clearly identifiable, or the cast list appears incomplete

CRITICAL: Your entire response must be ONLY a raw JSON object. No prose, no markdown.
Start with { and end with }. Shape must be exactly:
{"valid": true|false, "explanation": "brief reason", "confidence": "high"|"medium"|"low", "movie_id": int|null, "movie_title": "str|null", "movie_year": "str|null", "poster_url": "str|null", "backdrop_url": "str|null", "from_actor_found": true|false, "to_actor_found": true|false}"""


FALLBACK_SYSTEM = """You are a movie trivia validator for a cinema connections game.

Your job is to verify whether two actors both appeared in a specific movie.
Be thorough but efficient. Use TMDb tools to look up the movie and its cast.
If a movie title is ambiguous or might have a different exact spelling, try web_search.

CRITICAL: Your entire response must be ONLY a raw JSON object. No prose, no markdown, no code fences.
Start your response with { and end with }. The shape must be exactly:
{"valid": true|false, "explanation": "brief reason", "confidence": "high", "movie_id": int|null, "movie_title": "str|null", "movie_year": "str|null", "poster_url": "str|null", "backdrop_url": "str|null", "from_actor_found": true|false, "to_actor_found": true|false}"""


def _extract_json(text: str) -> dict | None:
    """Extract the first valid JSON object from a string, tolerating surrounding prose."""
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    cleaned = re.sub(r"```(?:json)?", "", text).strip().strip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


@traceable(run_type="tool", name="tmdb_prefetch")
async def _prefetch_movie_context(tmdb: TMDbClient, movie_title: str) -> dict | None:
    """Pre-fetch movie metadata and cast from TMDb. Fast when cached."""
    movie = await tmdb.search_movie(movie_title)
    if not movie:
        return None
    cast = await tmdb.get_movie_cast(movie.id)
    return {"movie": movie, "cast": cast}


@traceable(run_type="chain", name="fast_path_validation")
async def _validate_fast_path(
    from_actor: str,
    movie_title: str,
    to_actor: str,
    context: dict,
) -> ValidationResult | None:
    """One-shot validation using pre-fetched context. No tool calls needed.

    When reusable-llm-provider is integrated, replace _call_llm_once + manual
    parsing with: provider.invoke_json(prompt, ValidationResult)
    """
    movie = context["movie"]
    cast = context["cast"]
    cast_names = ", ".join(c.name for c in cast[:60])

    prompt = (
        f"Movie: {movie.title} ({movie.year})\n"
        f"TMDb cast: {cast_names}\n\n"
        f"Verify: does this cast include both '{from_actor}' and '{to_actor}'?\n"
        f"Return only the raw JSON object."
    )

    response = _call_llm_once(
        [{"role": "user", "content": prompt}],
        FAST_PATH_SYSTEM,
    )

    raw = next((b.text for b in response.content if b.type == "text"), "")
    parsed = _extract_json(raw)

    if not parsed:
        with trace(name="parse_error", run_type="tool", inputs={"raw": raw}) as t:
            t.error = "Fast path: could not extract JSON from response"
        return None

    parsed.setdefault("movie_id", movie.id)
    parsed.setdefault("movie_title", movie.title)
    parsed.setdefault("movie_year", movie.year)
    # Always use TMDb ground-truth URLs — Claude returns null for these
    # because they aren't in the prompt, so setdefault() would never fire.
    parsed["poster_url"] = movie.poster_url
    parsed["backdrop_url"] = movie.backdrop_url

    try:
        return ValidationResult.model_validate(parsed)
    except Exception:
        with trace(
            name="parse_error", run_type="tool", inputs={"raw": raw, "parsed": parsed}
        ) as t:
            t.error = "Fast path: ValidationResult schema validation failed"
        return None


@traceable(run_type="chain", name="fallback_validation")
async def _validate_fallback(
    tmdb: TMDbClient, from_actor: str, movie_title: str, to_actor: str
) -> ValidationResult:
    """Full agentic loop fallback — handles typos, ambiguous titles, web search."""
    user_message = (
        f"Verify this movie connection:\n"
        f"- Actor 1 (current): {from_actor}\n"
        f"- Movie: {movie_title}\n"
        f"- Actor 2 (proposed): {to_actor}\n\n"
        f"The player may have made minor typos or misspellings. Do your best to "
        f"find the intended movie and actors using fuzzy search. If the exact title "
        f"isn't found, try common alternative spellings or use web_search.\n\n"
        f"Steps:\n"
        f"1. Search for '{movie_title}' using search_movie. If not found, try web_search.\n"
        f"2. Get the cast using get_movie_cast.\n"
        f"3. Check whether '{from_actor}' AND '{to_actor}' appear (approximately) in the cast.\n"
        f"Return only the raw JSON object, nothing else."
    )

    raw = await run_agent(tmdb, FALLBACK_SYSTEM, user_message, ALL_TOOLS)

    parsed = _extract_json(raw)
    if parsed:
        try:
            return ValidationResult.model_validate(parsed)
        except Exception:
            logger.warning(
                "Fallback ValidationResult failed schema validation. Parsed: %r", parsed
            )
            with trace(
                name="parse_error",
                run_type="tool",
                inputs={"raw": raw, "parsed": parsed},
            ) as t:
                t.error = "Fallback: ValidationResult schema validation failed"

    logger.warning("Fallback could not parse validation result. Raw: %r", raw)
    with trace(name="parse_error", run_type="tool", inputs={"raw": raw}) as t:
        t.error = "Fallback: could not extract JSON from agent response"
    return ValidationResult(
        valid=False,
        explanation="Could not parse validation result. Please try again.",
        confidence=Confidence.high,
    )


@traceable(run_type="chain", name="validate_move")
async def validate_move(
    tmdb: TMDbClient, from_actor: str, movie_title: str, to_actor: str
) -> ValidationResult:
    """
    Verify that from_actor and to_actor both appeared in movie_title.

    Fast path: pre-fetch TMDb data, one Claude call, no tool use.
    Falls back to full agentic loop when confidence is low or pre-fetch fails.
    Strike is only counted by the caller if the final result is invalid.
    """
    context = await _prefetch_movie_context(tmdb, movie_title)

    if context is not None:
        result = await _validate_fast_path(from_actor, movie_title, to_actor, context)
        if result is not None and result.confidence != Confidence.low:
            return result

    result = await _validate_fallback(tmdb, from_actor, movie_title, to_actor)

    # Fallback agents don't reliably copy poster URLs from tool results.
    # If we have a movie_id but no poster, do one cheap TMDb lookup.
    if result.movie_id and not result.poster_url:
        movie = await tmdb.search_movie(result.movie_title or movie_title)
        if movie:
            result = result.model_copy(
                update={
                    "poster_url": movie.poster_url,
                    "backdrop_url": movie.backdrop_url,
                }
            )

    return result
