import os

from sqlalchemy import create_engine

from art_graph.cinema_data_providers.cache.cached_client import CachedTMDbClient
from art_graph.cinema_data_providers.tmdb.client import TMDbClient
from art_graph.cinema_data_providers.tmdb.config import TMDbConfig
from art_graph.cinema_data_providers.filters import MovieFilter

from . import directories
from .env import load_cinema_game_env

load_cinema_game_env()

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

NEXTAUTH_SECRET = os.getenv("NEXTAUTH_SECRET", "")
INTERNAL_SECRET = os.getenv("INTERNAL_SECRET", "")

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


DB_PATH = directories.base("cinema_game.db")


def create_llm_provider():
    """Create an LLM provider for fallback name matching.

    Currently hardcoded to Anthropic. A follow-up PR will make the provider
    configurable via an environment variable (e.g. LLM_PROVIDER=openai).

    Returns None if ANTHROPIC_API_KEY is not set, in which case validation
    falls back to fuzzy string matching only.
    """
    if not ANTHROPIC_API_KEY:
        return None
    from reusable_llm_provider.config import create_anthropic_config
    from reusable_llm_provider.providers import create_provider

    model = os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001")
    config = create_anthropic_config(model=model)
    return create_provider(config)


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

# Movie quality filters per difficulty. vote_count is the strongest signal for
# whether a film is widely recognised (see docs/tmdb_fields.md in artist-graph).
MOVIE_FILTERS = {
    "easy": MovieFilter(
        allowed_languages={"en"},
        min_vote_average=5.5,
        min_vote_count=500,
        min_popularity=5.0,
        excluded_genre_ids={99, 10770},
    ),
    "medium": MovieFilter(
        allowed_languages={"en"},
        min_vote_average=4.0,
        min_vote_count=100,
        min_popularity=3.0,
        excluded_genre_ids={99, 10770},
    ),
    "hard": MovieFilter(
        allowed_languages={"en"},
        min_vote_average=0.0,
        min_vote_count=20,
        min_popularity=0.0,
        excluded_genre_ids={99, 10770},
    ),
}
