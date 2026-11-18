"""Deterministic model validation, grouped by the object being checked.

Sections: JSON schema, acceptance requirements, specification/implementation
consistency, event effects, generated tests, and final artifact validation.
Public validation entry points use validate_*; internal helpers use _ prefixes.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import jsonschema

from src.contracts import load_json, strict_equal
from src.contracts.errors import EnvironmentContractError
from src.contracts.schema import DEVICE_SPEC_SCHEMA
from .sandbox import SandboxLimits, run_generated_code, scan_generated_source
from .specification import (
    POWER_FUNCTIONS,
    active_section,
    normalize_power_contract,
    resolve_specification,
    supports_deferred_power,
)



def validate_json_schema(json_content: dict, schema: dict) -> tuple[str, list[str]]:
    """
    Validate the given JSON content against the device specification schema.

    Args:
        json_content: The JSON content to validate.
        schema: The JSON schema to validate against.

    Returns:
        (code, error_messages)
    """
    validator = jsonschema.Draft202012Validator(schema)
    errors = [str(error) for error in validator.iter_errors(json_content)]
    return "[JSON_SCHEMA_CHECK_FAILED]" if errors else "[PASS]", errors



def validate_required_contract(
    specification: dict[str, Any],
    required: dict[str, Any],
    *,
    effective_specification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Check a frozen representative case against a generated specification."""

    if not isinstance(required, dict):
        raise ValueError("required contract must be an object")
    effective = specification if effective_specification is None else effective_specification
    sections = {
        name: set(active_section(effective, name))
        for name in ("properties", "functions", "events")
    }
    disabled_sections = {}
    for name in sections:
        active_section(specification, name)
        disabled_sections[name] = set(specification[name].get("disabled", []))
    for name in ("required_properties", "required_functions", "required_disabled_properties",
                 "required_disabled_functions", "required_disabled_events"):
        if name in required and (
            not isinstance(required[name], list)
            or not all(isinstance(item, str) for item in required[name])
        ):
            raise ValueError(f"{name} must be a list of names")
    for name in ("required_parent", "required_event"):
        if name in required and not isinstance(required[name], str):
            raise ValueError(f"{name} must be a string")
    for name in ("max_properties", "max_functions"):
        if name in required and (type(required[name]) is not int or required[name] < 0):
            raise ValueError(f"{name} must be a non-negative integer")
    errors: list[str] = []
    required_parent = required.get("required_parent")
    if isinstance(required_parent, str):
        source = specification["meta"].get("from", "")
        if not isinstance(source, str):
            raise ValueError("meta.from must be a string")
        actual_parent = Path(source).stem if source else None
        if actual_parent != required_parent:
            errors.append(
                f"expected parent {required_parent}, got "
                f"{actual_parent or 'no parent'}"
            )
    for section_name, requirement_name in (
        ("properties", "required_properties"),
        ("functions", "required_functions"),
    ):
        missing = set(required.get(requirement_name, [])) - sections[section_name]
        if missing:
            errors.append(f"missing {section_name} {sorted(missing)}")
    for section_name, requirement_name in (
        ("properties", "required_disabled_properties"),
        ("functions", "required_disabled_functions"),
        ("events", "required_disabled_events"),
    ):
        missing = set(required.get(requirement_name, [])) - disabled_sections[section_name]
        if missing:
            errors.append(
                f"missing disabled {section_name} {sorted(missing)}"
            )
    required_event = required.get("required_event")
    if required_event and required_event not in sections["events"]:
        errors.append(f"missing event {required_event}")
    for section_name, maximum_name in (
        ("properties", "max_properties"),
        ("functions", "max_functions"),
    ):
        maximum = required.get(maximum_name)
        if maximum is not None and len(sections[section_name]) > maximum:
            errors.append(
                f"{section_name[:-1]} count {len(sections[section_name])} "
                f"exceeds {maximum}"
            )
    return {
        "code": "[PASS]" if not errors else "[CASE_CONTRACT_FAILED]",
        "properties": sorted(sections["properties"]),
        "functions": sorted(sections["functions"]),
        "events": sorted(sections["events"]),
        "disabled": {
            name: sorted(values)
            for name, values in disabled_sections.items()
        },
        "errors": errors,
    }


