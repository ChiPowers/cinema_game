from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routes.game import router as game_router

app = FastAPI(title="Cinema Game API", version="2.0.0")

import os

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


@app.on_event("startup")
def startup():
    init_db()


app.include_router(game_router)


@app.get("/health")
def health():
    return {"status": "ok"}
