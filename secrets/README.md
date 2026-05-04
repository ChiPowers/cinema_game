# Secrets directory

This directory contains secrets used by cinema_game in development and testing. Secrets are sensitive information that should not be shared with others. This directory is included in the `.gitignore` file, so secrets will not accidentally be committed to the repository.

## Setup

Copy `.env.example` to `.env` and fill in your actual API credentials:

```bash
cp .env.example .env
```

Edit `.env` with your keys:
- `TMDB_API_KEY`: Get from [The Movie Database (TMDb)](https://www.themoviedb.org/settings/api)
- `ANTHROPIC_API_KEY`: Get from [Anthropic](https://console.anthropic.com/)
- `OPENAI_API_KEY`: For GPT-5 mini
- `OPENROUTER_API_KEY`: For Kimi K2 and Llama 4 Maverick via OpenRouter
- `GEMINI_API_KEY`: For Gemini Flash models

The `.env` file is automatically loaded by `cinema_game_backend/env.py` when the backend starts.

## Functional Tests

Functional tests (in `functional_tests/`) use the credentials in this `.env` file to verify that the backend can make real API calls to Anthropic, TMDb, and other services. These tests are never run in CI — they require actual API credentials and external service access.
