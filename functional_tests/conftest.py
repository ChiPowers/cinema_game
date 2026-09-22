"""Shared pytest fixtures for functional tests.

These tests verify that validate_move works correctly against the real
TMDb API (and, when an llm fixture is passed, the provider named by
LLM_PROVIDER). They require valid credentials in secrets/.env.

Functional tests are never run in CI — they require actual API credentials
and external service access.
"""

import asyncio

import pytest

from cinema_game_backend.agents.validation_agent import validate_move
from cinema_game_backend.config import create_llm_provider, create_tmdb_client
from cinema_game_backend.env import load_cinema_game_env

# Load credentials from secrets/.env
load_cinema_game_env()


@pytest.fixture(autouse=True)
async def throttle_between_tests():
    """Sleep between tests to stay under the LLM provider's rate limit.

    Conservative and calibrated for Anthropic's 30k tokens/min limit; may be
    more throttling than other providers need.
    """
    yield
    await asyncio.sleep(3)


@pytest.fixture
def tmdb():
    """Provide a real TMDb client configured from secrets/.env."""
    return create_tmdb_client()


@pytest.fixture
def llm():
    """Provide the real LLM provider selected by LLM_PROVIDER.

    Raises rather than skipping. These tests exist to exercise a real
    provider; silently skipping them is how the suite came to pass against
    a dead key for months.
    """
    return create_llm_provider()


@pytest.fixture
def validate_move_fixture(tmdb):
    """Fixture to validate movie connections.

    Returns a wrapper that injects the tmdb client into validate_move. If
    from_actor_id isn't supplied, it's resolved via a real TMDb person
    search, mirroring how a real game establishes the anchor from a prior
    move.
    """

    async def _validate(
        from_actor, movie_title, to_actor, from_actor_id=None, **kwargs
    ):
        if from_actor_id is None:
            person = await tmdb.search_person(from_actor)
            from_actor_id = person.id if person else 0
        return await validate_move(
            tmdb,
            from_actor,
            movie_title,
            to_actor,
            from_actor_id=from_actor_id,
            **kwargs,
        )

    return _validate
