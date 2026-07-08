"""Shared pytest fixtures for functional tests.

These tests verify that validate_move works correctly against the real
TMDb API (and, when an llm fixture is passed, the real Anthropic API).
They require valid credentials in secrets/.env.

Functional tests are never run in CI — they require actual API credentials
and external service access.
"""

import asyncio
import pytest
from cinema_game_backend.env import load_cinema_game_env
from cinema_game_backend.config import create_tmdb_client
from cinema_game_backend.agents.validation_agent import validate_move

# Load credentials from secrets/.env
load_cinema_game_env()


@pytest.fixture(autouse=True)
async def throttle_between_tests():
    """Sleep between tests to avoid Anthropic 30k tokens/min rate limit."""
    yield
    await asyncio.sleep(3)


@pytest.fixture
def tmdb():
    """Provide a real TMDb client configured from secrets/.env."""
    return create_tmdb_client()


@pytest.fixture
def validate_move_fixture(tmdb):
    """Fixture to validate movie connections.

    Returns a wrapper that injects the tmdb client into validate_move.
    """

    async def _validate(from_actor, movie_title, to_actor, **kwargs):
        return await validate_move(tmdb, from_actor, movie_title, to_actor, **kwargs)

    return _validate
