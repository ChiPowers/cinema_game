"""Fixtures for the concurrency tests.

These tests need no credentials and call no external service, so the parent
conftest's LLM rate-limit throttle is switched off here.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cinema_game_backend import database
from cinema_game_backend.dependencies import get_llm, get_tmdb, require_auth
from cinema_game_backend.main import app


@pytest.fixture(autouse=True)
async def throttle_between_tests():
    """Override the parent conftest's 3-second sleep between tests."""
    yield


@pytest.fixture(autouse=True)
def app_database(monkeypatch, tmp_path):
    """A real SQLite file, so the app opens its own connection on each call."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "cinema_game.db"))
    # A database layer that caches one engine per process (#109) would keep
    # the previous test's file; drop it so the next call builds one on DB_PATH.
    reset_engine = getattr(database, "set_engine", lambda engine: None)
    reset_engine(None)
    database.init_db()
    yield
    reset_engine(None)


@pytest.fixture(autouse=True)
def app_overrides():
    """No TMDb, no LLM, and a fixed signed-in user."""
    app.dependency_overrides[get_tmdb] = lambda: MagicMock()
    app.dependency_overrides[get_llm] = lambda: None
    app.dependency_overrides[require_auth] = lambda: {
        "sub": "test-user",
        "email": "test@example.com",
    }
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def game_id():
    """A saved game, created through the route as a real client would."""
    from fastapi.testclient import TestClient

    puzzle = {
        "start_actor": {"name": "Brad Pitt", "id": 287, "profile_url": None},
        "end_actor": {"name": "Colin Firth", "id": 1891, "profile_url": None},
        "difficulty": "easy",
        "min_moves": 1,
        "known_solution": [],
    }
    with patch(
        "cinema_game_backend.routes.game.generate_puzzle",
        new_callable=AsyncMock,
        return_value=puzzle,
    ):
        res = TestClient(app).post("/game/new?difficulty=easy")
    assert res.status_code == 200, res.text
    return res.json()["game_id"]
