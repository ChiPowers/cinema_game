# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    POETRY_VERSION=2.3.4 \
    TMDB_CACHE_DISABLE=true \
    DB_PATH=/data/cinema_game.db

WORKDIR /app

# git is required for poetry to install the art-graph and
# reusable-llm-provider dependencies, which are pinned to GitHub tags
# rather than published to PyPI.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && pip install "poetry==${POETRY_VERSION}"

# Install dependencies before copying source, so this layer is cached
# across source-only changes.
COPY pyproject.toml poetry.lock README.md ./
RUN poetry install --only main --no-root

COPY cinema_game_backend ./cinema_game_backend
RUN poetry install --only main

RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app

# DB_PATH points here rather than the app code directory so a volume can be
# mounted at /data alone (see docker-compose.yml) without shadowing the
# application code on every `docker compose up` — mounting a volume over
# /app itself would pin the container to whatever code existed the first
# time the volume was created, defeating rebuilds. This is what lets game
# state and the beta_users table survive `docker compose down`/`up`/`--build`
# instead of resetting every run.
RUN mkdir -p /data && chown appuser:appuser /data

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "cinema_game_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
