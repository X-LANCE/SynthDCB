"""Strict JSON loading and comparison for contract payloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.utils import load_json as read_json_file

from .errors import EnvironmentContractError


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Return the unique object."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EnvironmentContractError(
                "DUPLICATE_KEY",
                "$",
                f"duplicate JSON key {key!r}",
            )
        result[key] = value
    return result


def load_json(path: str | Path) -> Any:
    """Load UTF-8 JSON while accepting POSIX or Windows separators."""
    normalized_path = Path(str(path).replace("\\", "/"))
    try:
        return read_json_file(
            normalized_path,
            object_pairs_hook=_unique_object,
        )
    except EnvironmentContractError:
        raise
    except (OSError, json.JSONDecodeError) as error:
        raise EnvironmentContractError(
            "MALFORMED_JSON",
            str(normalized_path),
            str(error),
        ) from error


def is_number(value: Any) -> bool:
    """Return whether the value is a JSON-compatible number."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def strict_equal(left: Any, right: Any) -> bool:
    """Compare JSON recursively; int and float numbers are equivalent."""
    if is_number(left) and is_number(right):
        return float(left) == float(right)
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            strict_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            strict_equal(left_item, right_item)
            for left_item, right_item in zip(left, right)
        )
    return left == right