PROPERTY_CLASSES = {
    "boolean": "BoolProperty",
    "integer": "IntProperty",
    "float": "FloatProperty",
    "number": "FloatProperty",
    "string": "StringProperty",
    "dict": "DictProperty",
    "object": "DictProperty",
}


def _section(spec: dict[str, Any], name: str) -> tuple[dict[str, Any], set[str]]:
    """Return the section."""
    payload = spec.get(name, {})
    update = payload.get("update", {}) if isinstance(payload, dict) else {}
    disabled = payload.get("disabled", []) if isinstance(payload, dict) else []
    return (
        update if isinstance(update, dict) else {},
        set(disabled) if isinstance(disabled, list) else set(),
    )


def _self_assignments(function: ast.FunctionDef) -> dict[str, ast.Call]:
    """Return the self assignments."""
    assignments: dict[str, ast.Call] = {}
    for node in ast.walk(function):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
            and isinstance(node.value, ast.Call)
        ):
            assignments[target.attr] = node.value
    return assignments


def _call_name(call: ast.Call) -> str:
    """Call the name."""
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return ""


def _signature_names(function: ast.FunctionDef) -> list[str]:
    """Return the signature names."""
    names = [item.arg for item in function.args.posonlyargs]
    names.extend(item.arg for item in function.args.args)
    return [name for name in names if name != "self"]


def _signature_defaults(function: ast.FunctionDef) -> dict[str, ast.expr | None]:
    """Map public positional arguments to their defaults, if any."""

    arguments = [*function.args.posonlyargs, *function.args.args]
    if arguments and arguments[0].arg == "self":
        arguments = arguments[1:]
    defaults: list[ast.expr | None] = [None] * (
        len(arguments) - len(function.args.defaults)
    ) + list(function.args.defaults)
    return {
        argument.arg: default
        for argument, default in zip(arguments, defaults, strict=True)
    }


def _contains_attribute(function: ast.FunctionDef, name: str) -> bool:
    """Return whether a function calls/uses one attribute name."""

    return any(
        isinstance(node, ast.Attribute) and node.attr == name
        for node in ast.walk(function)
    )


def _parent_has_power_template(
    specification_path: Path,
    inheritance_source: str,
) -> bool:
    """Return whether an inherited implementation owns the power scaffold."""

    if not inheritance_source:
        return False
    parent_json = (specification_path.parent / inheritance_source).resolve()
    parent_python = parent_json.with_suffix(".py")
    try:
        return supports_deferred_power(parent_python.read_text(encoding="utf-8"))
    except OSError:
        # Isolated contract checks often provide only JSON.  In that case the
        # metadata remains the best available indication that power is owned by
        # the parent; do not report a false duplicate-method error.
        return True


