"""Stable results returned by object-model actions."""

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ActionResult:
    target: str
    function: str
    code: str
    response: dict[str, Any]
