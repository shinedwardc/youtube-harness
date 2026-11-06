"""Wires settings, storage, plugins and providers together for the CLI and the API."""

from collections.abc import Mapping
from dataclasses import dataclass

from .core.config import Settings
from .core.db import Store
from .core.llm import LLM, resolve_providers
from .core.plugin import Plugin
from .plugins.youtube import YouTubePlugin


@dataclass(frozen=True)
class Harness:
    settings: Settings
    store: Store
    plugins: Mapping[str, Plugin]
    llms: list[LLM]


def build(env: Mapping[str, str] | None = None) -> Harness:
    """Raises ConfigError when no usable provider is configured."""
    settings = Settings.from_env(env)
    plugins = [YouTubePlugin(summary_language=settings.summary_language)]
    return Harness(
        settings=settings,
        store=Store(settings.db_path),
        plugins={plugin.name: plugin for plugin in plugins},
        llms=[LLM(config) for config in resolve_providers(env)],
    )
