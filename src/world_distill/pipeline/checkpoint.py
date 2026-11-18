"""Checkpoint persistence using stage inputs and artifact presence."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, TypeVar

from .models import as_jsonable
from src.utils import load_json, write_json


T = TypeVar("T")


class CheckpointStore:
    """Persist validated stage payloads and reject stale resume data."""

    def __init__(self, root: str | Path) -> None:
        """Initialize the CheckpointStore."""
        self.root = Path(root).resolve()

    def path_for(self, stage: str) -> Path:
        """Return the checkpoint path for a stage."""
        return self.root / f"{stage}.checkpoint.json"

    def save(
        self,
        stage: str,
        stage_input: Any,
        output: Any,
        *,
        validated: bool,
    ) -> Path:
        """Save stage inputs alongside a validated output."""
        path = self.path_for(stage)
        path.parent.mkdir(parents=True, exist_ok=True)
        normalized_output = as_jsonable(output)
        payload = {
            "stage": stage,
            "input": as_jsonable(stage_input),
            "validated": validated,
            "output": normalized_output,
        }
        write_json(path, payload)
        return path

    def load(
        self,
        stage: str,
        stage_input: Any,
        decoder: Callable[[dict[str, Any]], T],
    ) -> T | None:
        """Load a matching validated stage checkpoint."""
        path = self.path_for(stage)
        if not path.is_file():
            return None
        payload = load_json(path)
        if (
            payload.get("stage") != stage
            or payload.get("input") != as_jsonable(stage_input)
            or payload.get("validated") is not True
        ):
            return None
        output = payload.get("output")
        if not isinstance(output, dict):
            return None
        provenance = output.get("provenance")
        if (
            not isinstance(provenance, dict)
            or provenance.get("stage") != stage
            or provenance.get("validated") is not True
        ):
            return None
        artifact_paths = provenance.get("artifact_paths", [])
        if (
            not isinstance(artifact_paths, list)
            or any(
                not isinstance(path, str)
                or not Path(path).is_file()
                for path in artifact_paths
            )
        ):
            return None
        return decoder(output)
