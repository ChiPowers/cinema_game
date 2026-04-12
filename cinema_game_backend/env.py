"""Environment variable loading for cinema_game_backend.

Loads environment variables from secrets/.env file.
"""

from dotenv import load_dotenv, find_dotenv

from .directories import secrets


def find_cinema_game_env():
    """Find the .env file in the secrets directory."""
    return find_dotenv(secrets(".env"))


def load_cinema_game_env():
    """Load environment variables from secrets/.env."""
    _ = load_dotenv(find_cinema_game_env())
