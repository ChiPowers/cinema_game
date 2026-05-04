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
        model=os.getenv("EXPERIMENT_MODEL_HAIKU_4_5", "claude-3-5-haiku-latest"),
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


def _extract_text_from_openai_responses(payload: dict[str, Any]) -> str:
    output = payload.get("output", [])
    for item in output:
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                text = content.get("text")
                if text:
                    return text
    return payload.get("output_text", "")


def _invoke_model(model: HarnessModel, system: str, user: str, max_tokens: int) -> str:
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
        return "\n".join([b.text for b in response.content if b.type == "text"]).strip()

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
            return _extract_text_from_openai_responses(resp.json()).strip()

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
            return data["choices"][0]["message"]["content"].strip()

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
            if not candidates:
                return ""
            parts = candidates[0].get("content", {}).get("parts", [])
            return "\n".join(p.get("text", "") for p in parts).strip()

    raise ValueError(f"Unsupported provider: {model.provider}")


def _parse_json_or_none(text: str) -> dict[str, Any] | None:
    try:
        return json.loads(text)
    except Exception:
        return None


def _target_for_model(model: HarnessModel, max_tokens: int):
    def _target(inputs: dict[str, Any]) -> dict[str, Any]:
        start = time.perf_counter()
        output = _invoke_model(
            model,
            system=inputs["system"],
            user=inputs["user"],
            max_tokens=max_tokens,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        parsed = _parse_json_or_none(output)
        return {
            "text": output,
            "json_valid": parsed is not None,
            "latency_ms": elapsed_ms,
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
    if parsed is None:
        return {"key": "json_shape", "score": 0, "comment": "Output is not valid JSON"}

    missing = [k for k in must_include if k not in parsed]
    if missing:
        return {
            "key": "json_shape",
            "score": 0,
            "comment": f"Missing keys: {', '.join(missing)}",
        }

    return {"key": "json_shape", "score": 1}


_DATASET_NAME = "cinema-game-validation-prompts"


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


def run_matrix(
    experiment_prefix: str,
    selected_aliases: list[str] | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> list[str]:
    client = Client()
    _ensure_dataset(client)

    models = DEFAULT_MODELS
    if selected_aliases:
        alias_set = set(selected_aliases)
        models = [m for m in models if m.alias in alias_set]

    if not models:
        raise ValueError("No models selected for experiment run")

    experiment_names: list[str] = []

    for model in models:
        result = evaluate(
            _target_for_model(model, max_tokens=max_tokens),
            data=_DATASET_NAME,
            evaluators=[_json_shape_evaluator],
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

    return experiment_names