def _validate_power_protocol(
    *,
    specification_path: Path,
    specification: dict[str, Any],
    class_node: ast.ClassDef,
    methods: dict[str, ast.FunctionDef | ast.AsyncFunctionDef],
) -> list[str]:
    """Validate the reserved power protocol on newly generated classes."""

    if not supports_deferred_power(ast.unparse(class_node)):
        return []
    errors: list[str] = []
    functions, function_disabled = _section(specification, "functions")
    local_functions = {
        name for name in functions if name not in function_disabled
    }
    inheritance_source = str(
        specification.get("meta", {}).get("from") or ""
    )
    parent_has_template = _parent_has_power_template(
        specification_path,
        inheritance_source,
    )
    effective = specification
    parent = None
    if inheritance_source:
        try:
            effective, chain = resolve_specification(specification_path)
            if len(chain) > 1:
                parent, _ = resolve_specification(chain[-2])
                parent = normalize_power_contract(parent, is_base=True)
        except (OSError, ValueError, TypeError):
            # The ordinary contract checks below still provide useful errors
            # when inheritance resolution fails.
            effective = specification
    effective_properties, effective_disabled = _section(effective, "properties")
    active_power = (
        "power" in effective_properties
        and "power" not in effective_disabled
    )
    present = {
        name
        for name in POWER_FUNCTIONS
        if isinstance(methods.get(name), ast.FunctionDef)
    }
    declared_power = local_functions & set(POWER_FUNCTIONS)
    if active_power and (
        not inheritance_source
        or declared_power
        or not parent_has_template
    ):
        missing = set(POWER_FUNCTIONS) - present
        if missing:
            errors.append(
                "deterministic power methods are missing: "
                + ", ".join(sorted(missing))
            )
    if inheritance_source and parent is not None:
        parent_functions, parent_disabled = _section(parent, "functions")
        inherited_pair = {
            name
            for name in POWER_FUNCTIONS
            if name in parent_functions and name not in parent_disabled
        }
        duplicate = inherited_pair & present
        if duplicate and not declared_power and parent_has_template:
            errors.append(
                "child redeclares inherited power methods: "
                + ", ".join(sorted(duplicate))
            )

    get_power = methods.get("get_power")
    if isinstance(get_power, ast.FunctionDef):
        if _signature_names(get_power):
            errors.append("get_power must not declare arguments")
        if not _contains_attribute(get_power, "get"):
            errors.append("get_power must read the power property")
    set_power = methods.get("set_power")
    if isinstance(set_power, ast.FunctionDef):
        if _signature_names(set_power) != ["value"]:
            errors.append("set_power must accept exactly value")
        if not _contains_attribute(set_power, "handle_power_switch"):
            errors.append(
                "set_power must call handle_power_switch for managed properties"
            )
    return errors


