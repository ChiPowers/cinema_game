import pytest

from cinema_game_backend.config import (
    DIFFICULTY_HOPS,
    MIN_ACTOR_POPULARITY,
    validate_llm_config,
)


class TestDifficultyHops:
    def test_all_levels_present(self):
        assert set(DIFFICULTY_HOPS.keys()) == {"easy", "medium", "hard"}

    def test_values_are_tuples_of_two_ints(self):
        for level, (lo, hi) in DIFFICULTY_HOPS.items():
            assert isinstance(lo, int), f"{level} low bound is not int"
            assert isinstance(hi, int), f"{level} high bound is not int"

    def test_low_bound_le_high_bound(self):
        for level, (lo, hi) in DIFFICULTY_HOPS.items():
            assert lo <= hi, f"{level}: {lo} > {hi}"

    def test_difficulty_ordering(self):
        assert DIFFICULTY_HOPS["easy"][1] < DIFFICULTY_HOPS["medium"][1]
        assert DIFFICULTY_HOPS["medium"][1] < DIFFICULTY_HOPS["hard"][1]


class TestMinActorPopularity:
    def test_all_levels_present(self):
        assert set(MIN_ACTOR_POPULARITY.keys()) == {"easy", "medium", "hard"}

    def test_values_are_positive(self):
        for level, pop in MIN_ACTOR_POPULARITY.items():
            assert pop > 0, f"{level} popularity is not positive"

    def test_easy_has_highest_floor(self):
        assert MIN_ACTOR_POPULARITY["easy"] > MIN_ACTOR_POPULARITY["medium"]
        assert MIN_ACTOR_POPULARITY["medium"] > MIN_ACTOR_POPULARITY["hard"]


class TestValidateLLMConfig:
    def test_unset_provider_raises(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        with pytest.raises(RuntimeError, match="LLM_PROVIDER"):
            validate_llm_config()

    def test_unknown_provider_raises(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "gpt5")
        with pytest.raises(RuntimeError, match="gpt5"):
            validate_llm_config()

    def test_missing_credentials_raise(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            validate_llm_config()

    def test_vertex_requires_project_and_location(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "vertex")
        monkeypatch.delenv("VERTEX_PROJECT_ID", raising=False)
        monkeypatch.setenv("VERTEX_LOCATION", "us-central1")
        with pytest.raises(RuntimeError, match="VERTEX_PROJECT_ID"):
            validate_llm_config()

    def test_missing_backend_extra_raises(self, monkeypatch):
        """A provider whose extra is not installed must fail at startup."""
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.setattr("cinema_game_backend.config.find_spec", lambda name: None)
        with pytest.raises(RuntimeError, match="ollama"):
            validate_llm_config()

    def test_provider_name_is_case_insensitive(self, monkeypatch):
        # find_spec is monkeypatched here (rather than left to the real
        # importlib) because CI installs this package with no extras, so
        # langchain_anthropic is genuinely absent there. Without this, the
        # test passes only on a machine with the anthropic extra installed
        # and fails in CI -- exactly the local/CI drift this task removes.
        monkeypatch.setenv("LLM_PROVIDER", "ANTHROPIC")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "placeholder")
        monkeypatch.setattr(
            "cinema_game_backend.config.find_spec", lambda name: object()
        )
        assert validate_llm_config() == "anthropic"

    def test_validation_imports_no_vendor_sdk(self, monkeypatch):
        """Validation must stay off the 773 ms vendor-import path."""
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "placeholder")
        called = []
        monkeypatch.setattr(
            "cinema_game_backend.config.find_spec",
            lambda name: called.append(name) or object(),
        )
        validate_llm_config()
        assert called == ["langchain_anthropic"]
