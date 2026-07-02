"""LLM experiment harness for Cinema Game prompt surfaces.

Runs a matrix of model providers against shared test cases and logs each model run
as a LangSmith experiment.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

import anthropic
import httpx
from langsmith import Client
from langsmith.evaluation import evaluate
from langsmith.evaluation.evaluator import EvaluationResult


DEFAULT_MAX_TOKENS = 512


@dataclass(frozen=True)
class HarnessModel:
    alias: str
    provider: str
    model: str
    api_key_env: str
    base_url: str | None = None


DEFAULT_MODELS: list[HarnessModel] = [
    HarnessModel(
        alias="haiku_4_5",
        provider="anthropic",
        model=os.getenv("EXPERIMENT_MODEL_HAIKU_4_5", "claude-haiku-4-5-20251001"),
        api_key_env="ANTHROPIC_API_KEY",
    ),
    HarnessModel(
        alias="sonnet_4_5",
        provider="anthropic",
        model=os.getenv("EXPERIMENT_MODEL_SONNET_4_5", "claude-sonnet-4-5"),
        api_key_env="ANTHROPIC_API_KEY",
    ),
    HarnessModel(
        alias="gpt_5_mini",
        provider="openai_responses",
        model=os.getenv("EXPERIMENT_MODEL_GPT_5_MINI", "gpt-5-mini"),
        api_key_env="OPENAI_API_KEY",
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    ),
    HarnessModel(
        alias="kimi_k2",
        provider="openai_compatible",
        model=os.getenv("EXPERIMENT_MODEL_KIMI_K2", "moonshotai/kimi-k2"),
        api_key_env="OPENROUTER_API_KEY",
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    ),
    HarnessModel(
        alias="gemini_3_flash",
        provider="gemini",
        model=os.getenv("EXPERIMENT_MODEL_GEMINI_3_FLASH", "gemini-2.5-flash"),
        api_key_env="GEMINI_API_KEY",
        base_url=os.getenv(
            "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
        ),
    ),
    HarnessModel(
        alias="llama_4_maverick",
        provider="openai_compatible",
        model=os.getenv(
            "EXPERIMENT_MODEL_LLAMA_4_MAVERICK", "meta-llama/llama-4-maverick"
        ),
        api_key_env="OPENROUTER_API_KEY",
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    ),
    HarnessModel(
        alias="sonnet_5",
        provider="anthropic",
        model=os.getenv("EXPERIMENT_MODEL_SONNET_5", "claude-sonnet-5"),
        api_key_env="ANTHROPIC_API_KEY",
    ),
    HarnessModel(
        alias="opus_4_8",
        provider="anthropic",
        model=os.getenv("EXPERIMENT_MODEL_OPUS_4_8", "claude-opus-4-8"),
        api_key_env="ANTHROPIC_API_KEY",
    ),
    HarnessModel(
        alias="gpt_4o",
        provider="openai_compatible",
        model=os.getenv("EXPERIMENT_MODEL_GPT_4O", "openai/gpt-4o"),
        api_key_env="OPENROUTER_API_KEY",
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    ),
    HarnessModel(
        alias="gemini_25_flash",
        provider="openai_compatible",
        model=os.getenv("EXPERIMENT_MODEL_GEMINI_25_FLASH", "google/gemini-2.5-flash"),
        api_key_env="OPENROUTER_API_KEY",
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    ),
    HarnessModel(
        alias="deepseek_v3",
        provider="openai_compatible",
        model=os.getenv("EXPERIMENT_MODEL_DEEPSEEK_V3", "deepseek/deepseek-chat-v3-0324"),
        api_key_env="OPENROUTER_API_KEY",
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    ),
]


def _built_in_examples() -> list[dict[str, Any]]:
    """Core prompt surfaces matching current LLM call patterns in the app."""
    return [
        {
            "inputs": {
                "call_site": "validation_fast_path",
                "system": (
                    "You are a movie cast validator for a cinema connections game. "
                    "Return ONLY raw JSON with keys: valid, explanation, confidence."
                ),
                "user": (
                    "Movie: The Departed (2006)\\n"
                    "TMDb cast: Leonardo DiCaprio, Matt Damon, Jack Nicholson, Mark Wahlberg\\n\\n"
                    "Verify whether cast includes both 'Leonardo DiCaprio' and 'Matt Damon'."
                ),
            },
            "outputs": {
                "must_include": ["valid", "confidence"],
            },
        },
        {
            "inputs": {
                "call_site": "validation_fast_path",
                "system": (
                    "You are a movie cast validator for a cinema connections game. "
                    "Return ONLY raw JSON with keys: valid, explanation, confidence."
                ),
                "user": (
                    "Movie: The Matrix (1999)\\n"
                    "TMDb cast: Keanu Reeves, Carrie-Anne Moss, Laurence Fishburne\\n\\n"
                    "Verify whether cast includes both 'Keanu Reeves' and 'Tom Hanks'."
                ),
            },
            "outputs": {
                "must_include": ["valid", "confidence"],
            },
        },
        {
            "inputs": {
                "call_site": "fallback_style_single_turn",
                "system": (
                    "You are a movie trivia validator for a cinema connections game. "
                    "Return ONLY raw JSON with keys: valid, explanation, confidence, movie_title."
                ),
                "user": (
                    "Verify this connection: Brad Pitt -> 12 Years a Slave -> Michael Fassbender. "
                    "Return only JSON."
                ),
            },
            "outputs": {
                "must_include": ["valid", "confidence", "movie_title"],
            },
        },
    ]


@dataclass(frozen=True)
class _InvokeResult:
    text: str
    input_tokens: int | None
    output_tokens: int | None
    reported_cost_usd: float | None = None


# Input/output price per million tokens. Update as provider pricing changes.
# OpenRouter models use their reported cost field instead of this table.
_PRICE_PER_M_TOKENS: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5-20251001": (0.80, 4.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-opus-4-8": (15.00, 75.00),
    # OpenAI direct (responses API)
    "gpt-5-mini": (1.10, 4.40),
}


def _estimate_cost(model_id: str, input_tok: int | None, output_tok: int | None) -> float | None:
    if input_tok is None or output_tok is None:
        return None
    prices = _PRICE_PER_M_TOKENS.get(model_id)
    if prices is None:
        return None
    in_price, out_price = prices
    return round((input_tok * in_price + output_tok * out_price) / 1_000_000, 8)


def _extract_text_from_openai_responses(payload: dict[str, Any]) -> str:
    output = payload.get("output", [])
    for item in output:
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                text = content.get("text")
                if text:
                    return text
    return payload.get("output_text", "")


def _invoke_model(model: HarnessModel, system: str, user: str, max_tokens: int) -> _InvokeResult:
    api_key = os.getenv(model.api_key_env, "")
    if not api_key:
        raise RuntimeError(f"Missing API key env var: {model.api_key_env}")

    if model.provider == "anthropic":
        client = anthropic.Anthropic(api_key=api_key, max_retries=3)
        response = client.messages.create(
            model=model.model,
            system=system,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": user}],
        )
        text = "\n".join([b.text for b in response.content if b.type == "text"]).strip()
        return _InvokeResult(
            text=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    if model.provider == "openai_responses":
        url = f"{model.base_url.rstrip('/')}/responses"
        payload = {
            "model": model.model,
            "input": [
                {
                    "role": "developer",
                    "content": [{"type": "input_text", "text": system}],
                },
                {"role": "user", "content": [{"type": "input_text", "text": user}]},
            ],
            "max_output_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=90) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usage", {})
            return _InvokeResult(
                text=_extract_text_from_openai_responses(data).strip(),
                input_tokens=usage.get("input_tokens"),
                output_tokens=usage.get("output_tokens"),
            )

    if model.provider == "openai_compatible":
        url = f"{model.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": model.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": 0,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=90) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usage", {})
            return _InvokeResult(
                text=data["choices"][0]["message"]["content"].strip(),
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
                reported_cost_usd=usage.get("cost"),
            )

    if model.provider == "gemini":
        url = (
            f"{model.base_url.rstrip('/')}/models/{model.model}:generateContent"
            f"?key={api_key}"
        )
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0},
        }
        with httpx.Client(timeout=90) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            text = ""
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "\n".join(p.get("text", "") for p in parts).strip()
            meta = data.get("usageMetadata", {})
            return _InvokeResult(
                text=text,
                input_tokens=meta.get("promptTokenCount"),
                output_tokens=meta.get("candidatesTokenCount"),
            )

    raise ValueError(f"Unsupported provider: {model.provider}")


def _parse_json_or_none(text: str) -> dict[str, Any] | None:
    try:
        return json.loads(text)
    except Exception:
        return None


@dataclass
class CostRow:
    alias: str
    model: str
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    cost_source: str = "n/a"


def _target_for_model(model: HarnessModel, max_tokens: int, cost_row: CostRow):
    def _target(inputs: dict[str, Any]) -> dict[str, Any]:
        start = time.perf_counter()
        result = _invoke_model(
            model,
            system=inputs["system"],
            user=inputs["user"],
            max_tokens=max_tokens,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        parsed = _parse_json_or_none(result.text)
        if result.reported_cost_usd is not None:
            cost = result.reported_cost_usd
            cost_source = "reported"
        else:
            cost = _estimate_cost(model.model, result.input_tokens, result.output_tokens)
            cost_source = "estimated" if cost is not None else "n/a"

        cost_row.calls += 1
        cost_row.input_tokens += result.input_tokens or 0
        cost_row.output_tokens += result.output_tokens or 0
        cost_row.cost_usd += cost or 0.0
        cost_row.cost_source = cost_source

        return {
            "text": result.text,
            "json_valid": parsed is not None,
            "latency_ms": elapsed_ms,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "estimated_cost_usd": cost,
            "model_alias": model.alias,
            "model": model.model,
            "provider": model.provider,
        }

    return _target


def _json_shape_evaluator(
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del reference_outputs
    must_include = inputs.get("must_include") or []
    text = outputs.get("text", "")
    parsed = _parse_json_or_none(text)
    if not isinstance(parsed, dict):
        return {"key": "json_shape", "score": 0, "comment": "Output is not a JSON object"}

    missing = [k for k in must_include if k not in parsed]
    if missing:
        return {
            "key": "json_shape",
            "score": 0,
            "comment": f"Missing keys: {', '.join(missing)}",
        }

    return {"key": "json_shape", "score": 1}


_DATASET_NAME = "cinema-game-validation-prompts"
_NAME_MATCH_DATASET_NAME = "cinema-game-name-match"

# System prompt that mirrors the preamble of validation_agent.LLM_NAME_MATCH_PROMPT.
_NM_SYSTEM = (
    "You are matching a player-typed actor name against a movie cast list.\n"
    "The player is playing a cinema connections game where they name actors\n"
    "and movies to build a chain. They may use nicknames, abbreviations,\n"
    "or informal names (e.g. 'Larry' for 'Laurence', 'Dick' for 'Richard')."
)


def _nm_user(cast: list[str], query: str) -> str:
    """Build the user turn of the llm_name_match prompt from cast + query."""
    cast_lines = "\n".join(f"- {n}" for n in cast)
    return (
        f"Cast list:\n{cast_lines}\n\n"
        f'Player typed: "{query}"\n\n'
        "If the player clearly means one of the cast members, return a JSON object:\n"
        '  {"matched_name": "Exact Name From Cast List"}\n'
        "If no cast member matches, return:\n"
        '  {"matched_name": null}\n\n'
        "Return ONLY the JSON object, nothing else."
    )


def _name_match_examples() -> list[dict[str, Any]]:
    """Test cases for the llm_name_match prompt surface in validation_agent.py."""
    matrix_cast = [
        "Keanu Reeves", "Laurence Fishburne", "Carrie-Anne Moss",
        "Hugo Weaving", "Joe Pantoliano",
    ]
    departed_cast = [
        "Leonardo DiCaprio", "Matt Damon", "Jack Nicholson",
        "Mark Wahlberg", "Martin Sheen", "Alec Baldwin",
    ]
    gwh_cast = [
        "Matt Damon", "Robin Williams", "Ben Affleck",
        "Stellan Skarsgård", "Minnie Driver",
    ]
    sls_cast = [
        "Bradley Cooper", "Jennifer Lawrence", "Robert De Niro",
        "Jacki Weaver", "Chris Tucker",
    ]
    goodfellas_cast = [
        "Robert De Niro", "Ray Liotta", "Joe Pesci",
        "Lorraine Bracco", "Paul Sorvino",
    ]
    joker_cast = [
        "Joaquin Phoenix", "Robert De Niro", "Zazie Beetz",
        "Frances Conroy", "Brett Cullen",
    ]
    shawshank_cast = [
        "Tim Robbins", "Morgan Freeman", "Bob Gunton",
        "William Sadler", "Clancy Brown", "James Whitmore",
    ]
    avengers_cast = [
        "Robert Downey Jr.", "Chris Evans", "Chris Hemsworth",
        "Chris Pratt", "Mark Ruffalo", "Scarlett Johansson",
        "Benedict Cumberbatch", "Don Cheadle",
    ]

    return [
        # --- Positive: nicknames / informal names ---
        {
            "inputs": {
                "call_site": "llm_name_match",
                "system": _NM_SYSTEM,
                "user": _nm_user(matrix_cast, "Larry"),
                "must_include": ["matched_name"],
                "expected_matched_name": "Laurence Fishburne",
            },
        },
        {
            "inputs": {
                "call_site": "llm_name_match",
                "system": _NM_SYSTEM,
                "user": _nm_user(departed_cast, "Leo"),
                "must_include": ["matched_name"],
                "expected_matched_name": "Leonardo DiCaprio",
            },
        },
        {
            "inputs": {
                "call_site": "llm_name_match",
                "system": _NM_SYSTEM,
                "user": _nm_user(gwh_cast, "Damon"),
                "must_include": ["matched_name"],
                "expected_matched_name": "Matt Damon",
            },
        },
        {
            "inputs": {
                "call_site": "llm_name_match",
                "system": _NM_SYSTEM,
                "user": _nm_user(sls_cast, "JLaw"),
                "must_include": ["matched_name"],
                "expected_matched_name": "Jennifer Lawrence",
            },
        },
        {
            "inputs": {
                "call_site": "llm_name_match",
                "system": _NM_SYSTEM,
                "user": _nm_user(goodfellas_cast, "Bob De Niro"),
                "must_include": ["matched_name"],
                "expected_matched_name": "Robert De Niro",
            },
        },
        {
            "inputs": {
                "call_site": "llm_name_match",
                "system": _NM_SYSTEM,
                "user": _nm_user(joker_cast, "Joaquim Phoenix"),
                "must_include": ["matched_name"],
                "expected_matched_name": "Joaquin Phoenix",
            },
        },
        # --- Positive: exact match (fuzzy should catch this, but LLM must not regress) ---
        {
            "inputs": {
                "call_site": "llm_name_match",
                "system": _NM_SYSTEM,
                "user": _nm_user(departed_cast, "Jack Nicholson"),
                "must_include": ["matched_name"],
                "expected_matched_name": "Jack Nicholson",
            },
        },
        # --- Positive: honorific prefix ---
        {
            "inputs": {
                "call_site": "llm_name_match",
                "system": _NM_SYSTEM,
                "user": _nm_user(departed_cast, "Mr. Nicholson"),
                "must_include": ["matched_name"],
                "expected_matched_name": "Jack Nicholson",
            },
        },
        # --- Negative: actor not in cast ---
        {
            "inputs": {
                "call_site": "llm_name_match",
                "system": _NM_SYSTEM,
                "user": _nm_user(shawshank_cast, "Tom Cruise"),
                "must_include": ["matched_name"],
                "expected_matched_name": None,
            },
        },
        {
            "inputs": {
                "call_site": "llm_name_match",
                "system": _NM_SYSTEM,
                "user": _nm_user(gwh_cast, "Matthew Dillon"),
                "must_include": ["matched_name"],
                "expected_matched_name": None,
            },
        },
        {
            "inputs": {
                "call_site": "llm_name_match",
                "system": _NM_SYSTEM,
                "user": _nm_user(shawshank_cast, "Unknown Actor"),
                "must_include": ["matched_name"],
                "expected_matched_name": None,
            },
        },
        # --- Edge: ambiguous first name (three Chrises in cast — expect null) ---
        {
            "inputs": {
                "call_site": "llm_name_match",
                "system": _NM_SYSTEM,
                "user": _nm_user(avengers_cast, "Chris"),
                "must_include": ["matched_name"],
                "expected_matched_name": None,
            },
        },
    ]


def _cost_evaluator(
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del inputs, reference_outputs
    cost = outputs.get("estimated_cost_usd")
    if cost is None:
        return {"key": "cost_usd", "score": None, "comment": "cost unavailable"}
    return {"key": "cost_usd", "score": cost}


def _token_evaluator(
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    del inputs, reference_outputs
    results = []
    for key, field in (("input_tokens", "input_tokens"), ("output_tokens", "output_tokens")):
        val = outputs.get(field)
        results.append({"key": key, "score": val} if val is not None else {"key": key, "score": None, "comment": "unavailable"})
    return results


def _name_match_correctness_evaluator(
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del reference_outputs
    expected = inputs.get("expected_matched_name")
    parsed = _parse_json_or_none(outputs.get("text", ""))
    if not isinstance(parsed, dict):
        return {"key": "name_match_correctness", "score": 0, "comment": "not a JSON object"}
    actual = parsed.get("matched_name")
    score = 1 if actual == expected else 0
    comment = "" if score else f"expected={expected!r} got={actual!r}"
    return {"key": "name_match_correctness", "score": score, "comment": comment}


def _null_precision_evaluator(
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Only scores negative cases (expected_matched_name is None)."""
    del reference_outputs
    if inputs.get("expected_matched_name") is not None:
        return EvaluationResult(key="null_precision", score=None, comment="n/a (positive case)")
    parsed = _parse_json_or_none(outputs.get("text", ""))
    if not isinstance(parsed, dict):
        return {"key": "null_precision", "score": 0, "comment": "not a JSON object"}
    actual = parsed.get("matched_name")
    score = 1 if actual is None else 0
    comment = "" if score else f"hallucinated: {actual!r}"
    return {"key": "null_precision", "score": score, "comment": comment}


