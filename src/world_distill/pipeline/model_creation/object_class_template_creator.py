"""
Create Object Class Template (Python Class) from Object Class Meta (JSON Specification)
"""

import os
from copy import deepcopy
from pathlib import Path
import argparse
from src.utils import (
    indent,
    load_json,
    now_iso,
    print_run_config,
    print_run_summary,
    print_status,
    safe_json,
    save_file,
    write_json,
)
from src.object_model import (
    DeviceSpec,
    EventSpec,
    FunctionArgSpec,
    FunctionErrorSpec,
    FunctionResSpec,
    FunctionSpec,
    PropertySpec,
)
from .specification import (
    POWER_FUNCTIONS,
    active_section,
    normalize_power_contract,
    resolve_specification,
    resolve_specification_delta,
    supports_deferred_power,
)


def py_type(t: str,
            nullable=False):
    """Return the Python type."""
    t = (t or "string").lower()
    base = "str"
    if t in ("boolean", "bool"):
        base = "bool"
    elif t in ("integer", "int"):
        base = "int"
    elif t in ("number", "float", "double"):
        base = "float"
    elif t in ("object", "dict"):
        base = "dict"
    elif t in ("array", "list"):
        base = "list"
    # return f"{base} = None" if nullable else base
    return base


def prop_class(t: str):
    """Return the prop class."""
    t = (t or "string").lower()
    if t in ("boolean", "bool"): return "BoolProperty"
    if t in ("integer", "int"): return "IntProperty"
    if t in ("number", "float", "double"): return "FloatProperty"
    if t in ("object", "dict"): return "DictProperty"
    return "StringProperty"


def wrap_prop_init(prob_spec: PropertySpec) -> str:
    """Wrap the prop init."""
    cls = prop_class(prob_spec.ptype)
    params = [f"name={safe_json(prob_spec.key)}"]
    if prob_spec.description: params.append(f"description={safe_json(prob_spec.description)}")
    if prob_spec.default is not None: params.append(f"default={safe_json(prob_spec.default)}")
    if prob_spec.mode != 3: params.append(f"mode={safe_json(prob_spec.mode)}")
    if prob_spec.auto_reset: params.append(f"auto_reset={safe_json(prob_spec.auto_reset)}")
    if prob_spec.unit: params.append(f"unit={safe_json(prob_spec.unit)}")
    if cls in {"IntProperty", "FloatProperty"}:
        if prob_spec.minimum is not None:
            params.append(f"minimum={safe_json(prob_spec.minimum)}")
        if prob_spec.maximum is not None:
            params.append(f"maximum={safe_json(prob_spec.maximum)}")
        if prob_spec.step is not None:
            params.append(f"step={safe_json(prob_spec.step)}")
        if prob_spec.step_origin is not None:
            params.append(f"step_origin={safe_json(prob_spec.step_origin)}")
    if cls == "FloatProperty" and prob_spec.precision is not None:
        params.append(f"precision={safe_json(prob_spec.precision)}")
    if cls == "StringProperty":
        if prob_spec.pattern is not None:
            params.append(f"pattern={safe_json(prob_spec.pattern)}")
        if prob_spec.max_length is not None:
            params.append(f"max_length={safe_json(prob_spec.max_length)}")
        if prob_spec.choices:
            params.append(f"choices={safe_json(prob_spec.choices)}")
    if cls == "DictProperty" and prob_spec.schema is not None:
        params.append(f"schema={safe_json(prob_spec.schema)}")
    return "self.{k} = {cls}(\n{params}\n)".format(k=prob_spec.key, cls=cls, params=indent(",\n".join(params), 4))


