"""Assert the app is usable with exactly the extra that is installed.

Usage::

    python scripts/check_extras.py                # expect no provider usable
    python scripts/check_extras.py anthropic      # expect only Anthropic

This cannot be an ordinary unit test: it asserts what is *absent* from the
environment, and the development environment has a backend installed. It runs
in CI, in environments built with exactly one extra (or none).

Exits non-zero on the first mismatch, describing it.
"""

import os
import sys

from cinema_game_backend.config import _REQUIRED_ENV, create_llm_provider

# Watched names are full dotted module paths, not first segments. "google" is
# a PEP 420 namespace package shared by google-genai, google-auth and
# google-cloud-*: collapsing to the first segment would count any of those
# unrelated distributions as a "google" leak even when google.genai itself
# was never imported. langsmith (a core, non-vendor dependency used by
# agents/validation_agent.py) imports google and google.cloud on its own, so
# first-segment matching produces a false positive here. Matching on the
# dotted path keeps the check tied to the actual vendor module.
VENDOR_MODULES = {
    "anthropic",
    "openai",
    "google.genai",
    "langchain_anthropic",
    "langchain_google_genai",
    "langchain_ollama",
    "langchain_openai",
}

# Values that satisfy the credential guard so the run reaches the import that
# this script is actually testing. They are never used to make a network call.
PLACEHOLDER_ENV = {
    "ANTHROPIC_API_KEY": "placeholder",
    "OPENAI_API_KEY": "placeholder",
    "VERTEX_PROJECT_ID": "placeholder",
    "VERTEX_LOCATION": "us-central1",
}


def _fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def main() -> None:
    installed = sys.argv[1] if len(sys.argv) > 1 else None

    leaked = sorted(
        m
        for m in sys.modules
        if any(m == v or m.startswith(v + ".") for v in VENDOR_MODULES)
    )
    if leaked:
        _fail(f"importing cinema_game_backend.config loaded vendor SDKs: {leaked}")

    for var, value in PLACEHOLDER_ENV.items():
        os.environ.setdefault(var, value)

    for name in sorted(_REQUIRED_ENV):
        os.environ["LLM_PROVIDER"] = name
        try:
            create_llm_provider()
        except Exception as exc:  # noqa: BLE001 - reported, not swallowed
            # A missing extra now surfaces as the RuntimeError that
            # validate_llm_config raises when find_spec comes back empty,
            # rather than MissingBackendError from the constructor. Either
            # way the only question is whether failure was expected.
            if name == installed:
                _fail(f"{name} is installed but failed to construct: {exc!r}")
        else:
            if name != installed:
                _fail(f"{name} was constructed but its extra is not installed")

    if installed:
        print(f"OK: only the {installed} backend is usable")
    else:
        print("OK: no backend is usable")


if __name__ == "__main__":
    main()
