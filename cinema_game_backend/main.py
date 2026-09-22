import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import (
    BETA_SEED_EMAILS,
    INTERNAL_SECRET,
    NEXTAUTH_SECRET,
    create_tmdb_client,
    validate_llm_config,
)
from .database import init_db, seed_beta_users
from .routes.auth import router as auth_router
from .routes.game import router as game_router


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
    # Raises if LLM_PROVIDER is unset, unknown, its credentials are missing,
    # or its backend is not installed. A container that cannot resolve
    # nicknames must not start. The provider itself is built on first use --
    # importing it costs ~773 ms, and the LLM is a fallback most games never
    # reach, so it does not belong on the cold-start path.
    validate_llm_config()
    app.state.llm = None
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
