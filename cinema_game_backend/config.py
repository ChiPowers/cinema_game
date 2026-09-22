import os
from importlib.util import find_spec

from art_graph.cinema_data_providers.cache.cached_client import CachedTMDbClient
from art_graph.cinema_data_providers.filters import MovieFilter
from art_graph.cinema_data_providers.tmdb.client import TMDbClient
from art_graph.cinema_data_providers.tmdb.config import TMDbConfig
from reusable_llm_provider.config import (
    create_anthropic_config,
    create_ollama_config,
    create_openai_config,
    create_vertex_config,
)
from reusable_llm_provider.providers import create_provider
from sqlalchemy import create_engine

from . import directories
from .env import load_cinema_game_env

load_cinema_game_env()

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")

NEXTAUTH_SECRET = os.getenv("NEXTAUTH_SECRET", "")
INTERNAL_SECRET = os.getenv("INTERNAL_SECRET", "")

# Comma-separated allowlist re-applied to the beta_users table on every
# startup, so a database that gets wiped (container rebuild, fresh volume,
# etc.) self-heals instead of silently locking everyone out.
BETA_SEED_EMAILS = [
    email.strip()
    for email in os.getenv("BETA_SEED_EMAILS", "").split(",")
    if email.strip()
]

TMDB_CACHE_PATH = os.getenv("TMDB_CACHE_PATH")
TMDB_CACHE_DISABLE = os.getenv("TMDB_CACHE_DISABLE", "").lower() == "true"

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


DB_PATH = os.getenv("DB_PATH", directories.base("cinema_game.db"))


# Extra name == LLM_PROVIDER value == Docker build-arg value, deliberately.
_CONFIG_FACTORIES = {
    "anthropic": create_anthropic_config,
    "openai": create_openai_config,
    "vertex": create_vertex_config,
    "ollama": create_ollama_config,
}

# Vertex authenticates via Application Default Credentials (the Cloud Run
# runtime service account), so it needs no key -- only a project and region.
# Ollama is local and needs nothing.
_REQUIRED_ENV = {
    "anthropic": ("ANTHROPIC_API_KEY",),
    "openai": ("OPENAI_API_KEY",),
    "vertex": ("VERTEX_PROJECT_ID", "VERTEX_LOCATION"),
    "ollama": (),
}

# Model names are provider-specific, so the variable is too. One global
# LLM_MODEL would let a Claude model name survive a switch to Vertex and fail
# at first call rather than at startup. Whether a model still EXISTS is not
# knowable locally -- only the provider knows -- but this makes the category
# error unrepresentable. Unset falls through to the library's DEFAULT_MODELS.
_MODEL_ENV = {
    "anthropic": "ANTHROPIC_MODEL",
    "openai": "OPENAI_MODEL",
    "vertex": "VERTEX_MODEL",
    "ollama": "OLLAMA_MODEL",
}

# One module per extra, checked with find_spec, which locates without
# executing. Importing the SDK costs ~773 ms and belongs off the cold-start
# path. Every extra ships a langchain package, so these are uniform top-level
# names -- no PEP 420 namespace ambiguity, which `google` would carry.
_BACKEND_MODULE = {
    "anthropic": "langchain_anthropic",
    "openai": "langchain_openai",
    "vertex": "langchain_google_genai",
    "ollama": "langchain_ollama",
}


def validate_llm_config() -> str:
    """Check everything knowable without importing a vendor SDK; return the name.

    Called from the application lifespan so a misconfigured deployment fails
    at rollout instead of serving games with nickname resolution silently
    disabled. Deliberately does NOT construct the provider: that costs ~773 ms
    of vendor import, and the LLM is a fallback most games never reach.

    Reads os.getenv at call time rather than using this module's constants,
    which are bound at import and cannot be monkeypatched by tests.
    """
    names = ", ".join(sorted(_CONFIG_FACTORIES))
    name = os.getenv("LLM_PROVIDER", "").strip().lower()
    if not name:
        raise RuntimeError(f"LLM_PROVIDER is not set. Set it to one of: {names}")

    if name not in _CONFIG_FACTORIES:
        raise RuntimeError(f"LLM_PROVIDER={name!r} is not one of: {names}")

    missing = [var for var in _REQUIRED_ENV[name] if not os.getenv(var)]
    if missing:
        raise RuntimeError(
            f"LLM_PROVIDER={name} requires {', '.join(missing)}, which is not set"
        )

    module = _BACKEND_MODULE[name]
    if find_spec(module) is None:
        raise RuntimeError(
            f"LLM_PROVIDER={name} but its backend is not installed "
            f"({module!r} not found). Install with --extras {name}."
        )

    return name


def create_llm_provider():
    """Construct the configured provider, or raise. Never returns None.

    Pays the vendor import, so it is called lazily on first use rather than
    at startup. Validation has already run in the lifespan by then; it runs
    again here because the functional tests call this directly.
    """
    name = validate_llm_config()
    config = _CONFIG_FACTORIES[name](model=os.getenv(_MODEL_ENV[name]) or None)
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

# When a title is shared by multiple films, validate_move walks TMDb search
# results in order looking for one whose cast contains both named actors,
# stopping at the first match. This caps how many candidates get walked so a
# pathological title can't trigger unbounded get_movie_cast calls (each a
# live TMDb request when caching is disabled).
MAX_MOVIE_SEARCH_CANDIDATES = 10

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
