"""Shared pytest fixtures for functional tests.

These tests verify that the agentic loop works correctly against the real
Anthropic API, TMDb API, and other external services. They require valid
credentials in secrets/.env.

Functional tests are never run in CI — they require actual API credentials
and external service access.
"""

import pytest
from cinema_game_backend.env import load_cinema_game_env
from cinema_game_backend.agents.base import run_agent
from cinema_game_backend.agents.validation_agent import validate_move
from cinema_game_backend.tools.definitions import ALL_TOOLS

# Load credentials from secrets/.env
load_cinema_game_env()


@pytest.fixture
def tmdb_tools():
    """Provide the TMDb tool definitions for agent use."""
    return ALL_TOOLS


@pytest.fixture
def run_agentic_loop():
    """Fixture to run the agentic loop with clean environment.

    Returns the run_agent function, allowing tests to call it directly
    with custom system prompts and messages.
    """
    return run_agent


@pytest.fixture
def validate_move_fixture():
    """Fixture to validate movie connections.

    Returns the validate_move async function for testing the validation agent.
    """
    return validate_move