def _ensure_dataset(client: Client) -> None:
    """Create the LangSmith dataset from built-in examples if it doesn't exist or is empty."""
    has_ds = client.has_dataset(dataset_name=_DATASET_NAME)
    if (
        has_ds
        and next(client.list_examples(dataset_name=_DATASET_NAME), None) is not None
    ):
        return

    ls_inputs, ls_outputs = [], []
    for example in _built_in_examples():
        inputs = dict(example["inputs"])
        inputs["must_include"] = example["outputs"]["must_include"]
        ls_inputs.append(inputs)
        ls_outputs.append({})

    if not has_ds:
        client.create_dataset(
            dataset_name=_DATASET_NAME,
            description="Cinema Game validation prompt test cases",
        )
    client.create_examples(
        dataset_name=_DATASET_NAME,
        inputs=ls_inputs,
        outputs=ls_outputs,
    )


def _ensure_name_match_dataset(client: Client) -> None:
    """Create the name-match LangSmith dataset if it doesn't exist or is empty."""
    has_ds = client.has_dataset(dataset_name=_NAME_MATCH_DATASET_NAME)
    if (
        has_ds
        and next(client.list_examples(dataset_name=_NAME_MATCH_DATASET_NAME), None) is not None
    ):
        return

    ls_inputs = [ex["inputs"] for ex in _name_match_examples()]
    ls_outputs = [{} for _ in ls_inputs]

    if not has_ds:
        client.create_dataset(
            dataset_name=_NAME_MATCH_DATASET_NAME,
            description=(
                "Cinema Game llm_name_match eval: nickname/typo resolution "
                "with correctness and null-precision scoring."
            ),
        )
    client.create_examples(
        dataset_name=_NAME_MATCH_DATASET_NAME,
        inputs=ls_inputs,
        outputs=ls_outputs,
    )


