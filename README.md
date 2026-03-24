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

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python) |
| Agent | Claude claude-sonnet-4-6 via Anthropic SDK |
| Movie data | TMDb API + Claude web search |
| Database | SQLite |
| Frontend | Next.js, Tailwind CSS, Framer Motion ([separate repo](https://github.com/ChiPowers/cinema-frontend)) |

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

This enables:

```bash
make test     # run tests
make lint     # lint with ruff
make format   # format with black
make check    # format + lint + test
```

Copy `cinema_game_backend/.env.example` to `cinema_game_backend/.env` and fill in your keys:

```
TMDB_API_KEY=...
ANTHROPIC_API_KEY=...
```

Then run:

```bash
poetry run uvicorn cinema_game_backend.main:app --reload
```

API runs at `http://localhost:8000`.

### Frontend

See the [frontend repo](https://github.com/ChiPowers/cinema-frontend).

## API

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/game/new?difficulty=easy\|medium\|hard` | Generate a new puzzle |
| `POST` | `/game/{id}/move` | Submit a move `{ movie, next_actor }` |
| `GET`  | `/game/{id}` | Get current game state |

## Attribution

Movie and actor data provided by [TMDb](https://www.themoviedb.org). This product uses the TMDb API but is not endorsed or certified by TMDb.
