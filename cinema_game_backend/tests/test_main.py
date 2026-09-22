from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from cinema_game_backend.dependencies import get_llm
from cinema_game_backend.main import app


def test_startup_fails_when_provider_unconfigured(monkeypatch):
    """A misconfigured deployment must not boot.

    NEXTAUTH_SECRET and INTERNAL_SECRET are patched as module ATTRIBUTES, not
    as environment variables: config.py binds them to module constants at
    import time, so monkeypatch.setenv cannot reach them. Setting the
    environment instead passes locally, where secrets/.env happens to supply
    both at import, and fails in CI, where it does not -- the lifespan then
    raises about NEXTAUTH_SECRET before ever reaching the LLM_PROVIDER check
    this test is about.

    LLM_PROVIDER is different and correctly uses delenv: validate_llm_config
    reads it via os.getenv at call time, precisely so it stays testable.
    """
    monkeypatch.setattr("cinema_game_backend.main.NEXTAUTH_SECRET", "test-secret")
    monkeypatch.setattr("cinema_game_backend.main.INTERNAL_SECRET", "test-internal")
    # Everything the lifespan does BEFORE the LLM check is neutralised, so this
    # test asserts what it claims and nothing else. Each of these otherwise
    # reads real configuration -- a writable DB path, a TMDb cache setting --
    # which exists locally via secrets/.env and does not in CI, so leaving any
    # of them live makes the lifespan raise about that instead, and the test
    # fails on a message it was never about.
    monkeypatch.setattr("cinema_game_backend.main.init_db", lambda: None)
    monkeypatch.setattr("cinema_game_backend.main.seed_beta_users", lambda *_: None)
    monkeypatch.setattr("cinema_game_backend.main.create_tmdb_client", lambda: object())
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    with pytest.raises(RuntimeError, match="LLM_PROVIDER"):
        with TestClient(app):
            pass


def test_provider_is_built_on_first_use_and_cached():
    """Cold start must not pay the vendor import."""

    class FakeState:
        llm = None

    class FakeRequest:
        app = type("App", (), {"state": FakeState})()

    sentinel = object()
    request = FakeRequest()
    with patch(
        "cinema_game_backend.dependencies.create_llm_provider",
        return_value=sentinel,
    ) as create:
        assert get_llm(request) is sentinel
        assert get_llm(request) is sentinel
    assert create.call_count == 1
