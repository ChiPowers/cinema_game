"""Shared pytest fixtures for functional tests.

These tests verify that the agentic loop works correctly against the real
Anthropic API, TMDb API, and other external services. They require valid
credentials in secrets/.env.

Functional tests are never run in CI — they require actual API credentials
and external service access.
"""

import asyncio
import pytest
from cinema_game_backend.env import load_cinema_game_env
from cinema_game_backend.config import create_tmdb_client
from cinema_game_backend.agents.base import run_agent
from cinema_game_backend.agents.validation_agent import validate_move
from cinema_game_backend.tools.definitions import ALL_TOOLS

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
def tmdb_tools():
    """Provide the TMDb tool definitions for agent use."""
    return ALL_TOOLS


@pytest.fixture
def run_agentic_loop(tmdb):
    """Fixture to run the agentic loop with clean environment.

    Returns a wrapper that injects the tmdb client into run_agent.
    """

    async def _run(system, user_message, tools, max_iterations=10):
        return await run_agent(tmdb, system, user_message, tools, max_iterations)

    return _run


@pytest.fixture
def validate_move_fixture(tmdb):
    """Fixture to validate movie connections.

    Returns a wrapper that injects the tmdb client into validate_move.
    """

    async def _validate(from_actor, movie_title, to_actor, **kwargs):
        return await validate_move(tmdb, from_actor, movie_title, to_actor, **kwargs)

    return _validate
