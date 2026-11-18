"""Pure inheritance resolution for generated ObjectClass specifications."""

from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any

from src.contracts import load_json
from src.contracts.schema import builtin_tool_parameters


def supports_deferred_power(source: str) -> bool:
    """Whether a model constructor accepts deferred power initialization."""
    return any(
        isinstance(method, ast.FunctionDef) and method.name == "__init__"
        and any(arg.arg == "_defer_power_init" for arg in (
            *method.args.posonlyargs, *method.args.args, *method.args.kwonlyargs
        ))
        for owner in ast.parse(source).body if isinstance(owner, ast.ClassDef)
        for method in owner.body
    )


POWER_GET_FUNCTION = "get_power"
POWER_SET_FUNCTION = "set_power"
POWER_FUNCTIONS = (POWER_GET_FUNCTION, POWER_SET_FUNCTION)


def power_functions() -> dict[str, dict[str, Any]]:
    """Return fresh metadata for the power accessors."""

    return {
        POWER_GET_FUNCTION: {
            "description": "Get the current power state.",
            "parameters_schema": builtin_tool_parameters("get_power"),
            "mutation": False,
            "reads": ["power"],
            "writes": [],
            "semantics": {
                "kind": "read",
                "property": "power",
                "response_key": "power"
            },
            "response": {
                "power": {
                    "type": "boolean",
                    "description": "Current power state.",
                }
            },
            "errorcodes": {},
        },
        POWER_SET_FUNCTION: {
            "description": "Set power and dependent property access. While off, every non-power property is inaccessible through public getters/setters. Turning on restores access. A property marked auto_reset resets only when turning on.",
            "parameters_schema": builtin_tool_parameters("set_power"),
            "mutation": True,
            "reads": ["power"],
            "writes": ["power"],
            "semantics": {
                "kind": "set",
                "property": "power",
                "parameter": "value"
            },
            "response": {},
            "errorcodes": {},
        },
    }


def _section_parts(specification: dict[str, Any], name: str) -> tuple[dict[str, Any], list[str]]:
    """Read a section without replacing malformed declarations with empty data."""
    section = specification[name]
    if not isinstance(section, dict):
        raise ValueError(f"{name} must be an object")
    update = section.get("update", {})
    disabled = section.get("disabled", [])
    if not isinstance(update, dict):
        raise ValueError(f"{name}.update must be an object")
    if not isinstance(disabled, list) or not all(isinstance(item, str) for item in disabled):
        raise ValueError(f"{name}.disabled must be a list of names")
    return update, disabled


def active_section(specification: dict[str, Any], name: str) -> dict[str, Any]:
    """Return active members of a resolved or local specification."""
    update, disabled = _section_parts(specification, name)
    return {key: value for key, value in update.items() if key not in disabled}


def normalize_power_contract(
        specification: dict[str, Any],
        *,
        parent: dict[str, Any] | None = None,
        is_base: bool = False,
) -> dict[str, Any]:
    """Normalize one new-generation local delta to the power API.

    ``parent`` must be an already resolved effective specification when present.
    The input is never mutated. Inherited methods keep the builtin API, while
    a child's explicit setter dependencies describe its own reachable hooks.
    A local pair is synthesized when the parent does not provide both methods.
    """

    raw_function_update, _ = _section_parts(specification, "functions")
    result = deepcopy(specification)
    properties, property_disabled = _section_parts(result, "properties")
    functions, function_disabled = _section_parts(result, "functions")
    result["functions"]["update"] = functions
    result["functions"]["disabled"] = function_disabled
    for name in POWER_FUNCTIONS:
        # LLM-authored bodies and disabled flags are not authoritative.
        functions.pop(name, None)
        while name in function_disabled:
            function_disabled.remove(name)

    parent_properties = active_section(parent, "properties") if parent is not None else {}
    parent_functions = active_section(parent, "functions") if parent is not None else {}
    local_power_disabled = "power" in property_disabled
    local_power = "power" in properties and not local_power_disabled
    parent_power = parent is not None and "power" in parent_properties
    effective_power = (
        False
        if local_power_disabled
        else local_power or parent_power
    )
    if not effective_power and not local_power_disabled and set(raw_function_update).intersection(POWER_FUNCTIONS):
        raise ValueError("power functions require an explicit or inherited power property")
    parent_has_pair = all(name in parent_functions for name in POWER_FUNCTIONS)

    if effective_power and (is_base or not parent_has_pair):
        functions.update(power_functions())
    elif effective_power and POWER_SET_FUNCTION in raw_function_update:
        # Preserve child hook dependencies without accepting an LLM-authored API.
        functions[POWER_SET_FUNCTION] = power_functions()[POWER_SET_FUNCTION]
    if effective_power and POWER_SET_FUNCTION in functions:
        declared_setter = raw_function_update.get(POWER_SET_FUNCTION, {})
        for field in ("reads", "writes"):
            functions[POWER_SET_FUNCTION][field] = sorted({"power",
                                                           *declared_setter.get(field, [])})
    elif not effective_power:
        # A class that disables/removes power must not create a new power API.
        for name in POWER_FUNCTIONS:
            functions.pop(name, None)

    return result


