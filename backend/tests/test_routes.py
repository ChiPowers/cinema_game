import sqlite3
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from main import app
from database import init_db
from models.game import ValidationResult
from models.tmdb import TmdbPerson
from routes.game import _reached_end


# --- Pure logic: _reached_end ---


class TestReachedEnd:
    def test_match_by_id(self):
        assert (
            _reached_end(1891, "Colin Firth", {"name": "Colin Firth", "id": 1891})
            is True
        )

    def test_match_by_name_fallback(self):
        assert (
            _reached_end(0, "Colin Firth", {"name": "Colin Firth", "id": 1891}) is True
        )

    def test_case_insensitive_name(self):
        assert _reached_end(0, "colin firth", {"name": "Colin Firth", "id": 0}) is True

    def test_whitespace_stripped(self):
        assert (
            _reached_end(0, "  Colin Firth  ", {"name": "Colin Firth", "id": 0}) is True
        )

    def test_no_match(self):
        assert (
            _reached_end(287, "Brad Pitt", {"name": "Colin Firth", "id": 1891}) is False
        )

    def test_id_zero_falls_through_to_name(self):
        assert _reached_end(0, "Brad Pitt", {"name": "Colin Firth", "id": 0}) is False

    def test_different_id_same_name(self):
        """Name match wins even if IDs differ (one is 0)."""
        assert (
            _reached_end(0, "Colin Firth", {"name": "Colin Firth", "id": 1891}) is True
        )

    def test_same_id_different_name(self):
        """ID match wins regardless of name."""
        assert (
            _reached_end(1891, "Sir Colin Firth", {"name": "Colin Firth", "id": 1891})
            is True
        )


# --- FastAPI integration tests ---


class _NoCloseConnection:
    def __init__(self, conn):
        self._conn = conn

    def close(self):
        pass

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _mock_puzzle():
    return {
        "start_actor": {"name": "Brad Pitt", "id": 287, "profile_url": None},
        "end_actor": {"name": "Colin Firth", "id": 1891, "profile_url": None},
        "difficulty": "medium",
        "min_moves": 3,
        "known_solution": [
            {"type": "actor", "name": "Brad Pitt", "id": 287},
            {"type": "movie", "title": "12 Years a Slave", "id": 76203},
            {"type": "actor", "name": "Michael Fassbender", "id": 17288},
            {"type": "movie", "title": "X-Men: Apocalypse", "id": 246655},
            {"type": "actor", "name": "Nicholas Hoult", "id": 30614},
            {"type": "movie", "title": "A Single Man", "id": 24420},
            {"type": "actor", "name": "Colin Firth", "id": 1891},
        ],
    }


@pytest.fixture(autouse=True)
def use_in_memory_db():
    conn = sqlite3.connect(
        "file::memory:?cache=shared", uri=True, check_same_thread=False
    )
    conn.row_factory = sqlite3.Row

    def make_wrapper():
        return _NoCloseConnection(conn)

    with patch("database.get_db", side_effect=make_wrapper):
        init_db()
        yield
    conn.close()


@pytest.fixture
def client():
    return TestClient(app)


class TestNewGame:
    def test_creates_game(self, client):
        with patch(
            "routes.game.generate_puzzle",
            new_callable=AsyncMock,
            return_value=_mock_puzzle(),
        ):
            res = client.post("/game/new?difficulty=medium")

        assert res.status_code == 200
        data = res.json()
        assert "game_id" in data
        assert data["start_actor"]["name"] == "Brad Pitt"
        assert data["end_actor"]["name"] == "Colin Firth"
        assert data["difficulty"] == "medium"
        assert data["min_moves"] == 3

    def test_invalid_difficulty(self, client):
        res = client.post("/game/new?difficulty=impossible")
        assert res.status_code == 400

    def test_default_difficulty(self, client):
        with patch(
            "routes.game.generate_puzzle",
            new_callable=AsyncMock,
            return_value=_mock_puzzle(),
        ):
            res = client.post("/game/new")

        assert res.status_code == 200
        assert res.json()["difficulty"] == "medium"


