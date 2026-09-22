from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from cinema_game_backend.dependencies import get_llm
from cinema_game_backend.main import app


def test_startup_fails_when_provider_unconfigured(monkeypatch):
    """A misconfigured deployment must not boot."""
    monkeypatch.setenv("NEXTAUTH_SECRET", "test-secret")
    monkeypatch.setenv("INTERNAL_SECRET", "test-internal")
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
