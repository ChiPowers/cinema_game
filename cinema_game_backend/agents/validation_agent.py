"""
Validation Agent: verifies that two actors both appeared in a named movie.
Uses Claude with TMDb tools + web search to handle name variations and ambiguity.

TODO: Abstract the LLM provider behind a testable interface (e.g. langchain)
so we can substitute other providers or run locally with Ollama.
"""

import json
import logging
import re
from langsmith import traceable
from .base import run_agent
from ..models.game import ValidationResult
from ..tools.definitions import ALL_TOOLS

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a movie trivia validator for a cinema connections game.

Your job is to verify whether two actors both appeared in a specific movie.
Be thorough but efficient. Use TMDb tools to look up the movie and its cast.
If a movie title is ambiguous or might have a different exact spelling, try web_search.

CRITICAL: Your entire response must be ONLY a raw JSON object. No prose, no markdown, no code fences.
Start your response with { and end with }. The shape must be exactly:
{"valid": true|false, "explanation": "brief reason", "movie_id": int|null, "movie_title": "str|null", "movie_year": "str|null", "poster_url": "str|null", "backdrop_url": "str|null", "from_actor_found": true|false, "to_actor_found": true|false}"""


def _extract_json(text: str) -> dict | None:
    """Extract the first valid JSON object from a string, tolerating surrounding prose."""
    # Try the full response first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Strip markdown fences and retry
    cleaned = re.sub(r"```(?:json)?", "", text).strip().strip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find the first {...} block in the text
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


@traceable(run_type="chain", name="validate_move")
async def validate_move(from_actor: str, movie_title: str, to_actor: str) -> ValidationResult:
    """
    Verify that from_actor and to_actor both appeared in movie_title.
    Tolerates typos and misspellings — the agent uses TMDb search + web search to resolve them.
    Returns a dict with validation result and movie metadata.
    """
    user_message = (
        f"Verify this movie connection:\n"
        f"- Actor 1 (current): {from_actor}\n"
        f"- Movie: {movie_title}\n"
        f"- Actor 2 (proposed): {to_actor}\n\n"
        f"Important: the player may have made minor typos or misspellings in the movie title or actor names. "
        f"Do your best to find the intended movie and actors using fuzzy search. "
        f"If the exact title isn't found, try common alternative spellings or use web_search to identify the correct title. "
        f"Similarly, match actor names approximately — a last name alone or a slight misspelling should still resolve correctly.\n\n"
        f"Steps:\n"
        f"1. Search for '{movie_title}' using search_movie. If not found, try web_search to identify the correct title.\n"
        f"2. Get the cast using get_movie_cast.\n"
        f"3. Check whether '{from_actor}' AND '{to_actor}' appear (approximately) in the cast.\n"
        f"Return only the raw JSON object, nothing else."
    )

    raw = await run_agent(SYSTEM_PROMPT, user_message, ALL_TOOLS)

    parsed = _extract_json(raw)
    if parsed:
        try:
            return ValidationResult.model_validate(parsed)
        except Exception:
            logger.warning("ValidationResult failed schema validation. Parsed: %r", parsed)

    logger.warning("Could not parse validation result. Raw agent response: %r", raw)
    return ValidationResult(
        valid=False,
        explanation="Could not parse validation result. Please try again.",
    )
