"""Project-specific exceptions with user-facing messages."""

from __future__ import annotations

from collections.abc import Sequence


class Text2MujocoError(Exception):
    """Base class for expected project errors."""


class SceneValidationError(Text2MujocoError):
    """Raised when a SceneSpec is syntactically valid but unsafe or impossible."""

    def __init__(self, issues: Sequence[str]) -> None:
        self.issues = list(issues)
        message = "Scene validation failed: " + "; ".join(self.issues)
        super().__init__(message)


class MJCFBuildError(Text2MujocoError):
    """Raised when MJCF XML cannot be built or compiled."""


class SimulationStabilityError(Text2MujocoError):
    """Raised when MuJoCo state becomes unstable or non-finite."""


class LLMConfigurationError(Text2MujocoError):
    """Raised when OpenAI settings are missing or unsafe."""
