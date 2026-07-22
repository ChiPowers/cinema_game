import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import (
    create_tmdb_client,
    create_llm_provider,
    NEXTAUTH_SECRET,
    INTERNAL_SECRET,
    BETA_SEED_EMAILS,
)
from .database import init_db, seed_beta_users
from .routes.game import router as game_router
from .routes.auth import router as auth_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not NEXTAUTH_SECRET:
        raise RuntimeError(
            "NEXTAUTH_SECRET environment variable is required but not set"
        )
    if not INTERNAL_SECRET:
        raise RuntimeError(
            "INTERNAL_SECRET environment variable is required but not set"
        )
    init_db()
    seed_beta_users(BETA_SEED_EMAILS)
    app.state.tmdb = create_tmdb_client()
    app.state.llm = create_llm_provider()
    if app.state.llm is None:
        logger.warning(
            "No LLM provider configured — nickname resolution disabled. "
            "Set ANTHROPIC_API_KEY to enable LLM fallback for name matching."
        )
    yield


app = FastAPI(title="Cinema Game API", version="2.0.0", lifespan=lifespan)

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    os.getenv("FRONTEND_URL", ""),  # production Cloudflare URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in ALLOWED_ORIGINS if o],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(game_router)
app.include_router(auth_router)


@app.get("/health")
def health():
    return {"status": "ok"}
