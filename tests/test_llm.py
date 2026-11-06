"""Provider resolution: env vars beat presets, a missing primary key stops the run, a missing fallback key doesn't."""

from types import SimpleNamespace

import pytest

from harness.core.llm import LLM, PROVIDERS, ConfigError, LLMUnavailable, ProviderConfig, resolve_providers


def test_defaults_to_gemini_with_groq_as_fallback():
    configs = resolve_providers({"GEMINI_API_KEY": "g", "GROQ_API_KEY": "q"})
    assert [c.provider for c in configs] == ["gemini", "groq"]
    assert configs[0].model == PROVIDERS["gemini"]["model"]
    assert configs[0].base_url == PROVIDERS["gemini"]["base_url"]


def test_no_fallback_key_means_no_fallback():
    assert [c.provider for c in resolve_providers({"GEMINI_API_KEY": "g"})] == ["gemini"]


def test_an_empty_fallback_setting_disables_it():
    env = {"GEMINI_API_KEY": "g", "GROQ_API_KEY": "q", "HARNESS_FALLBACK_PROVIDER": ""}
    assert len(resolve_providers(env)) == 1


def test_missing_primary_key_is_a_config_error():
    with pytest.raises(ConfigError, match="GEMINI_API_KEY"):
        resolve_providers({})


def test_unknown_provider_is_a_config_error():
    with pytest.raises(ConfigError, match="Known providers"):
        resolve_providers({"HARNESS_PROVIDER": "nope"})


def test_env_vars_override_each_preset_separately():
    env = {
        "GEMINI_API_KEY": "g",
        "GROQ_API_KEY": "q",
        "HARNESS_MODEL": "gemini-other",
        "HARNESS_MAX_INPUT_TOKENS": "1000",
        "HARNESS_FALLBACK_BASE_URL": "http://proxy/v1",
    }
    primary, fallback = resolve_providers(env)
    assert (primary.model, primary.max_input_tokens) == ("gemini-other", 1000)
    assert fallback.base_url == "http://proxy/v1"
    assert fallback.model == PROVIDERS["groq"]["model"]


def test_ollama_needs_no_key():
    [config] = resolve_providers({"HARNESS_PROVIDER": "ollama", "HARNESS_FALLBACK_PROVIDER": ""})
    assert config.api_key


def fake_client(content):
    reply = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: reply)))


CONFIG = ProviderConfig("gemini", "http://x", "k", "m", 10)


def test_complete_returns_the_reply_text():
    assert LLM(CONFIG, client=fake_client("hello")).complete("s", "u") == "hello"


def test_an_empty_reply_counts_as_unavailable():
    with pytest.raises(LLMUnavailable):
        LLM(CONFIG, client=fake_client(None)).complete("s", "u")