class TestGetGame:
    def test_get_existing_game(self, client):
        with patch(
            "routes.game.generate_puzzle",
            new_callable=AsyncMock,
            return_value=_mock_puzzle(),
        ):
            create_res = client.post("/game/new?difficulty=medium")
        game_id = create_res.json()["game_id"]

        res = client.get(f"/game/{game_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == game_id
        assert data["status"] == "in_progress"
        assert data["moves"] == []
        assert data["current_actor"]["name"] == "Brad Pitt"

    def test_get_nonexistent_game(self, client):
        res = client.get("/game/does-not-exist")
        assert res.status_code == 404


class TestMakeMove:
    def _create_game(self, client):
        with patch(
            "routes.game.generate_puzzle",
            new_callable=AsyncMock,
            return_value=_mock_puzzle(),
        ):
            res = client.post("/game/new?difficulty=medium")
        return res.json()["game_id"]

    def test_valid_move(self, client):
        game_id = self._create_game(client)

        mock_validation = ValidationResult(
            valid=True,
            explanation="Both actors appear in 12 Years a Slave.",
            movie_id=76203,
            movie_title="12 Years a Slave",
            movie_year="2013",
        )
        mock_person = TmdbPerson(name="Michael Fassbender", id=17288)

        with (
            patch(
                "routes.game.validate_move",
                new_callable=AsyncMock,
                return_value=mock_validation,
            ),
            patch(
                "routes.game.tmdb.search_person",
                new_callable=AsyncMock,
                return_value=mock_person,
            ),
        ):
            res = client.post(
                f"/game/{game_id}/move",
                json={"movie": "12 Years a Slave", "next_actor": "Michael Fassbender"},
            )

        assert res.status_code == 200
        data = res.json()
        assert data["valid"] is True
        assert data["game_status"] == "in_progress"
        assert data["current_actor"]["name"] == "Michael Fassbender"
        assert data["movie_title"] == "12 Years a Slave"

    def test_invalid_move(self, client):
        game_id = self._create_game(client)

        mock_validation = ValidationResult(
            valid=False,
            explanation="Actor not found in cast.",
        )

        with patch(
            "routes.game.validate_move",
            new_callable=AsyncMock,
            return_value=mock_validation,
        ):
            res = client.post(
                f"/game/{game_id}/move",
                json={"movie": "The Matrix", "next_actor": "Brad Pitt"},
            )

        assert res.status_code == 200
        data = res.json()
        assert data["valid"] is False
        assert data["game_status"] == "in_progress"
        assert data["current_actor"]["name"] == "Brad Pitt"  # unchanged

    def test_winning_move(self, client):
        game_id = self._create_game(client)

        mock_validation = ValidationResult(
            valid=True,
            explanation="Correct!",
            movie_id=24420,
            movie_title="A Single Man",
            movie_year="2009",
        )
        mock_person = TmdbPerson(name="Colin Firth", id=1891)

        with (
            patch(
                "routes.game.validate_move",
                new_callable=AsyncMock,
                return_value=mock_validation,
            ),
            patch(
                "routes.game.tmdb.search_person",
                new_callable=AsyncMock,
                return_value=mock_person,
            ),
        ):
            res = client.post(
                f"/game/{game_id}/move",
                json={"movie": "A Single Man", "next_actor": "Colin Firth"},
            )

        assert res.status_code == 200
        data = res.json()
        assert data["valid"] is True
        assert data["game_status"] == "won"

    def test_move_on_nonexistent_game(self, client):
        res = client.post(
            "/game/does-not-exist/move",
            json={"movie": "Test", "next_actor": "Test"},
        )
        assert res.status_code == 404

    def test_move_on_finished_game(self, client):
        game_id = self._create_game(client)

        # Win the game first
        mock_validation = ValidationResult(
            valid=True,
            explanation="Correct!",
            movie_id=1,
            movie_title="T",
            movie_year="2000",
        )
        mock_person = TmdbPerson(name="Colin Firth", id=1891)

        with (
            patch(
                "routes.game.validate_move",
                new_callable=AsyncMock,
                return_value=mock_validation,
            ),
            patch(
                "routes.game.tmdb.search_person",
                new_callable=AsyncMock,
                return_value=mock_person,
            ),
        ):
            client.post(
                f"/game/{game_id}/move",
                json={"movie": "X", "next_actor": "Colin Firth"},
            )

        # Try another move
        res = client.post(
            f"/game/{game_id}/move", json={"movie": "Y", "next_actor": "Z"}
        )
        assert res.status_code == 400

    def test_move_missing_fields(self, client):
        game_id = self._create_game(client)
        res = client.post(f"/game/{game_id}/move", json={"movie": "Test"})
        assert res.status_code == 422


class TestHealthEndpoint:
    def test_health(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}
