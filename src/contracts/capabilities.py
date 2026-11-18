"""Device declaration checks shared by generation and runtime loading."""

from __future__ import annotations

from copy import deepcopy
import keyword
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .jsonio import load_json, strict_equal


CAPABILITY_SCHEMA = load_json(Path(__file__).parent / "schemas/capability.schema.json")
FUNCTION_FIELDS = ("parameters_schema", "mutation", "reads", "writes", "semantics", "argument_sources")
PROCESS_PROPERTIES = ("status", "phase", "remaining_minutes", "started_at_minute", "progress_minutes")


def collection_change_matches(assertion: dict, initial: Any, final: Any) -> bool:
    """Match exact CRUD changes; only IDs assigned to new records are ignored."""
    if not isinstance(initial, dict) or not isinstance(final, dict):
        return False
    removed = set(assertion["remove"])
    updates = assertion["update"]
    if not (removed | set(updates)).issubset(initial) or removed & set(updates):
        return False
    if set(initial) - set(final) != removed:
        return False
    for key in set(initial) - removed:
        expected = deepcopy(initial[key])
        if key in updates:
            if not isinstance(expected, dict):
                return False
            expected.update(updates[key])
        if not strict_equal(expected, final[key]):
            return False
    new_records = [final[key] for key in final if key not in initial]
    if len(new_records) != len(assertion["add"]):
        return False
    # ponytail: exact quadratic matching of small add batches; index if batches grow.
    for expected in assertion["add"]:
        match = next((index for index, value in enumerate(new_records) if strict_equal(value, expected)), None)
        if match is None:
            return False
        new_records.pop(match)
    return True


def declaration_schema(name: str) -> dict[str, Any]:
    return {"$defs": CAPABILITY_SCHEMA["$defs"], "$ref": f"#/$defs/{name}"}


def function_declaration(spec: dict[str, Any]) -> dict[str, Any]:
    return {name: deepcopy(spec[name]) for name in FUNCTION_FIELDS if name in spec}


def effect_properties(spec: dict[str, Any]) -> tuple[str, ...]:
    """Collect active event dependencies from an inheritance-resolved spec."""
    events = spec.get("events", {})
    return tuple(dict.fromkeys(
        prop["name"]
        for name, event in events.get("update", {}).items()
        if name not in events.get("disabled", [])
        for prop in event.get("effect_properties", [])
    ))