def wrap_func(func_spec: FunctionSpec) -> str:
    """Wrap the func."""
    if func_spec.arguments:
        args_doc = ""
        args_anno = ""
        for arg in func_spec.arguments:
            arg_type = py_type(arg.atype, arg.nullable)
            if arg.nullable:
                if arg.default is None:
                    args_anno += f", {arg.name}: {arg_type} = None"
                else:
                    args_anno += f", {arg.name}: {arg_type} = {safe_json(arg.default)}"
            else:
                args_anno += f", {arg.name}: {arg_type}"
            constraints = []
            if arg.minimum is not None:
                constraints.append(f"min={arg.minimum}")
            if arg.maximum is not None:
                constraints.append(f"max={arg.maximum}")
            if arg.choices:
                constraints.append(f"choices={arg.choices}")
            constraints_str = f" ({', '.join(constraints)})" if constraints else ""
            args_doc += f"- {arg.name}: {arg.description}{constraints_str}\n"
        args_doc = args_doc.strip()
    else:
        args_doc = "(no arguments required)"
        args_anno = ""

    res_anno = " -> tuple[str, dict]"
    if len(func_spec.response) == 1:
        res = func_spec.response[0]
        res_doc = f"\t- {res.name}: {res.description} (type={res.rtype})"
        # 不在f-string的表达式部分使用反斜杠
        items = ",\n".join([f"{safe_json(res.name)}: None" for res in func_spec.response])
        res_body = f"response = {{\n{indent(items, 4)}\n}}"
    elif len(func_spec.response) > 1:
        res_doc = "\n".join(
            [f"\t- {res.name}: {res.description or ''} (type={res.rtype})" for res in func_spec.response])
        items = ",\n".join([f"{safe_json(res.name)}: None" for res in func_spec.response])
        res_body = f"response = {{\n{indent(items, 4)}\n}}"
    else:
        res_doc = "\t(no explicit response)"
        res_body = "response = {}"

    if func_spec.errorcodes:
        err_doc = "\n".join([f"- {err.name}: {err.description}" for err in func_spec.errorcodes])
    else:
        err_doc = "(no specified error codes)"

    signature = f"def {func_spec.key}(self{args_anno}){res_anno}:"

    doc = f"""
\"\"\"
{func_spec.description}

Args:
{args_doc}

Returns:
- Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
- Response Data: A dictionary containing response data (type=dict)
{res_doc}

Error Codes:
{err_doc}
\"\"\"
""".strip()

    body = f"""
code = "[NOT_IMPLEMENTED_FUNCTION] Function '{func_spec.key}' is not yet implemented."
{res_body}
return code, response
""".strip()

    wrapped_func = f"""
{signature}
{indent(doc, 4)}
{indent(body, 4)}
""".strip()
    return wrapped_func


def wrap_event(event_spec: EventSpec) -> str:
    """Wrap the event."""
    effect_doc = ""
    if event_spec.effect_properties:
        bullets = "\n".join(
            f"- {item['name']}: {item['description']}"
            for item in event_spec.effect_properties
        )
        effect_doc = f"\n\nEffect properties:\n{bullets}"
    wrapped_event = f"""
def _on_{event_spec.key}(self, context: dict) -> tuple[str, list[dict]]:
    \"\"\"
    {event_spec.description}{effect_doc}
    \"\"\"
    return "[NOT_IMPLEMENTED_EVENT] Event '{event_spec.key}' is not yet implemented.", []
""".strip()
    return wrapped_event


# The historical renderer above remains available for compatibility.  New
# generation uses the deterministic renderer below, which owns the power API.
def _property_spec(key: str, value: dict) -> PropertySpec:
    """Build a typed property specification from JSON."""

    value_block = value.get("value", {}) if isinstance(value, dict) else {}
    default = value_block.get(
        "default",
        False if key == "power" else None,
    )
    return PropertySpec(
        key=key,
        ptype=value.get("type", "string"),
        description=value.get("description", ""),
        default=default,
        mode=value.get("mode", 3),
        auto_reset=value.get("auto_reset", False),
        unit=value_block.get("unit"),
        minimum=value_block.get("minimum"),
        maximum=value_block.get("maximum"),
        step=value_block.get("step"),
        step_origin=value_block.get("step_origin"),
        precision=value_block.get("precision"),
        choices=value_block.get("choices"),
        pattern=value_block.get("pattern"),
        max_length=value_block.get("max_length"),
        schema=value_block.get("schema"),
    )


