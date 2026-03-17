import sqlite3
import pytest
from unittest.mock import patch
from database import init_db, save_game, load_game, update_game


def _make_game(game_id="test-123"):
    return {
        "id": game_id,
        "start_actor": {"name": "Brad Pitt", "id": 287},
        "end_actor": {"name": "Colin Firth", "id": 1891},
        "difficulty": "medium",
        "known_solution": [
            {"type": "actor", "name": "Brad Pitt", "id": 287},
            {"type": "movie", "title": "12 Years a Slave", "id": 76203},
            {"type": "actor", "name": "Michael Fassbender", "id": 17288},
        ],
        "moves": [],
        "current_actor": {"name": "Brad Pitt", "id": 287},
        "status": "in_progress",
    }


class _NoCloseConnection:
    """Wraps a sqlite3.Connection so that .close() is a no-op."""

    def __init__(self, conn):
        self._conn = conn

    def close(self):
        pass  # prevent database.py from closing the shared connection

    def __getattr__(self, name):
        return getattr(self._conn, name)


@pytest.fixture(autouse=True)
def use_in_memory_db():
    """Use a shared named in-memory SQLite DB for each test."""
    conn = sqlite3.connect("file::memory:?cache=shared", uri=True)
    conn.row_factory = sqlite3.Row

    def make_wrapper():
        wrapper = _NoCloseConnection(conn)
        return wrapper

    with patch("database.get_db", side_effect=make_wrapper):
        init_db()
        yield
    conn.close()


class TestInitDb:
    def test_creates_games_table(self):
        from database import get_db

        conn = get_db()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='games'"
        )
        assert cursor.fetchone() is not None

    def test_idempotent(self):
        """Calling init_db twice doesn't raise."""
        init_db()


class TestSaveAndLoadGame:
    def test_save_and_load(self):
        game = _make_game()
        save_game(game)
        loaded = load_game("test-123")
        assert loaded is not None
        assert loaded["id"] == "test-123"
        assert loaded["start_actor"] == {"name": "Brad Pitt", "id": 287}
        assert loaded["end_actor"] == {"name": "Colin Firth", "id": 1891}
        assert loaded["difficulty"] == "medium"
        assert loaded["status"] == "in_progress"
        assert loaded["moves"] == []
        assert len(loaded["known_solution"]) == 3

    def test_load_nonexistent(self):
        assert load_game("does-not-exist") is None

    def test_known_solution_round_trips_as_list(self):
        game = _make_game()
        save_game(game)
        loaded = load_game("test-123")
        assert isinstance(loaded["known_solution"], list)
        assert loaded["known_solution"][1]["title"] == "12 Years a Slave"

    def test_created_at_populated(self):
        game = _make_game()
        save_game(game)
        loaded = load_game("test-123")
        assert loaded["created_at"] is not None


class TestUpdateGame:
    def test_update_moves_and_status(self):
        game = _make_game()
        save_game(game)

        new_moves = [
            {
                "from_actor": "Brad Pitt",
                "movie": "12 Years a Slave",
                "to_actor": "Michael Fassbender",
            }
        ]
        new_actor = {"name": "Michael Fassbender", "id": 17288}
        update_game("test-123", new_moves, new_actor, "in_progress")

        loaded = load_game("test-123")
        assert loaded["moves"] == new_moves
        assert loaded["current_actor"] == new_actor
        assert loaded["status"] == "in_progress"

    def test_update_to_won(self):
        game = _make_game()
        save_game(game)

        update_game("test-123", [], {"name": "Colin Firth", "id": 1891}, "won")

        loaded = load_game("test-123")
        assert loaded["status"] == "won"
        assert loaded["current_actor"]["name"] == "Colin Firth"

    def test_multiple_games_independent(self):
        save_game(_make_game("game-a"))
        save_game(_make_game("game-b"))

        update_game("game-a", [{"move": 1}], {"name": "X", "id": 1}, "won")

        a = load_game("game-a")
        b = load_game("game-b")
        assert a["status"] == "won"
        assert b["status"] == "in_progress"
