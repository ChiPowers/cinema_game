import os
from types import SimpleNamespace

import pytest

from cinema_game_backend.config import (
    DIFFICULTY_HOPS,
    MIN_ACTOR_POPULARITY,
    validate_llm_config,
)


class TestDifficultyHops:
    def test_all_levels_present(self):
        assert set(DIFFICULTY_HOPS.keys()) == {"easy", "medium", "hard"}

    def test_values_are_tuples_of_two_ints(self):
        for level, (lo, hi) in DIFFICULTY_HOPS.items():
            assert isinstance(lo, int), f"{level} low bound is not int"
            assert isinstance(hi, int), f"{level} high bound is not int"

    def test_low_bound_le_high_bound(self):
        for level, (lo, hi) in DIFFICULTY_HOPS.items():
            assert lo <= hi, f"{level}: {lo} > {hi}"

    def test_difficulty_ordering(self):
        assert DIFFICULTY_HOPS["easy"][1] < DIFFICULTY_HOPS["medium"][1]
        assert DIFFICULTY_HOPS["medium"][1] < DIFFICULTY_HOPS["hard"][1]


class TestMinActorPopularity:
    def test_all_levels_present(self):
        assert set(MIN_ACTOR_POPULARITY.keys()) == {"easy", "medium", "hard"}

    def test_values_are_positive(self):
        for level, pop in MIN_ACTOR_POPULARITY.items():
            assert pop > 0, f"{level} popularity is not positive"

    def test_easy_has_highest_floor(self):
        assert MIN_ACTOR_POPULARITY["easy"] > MIN_ACTOR_POPULARITY["medium"]
        assert MIN_ACTOR_POPULARITY["medium"] > MIN_ACTOR_POPULARITY["hard"]


class TestValidateLLMConfig:
    def test_unset_provider_raises(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        with pytest.raises(RuntimeError, match="LLM_PROVIDER"):
            validate_llm_config()

    def test_unknown_provider_raises(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "gpt5")
        with pytest.raises(RuntimeError, match="gpt5"):
            validate_llm_config()

    def test_missing_credentials_raise(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            validate_llm_config()

    def test_vertex_requires_project_and_location(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "vertex")
        monkeypatch.delenv("VERTEX_PROJECT_ID", raising=False)
        monkeypatch.setenv("VERTEX_LOCATION", "us-central1")
        with pytest.raises(RuntimeError, match="VERTEX_PROJECT_ID"):
            validate_llm_config()

    def test_missing_backend_extra_raises(self, monkeypatch):
        """A provider whose extra is not installed must fail at startup."""
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.setattr("cinema_game_backend.config.find_spec", lambda name: None)
        with pytest.raises(RuntimeError, match="ollama"):
            validate_llm_config()

    def test_provider_name_is_case_insensitive(self, monkeypatch):
        # find_spec is monkeypatched here (rather than left to the real
        # importlib) because CI installs this package with no extras, so
        # langchain_anthropic is genuinely absent there. Without this, the
        # test passes only on a machine with the anthropic extra installed
        # and fails in CI -- exactly the local/CI drift this task removes.
        monkeypatch.setenv("LLM_PROVIDER", "ANTHROPIC")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "placeholder")
        monkeypatch.setattr(
            "cinema_game_backend.config.find_spec", lambda name: object()
        )
        assert validate_llm_config() == "anthropic"

    def test_validation_imports_no_vendor_sdk(self, monkeypatch):
        """Validation must stay off the 773 ms vendor-import path."""
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "placeholder")
        called = []
        monkeypatch.setattr(
            "cinema_game_backend.config.find_spec",
            lambda name: called.append(name) or object(),
        )
        validate_llm_config()
        assert called == ["langchain_anthropic"]


