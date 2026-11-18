from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EnvironmentContractError(Exception):
    """Stable loader/runtime validation error."""

    code: str
    path: str
    message: str

    def __str__(self) -> str:
        """Return the human-readable string representation."""
        return f"{self.code} at {self.path}: {self.message}"