def _merge(base: Any, update: Any) -> Any:
    """Recursively merge a specification update into its base."""
    if not isinstance(base, dict) or not isinstance(update, dict):
        return deepcopy(update)
    if "type" in base and "type" in update and base["type"] != update["type"]:
        return deepcopy(update)
    merged = deepcopy(base)
    for key, value in update.items():
        merged[key] = _merge(merged[key], value) if key in merged else deepcopy(value)
    return merged


def _load_single(path: Path) -> tuple[str, dict[str, Any]]:
    """Load exactly one class specification."""
    payload = load_json(path)
    if not isinstance(payload, dict) or len(payload) != 1:
        raise ValueError(f"specification must contain exactly one class: {path}")
    class_name, spec = next(iter(payload.items()))
    if not isinstance(class_name, str) or not isinstance(spec, dict):
        raise ValueError(f"invalid specification payload: {path}")
    return class_name, spec


def resolve_specification_delta(
        parent: dict[str, Any],
        class_name: str,
        local: dict[str, Any],
) -> dict[str, Any]:
    """Apply one local inheritance delta to an already resolved parent."""
    resolved = deepcopy(local)
    if "process" in parent:
        # A declared process is complete; a child can remove parent modes.
        resolved["process"] = deepcopy(local.get("process", parent["process"]))
    for section_name in ("properties", "functions", "events"):
        parent_update = active_section(parent, section_name) if parent else {}
        local_update, disabled = _section_parts(local, section_name)
        active = {
            key: deepcopy(value)
            for key, value in parent_update.items()
            if key not in disabled
        }
        for key, value in local_update.items():
            if key not in disabled:
                # Changed functions are complete contracts, including removals
                # from parameter schemas and semantic mappings.
                active[key] = deepcopy(value) if section_name == "functions" else _merge(active.get(key, {}), value)
        resolved[section_name] = {
            "update": active,
            "disabled": []
        }
    functions = resolved["functions"]["update"]
    if POWER_SET_FUNCTION in functions:
        if "process" in resolved:
            functions[POWER_SET_FUNCTION][
                "description"] += " The process after_action hook pauses running status on power-off; powering on does not resume it."
        functions[POWER_SET_FUNCTION]["writes"] = sorted({
            "power",
            *(name for name, prop in resolved["properties"]["update"].items() if prop.get("auto_reset")),
            *(functions[POWER_SET_FUNCTION].get("writes", [])),
            *(["status"] if "process" in resolved else []),
        })
    resolved["meta"]["name"] = class_name
    return resolved


def resolve_specification(
        specification_path: str | Path,
) -> tuple[dict[str, Any], tuple[Path, ...]]:
    """Resolve a base-to-child chain into one active specification."""

    def visit(path: Path, ancestors: tuple[Path, ...]) -> tuple[dict[str, Any], list[Path]]:
        """Resolve one specification and its declared parent."""
        resolved_path = path.resolve()
        if resolved_path in ancestors:
            cycle = " -> ".join(str(item) for item in (*ancestors, resolved_path))
            raise ValueError(f"specification inheritance cycle: {cycle}")
        class_name, local = _load_single(resolved_path)
        source = local["meta"].get("from", "")
        if not isinstance(source, str):
            raise ValueError(f"meta.from must be a string: {resolved_path}")
        if source:
            parent_path = (resolved_path.parent / source).resolve()
            parent, chain = visit(parent_path, (*ancestors, resolved_path))
        else:
            parent, chain = {}, []

        resolved = resolve_specification_delta(parent, class_name, local)
        return resolved, [*chain, resolved_path]

    resolved, chain = visit(Path(specification_path), ())
    return resolved, tuple(chain)
