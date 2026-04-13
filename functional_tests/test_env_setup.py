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

    def test_anthropic_api_key_present(self):
        """Test that Anthropic API key is set."""
        load_cinema_game_env()
        api_key = os.getenv("ANTHROPIC_API_KEY")
        assert api_key is not None, "ANTHROPIC_API_KEY required but not set"
        assert len(api_key) > 0, "ANTHROPIC_API_KEY is empty"
        assert api_key.startswith("sk-ant-"), (
            "ANTHROPIC_API_KEY does not look like a valid Anthropic key "
            "(should start with 'sk-ant-')"
        )

    def test_tmdb_api_key_present(self):
        """Test that TMDb API key is set."""
        load_cinema_game_env()
        api_key = os.getenv("TMDB_API_KEY")
        assert api_key is not None, "TMDB_API_KEY required but not set"
        assert len(api_key) > 0, "TMDB_API_KEY is empty"

    def test_model_config(self):
        """Test that the model configuration can be imported."""
        from cinema_game_backend.config import MODEL

        assert MODEL is not None
        assert len(MODEL) > 0
        assert isinstance(MODEL, str)