def validate_specification_implementation(
    specification_path: str | Path,
    implementation_path: str | Path,
) -> dict[str, Any]:
    """Compare a generated class against its authoritative JSON specification."""

    spec_path = Path(specification_path).resolve()
    source_path = Path(implementation_path).resolve()
    payload = load_json(spec_path)
    if not isinstance(payload, dict) or len(payload) != 1:
        return {
            "code": "[MODEL_CONTRACT_FAILED]",
            "errors": ["specification must contain exactly one class"],
            "warnings": [],
        }
    class_name, spec = next(iter(payload.items()))
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(spec, dict):
        return {
            "code": "[MODEL_CONTRACT_FAILED]",
            "errors": [f"{class_name} specification must be an object"],
            "warnings": [],
        }
    meta = spec.get("meta", {})
    if meta.get("name") != class_name:
        errors.append("meta.name must equal the specification mapping key")
    if not str(meta.get("description", "")).strip():
        errors.append("meta.description must be non-empty")

    source = source_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(source_path))
    except SyntaxError as error:
        return {
            "code": "[MODEL_CONTRACT_FAILED]",
            "errors": [f"syntax error at line {error.lineno}: {error.msg}"],
            "warnings": [],
        }
    class_nodes = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    ]
    if len(class_nodes) != 1:
        return {
            "code": "[MODEL_CONTRACT_FAILED]",
            "errors": [f"expected exactly one top-level class {class_name}"],
            "warnings": [],
        }
    class_node = class_nodes[0]
    inheritance_source = str(meta.get("from") or "")
    if inheritance_source:
        expected_base = Path(inheritance_source).stem
        declared_bases = {
            base.id
            for base in class_node.bases
            if isinstance(base, ast.Name)
        }
        if expected_base not in declared_bases:
            errors.append(
                f"class must inherit {expected_base} declared by meta.from"
            )
    methods = {
        node.name: node
        for node in class_node.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    # Compare generated power methods with the deterministic contract.
    if supports_deferred_power(source):
        parent_specification = None
        if inheritance_source:
            try:
                _, chain = resolve_specification(spec_path)
                if len(chain) > 1:
                    parent_specification, _ = resolve_specification(chain[-2])
                    parent_specification = normalize_power_contract(
                        parent_specification,
                        is_base=True,
                    )
            except (OSError, TypeError, ValueError):
                parent_specification = None
        spec = normalize_power_contract(
            spec,
            parent=parent_specification,
            is_base=not bool(inheritance_source),
        )
    init = methods.get("__init__")
    if not isinstance(init, ast.FunctionDef):
        errors.append("class must define __init__")
        assignments: dict[str, ast.Call] = {}
    else:
        assignments = _self_assignments(init)

    properties, property_disabled = _section(spec, "properties")
    active_properties = {
        name: item
        for name, item in properties.items()
        if name not in property_disabled
    }
    if not active_properties and not inheritance_source:
        errors.append("at least one active property is required")
    for name, item in active_properties.items():
        assignment = assignments.get(name)
        if assignment is None:
            errors.append(f"property {name} is not initialized on self")
            continue
        expected_class = PROPERTY_CLASSES.get(item.get("type"))
        actual_class = _call_name(assignment)
        if expected_class and actual_class != expected_class:
            errors.append(
                f"property {name} expects {expected_class}, got {actual_class or 'unknown'}"
            )

    functions, function_disabled = _section(spec, "functions")
    active_functions = {
        name: item
        for name, item in functions.items()
        if name not in function_disabled
    }
    if not active_functions and not inheritance_source:
        errors.append("at least one active public function is required")
    for name, item in active_functions.items():
        method = methods.get(name)
        if not isinstance(method, ast.FunctionDef):
            errors.append(f"public function {name} is missing")
            continue
        parameters = item["parameters_schema"]
        required_parameters = set(parameters["required"])
        expected_arguments = sorted(parameters["properties"], key=lambda key: key not in required_parameters)
        actual_arguments = _signature_names(method)
        if actual_arguments != expected_arguments:
            errors.append(
                f"function {name} arguments differ: "
                f"expected={expected_arguments}, actual={actual_arguments}"
            )
            continue
        actual_defaults = _signature_defaults(method)
        for argument_name, argument_spec in parameters["properties"].items():
            expected_optional = argument_name not in required_parameters
            actual_default = actual_defaults.get(argument_name)
            actual_optional = actual_default is not None
            if actual_optional != expected_optional:
                errors.append(
                    f"function {name} argument {argument_name} optionality differs: "
                    f"expected_optional={expected_optional}, "
                    f"actual_optional={actual_optional}"
                )
                continue
            if "default" in argument_spec and actual_default is not None:
                try:
                    parsed_default = ast.literal_eval(actual_default)
                except (TypeError, ValueError):
                    errors.append(
                        f"function {name} argument {argument_name} default "
                        "must be a literal"
                    )
                else:
                    if parsed_default != argument_spec["default"]:
                        errors.append(
                            f"function {name} argument {argument_name} default differs: "
                            f"expected={argument_spec['default']!r}, "
                            f"actual={parsed_default!r}"
                        )

    events, event_disabled = _section(spec, "events")
    active_events = {
        name: item
        for name, item in events.items()
        if name not in event_disabled
    }
    expected_effect_properties: list[str] = []
    for name, item in active_events.items():
        hook_name = f"_on_{name}"
        if not isinstance(methods.get(hook_name), ast.FunctionDef):
            errors.append(f"event hook {hook_name} is missing")
        for effect_property in item.get("effect_properties", []):
            property_name = effect_property.get("name")
            if isinstance(property_name, str) and property_name not in expected_effect_properties:
                expected_effect_properties.append(property_name)

    allowed_public = set(active_functions)
    extra_public = sorted(
        name
        for name in methods
        if not name.startswith("_") and name not in allowed_public
    )
    if extra_public:
        warnings.append(f"extra public helpers: {extra_public}")
    for marker in ("[NOT_IMPLEMENTED_FUNCTION]", "[NOT_IMPLEMENTED_EVENT]"):
        if marker in source:
            errors.append(f"implementation contains {marker}")

    errors.extend(
        _validate_power_protocol(
            specification_path=spec_path,
            specification=spec,
            class_node=class_node,
            methods=methods,
        )
    )

    # PROCESS remains implementation data; tools and event dependencies come from JSON.
    if any("semantics" in item for item in active_functions.values()):
        effective = resolve_specification(spec_path)[0] if inheritance_source else spec
        effective = normalize_power_contract(effective, is_base=True)
        expected = {}
        if "process" in effective:
            expected["PROCESS"] = effective["process"]
        literals = {
            node.targets[0].id: node.value
            for node in class_node.body
            if isinstance(node, ast.Assign) and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        }
        for name, value in expected.items():
            if name not in literals:
                errors.append(f"template declaration {name} is missing")
                continue
            try:
                actual = ast.literal_eval(literals[name])
            except (ValueError, TypeError):
                errors.append(f"template declaration {name} must remain literal data")
            else:
                if not strict_equal(actual, value):
                    errors.append(f"template declaration {name} differs from the specification")

    return {
        "code": "[PASS]" if not errors else "[MODEL_CONTRACT_FAILED]",
        "class_name": class_name,
        "specification_path": str(spec_path),
        "implementation_path": str(source_path),
        "summary": {
            "property_count": len(active_properties),
            "function_count": len(active_functions),
            "event_count": len(active_events),
            "effect_property_count": len(expected_effect_properties),
        },
        "errors": errors,
        "warnings": warnings,
    }


_EFFECT_ENVELOPE_KEYS = {
    "trigger",
    "source",
    "target",
    "function",
    "parameters",
}


_EFFECT_FUNCTIONS = {"set_contribution", "delta", "approach"}


def _literal_dict_items(node: ast.Dict) -> dict[str, ast.AST]:
    """Return the literal dict items."""
    return {
        key.value: value
        for key, value in zip(node.keys, node.values)
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    }


def _event_functions(tree: ast.AST) -> list[ast.FunctionDef]:
    """Return the event functions."""
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name.startswith("_on_")
    ]


