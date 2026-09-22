"""Fuzzy name matching for player-typed actor names against TMDb cast lists."""

from dataclasses import dataclass

from rapidfuzz import fuzz, process
from rapidfuzz.distance import Levenshtein

_MIN_SCORE = 85


@dataclass
class ActorMatch:
    matched_name: str


def _normalize(name: str) -> str:
    """Lowercase and collapse whitespace."""
    return " ".join(name.lower().split())


def _effective_distance(query: str, candidate: str) -> int:
    """Minimum Levenshtein distance across multiple matching strategies.

    Tries full-string, last-name-only, and token-pair comparisons to handle
    partial names, last-name-only queries, and abbreviated first names.
    """
    d = Levenshtein.distance(query, candidate)

    q_parts = query.split()
    c_parts = candidate.split()

    # Single-token query: compare against candidate's last name
    if len(q_parts) == 1 and c_parts:
        d = min(d, Levenshtein.distance(query, c_parts[-1]))

    # Multi-token: compare first and last names separately
    if len(q_parts) >= 2 and len(c_parts) >= 2:
        last_d = Levenshtein.distance(q_parts[-1], c_parts[-1])
        first_d = Levenshtein.distance(q_parts[0], c_parts[0])
        # Prefix match on first name (e.g. "Leo" -> "Leonardo")
        if c_parts[0].startswith(q_parts[0]) or q_parts[0].startswith(c_parts[0]):
            first_d = 0
        d = min(d, last_d + first_d)

    return d


def find_actor_in_cast(
    query: str,
    cast_names: list[str],
    max_distance: int = 3,
) -> ActorMatch | None:
    """Find the best match for a player-typed actor name in a cast list.

    Uses Levenshtein distance as a gate to filter candidates, then
    rapidfuzz scoring to select the best match among those that pass.

    Returns None if no match is found within the threshold.
    """
    query_norm = _normalize(query)
    if not query_norm or not cast_names:
        return None

    # Exact match — skip fuzzy logic entirely
    for name in cast_names:
        if _normalize(name) == query_norm:
            return ActorMatch(matched_name=name)

    # Gate: only consider candidates within Levenshtein threshold
    candidates = []
    for name in cast_names:
        d = _effective_distance(query_norm, _normalize(name))
        if d <= max_distance:
            candidates.append(name)

    if not candidates:
        return None

    # Score surviving candidates with rapidfuzz
    normed_to_original = {_normalize(n): n for n in candidates}
    result = process.extractOne(
        query_norm,
        list(normed_to_original.keys()),
        scorer=fuzz.WRatio,
        score_cutoff=_MIN_SCORE,
    )

    if result is None:
        return None

    matched_norm = result[0]
    return ActorMatch(matched_name=normed_to_original[matched_norm])