def _function_spec(key: str, value: dict) -> FunctionSpec:
    """Build a function specification from JSON."""

    parameters = value["parameters_schema"]
    required = set(parameters["required"])
    ordered = sorted(parameters["properties"].items(), key=lambda item: item[0] not in required)
    arguments = [
        FunctionArgSpec(
            name=name,
            atype=(next(kind for kind in item["type"] if kind != "null") if isinstance(item.get("type"), list) else item.get("type", "object")),
            description=item.get("description") or "",
            default=item.get("default"),
            minimum=item.get("minimum"),
            maximum=item.get("maximum"),
            choices=item.get("enum"),
            nullable=name not in required,
        )
        for name, item in ordered
    ]
    response = [
        FunctionResSpec(
            name=name,
            rtype=str(item.get("type") or "string"),
            description=item.get("description") or "",
        )
        for name, item in (value.get("response") or {}).items()
    ]
    errorcodes = [
        FunctionErrorSpec(
            name=name,
            description=description or "",
        )
        for name, description in (value.get("errorcodes") or {}).items()
    ]
    return FunctionSpec(
        key=key,
        description=value.get("description") or "",
        arguments=arguments,
        response=response,
        errorcodes=errorcodes,
    )


def _base_supports_deferred_power(args, meta: dict) -> bool:
    """Return whether the parent constructor accepts deferred power init."""

    source = str(meta.get("from") or "")
    json_value = getattr(args, "json", None)
    if not source or not json_value:
        return False
    json_path = Path(json_value)
    parent_stem = (json_path.parent / source).with_suffix("")
    # During a parallel run the parent's template can exist before its
    # completed source.  Once a runnable ``.py`` exists, however, it is the
    # authority: a fresh template must not make a child pass the new defer
    # keyword to an older completed parent.
    implementation = parent_stem.with_suffix(".py")
    try:
        implementation_content = implementation.read_text(encoding="utf-8")
    except OSError:
        implementation_content = None
    if implementation_content is not None:
        return supports_deferred_power(implementation_content)

    template = parent_stem.with_suffix(".template.py")
    try:
        template_content = template.read_text(encoding="utf-8")
    except OSError:
        template_content = None
    if template_content is not None:
        return supports_deferred_power(template_content)
    # In-memory/new parents are generated with the protocol.  When a parent
    # JSON is available but its source has not landed yet, only pass the
    # reserved keyword if that metadata actually exposes a power contract; a
    # non-power parent cannot accept the defer flag.
    parent_json = parent_stem.with_suffix(".json")
    if parent_json.is_file():
        try:
            parent_specification, _ = resolve_specification(parent_json)
        except (OSError, TypeError, ValueError):
            return False
        parent_properties = active_section(parent_specification, "properties")
        parent_functions = active_section(parent_specification, "functions")
        return "power" in parent_properties or any(
            name in parent_functions for name in POWER_FUNCTIONS
        )
    # If no parent metadata is available, retain the in-memory/new-generation
    # assumption used by isolated template rendering callers.
    return True


def _power_get_method() -> str:
    """Return the deterministic get_power implementation."""

    return """
def get_power(self) -> tuple[str, dict]:
    \"\"\"
    Get the current power state.
    \"\"\"
    code, value = self.power.get()
    if code != \"[PASS]\":
        return code, {}
    return \"[PASS]\", {\"power\": value}
""".strip()