def run_matrix(
    experiment_prefix: str,
    selected_aliases: list[str] | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> tuple[list[str], list[CostRow]]:
    client = Client()
    _ensure_dataset(client)

    models = DEFAULT_MODELS
    if selected_aliases:
        alias_set = set(selected_aliases)
        models = [m for m in models if m.alias in alias_set]

    if not models:
        raise ValueError("No models selected for experiment run")

    experiment_names: list[str] = []
    cost_rows: list[CostRow] = []

    for model in models:
        cost_row = CostRow(alias=model.alias, model=model.model)
        result = evaluate(
            _target_for_model(model, max_tokens=max_tokens, cost_row=cost_row),
            data=_DATASET_NAME,
            evaluators=[_json_shape_evaluator, _cost_evaluator, _token_evaluator],
            experiment_prefix=f"{experiment_prefix}-{model.alias}",
            description=(
                "Cinema Game LLM harness: compare per-call prompt behavior "
                f"for {model.alias}"
            ),
            metadata={
                "model_alias": model.alias,
                "provider": model.provider,
                "model": model.model,
                "harness": "cinema_game_backend.experiments_llm_harness",
            },
            client=client,
            max_concurrency=1,
        )
        experiment_names.append(result.experiment_name)
        cost_rows.append(cost_row)

    return experiment_names, cost_rows


def run_name_match_matrix(
    experiment_prefix: str,
    selected_aliases: list[str] | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> tuple[list[str], list[CostRow]]:
    """Run the name-match eval matrix against the cinema-game-name-match dataset."""
    client = Client()
    _ensure_name_match_dataset(client)

    models = DEFAULT_MODELS
    if selected_aliases:
        alias_set = set(selected_aliases)
        models = [m for m in models if m.alias in alias_set]

    if not models:
        raise ValueError("No models selected for experiment run")

    experiment_names: list[str] = []
    cost_rows: list[CostRow] = []

    for model in models:
        cost_row = CostRow(alias=model.alias, model=model.model)
        result = evaluate(
            _target_for_model(model, max_tokens=max_tokens, cost_row=cost_row),
            data=_NAME_MATCH_DATASET_NAME,
            evaluators=[
                _json_shape_evaluator,
                _cost_evaluator,
                _token_evaluator,
                _name_match_correctness_evaluator,
                _null_precision_evaluator,
            ],
            experiment_prefix=f"{experiment_prefix}-{model.alias}",
            description=(
                "Cinema Game llm_name_match harness: nickname/typo resolution "
                f"correctness for {model.alias}"
            ),
            metadata={
                "model_alias": model.alias,
                "provider": model.provider,
                "model": model.model,
                "harness": "cinema_game_backend.experiments_llm_harness",
                "dataset": _NAME_MATCH_DATASET_NAME,
            },
            client=client,
            max_concurrency=1,
        )
        experiment_names.append(result.experiment_name)
        cost_rows.append(cost_row)

    return experiment_names, cost_rows
