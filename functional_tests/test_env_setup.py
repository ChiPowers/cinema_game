"""Functional tests for environment setup and configuration.

These tests verify that the secrets/.env file exists and contains the necessary
API keys for the backend to function.
"""

import os

from cinema_game_backend.directories import secrets
from cinema_game_backend.env import load_cinema_game_env


class TestEnvironmentSetup:
    """Test environment configuration and secrets."""

    def test_env_file_exists(self):
        """Test that .env file exists in secrets directory."""
        env_path = secrets(".env")
        assert os.path.exists(env_path), f".env file not found at {env_path}"

    def test_env_loads_without_error(self):
        """Test that .env file can be loaded without errors."""
        load_cinema_game_env()

    def test_selected_provider_credentials_present(self):
        """Test that the provider named by LLM_PROVIDER has its credentials."""
        load_cinema_game_env()
        from cinema_game_backend.config import _REQUIRED_ENV

        name = os.getenv("LLM_PROVIDER", "").strip().lower()
        assert name in _REQUIRED_ENV, (
            f"LLM_PROVIDER={name!r} is not a known provider; "
            f"expected one of {sorted(_REQUIRED_ENV)}"
        )
        for var in _REQUIRED_ENV[name]:
            value = os.getenv(var)
            assert value, f"{var} required for LLM_PROVIDER={name} but not set"

    def test_tmdb_api_key_present(self):
        """Test that TMDb API key is set."""
        load_cinema_game_env()
        api_key = os.getenv("TMDB_API_KEY")
        assert api_key is not None, "TMDB_API_KEY required but not set"
        assert len(api_key) > 0, "TMDB_API_KEY is empty"

    def test_llm_provider_can_be_created(self):
        """Test that the LLM provider can be constructed from real credentials."""
        from cinema_game_backend.config import create_llm_provider

        provider = create_llm_provider()
        assert provider is not None