def _literal_dict_values(
    node: ast.AST,
    key_name: str,
) -> set[str]:
    """Return the literal dict values."""
    values: set[str] = set()
    for item in ast.walk(node):
        if not isinstance(item, ast.Dict):
            continue
        for key, value in zip(item.keys, item.values):
            if (
                isinstance(key, ast.Constant)
                and key.value == key_name
                and isinstance(value, ast.Constant)
                and isinstance(value.value, str)
            ):
                values.add(value.value)
    return values


def _literal_property_units(node: ast.AST) -> list[tuple[int, str, str | None]]:
    """Return literal effect parameter property/unit triples."""
    result: list[tuple[int, str, str | None]] = []
    for item in ast.walk(node):
        if not isinstance(item, ast.Dict):
            continue
        parameters = _literal_dict_items(item).get("parameters")
        if not isinstance(parameters, ast.Dict):
            continue
        values = _literal_dict_items(parameters)
        prop = values.get("property")
        unit = values.get("unit")
        if (
            isinstance(prop, ast.Constant)
            and isinstance(prop.value, str)
            and isinstance(unit, ast.Constant)
            and (unit.value is None or isinstance(unit.value, str))
        ):
            result.append((parameters.lineno, prop.value, unit.value))
    return result


def validate_event_effect_shapes(
    source: str,
    *,
    label: str = "<generated>",
) -> list[str]:
    """Check recognizable literal effects against the current envelope format."""

    tree = ast.parse(source, filename=label)
    errors: list[str] = []
    for function in _event_functions(tree):
        expected_trigger = function.name[4:]
        for node in ast.walk(function):
            if not isinstance(node, ast.Dict):
                continue
            items = _literal_dict_items(node)
            keys = set(items)
            looks_like_effect = bool(keys & {"trigger", "source", "target", "function"})
            if not looks_like_effect:
                continue
            missing = _EFFECT_ENVELOPE_KEYS - keys
            if missing:
                errors.append(
                    f"INVALID_EFFECT_FORMAT line {node.lineno}: "
                    f"{function.name} effect is missing {sorted(missing)}; "
                    "use trigger/source/target/function/parameters"
                )
                continue
            extras = keys - _EFFECT_ENVELOPE_KEYS
            if extras:
                errors.append(
                    f"INVALID_EFFECT_FORMAT line {node.lineno}: "
                    f"{function.name} effect has unsupported keys {sorted(extras)}"
                )

            trigger_node = items["trigger"]
            if (
                isinstance(trigger_node, ast.Constant)
                and trigger_node.value != expected_trigger
            ):
                errors.append(
                    f"INVALID_EFFECT_FORMAT line {node.lineno}: "
                    f"trigger {trigger_node.value!r} does not match "
                    f"{expected_trigger!r}"
                )

            effect_function_node = items["function"]
            effect_function = (
                effect_function_node.value
                if isinstance(effect_function_node, ast.Constant)
                and isinstance(effect_function_node.value, str)
                else None
            )
            if effect_function is not None and effect_function not in _EFFECT_FUNCTIONS:
                errors.append(
                    f"INVALID_EFFECT_FORMAT line {node.lineno}: "
                    f"unsupported function {effect_function!r}"
                )

            parameters_node = items["parameters"]
            if not isinstance(parameters_node, ast.Dict):
                continue
            parameter_keys = set(_literal_dict_items(parameters_node))
            required_parameters = {"property", "value", "unit"}
            if effect_function == "approach":
                required_parameters.add("rate_per_minute")
            missing_parameters = required_parameters - parameter_keys
            if missing_parameters:
                errors.append(
                    f"INVALID_EFFECT_FORMAT line {parameters_node.lineno}: "
                    f"{effect_function or 'effect'} parameters are missing "
                    f"{sorted(missing_parameters)}"
                )
    return errors


