"""Environment-derived project settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_OPENAI_MODEL = "gpt-5.6"


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    openai_api_key: str | None
    openai_model: str
    artifact_dir: Path = Path("artifacts")

    @classmethod
    def from_env(cls) -> Settings:
        """Load settings without logging secret values."""

        artifact_dir = Path(os.environ.get("TEXT2MUJOCO_ARTIFACT_DIR", "artifacts"))
        return cls(
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            openai_model=os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
            artifact_dir=artifact_dir,
        )

    @property
    def has_api_key(self) -> bool:
        """Whether an API key is configured, without exposing its value."""

        return bool(self.openai_api_key)
