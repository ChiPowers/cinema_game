"""Tests for require_auth.

These establish a behavioral baseline against the current JWT library
before swapping it out (see the Minerva/python-ecdsa timing-attack
remediation), so the swap can be verified to preserve behavior exactly.
"""

import time
import jwt
import pytest
from fastapi import HTTPException

from cinema_game_backend.dependencies import require_auth

SECRET = "test-secret-that-is-long-enough-for-hs256"


def _make_token(secret=SECRET, algorithm="HS256", **claims):
    return jwt.encode(claims, secret, algorithm=algorithm)


@pytest.fixture(autouse=True)
def configured_secret(monkeypatch):
    monkeypatch.setattr("cinema_game_backend.dependencies.NEXTAUTH_SECRET", SECRET)


class TestRequireAuth:
    async def test_valid_token_returns_claims(self):
        token = _make_token(email="user@example.com", sub="123")
        payload = await require_auth(authorization=f"Bearer {token}")
        assert payload["email"] == "user@example.com"
        assert payload["sub"] == "123"

    async def test_missing_bearer_prefix_rejected(self):
        token = _make_token(email="user@example.com")
        with pytest.raises(HTTPException) as exc_info:
            await require_auth(authorization=token)
        assert exc_info.value.status_code == 401

    async def test_wrong_secret_rejected(self):
        token = _make_token(
            secret="a-completely-different-secret-value-here", email="user@example.com"
        )
        with pytest.raises(HTTPException) as exc_info:
            await require_auth(authorization=f"Bearer {token}")
        assert exc_info.value.status_code == 401

    async def test_expired_token_rejected(self):
        token = _make_token(email="user@example.com", exp=int(time.time()) - 3600)
        with pytest.raises(HTTPException) as exc_info:
            await require_auth(authorization=f"Bearer {token}")
        assert exc_info.value.status_code == 401

    async def test_malformed_token_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            await require_auth(authorization="Bearer not-a-real-token")
        assert exc_info.value.status_code == 401

    async def test_missing_secret_returns_500(self, monkeypatch):
        monkeypatch.setattr("cinema_game_backend.dependencies.NEXTAUTH_SECRET", "")
        token = _make_token(email="user@example.com")
        with pytest.raises(HTTPException) as exc_info:
            await require_auth(authorization=f"Bearer {token}")
        assert exc_info.value.status_code == 500