def validate_effects(
    domain_root: str | Path,
    property_catalog: str | Path,
    *,
    implementation_paths: list[Path] | None = None,
) -> dict[str, Any]:
    """Check literal effect properties/functions against one Domain catalog."""
    root = Path(domain_root).resolve()
    catalog_path = Path(property_catalog).resolve()
    catalog = load_json(catalog_path)
    domain = catalog["domain_type"]
    allowed_properties = set(catalog["space_properties"])
    expected_units = {
        name: spec["unit"]
        for name, spec in catalog["space_properties"].items()
    }
    allowed_functions = {
        function
        for spec in catalog["space_properties"].values()
        for function in spec["allowed_effect_functions"]
    }

    errors: list[str] = []
    warnings: list[str] = []
    events: list[dict[str, Any]] = []
    implementations = [
        path
        for path in sorted(root.rglob("*.py") if implementation_paths is None else implementation_paths)
        if path.name != "__init__.py"
        and "_test" not in path.stem
        and not path.stem.startswith("test_")
        and ".template" not in path.name
    ]
    for path in implementations:
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(
                source,
                filename=str(path),
            )
        except SyntaxError as exc:
            errors.append(f"{path}: syntax error: {exc}")
            continue
        errors.extend(validate_event_effect_shapes(source, label=str(path)))
        for function in _event_functions(tree):
            properties = _literal_dict_values(function, "property")
            effect_functions = _literal_dict_values(function, "function")
            unsupported_properties = properties - allowed_properties
            unsupported_functions = effect_functions - allowed_functions
            if unsupported_properties:
                errors.append(
                    f"{path}:{function.name}: unsupported effect "
                    f"properties {sorted(unsupported_properties)}"
                )
            if unsupported_functions:
                errors.append(
                    f"{path}:{function.name}: unsupported effect "
                    f"functions {sorted(unsupported_functions)}"
                )
            for line, prop, unit in _literal_property_units(function):
                if prop not in expected_units:
                    continue  # Already reported as an unsupported property.
                expected = expected_units[prop]
                if unit != expected:
                    errors.append(
                        f"{path}:{function.name} line {line}: effect unit "
                        f"{unit!r} for {prop!r}; expected {expected!r}"
                    )
            if not properties:
                warnings.append(
                    f"{path}:{function.name}: effect property is dynamic; "
                    "runtime validation remains authoritative"
                )
            events.append(
                {
                    "implementation": str(path.relative_to(root)),
                    "event": function.name[4:],
                    "literal_properties": sorted(properties),
                    "literal_functions": sorted(effect_functions),
                }
            )

    return {
        "code": "[PASS]" if not errors else "[EFFECT_REVIEW_FAILED]",
        "domain": domain,
        "property_catalog": str(catalog_path),
        "summary": {
            "implementation_count": len(implementations),
            "event_count": len(events),
            "allowed_properties": sorted(allowed_properties),
            "allowed_functions": sorted(allowed_functions),
        },
        "events": events,
        "warnings": warnings,
        "errors": errors,
    }



