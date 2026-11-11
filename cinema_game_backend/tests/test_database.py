import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, inspect, text

from cinema_game_backend.database import (
    _format_timestamp,
    _normalise_url,
    add_beta_user,
    get_engine,
    init_db,
    is_beta_user,
    list_beta_users,
    list_games,
    load_game,
    metadata,
    remove_beta_user,
    save_game,
    seed_beta_users,
    update_game,
)


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


class TestInitDb:
    def test_creates_tables(self):
        tables = set(inspect(get_engine()).get_table_names())
        assert {"games", "beta_users"} <= tables

    def test_idempotent(self):
        """Calling init_db twice doesn't raise."""
        init_db()

    def test_adds_strikes_column_to_legacy_games_table(self):
        engine = get_engine()
        metadata.drop_all(engine)
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                CREATE TABLE games (
                    id TEXT PRIMARY KEY,
                    start_actor_name TEXT NOT NULL,
                    start_actor_id INTEGER NOT NULL,
                    end_actor_name TEXT NOT NULL,
                    end_actor_id INTEGER NOT NULL,
                    difficulty TEXT NOT NULL,
                    known_solution TEXT NOT NULL,
                    moves TEXT NOT NULL DEFAULT '[]',
                    current_actor_name TEXT NOT NULL,
                    current_actor_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'in_progress',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
                )
            )
            conn.execute(
                text(
                    "INSERT INTO games (id, start_actor_name, start_actor_id,"
                    " end_actor_name, end_actor_id, difficulty, known_solution,"
                    " current_actor_name, current_actor_id)"
                    " VALUES ('old', 'A', 1, 'B', 2, 'easy', '[]', 'A', 1)"
                )
            )
        init_db()
        assert load_game("old")["strikes"] == 0

    @pytest.mark.skipif(
        not os.getenv("TEST_DATABASE_URL", "").startswith("postgres"),
        reason="concurrent init is only a hazard on a server database",
    )
    def test_concurrent_init_db_is_safe(self):
        """Overlapping instances at deploy time must not collide on DDL."""
        engine = get_engine()
        metadata.drop_all(engine)

        def run(_):
            # Each "instance" has its own engine, as separate processes would.
            instance = create_engine(_normalise_url(os.environ["TEST_DATABASE_URL"]))
            try:
                init_db(instance)
            finally:
                instance.dispose()

        with ThreadPoolExecutor(8) as pool:
            list(pool.map(run, range(8)))  # re-raises any worker failure
        assert {"games", "beta_users"} <= set(inspect(engine).get_table_names())


class TestBetaUsers:
    def test_add_and_check(self):
        add_beta_user("A@Example.com")
        assert is_beta_user("a@example.com")
        assert is_beta_user("A@EXAMPLE.COM")

    def test_unknown_is_not_beta(self):
        assert not is_beta_user("nobody@example.com")

    def test_add_is_idempotent(self):
        add_beta_user("a@example.com")
        add_beta_user("a@example.com")
        assert list_beta_users() == ["a@example.com"]

    def test_seed_is_idempotent_and_keeps_existing(self):
        add_beta_user("a@example.com")
        seed_beta_users(["a@example.com", "b@example.com"])
        seed_beta_users(["b@example.com"])
        assert sorted(list_beta_users()) == ["a@example.com", "b@example.com"]

    def test_remove(self):
        add_beta_user("a@example.com")
        remove_beta_user("A@example.com")
        assert not is_beta_user("a@example.com")

    def test_remove_missing_is_noop(self):
        remove_beta_user("nobody@example.com")


class TestFormatTimestamp:
    def test_none(self):
        assert _format_timestamp(None) is None

    def test_naive_sqlite_value(self):
        assert _format_timestamp(datetime(2026, 11, 11, 12, 0, 0)) == (
            "2026-11-11 12:00:00"
        )

    def test_aware_postgres_value_is_utc_fixed_width(self):
        est = timezone(timedelta(hours=-5))
        value = datetime(2026, 11, 11, 7, 0, 0, 123456, tzinfo=est)
        assert _format_timestamp(value) == "2026-11-11 12:00:00"


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
        assert re.fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d", loaded["created_at"])

    def test_strikes_default_and_update(self):
        save_game(_make_game())
        assert load_game("test-123")["strikes"] == 0
        update_game("test-123", [], {"name": "Brad Pitt", "id": 287}, "in_progress", 2)
        assert load_game("test-123")["strikes"] == 2


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


class TestListGames:
    def test_empty_database(self):
        assert list_games() == []

    def test_returns_all_games(self):
        save_game(_make_game("game-a"))
        save_game(_make_game("game-b"))
        games = list_games()
        assert len(games) == 2

    def test_returns_games_with_correct_fields(self):
        save_game(_make_game("game-a"))
        games = list_games()
        assert games[0]["id"] == "game-a"
        assert games[0]["start_actor"]["name"] == "Brad Pitt"
        assert games[0]["difficulty"] == "medium"

    def test_limit(self):
        save_game(_make_game("game-a"))
        save_game(_make_game("game-b"))
        save_game(_make_game("game-c"))
        games = list_games(limit=2)
        assert len(games) == 2

    def test_limit_none_returns_all(self):
        save_game(_make_game("game-a"))
        save_game(_make_game("game-b"))
        save_game(_make_game("game-c"))
        games = list_games(limit=None)
        assert len(games) == 3


class TestAppDatabaseUrl:
    def test_sqlite_fallback_keeps_special_characters(self, monkeypatch):
        from cinema_game_backend import database

        monkeypatch.setattr(database, "DATABASE_URL", None)
        monkeypatch.setattr(database, "DB_PATH", "/data/a?b#c%41.db")
        url = database._app_database_url()
        assert url.drivername == "sqlite"
        assert url.database == "/data/a?b#c%41.db"

    def test_database_url_wins_and_pins_psycopg(self, monkeypatch):
        from cinema_game_backend import database

        monkeypatch.setattr(database, "DATABASE_URL", "postgres://u:p@h/db")
        assert database._app_database_url() == "postgresql+psycopg://u:p@h/db"
