# Cinema Game

Connect two actors through shared movies — one hop at a time.

Brad Pitt and Michael Fassbender were both in *12 Years a Slave*. Michael Fassbender and Nicholas Hoult were both in *X-Men: Apocalypse*. Nicholas Hoult and Colin Firth were both in *A Single Man*. That's a path of length 3 connecting Brad Pitt to Colin Firth.

Can you find it faster?

## How it works

An AI agent (Claude) proposes a puzzle: a start actor, an end actor, and a guaranteed solution path. You play by naming a movie the current actor appeared in, then naming a co-star from that movie. The agent verifies each move in real time using TMDb data and web search — typos and partial names are handled gracefully.

**Difficulty levels:**
| Level | Hops | Notes |
|-------|------|-------|
| Easy | 2 | No movie repeated |
| Medium | 3–5 | Random within range |
| Hard | 6–8 | — |

## Stack

| Layer      | Technology                                                                                           |
|------------|------------------------------------------------------------------------------------------------------|
| Backend    | FastAPI (Python)                                                                                     |
| Agent      | Claude claude-sonnet-4-6 via Anthropic SDK                                                           |
| Movie data | TMDb API via [art-graph](https://github.com/ChiPowers/artist-graph) + Claude web search              |
| TMDb cache | SQLAlchemy (SQLite locally, Postgres/MySQL in production)                                            |
| Database   | SQLite (game state)                                                                                  |
| Tracing    | LangSmith (optional)                                                                                 |
| Frontend   | Next.js, Tailwind CSS, Framer Motion ([separate repo](https://github.com/ChiPowers/cinema-frontend)) |

## Getting started

### Backend

Requires Python >=3.10, <3.15.

```bash
poetry install
```

To also install dev tools (ruff, black, pytest):

```bash
poetry install --with dev
```

### Configuration

Copy `secrets/.env.example` to `secrets/.env` and fill in your keys:

```
TMDB_API_KEY=...
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
OPENROUTER_API_KEY=...
GEMINI_API_KEY=...
```

**TMDb cache** — one of these must be set or the app will refuse to start:

| Variable | Effect |
|----------|--------|
| `TMDB_CACHE_PATH=/path/to/tmdb_cache.db` | Enable SQLite-backed TMDb caching at the given path |
| `TMDB_CACHE_DISABLE=true` | Run without caching (every request hits TMDb directly) |

For local development, `TMDB_CACHE_DISABLE=true` is the simplest option. For production or heavy use, set `TMDB_CACHE_PATH` to a writable file path — this dramatically reduces TMDb API calls.

**LangSmith tracing** (optional):

```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=...
LANGCHAIN_PROJECT=cinema-game
```

See `secrets/README.md` for more detail.

### LLM experiment harness (LangSmith)

Run a model matrix over Cinema Game prompt surfaces and log each model run as a LangSmith experiment:

```bash
poetry run python scripts/run_llm_experiments.py --prefix cinema-game-llm-matrix
```

Run only a subset:

```bash
poetry run python scripts/run_llm_experiments.py --models haiku_4_5,sonnet_4_5,gpt_5_mini
```

Current model aliases:
- `haiku_4_5`
- `sonnet_4_5`
- `gpt_5_mini`
- `kimi_k2`
- `gemini_3_flash`
- `llama_4_maverick`

If a provider's canonical model id changes, set the `EXPERIMENT_MODEL_*` env vars in `secrets/.env`.

### Development with Make

A `Makefile` provides standard development commands:

| Target                | Description                                         |
|-----------------------|-----------------------------------------------------|
| `make test`           | Run unit tests                                      |
| `make test-functional`| Run functional tests (requires API credentials)     |
| `make test-all`       | Run unit + functional tests                         |
| `make lint`           | Lint with ruff                                      |
| `make format`         | Format with ruff                                    |
| `make check`          | Format + lint + test                                |
| `make coverage`       | Run unit tests with coverage enforcement (50% min)  |
| `make coverage-html`  | Generate an HTML coverage report at `htmlcov/`      |

### Running the server

```bash
poetry run uvicorn cinema_game_backend.main:app --reload
```

API runs at `http://localhost:8000`.

### Frontend

See the [frontend repo](https://github.com/ChiPowers/cinema-frontend).

## API

| Method   | Route                                     | Description                           |
|----------|-------------------------------------------|---------------------------------------|
| `POST`   | `/game/new?difficulty=easy\|medium\|hard` | Generate a new puzzle                 |
| `POST`   | `/game/{id}/move`                         | Submit a move `{ movie, next_actor }` |
| `DELETE`  | `/game/{id}/move`                         | Undo the last move                    |
| `GET`    | `/game/{id}`                              | Get current game state                |
| `GET`    | `/health`                                 | Health check                          |

## Architecture

The backend uses **FastAPI dependency injection** to provide the TMDb client. At startup, `create_tmdb_client()` reads the cache configuration and produces either a `CachedTMDbClient` (backed by SQLAlchemy) or a plain `TMDbClient`. This client is stored on `app.state` and injected into route handlers via `Depends(get_tmdb)`.

The TMDb cache layer lives in the [art-graph](https://github.com/ChiPowers/artist-graph) library. It caches people, movies, and credits in three tables. The caller (this app) owns the database engine and configuration — art-graph has no opinion about which database backend is used.

## Attribution

Movie and actor data provided by [TMDb](https://www.themoviedb.org). This product uses the TMDb API but is not endorsed or certified by TMDb.