def _validate_generated_test(
    implementation: Path,
    path: Path,
    *,
    candidate_root: Path,
    limits: SandboxLimits | None,
) -> tuple[bool, str, dict[str, Any]]:
    """Run the test."""
    report = run_generated_code(
        candidate_root=candidate_root,
        source_paths=[implementation, path],
        mode="unittest",
        test_path=path,
        limits=limits,
    )
    dynamic = report["dynamic"]
    if dynamic is None:
        return False, str(report["static"]["errors"]), report
    if report["code"] == "[SANDBOX_TIMEOUT]":
        return False, dynamic["output"], report
    worker_result = dynamic["result"]
    if worker_result is not None and "output" in worker_result:
        output = worker_result["output"]
    else:
        # Process/worker failures have no unittest output; retain process diagnostics.
        output = dynamic["output"]
    return report["code"] == "[PASS]", output, report


def expected_class_names(
    object_types: dict[str, Any],
) -> tuple[str, ...]:
    """Return the expected class names."""
    names: list[str] = []
    for class_name, item in object_types.items():
        names.append(class_name)
        names.extend(
            variant["class"]
            for variant in item.get("inherited_list", [])
        )
    return tuple(names)


def _single_path(
    root: Path,
    pattern: str,
    class_name: str,
) -> Path | None:
    """Return the single path."""
    matches = sorted(root.rglob(pattern))
    if len(matches) > 1:
        raise ValueError(
            f"multiple artifacts found for {class_name}: {matches}"
        )
    return matches[0] if matches else None


