"""Run multi-model LLM experiments for Cinema Game and upload to LangSmith."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

# Load secrets/.env before any langsmith or anthropic clients are constructed.
from cinema_game_backend.env import load_cinema_game_env

load_cinema_game_env()

from cinema_game_backend.experiments_llm_harness import run_matrix  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Cinema Game LLM matrix experiments"
    )
    parser.add_argument(
        "--models",
        default="",
        help="Comma-separated model aliases (default: all)",
    )
    parser.add_argument(
        "--prefix",
        default="cinema-game-llm-matrix",
        help="LangSmith experiment prefix",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="max output tokens per call",
    )

    args = parser.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    prefix = f"{args.prefix}-{stamp}"
    models = [m.strip() for m in args.models.split(",") if m.strip()] or None

    experiment_names = run_matrix(
        experiment_prefix=prefix,
        selected_aliases=models,
        max_tokens=args.max_tokens,
    )

    print("Created LangSmith experiments:")
    for name in experiment_names:
        print(f"- {name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