def _power_set_method() -> str:
    """Return the deterministic set_power implementation."""

    return """
def set_power(self, value: bool) -> tuple[str, dict]:
    \"\"\"
    Set power and update access for active dependent properties.
    \"\"\"
    if self._power_initialized:
        current_code, current_value = self.power.get()
        if current_code != \"[PASS]\":
            return current_code, {}
        if type(value) is bool and current_value == value:
            return \"[PASS]\", {}
    code = self.power.set(value)
    if code != \"[PASS]\":
        return code, {}
    for prop in self._power_managed_properties:
        switch_code = prop.handle_power_switch(value)
        if switch_code != \"[PASS]\" and not switch_code.startswith(\"[NO_ACTION]\"):
            return switch_code, {}
    self._power_initialized = True
    return \"[PASS]\", {}
""".strip()


def _template_context(
    json_content: dict,
    args,
) -> tuple[dict, dict, dict | None]:
    """Return local, effective, and parent specifications for a template."""

    device_key = next(iter(json_content.keys()))
    local = deepcopy(json_content[device_key])
    meta = local.get("meta", {}) if isinstance(local.get("meta"), dict) else {}
    source = str(meta.get("from") or "")
    parent = None
    effective = deepcopy(local)
    json_value = getattr(args, "json", None)
    json_path = Path(json_value) if json_value else None
    if json_path is not None and json_path.is_file():
        effective, chain = resolve_specification(json_path)
        if source and len(chain) > 1:
            parent, _ = resolve_specification(chain[-2])
    if parent is not None:
        # Materialize the standard power API before checking inheritance.
        parent = normalize_power_contract(parent, is_base=True)
    local = normalize_power_contract(
        local,
        parent=parent,
        is_base=not bool(source),
    )
    if parent is not None:
        # ``code_gen`` is also used directly by isolated callers, not only by
        # ``update_json_content``.  Materialize details for explicitly local
        # delta members in memory so a child refinement does not lose inherited
        # defaults or constraints, while keeping unaffected members omitted.
        materialized = resolve_specification_delta(
            parent,
            str(meta.get("name") or device_key),
            local,
        )
        # Use the resolved parent-backed view for runtime scaffolding too.
        effective = materialized
        for section_name in ("properties", "functions", "events"):
            local_section = local.get(section_name, {})
            local_update = (
                local_section.get("update", {})
                if isinstance(local_section, dict)
                else {}
            )
            resolved_update = materialized[section_name]["update"]
            if isinstance(local_update, dict):
                local_section["update"] = {
                    key: resolved_update[key]
                    for key in local_update
                    if key in resolved_update
                }
    effective = normalize_power_contract(
        effective,
        # ``effective`` is already a fully resolved class body.  Treat it as
        # the owner view so inherited methods remain visible to
        # callers that inspect the resolved context.
        is_base=True,
    )
    return local, effective, parent


def _base_module(meta: dict, args, base_class: str | None) -> str:
    """Resolve an inherited template's relative import when metadata is sparse."""

    explicit = str(meta.get("base_module") or "")
    if explicit:
        return explicit
    source = str(meta.get("from") or "")
    if not source:
        return "." + str(base_class or "")
    json_value = getattr(args, "json", None)
    if not json_value:
        return "." + str(base_class or "")
    json_path = Path(json_value)
    parent_path = (json_path.parent / source).with_suffix("")
    relative = Path(os.path.relpath(parent_path, json_path.parent))
    parts = list(relative.parts)
    hops = 0
    while parts and parts[0] == "..":
        hops += 1
        parts.pop(0)
    if not parts:
        return "." * (hops + 1)
    return "." * (hops + 1) + ".".join(parts)


