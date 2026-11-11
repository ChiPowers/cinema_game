import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from cinema_game_backend.database import (
    _normalise_url,
    init_db,
    metadata,
    set_engine,
)


@pytest.fixture(autouse=True)
def db_engine():
    """A clean, empty-schema database per test, never the real one.

    In-memory SQLite by default. Set TEST_DATABASE_URL to run the same suite
    against a real database (e.g. Postgres); it must be a dedicated, throwaway
    database because the app's tables are dropped before and after each test.
    """
    url = os.getenv("TEST_DATABASE_URL")
    app_url = os.getenv("DATABASE_URL")
    if url and app_url and _normalise_url(url) == _normalise_url(app_url):
        # This fixture drops the app's tables; never let it near the real data.
        pytest.exit(
            "TEST_DATABASE_URL must not be the app's DATABASE_URL: the test "
            "suite drops its tables.",
            returncode=2,
        )
    if url:
        engine = create_engine(_normalise_url(url))
    else:
        # StaticPool: one shared connection, so every checkout sees the same
        # in-memory database.
        engine = create_engine(
            "sqlite://",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
    set_engine(engine)
    metadata.drop_all(engine)
    init_db()
    yield engine
    metadata.drop_all(engine)
    set_engine(None)
    engine.dispose()


@pytest.fixture
def departed_cast():
    return [
        "Leonardo DiCaprio",
        "Matt Damon",
        "Jack Nicholson",
        "Mark Wahlberg",
        "Martin Sheen",
        "Ray Winstone",
        "Vera Farmiga",
        "Alec Baldwin",
    ]


@pytest.fixture
def apocalypse_now_cast():
    return [
        "Marlon Brando",
        "Martin Sheen",
        "Robert Duvall",
        "Frederic Forrest",
        "Sam Bottoms",
        "Laurence Fishburne",
        "Dennis Hopper",
    ]


@pytest.fixture
def toy_story_cast():
    return [
        "Tom Hanks",
        "Tim Allen",
        "Don Rickles",
        "Jim Varney",
        "Wallace Shawn",
        "John Ratzenberger",
        "Annie Potts",
    ]
