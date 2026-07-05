"""Run multi-model LLM experiments for Cinema Game and upload to LangSmith."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

# Load secrets/.env before any langsmith or anthropic clients are constructed.
from cinema_game_backend.env import load_cinema_game_env

load_cinema_game_env()

from cinema_game_backend.experiments_llm_harness import (  # noqa: E402
    CostRow,
    run_matrix,
    run_name_match_matrix,
)

_DATASET_CHOICES = ("validation", "name_match", "all")


def _print_cost_table(rows: list[CostRow], label: str) -> None:
    if not rows:
        return
    print(f"\n{'─' * 72}")
    print(f"  Cost summary — {label}")
    print(f"{'─' * 72}")
    print(
        f"  {'Model alias':<22} {'In tok':>8} {'Out tok':>8} {'Cost (USD)':>12}  Source"
    )
    print(f"  {'─' * 22} {'─' * 8} {'─' * 8} {'─' * 12}  {'─' * 9}")
    total_cost = 0.0
    for r in rows:
        cost_str = f"${r.cost_usd:.6f}" if r.cost_usd else "n/a"
        print(
            f"  {r.alias:<22} {r.input_tokens:>8,} {r.output_tokens:>8,} {cost_str:>12}  {r.cost_source}"
        )
        total_cost += r.cost_usd
    print(f"  {'─' * 22} {'─' * 8} {'─' * 8} {'─' * 12}")
    total_in = sum(r.input_tokens for r in rows)
    total_out = sum(r.output_tokens for r in rows)
    print(f"  {'TOTAL':<22} {total_in:>8,} {total_out:>8,} ${total_cost:>11.6f}")
    print(f"{'─' * 72}\n")


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
    parser.add_argument(
        "--dataset",
        default="all",
        choices=_DATASET_CHOICES,
        help=(
            "Which dataset to evaluate against: "
            "'validation' (json-shape), "
            "'name_match' (nickname/typo correctness), "
            "or 'all' (both). Default: all."
        ),
    )

    args = parser.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    prefix = f"{args.prefix}-{stamp}"
    models = [m.strip() for m in args.models.split(",") if m.strip()] or None

    experiment_names: list[str] = []
    all_cost_rows: list[CostRow] = []

    if args.dataset in ("validation", "all"):
        names, cost_rows = run_matrix(
            experiment_prefix=prefix,
            selected_aliases=models,
            max_tokens=args.max_tokens,
        )
        experiment_names += names
        _print_cost_table(cost_rows, "validation dataset")
        all_cost_rows += cost_rows

    if args.dataset in ("name_match", "all"):
        names, cost_rows = run_name_match_matrix(
            experiment_prefix=f"{prefix}-nm",
            selected_aliases=models,
            max_tokens=args.max_tokens,
        )
        experiment_names += names
        _print_cost_table(cost_rows, "name-match dataset")
        all_cost_rows += cost_rows

    if args.dataset == "all" and all_cost_rows:
        # Merge rows by alias for a combined total
        merged: dict[str, CostRow] = {}
        for r in all_cost_rows:
            if r.alias not in merged:
                merged[r.alias] = CostRow(alias=r.alias, model=r.model)
            m = merged[r.alias]
            m.calls += r.calls
            m.input_tokens += r.input_tokens
            m.output_tokens += r.output_tokens
            m.cost_usd += r.cost_usd
            m.cost_source = r.cost_source
        _print_cost_table(list(merged.values()), "ALL datasets combined")

    print("LangSmith experiments:")
    for name in experiment_names:
        print(f"  - {name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