def code_gen(json_content: dict, args) -> str:
    """Generate the new deterministic template with power methods."""

    device_key = next(iter(json_content.keys()))
    dev, effective, parent = _template_context(json_content, args)
    json_value = getattr(args, "json", None)
    json_source = str(json_value) if json_value else "(in-memory specification)"
    meta = dev.get("meta", {})
    base_class = meta.get("base_class")
    if not base_class and meta.get("from"):
        base_class = Path(str(meta["from"])).stem
    # Infer the class name before deriving a fallback relative module.  This
    # matters for callers that render an in-memory child without an ``args.json``
    # path: ``from .Parent import Parent`` is still a valid deterministic
    # import, whereas ``from . import Parent`` is not.
    base_module = _base_module(meta, args, base_class)
    class_name = meta.get("name") or device_key
    class_description = meta.get("description", "")
    version = meta.get("version", "")
    print_status(f"Generating code for class {class_name}", "info")

    prop_node = dev.get("properties", {}).get("update", {})
    prop_disabled = set(dev.get("properties", {}).get("disabled", []) or [])
    properties = [
        _property_spec(key, value)
        for key, value in prop_node.items()
        if key not in prop_disabled
    ]
    func_node = dev.get("functions", {}).get("update", {})
    func_disabled = set(dev.get("functions", {}).get("disabled", []) or [])
    functions = [
        _function_spec(key, value)
        for key, value in func_node.items()
        if key not in func_disabled
        and key not in POWER_FUNCTIONS
    ]
    event_node = dev.get("events", {}).get("update", {})
    event_disabled = set(dev.get("events", {}).get("disabled", []) or [])
    events = []
    for event_key, event_spec in event_node.items():
        if event_key in event_disabled:
            continue
        if not isinstance(event_spec, dict):
            raise TypeError(
                f"events.update.{event_key} must be an object with description and effect_properties"
            )
        effect_properties = event_spec.get("effect_properties", [])
        if not isinstance(event_spec.get("description"), str):
            raise TypeError(f"events.update.{event_key}.description must be a string")
        if not isinstance(effect_properties, list) or not all(
            isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and isinstance(item.get("description"), str)
            for item in effect_properties
        ):
            raise TypeError(
                f"events.update.{event_key}.effect_properties must be a list of name/description objects"
            )
        events.append(
            EventSpec(
                key=event_key,
                description=event_spec["description"],
                effect_properties=effect_properties,
            )
        )

    effective_properties = active_section(effective, "properties")
    parent_properties = active_section(parent, "properties") if parent is not None else {}
    parent_functions = active_section(parent, "functions") if parent is not None else {}
    power_active = "power" in effective_properties
    # A child-level disable removes the inherited power protocol as well.  Do
    # not pass a power keyword (or invoke the parent's finalizer) after that
    # removal; otherwise a disabled child would still call ``set_power``.
    parent_power = "power" in parent_properties and "power" not in prop_disabled
    power_protocol = power_active or parent_power
    parent_has_power_api = (
        all(name in parent_functions for name in POWER_FUNCTIONS)
        and _base_supports_deferred_power(args, meta)
    )
    emit_power_methods = power_active and (
        not base_class or not parent_has_power_api
        or any(name in func_node and name not in func_disabled for name in POWER_FUNCTIONS)
    )
    power_spec = effective_properties.get("power", {})
    power_value = (
        power_spec.get("value", {}).get("default", False)
        if isinstance(power_spec, dict)
        else False
    )
    if power_value is None:
        power_value = False

    local_property_keys = {item.key for item in properties}
    init_args = [
        f"{item.key}: {py_type(item.ptype, True)} = None"
        for item in properties
    ]
    keyword_args: list[str] = []
    if base_class and power_protocol and "power" not in local_property_keys:
        keyword_args.append("power: bool | None = None")
    if power_protocol:
        keyword_args.append("_defer_power_init: bool = False")
    signature_parts = list(init_args)
    if keyword_args:
        signature_parts.append("*")
        signature_parts.extend(keyword_args)
    if base_class:
        signature_parts.append("**base_kwargs")
    init_sig = (
        f"def __init__(self, {', '.join(signature_parts)}) -> None:"
        if signature_parts
        else "def __init__(self) -> None:"
    )

    header = f"""
# This file is auto-generated. Do not edit manually.
# Source JSON
#     {json_source}
# Generation command
#     python -m src.world_distill.pipeline.model_creation.object_class_template_creator --json {json_source}
# Generated at
#     {now_iso()}

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
    """.strip()
    if base_class:
        header += f"\nfrom {base_module} import {base_class}"

    spec = DeviceSpec(
        devkey=device_key,
        class_name=class_name,
        description=class_description,
        version=version,
        properties=properties,
        functions=functions,
        events=events,
    )
    class_doc = f"""
\"\"\"
{class_name}
Description: {spec.description or '-'}
Version: {version or '-'}
Base: {base_class or '-'}
\"\"\"
    """.strip()

    init_lines: list[str] = []
    if power_protocol:
        init_lines.append(
            f"_power_init_value = power if power is not None else {safe_json(power_value)}"
        )
    if base_class:
        init_lines.append(f"# initialize base {base_class} class")
        call_args: list[str] = []
        # Only the deterministic parent template promises the reserved
        # ``power`` keyword.  Historical parents are deliberately left
        # untouched and may have a narrower constructor; initialize them with
        # their own defaults, then let this child's finalizer apply
        # the requested state.
        parent_supports_deferred_power = _base_supports_deferred_power(args, meta)
        if parent_power and parent_supports_deferred_power:
            call_args.append("power=_power_init_value")
        if parent_power and parent_supports_deferred_power:
            call_args.append("_defer_power_init=True")
        call_args.append("**base_kwargs")
        init_lines.append(f"super().__init__({', '.join(call_args)})")

    init_lines.append("# define properties")
    init_lines.extend(wrap_prop_init(item) for item in properties)
    if "power" in local_property_keys:
        # A child may refine the inherited power property's metadata.  The
        # parent receives the requested value for compatibility, but the
        # child's replacement must receive it as well before the final,
        # template-owned power transition runs.
        init_lines.append("code = self.power.internal_set(_power_init_value)")
    setters = [
        f"if {item.key} is not None: code = self.{item.key}.internal_set({item.key})"
        for item in properties
        if item.key != "power"
    ]
    if setters:
        init_lines.append("\n# initialize properties")
        init_lines.extend(setters)

    local_disabled_properties = prop_disabled - {item.key for item in properties}
    if local_disabled_properties:
        init_lines.append("\n# disable inherited properties")
        init_lines.extend(
            f"self.{key}.chmod(0)" for key in sorted(local_disabled_properties)
        )
    if power_protocol:
        managed_names = [
            name
            for name, item in effective_properties.items()
            if name != "power"
            and isinstance(item, dict)
            and item.get("mode", 3) != 0
        ]
        managed_tuple = (
            "()"
            if not managed_names
            else "(" + ", ".join(f"self.{name}" for name in managed_names) + ",)"
        )
        init_lines.append(f"self._power_managed_properties = {managed_tuple}")
        init_lines.append("self._power_initialized = False")
    init_lines.append(
        f"""
self._disabled = {{
    'properties': {sorted(prop_disabled)},
    'functions': {sorted(func_disabled)},
    'events': {sorted(event_disabled)}
}}
""".strip()
    )
    if power_protocol:
        init_lines.append("\nif not _defer_power_init:")
        init_lines.append("    self.set_power(_power_init_value)")
    init_body = "\n".join(init_lines) if init_lines else "pass"

    chunks: list[str] = []
    if power_active and emit_power_methods:
        chunks.extend((_power_get_method(), _power_set_method()))
    for function in functions:
        chunks.append(wrap_func(function))
    for event in events:
        chunks.append(wrap_event(event))
    for fname in sorted(func_disabled):
        if fname in POWER_FUNCTIONS:
            continue
        chunks.append(
            f"""
def {fname}(self, *args, **kwargs):
    \"\"\"
    Disabled function (overrides base implementation if any).
    \"\"\"
    return \"[DISABLED_FUNCTION] Function '{fname}' is disabled in {class_name}.\", {{}}
""".strip()
        )
    for ename in sorted(event_disabled):
        chunks.append(
            f"""
def _on_{ename}(self, context: dict) -> tuple[str, list[dict]]:
    \"\"\"
    Disabled event for this device class.
    \"\"\"
    return \"[DISABLED_EVENT]\", []
""".strip()
        )
    joined_chunks = "\n\n".join(chunks) if chunks else "pass"
    declarations_block = ""
    if "process" in effective:
        declarations_block += f"\n\n    PROCESS = {safe_json(effective['process'])}"
    class_decl = (
        f"class {class_name}({base_class}):"
        if base_class
        else f"class {class_name}:"
    )
    return f"""
{header}

{class_decl}
{indent(class_doc, 4)}{declarations_block}

    {init_sig}
{indent(init_body, 8)}

{indent(joined_chunks, 4)}
""".strip()


