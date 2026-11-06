"""Chat completions against OpenAI-compatible endpoints. The presets follow Hone's provider layer."""

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass

from openai import APIError, OpenAI, Timeout

log = logging.getLogger(__name__)

# Presets. Each field can be overridden by an env var: HARNESS_* for the primary
# provider, HARNESS_FALLBACK_* for the fallback.
PROVIDERS = {
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key_env": "GEMINI_API_KEY",
        "model": "gemini-3.5-flash-lite",
        # The model takes ~1M tokens; past this, map-reduce keeps each call quick.
        "max_input_tokens": 200_000,
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "model": "openai/gpt-oss-20b",
        # The free tier's tokens-per-minute cap sets this, not the context window.
        "max_input_tokens": 4_000,
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "api_key_env": None,
        "model": "qwen2.5:7b",
        "max_input_tokens": 8_000,
    },
}

DEFAULT_PROVIDER = "gemini"
DEFAULT_FALLBACK = "groq"
MAX_OUTPUT_TOKENS = 8192
# The SDK retries connection errors, timeouts, 429s and 5xx with exponential backoff.
MAX_RETRIES = 3
# A long summary can take minutes to generate, but an endpoint that is up connects in
# well under a second; a short connect timeout makes a dead one fail fast.
TIMEOUT = Timeout(120, connect=10)


class ConfigError(Exception):
    """The environment does not describe a usable provider."""


class LLMUnavailable(Exception):
    """A provider could not answer after its retries; the next provider in the chain may."""


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    base_url: str
    api_key: str
    model: str
    max_input_tokens: int


def resolve_providers(env: Mapping[str, str] | None = None) -> list[ProviderConfig]:
    """The primary provider, then the fallback when its key is set."""
    env = os.environ if env is None else env
    primary = env.get("HARNESS_PROVIDER") or DEFAULT_PROVIDER
    configs = [_resolve(primary, env, prefix="HARNESS_", required=True)]

    fallback = env.get("HARNESS_FALLBACK_PROVIDER", DEFAULT_FALLBACK)
    if fallback and fallback != primary:
        config = _resolve(fallback, env, prefix="HARNESS_FALLBACK_", required=False)
        if config is None:
            log.info("No key for fallback provider %r; running without a fallback", fallback)
        else:
            configs.append(config)
    return configs


def _resolve(name: str, env: Mapping[str, str], *, prefix: str, required: bool) -> ProviderConfig | None:
    if name not in PROVIDERS:
        known = ", ".join(sorted(PROVIDERS))
        raise ConfigError(f"Unknown provider {name!r}. Known providers: {known}")

    preset = PROVIDERS[name]
    key_env = preset["api_key_env"]
    # Ollama ignores the key, but the SDK insists on one.
    api_key = env.get(key_env) if key_env else "ollama"
    if not api_key:
        if required:
            raise ConfigError(f"No API key for provider {name!r}. Set {key_env} in .env.")
        return None

    return ProviderConfig(
        provider=name,
        base_url=env.get(f"{prefix}BASE_URL") or preset["base_url"],
        api_key=api_key,
        model=env.get(f"{prefix}MODEL") or preset["model"],
        max_input_tokens=int(env.get(f"{prefix}MAX_INPUT_TOKENS") or preset["max_input_tokens"]),
    )


class LLM:
    """One provider. Plugins call complete() and size their chunks by max_input_tokens."""

    def __init__(self, config: ProviderConfig, client: OpenAI | None = None):
        self.config = config
        self.client = client or OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            max_retries=MAX_RETRIES,
            timeout=TIMEOUT,
        )

    @property
    def name(self) -> str:
        return f"{self.config.provider}:{self.config.model}"

    @property
    def max_input_tokens(self) -> int:
        return self.config.max_input_tokens

    def complete(self, system: str, user: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=MAX_OUTPUT_TOKENS,
                temperature=0.2,
            )
        except APIError as error:
            raise LLMUnavailable(f"{self.name}: {error}") from error

        content = response.choices[0].message.content
        if not content:
            raise LLMUnavailable(f"{self.name} returned an empty reply")
        return content