class TestCreateTmdbClient:
    def test_cache_path_is_used_verbatim(self, monkeypatch, tmp_path):
        # Formatted into "sqlite:///...", a "?" starts a query string, so the
        # path is cut short there and a different file is opened.
        from cinema_game_backend import config

        cache_path = tmp_path / "tmdb?v=1.db"
        monkeypatch.setattr(config, "TMDB_CACHE_DISABLE", False)
        monkeypatch.setattr(config, "TMDB_CACHE_PATH", str(cache_path))

        config.create_tmdb_client()

        assert cache_path.exists()
        assert [p.name for p in tmp_path.iterdir()] == [cache_path.name]

    def test_cache_url_sqlite(self, monkeypatch, tmp_path):
        from cinema_game_backend import config

        db = tmp_path / "cache.db"
        monkeypatch.setattr(config, "TMDB_CACHE_DISABLE", False)
        monkeypatch.setattr(config, "TMDB_CACHE_PATH", None)
        monkeypatch.setattr(config, "TMDB_CACHE_URL", f"sqlite:///{db}")

        config.create_tmdb_client()

        assert db.exists()

    def test_cache_url_wins_over_path_and_fixes_postgres_scheme(self, monkeypatch):
        from cinema_game_backend import config

        seen = []
        monkeypatch.setattr(config, "TMDB_CACHE_DISABLE", False)
        monkeypatch.setattr(config, "TMDB_CACHE_PATH", "/ignored.db")
        monkeypatch.setattr(config, "TMDB_CACHE_URL", "postgres://u:p@h/db")
        fake_engine = SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))
        monkeypatch.setattr(
            config, "create_engine", lambda url, **kw: seen.append(url) or fake_engine
        )
        monkeypatch.setattr(
            config, "CachedTMDbClient", lambda cfg, engine: ("client", engine)
        )

        assert config.create_tmdb_client() == ("client", fake_engine)
        assert seen == ["postgresql+psycopg://u:p@h/db"]

    def test_both_set_warns_that_path_is_ignored(self, monkeypatch, caplog, tmp_path):
        from cinema_game_backend import config

        monkeypatch.setattr(config, "TMDB_CACHE_DISABLE", False)
        monkeypatch.setattr(config, "TMDB_CACHE_PATH", str(tmp_path / "old.db"))
        monkeypatch.setattr(config, "TMDB_CACHE_URL", f"sqlite:///{tmp_path}/new.db")

        with caplog.at_level("WARNING"):
            config.create_tmdb_client()

        assert "ignoring TMDB_CACHE_PATH" in caplog.text
        assert (tmp_path / "new.db").exists()
        assert not (tmp_path / "old.db").exists()

    def test_blank_cache_url_env_falls_back_to_path(self, monkeypatch):
        import importlib

        from cinema_game_backend import config

        monkeypatch.setenv("TMDB_CACHE_URL", "   ")
        try:
            importlib.reload(config)
            assert config.TMDB_CACHE_URL is None
        finally:
            monkeypatch.delenv("TMDB_CACHE_URL")
            importlib.reload(config)


_needs_postgres = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL", "").startswith("postgres"),
    reason="needs a real Postgres in TEST_DATABASE_URL",
)


@pytest.fixture
def postgres_cache_url(monkeypatch):
    """TEST_DATABASE_URL as the cache URL; refuses to touch a real cache."""
    from cinema_game_backend import config

    url = os.environ["TEST_DATABASE_URL"]
    real = os.getenv("TMDB_CACHE_URL", "").strip()
    if real and config.normalise_db_url(real) == config.normalise_db_url(url):
        # These tests drop the cache tables; never let them near real data.
        pytest.exit(
            "TEST_DATABASE_URL must not be the TMDB_CACHE_URL: the test suite "
            "drops the cache tables.",
            returncode=2,
        )
    monkeypatch.setattr(config, "TMDB_CACHE_DISABLE", False)
    monkeypatch.setattr(config, "TMDB_CACHE_PATH", None)
    monkeypatch.setattr(config, "TMDB_CACHE_URL", url)
    return url


@_needs_postgres
def test_concurrent_cache_init_is_safe(postgres_cache_url):
    """Instances starting together must not collide on the cache's DDL."""
    from concurrent.futures import ThreadPoolExecutor

    from art_graph.cinema_data_providers.cache.orm_models import Base
    from sqlalchemy import create_engine, inspect

    from cinema_game_backend import config

    engine = create_engine(config.normalise_db_url(postgres_cache_url))
    Base.metadata.drop_all(engine)

    def run(_):
        # Each "instance" builds its own engine, as separate processes would.
        config.create_tmdb_client().engine.dispose()

    try:
        with ThreadPoolExecutor(8) as pool:
            list(pool.map(run, range(8)))  # re-raises any worker failure
        assert {"person", "movie", "credit"} <= set(inspect(engine).get_table_names())
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@_needs_postgres
def test_cache_url_round_trips_on_postgres(postgres_cache_url):
    """TMDB_CACHE_URL alone points the cache at Postgres: schema + cache hit."""
    import asyncio
    import datetime

    from art_graph.cinema_data_providers.cache.operations import store_person_movies
    from art_graph.cinema_data_providers.cache.orm_models import Base
    from art_graph.cinema_data_providers.tmdb_models import MovieCreditRole, Person
    from sqlalchemy import inspect
    from sqlalchemy.orm import Session

    from cinema_game_backend import config

    client = config.create_tmdb_client()
    try:
        assert client.engine.dialect.name == "postgresql"
        assert {"person", "movie", "credit"} <= set(
            inspect(client.engine).get_table_names()
        )

        person = Person(id=1, name="Test Actor", popularity=9.0)
        movies = [
            MovieCreditRole(
                id=10,
                title="Test Movie",
                popularity=5.0,
                character="Lead",
                order=0,
                release_date=datetime.date(2000, 1, 1),
            )
        ]
        with Session(bind=client.engine) as session:
            store_person_movies(session, person, movies)
            session.commit()

        # trust_cache=True returns from the database without calling TMDb, so
        # this has no network dependency (and no API key) to pass.
        cached = asyncio.run(client.get_person_movies(1, trust_cache=True))
        assert [m.title for m in cached] == ["Test Movie"]
    finally:
        # Only the cache's own tables; the app tables belong to db_engine.
        Base.metadata.drop_all(client.engine)
        client.engine.dispose()
