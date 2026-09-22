"""The application must not import a vendor SDK to be importable.

With every extra installed locally this can only catch an import that has
moved to module scope -- which is exactly the regression worth catching. CI
runs the stronger version of this check in environments that really are
missing backends.
"""

import subprocess
import sys

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


def test_importing_config_pulls_in_no_vendor_sdk():
    code = (
        "import sys; import cinema_game_backend.config; "
        "print(' '.join(sorted(sys.modules)))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    loaded = set(out.stdout.split())
    leaked = {
        m
        for m in loaded
        if any(m == v or m.startswith(v + ".") for v in VENDOR_MODULES)
    }
    assert not leaked, (
        f"importing cinema_game_backend.config loaded vendor SDKs: {sorted(leaked)}"
    )
