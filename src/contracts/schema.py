"""Load fixed schemas and build domain-specific or self-contained views."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .capabilities import CAPABILITY_SCHEMA
from .jsonio import load_json


SCHEMA_ROOT = Path(__file__).parent / "schemas"
TYPE_LIST_CHANGE_SCHEMA_VERSION = "type-list-change-v2"
TYPE_LIST_CHANGE_SCHEMA = load_json(SCHEMA_ROOT / "type_list_change.schema.json")
DELETE_LIST_KEY = "delete_list"
PASCAL_CASE_PATTERN = next(iter(TYPE_LIST_CHANGE_SCHEMA["patternProperties"]))

DEVICE_SPEC_SCHEMA = load_json(SCHEMA_ROOT / "device_spec.schema.json")
# Keep prompt payloads and standalone validators independent of external references.
DEVICE_SPEC_SCHEMA["$defs"] = deepcopy(CAPABILITY_SCHEMA["$defs"])

BUILTIN_TOOL_PARAMETERS_SCHEMA = load_json(SCHEMA_ROOT / "builtin_tool_parameters.schema.json")


def type_list_change_schema(domain: str) -> dict[str, Any]:
    """Constrain a fresh list-response schema to the requested domain."""
    schema = deepcopy(TYPE_LIST_CHANGE_SCHEMA)
    schema["patternProperties"][PASCAL_CASE_PATTERN]["properties"]["domain"] = {"const": domain}
    return schema


def builtin_tool_parameters(name: str) -> dict[str, Any]:
    """Return an independent parameter schema for a built-in tool."""
    return deepcopy(BUILTIN_TOOL_PARAMETERS_SCHEMA["$defs"][name])