def validate_capability_spec(spec: dict[str, Any]) -> list[str]:
    """Check an effective model's external declarations before code generation."""
    errors = []
    properties = spec["properties"]["update"]
    functions = spec["functions"]["update"]
    for name in properties:
        if keyword.iskeyword(name):
            errors.append(f"property {name!r} is a reserved Python keyword; choose a valid attribute name")
    validator = Draft202012Validator(declaration_schema("function"))
    for name, function in functions.items():
        if keyword.iskeyword(name):
            errors.append(f"function {name!r} is a reserved Python keyword; choose a valid method name")
        issues = list(validator.iter_errors(function))
        if issues:
            errors.extend(f"{name}: {issue.message}" for issue in issues)
            continue
        parameters = function["parameters_schema"]
        try:
            Draft202012Validator.check_schema(parameters)
        except SchemaError as error:
            errors.append(f"{name}: invalid parameters_schema: {error.message}")
            continue
        if not set(parameters["required"]).issubset(parameters["properties"]):
            errors.append(f"{name}: required names must have parameter schemas")
        read, write = set(function["reads"]), set(function["writes"])
        undeclared = (read | write) - set(properties)
        if undeclared:
            errors.append(f"{name}: reads/writes refer to undeclared properties: {sorted(undeclared)}")
        if not function["mutation"] and write:
            errors.append(f"{name}: an observation cannot declare writes")
        semantics = function["semantics"]
        kind = semantics["kind"]
        expected_mutation = kind not in {"read", "collection_read"}
        if kind != "custom" and function["mutation"] != expected_mutation:
            errors.append(f"{name}: mutation flag disagrees with {kind}")
        prop = semantics.get("property")
        if prop is not None and prop not in (write if expected_mutation else read):
            errors.append(f"{name}: semantic property is absent from reads/writes")
        if kind == "set" and prop in properties:
            if properties[prop]["mode"] != 3 or properties[prop]["type"] in {"object", "dict"}:
                errors.append(f"{name}: generic setter is forbidden for read-only or collection properties")
        for key in ("parameter", "id_parameter", "mode_parameter"):
            if key in semantics and semantics[key] not in parameters["properties"]:
                errors.append(f"{name}: {key} references an undeclared parameter")
        for field, binding in semantics.get("fields", {}).items():
            if kind == "update" and field not in write:
                errors.append(f"{name}: field {field} is absent from writes")
            if "parameter" in binding and binding["parameter"] not in parameters["properties"]:
                errors.append(f"{name}: field {field} references an undeclared parameter")
        if set(semantics.get("preconditions", {})) - read:
            errors.append(f"{name}: preconditions are absent from reads")
        for property_name, condition in semantics.get("preconditions", {}).items():
            if isinstance(condition, dict) and "contains_key" in condition:
                binding = condition["contains_key"]
                if (set(condition) != {"contains_key"} or not isinstance(binding, dict)
                    or set(binding) != {"parameter"}
                    or not isinstance(binding.get("parameter"), str)
                    or properties.get(property_name, {}).get("type") not in {"dict", "object"}
                    or binding.get("parameter") not in parameters["properties"]
                    or function.get("argument_sources", {}).get(binding.get("parameter"))
                    != {"property": property_name, "field": "$key"}):
                    errors.append(f"{name}: contains_key requires a declared parameter bound to this collection's keys")
            elif isinstance(condition, dict) and set(condition) == {"one_of"}:
                if not isinstance(condition["one_of"], list) or not condition["one_of"]:
                    errors.append(f"{name}: one_of requires a nonempty list of property values")
            elif isinstance(condition, dict) and properties.get(property_name, {}).get("type") not in {"dict", "object"}:
                errors.append(f"{name}: unsupported object precondition for scalar property {property_name}; use a literal or one_of, and enforce parameter-conditional restrictions in action code")
        for parameter, source in function.get("argument_sources", {}).items():
            if parameter not in parameters["properties"] or source["property"] not in read:
                errors.append(f"{name}: invalid World argument source for {parameter}")
    if "process" in spec:
        process = spec["process"]
        issues = list(Draft202012Validator(declaration_schema("process")).iter_errors(process))
        errors.extend(f"process: {issue.message}" for issue in issues)
        if not issues:
            for name in PROCESS_PROPERTIES:
                if name not in properties or properties[name]["mode"] != 2:
                    errors.append(f"process: {name} must be a persisted read-only property")
            if process["mode_property"] not in properties:
                errors.append("process: mode property is missing")
            for phases in process["modes"].values():
                for phase in phases:
                    if isinstance(phase["minutes"], dict):
                        name = phase["minutes"]["property"]
                        prop = properties.get(name)
                        if prop is None or prop["type"] != "integer" or prop["value"]["default"] < 1:
                            errors.append(f"process: phase duration {name} must reference a positive integer property")
            for key, kind in (("start_function", "process_start"), ("pause_function", "process_pause"), ("resume_function", "process_resume")):
                if key in process and (process[key] not in functions or functions[process[key]].get("semantics", {}).get("kind") != kind):
                    errors.append(f"process: {key} must declare {kind}")
            events = spec["events"]["update"]
            if not {"tick", "after_action"}.issubset(events):
                errors.append("process: tick and after_action events are required")
    return errors


def precondition_matches(value: Any, condition: Any, parameters: dict | None = None) -> bool:
    if isinstance(condition, dict) and set(condition) == {"contains_key"}:
        binding = condition["contains_key"]
        if not isinstance(binding, dict) or set(binding) != {"parameter"} or not isinstance(binding["parameter"], str):
            return False
        key = (parameters or {}).get(binding["parameter"])
        return isinstance(value, dict) and isinstance(key, str) and key in value
    if isinstance(condition, dict) and set(condition) == {"one_of"}:
        return any(strict_equal(value, candidate) for candidate in condition["one_of"])
    return strict_equal(value, condition)


def process_phases(process: dict, properties: dict, mode: str) -> list[dict]:
    return [{"phase": phase["phase"], "minutes": properties[phase["minutes"]["property"]] if isinstance(phase["minutes"], dict) else phase["minutes"]} for phase in process["modes"][mode]]
