"""Settings shared by the CLI, the API and the worker. Env vars beat the defaults here."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    vault_dir: Path
    db_path: Path
    # "auto" summarizes in the language of the captions; a code such as "en" forces one.
    summary_language: str
    poll_interval: float

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        return cls(
            vault_dir=Path(env.get("HARNESS_VAULT_DIR") or PROJECT_ROOT / "vault"),
            db_path=Path(env.get("HARNESS_DB_PATH") or PROJECT_ROOT / "data" / "harness.db"),
            summary_language=env.get("HARNESS_SUMMARY_LANGUAGE") or "auto",
            poll_interval=float(env.get("HARNESS_POLL_INTERVAL") or 1.0),
        )
