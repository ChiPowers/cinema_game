import os

from sqlalchemy import create_engine

from art_graph.cinema_data_providers.cache.cached_client import CachedTMDbClient
from art_graph.cinema_data_providers.tmdb.client import TMDbClient
from art_graph.cinema_data_providers.tmdb.config import TMDbConfig

from .env import load_cinema_game_env

load_cinema_game_env()

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

TMDB_CACHE_PATH = os.getenv("TMDB_CACHE_PATH")
TMDB_CACHE_DISABLE = os.getenv("TMDB_CACHE_DISABLE", "").lower() == "true"

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
TMDB_BACKDROP_BASE = "https://image.tmdb.org/t/p/w1280"


def create_tmdb_client() -> TMDbClient:
    config = TMDbConfig(
        api_key=TMDB_API_KEY,
        image_base=TMDB_IMAGE_BASE,
        backdrop_base=TMDB_BACKDROP_BASE,
    )

    if TMDB_CACHE_DISABLE:
        return TMDbClient(config)
    elif TMDB_CACHE_PATH:
        engine = create_engine(f"sqlite:///{TMDB_CACHE_PATH}")
        return CachedTMDbClient(config, engine=engine)
    else:
        raise RuntimeError(
            "TMDB_CACHE_PATH must be set to a writable file path for the TMDb cache, "
            "or set TMDB_CACHE_DISABLE=true to run without caching."
        )


MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
DB_PATH = "cinema_game.db"

# Hops = number of actor→movie→actor steps.
# Easy: exactly 2 hops (no movie may repeat).
# Medium: 3–5 hops (random within range).
# Hard: 6–8 hops.
DIFFICULTY_HOPS = {
    "easy": (2, 2),
    "medium": (3, 5),
    "hard": (6, 8),
}

# Minimum TMDb popularity score for actors selected in puzzles.
# TMDb popularity is a daily trending score — even major stars typically score 5–20.
MIN_ACTOR_POPULARITY = {
    "easy": 8,
    "medium": 4,
    "hard": 1,
}