def validate_model_artifacts(
    domain_root: str | Path,
    object_types: dict[str, Any],
    *,
    property_catalog: str | Path | None = None,
    run_tests: bool = True,
    sandbox_limits: SandboxLimits | None = None,
    required_contracts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate every requested object model and return exact artifacts."""
    root = Path(domain_root).resolve()
    contracts = {} if required_contracts is None else required_contracts
    if not isinstance(contracts, dict) or not all(isinstance(value, dict) for value in contracts.values()):
        raise ValueError("required_contracts must map class names to contract objects")
    errors: list[str] = []
    artifacts: list[dict[str, Any]] = []
    for class_name in expected_class_names(object_types):
        try:
            implementation = _single_path(
                root,
                f"{class_name}.py",
                class_name,
            )
            test_path = _single_path(
                root,
                f"{class_name}_test.py",
                class_name,
            )
            specification = _single_path(
                root,
                f"{class_name}.json",
                class_name,
            )
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if implementation is None:
            errors.append(f"missing implementation for {class_name}")
            continue

        source = implementation.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(implementation))
            compile(tree, str(implementation), "exec")
        except SyntaxError as exc:
            errors.append(f"{implementation}: {exc}")
            continue
        classes = {
            node.name
            for node in tree.body
            if isinstance(node, ast.ClassDef)
        }
        if class_name not in classes:
            errors.append(
                f"{implementation}: class {class_name} is missing"
            )
        for placeholder in (
            "[NOT_IMPLEMENTED_FUNCTION]",
            "[NOT_IMPLEMENTED_EVENT]",
        ):
            if placeholder in source:
                errors.append(
                    f"{implementation}: contains {placeholder}"
                )

        security_report = scan_generated_source(implementation)
        if not security_report["passed"]:
            errors.append(
                f"{implementation}: security gate failed: "
                f"{security_report['errors']}"
            )

        contract_report: dict[str, Any] | None = None
        schema_report: dict[str, Any] | None = None
        case_contract: dict[str, Any] | None = None
        if specification is None:
            errors.append(f"missing specification for {class_name}")
        else:
            try:
                specification_payload = load_json(specification)
                code, schema_errors = validate_json_schema(specification_payload, DEVICE_SPEC_SCHEMA)
                if code == "[PASS]" and set(specification_payload) != {class_name}:
                    code = "[JSON_SCHEMA_CHECK_FAILED]"
                    schema_errors.append(f"specification must contain exactly the requested class {class_name}")
            except (EnvironmentContractError, OSError, ValueError) as exc:
                code, schema_errors = "[JSON_SCHEMA_CHECK_FAILED]", [str(exc)]
            schema_report = {"code": code, "errors": schema_errors}
            if code != "[PASS]":
                errors.append(f"{specification}: {schema_errors}")
            else:
                try:
                    if class_name in contracts:
                        effective_spec, _ = resolve_specification(specification)
                        case_contract = validate_required_contract(
                            specification_payload[class_name],
                            contracts[class_name],
                            effective_specification=effective_spec,
                        )
                        if case_contract["code"] != "[PASS]":
                            errors.append(
                                f"{specification}: representative case contract failed: "
                                f"{case_contract['errors']}"
                            )
                    contract_report = validate_specification_implementation(specification, implementation)
                except (EnvironmentContractError, OSError, ValueError, KeyError, TypeError) as exc:
                    contract_report = {"code": "[MODEL_CONTRACT_FAILED]", "errors": [str(exc)]}
                if contract_report["code"] != "[PASS]":
                    errors.append(
                        f"{implementation}: specification/implementation "
                        f"mismatch: {contract_report['errors']}"
                    )

        test_passed: bool | None = None
        sandbox_report: dict[str, Any] | None = None
        if run_tests:
            if test_path is None:
                errors.append(f"missing test for {class_name}")
                test_passed = False
            else:
                test_passed, output, sandbox_report = _validate_generated_test(
                    implementation,
                    test_path,
                    candidate_root=root,
                    limits=sandbox_limits,
                )
                if not test_passed:
                    errors.append(
                        f"{test_path}: test failed\n{output[-4000:]}"
                    )
        artifacts.append(
            {
                "class_name": class_name,
                "implementation_path": str(implementation),
                "test_path": (
                    str(test_path) if test_path is not None else None
                ),
                "specification_path": (
                    str(specification)
                    if specification is not None
                    else None
                ),
                "test_passed": test_passed,
                "schema_report": schema_report,
                "case_contract": case_contract,
                "security_report": security_report,
                "contract_report": contract_report,
                "sandbox_report": sandbox_report,
            }
        )

    effect_report: dict[str, Any] | None = None
    if property_catalog is not None:
        effect_report = validate_effects(root, property_catalog)
        errors.extend(effect_report["errors"])
    case_details = [
        {
            "class_name": item["class_name"],
            **item["case_contract"],
        }
        for item in artifacts
        if item["case_contract"] is not None
    ]
    return {
        "code": "[PASS]" if not errors else "[MODEL_VALIDATION_FAILED]",
        "domain_root": str(root),
        "summary": {
            "expected_class_count": len(
                expected_class_names(object_types)
            ),
            "artifact_count": len(artifacts),
            "test_count": sum(
                item["test_path"] is not None for item in artifacts
            ),
        },
        "artifacts": artifacts,
        "case_contract": {
            "code": (
                "[PASS]"
                if all(item["code"] == "[PASS]" for item in case_details)
                else "[CASE_CONTRACT_FAILED]"
            ),
            "cases": case_details,
        },
        "effect_review": effect_report,
        "errors": errors,
    }