def update_json_content(json_path: Path) -> dict:
    """Materialize only locally updated members against the base chain."""
    json_content = load_json(json_path)
    device_key = next(iter(json_content.keys()))
    dev = json_content[device_key]
    
    if dev["meta"].get("from"):
        from_path = (json_path.parent / dev["meta"]["from"]).resolve()
        print_status(f"Resolving base JSON spec from {from_path}", "info")
        json_content[device_key]["meta"]["base_class"] = from_path.stem
        
        relative_base = Path(
            os.path.relpath(from_path.with_suffix(""), json_path.parent)
        )
        relative_parts = list(relative_base.parts)
        parent_hops = 0
        while relative_parts and relative_parts[0] == "..":
            parent_hops += 1
            relative_parts.pop(0)
        if not relative_parts or any(part in {".", ".."} for part in relative_parts):
            raise ValueError(f"cannot derive relative base import from {from_path}")
        base_module = "." * (parent_hops + 1) + ".".join(relative_parts)
        json_content[device_key]["meta"]["base_module"] = base_module
        print_status(f"Resolved base module as {base_module}", "info")

        resolved, _ = resolve_specification(json_path)
        for section_name in ("properties", "functions", "events"):
            local_section = dev.get(section_name, {})
            local_update = local_section.get("update", {})
            resolved_update = resolved[section_name]["update"]
            local_section["update"] = {
                key: resolved_update[key]
                for key in local_update
                if key in resolved_update
            }

        parent_specification, _ = resolve_specification(from_path)
        parent_specification = normalize_power_contract(
            parent_specification,
            is_base=True,
        )
        json_content[device_key] = normalize_power_contract(
            json_content[device_key],
            parent=parent_specification,
            is_base=False,
        )

        # save updated json_content
        updated_json_path = json_path.parent / f"{json_path.stem}.updated.json"
        write_json(updated_json_path, json_content)
        print_status(f"Successfully loaded updated JSON spec and saved to {updated_json_path}", "success")
    else:
        json_content[device_key] = normalize_power_contract(
            json_content[device_key],
            is_base=True,
        )
        print_status(f"Successfully loaded base JSON spec from {json_path}", "success")
    
    return json_content


def main(args):
    """Run the command-line entry point."""
    json_path = Path(args.json)
    output_path = Path(args.output)

    print_run_config(
        "Object class template",
        (
            ("Specification", json_path),
            ("Output", output_path),
        ),
    )
    json_content = update_json_content(json_path)
    final_code = code_gen(json_content, args)
    save_file(output_path, final_code)
    print_run_summary(
        "Object class template",
        "PASS",
        (("Output", output_path),),
    )
    return str(output_path), {"code": "[PASS]"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Object Class Template (Python Class) from Object Class Meta (JSON Specification).")
    parser.add_argument("--json", type=str, required=True, help="Path to the Object Class Meta file.")
    args = parser.parse_args()
    args.output = str(Path(args.json).parent / f"{Path(args.json).stem}.template.py")
    main(args)
