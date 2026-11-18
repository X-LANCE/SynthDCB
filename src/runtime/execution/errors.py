"""Stable atomic runtime execution failures."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeExecutionError(Exception):
    code: str
    kind: str
    message: str
    path: str = "$"

    def __str__(self) -> str:
        """Return the human-readable string representation."""
        return f"{self.code} ({self.kind}) at {self.path}: {self.message}"
