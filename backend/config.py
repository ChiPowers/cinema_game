import os
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
TMDB_BACKDROP_BASE = "https://image.tmdb.org/t/p/w1280"

MODEL = "claude-sonnet-4-6"
DB_PATH = "cinema_game.db"

DIFFICULTY_HOPS = {
    "easy": 1,
    "medium": 2,
    "hard": 3,
}

# Minimum TMDb popularity score for actors selected in puzzles.
# TMDb popularity is a daily trending score — even major stars typically score 5–20.
MIN_ACTOR_POPULARITY = {
    "easy": 8,
    "medium": 4,
    "hard": 1,
}
