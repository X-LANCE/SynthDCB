"""Shared prompts for declared device capabilities, code, and tests."""

from __future__ import annotations



GENERAL_SYSTEM_PROMPT = """
# Device Control Bench model generation

Create deterministic device models for a simulated physical world used to test tool-calling agents. An Object Class is an instantiable device type. Properties hold state, public functions are the agent-facing tool API, and private `_on_*` events update the device's own state and may emit physical effects on the surrounding Space.

## Authority and scope

Apply information in this order:
1. The current device request, representative acceptance contract, and any inherited base specification.
2. The supplied JSON schema, property runtime contract, Domain Space catalog, and generated-code security contract.
3. Fixed and retrieved references, which are patterns only and may never override 1 or 2.

An explicitly supplied acceptance contract is a minimum coverage requirement. Preserve its required parent, properties, functions, disabled inherited members, events, and behavioral requirements. You may add a small justified capability, but never simplify below that floor.

Do not copy an example's capabilities, magic constants, or behavior unless the current device request independently requires them. Model requested Phone/Car system settings, networking, notifications, schedules, collections, and infotainment as local deterministic state. Do not invent unrelated capabilities or access real services. Phone modules have no Space and no separate electrical power switch unless explicitly requested. Car devices use only their allowed physical or functional Space; the Space owns overall results, while the Device owns control settings. Never copy Home-only effect properties into another Domain. A supplied Domain property catalog is authoritative.
"""


HOME_ENVIRONMENT_EFFECT_RULES = """
## Domain Space effects

These rules apply to the supplied Domain catalog. Phone has no Space and emits no Space effects; its minute ticks may update its own state. Car uses the properties allowed for its actual containing Space, including functional Spaces. For Home only, the mutable Space targets are `temperature`, `humidity`, `illuminance`, `noise`, and `air_quality`.

- Events may implement a device's own timed process even without any Space effect. Otherwise add events only for direct physical effects on those Space targets.
- For ordinary device effects use `tick` for continuous or minute-by-minute output, and `after_action` for an effect recalculated after a successful public mutation that changes device state. Cross-module dependency receivers may additionally declare dependency_changed and implement _on_dependency_changed(context). The runtime supplies context["dependencies"] keyed by source object ID, each with its declared properties. Recompute only the receiver's own state, idempotently, using internal_set; return no Space effects. The World owns contains/depends_on relations. Do not store foreign object IDs as device properties.
- Represent each physical effect with exactly one event trigger. Use `tick` for sustained output such as conditioning or active audio; use `after_action` for state-change output such as a lamp or curtain contribution. Never duplicate the same target and behavior under both triggers.
- A curtain or blind changes `illuminance`; an actively playing speaker changes `noise`. These are Space effects, not device-internal sensor properties.
- In a JSON specification, an event description states only physical behavior and device-property dependencies. Never put `context` keys, hook/dispatcher details, source/target IDs, effect-dictionary syntax, or test instructions in specification prose.
- `effect_properties` contains only actual device properties needed to decide the effect; it never contains Space fields or implementation details.
- Event context provides `object_id`, `space_id`, and `space_state`. Use direct indexing, without fallback defaults, for the keys the effect actually needs. A `set_contribution` event normally needs the two IDs but does not need to read aggregate `space_state`.
- `context["pre_state"]` is the entire World snapshot, not a device property dictionary. Previous properties of this device are exactly `context["pre_state"]["objects"][context["object_id"]]["properties"]`. Event tests must construct that same nested shape. `context["time_state"]` contains `date`, `clock`, `timezone`, and `elapsed_minutes`; tick context also includes `minutes`.
- When ambient room state is semantically needed, treat `space_state` as its source of truth. Do not duplicate room sensor state inside the device.
- `set_contribution` is an absolute contribution from one source, not the aggregate room value. Emit it whenever its event is dispatched, including a zero contribution needed to clear stale output; never compare its value with the aggregate `space_state` value. For `approach`, return no effect when the room is already at the target. Emit only `set_contribution`, `delta`, or `approach` effects supported by the supplied property catalog.
"""


PROPERTY_RUNTIME_CONTRACT = """
## Property runtime contract

Public Object Class functions return `(code: str, response: dict)` and events return `(code: str, effects: list[dict])`. Property wrappers deliberately use a smaller internal API.

- `self.<property>.get()` returns exactly `(code, value)`, using `None` as the value when a read fails.
- `self.<property>.set(value)` and `internal_set(value)` return exactly one status-code string, never a tuple. Use `code = self.<property>.set(value)`; never unpack a property write.
- A public Object Class function converts a failed property read or write into `(code, {})`; an event converts it into `(code, [])`. Validation failures must leave all state unchanged.
- The only success code is the exact string `[PASS]`; never use `success`, `ok`, or another spelling.
- `mode=3` is read-write, `mode=2` is read-only, and `mode=0` is disabled.
- Boolean values are accepted only by `BoolProperty`. `IntProperty` rejects booleans. `FloatProperty` accepts integers or floats but rejects booleans.
- Shared property keyword arguments are `name`, `default`, `mode`, `auto_reset`, `unit`, `description`, and `allow_none`.
- `IntProperty` additionally supports `minimum`, `maximum`, `step`, and `step_origin`.
- `FloatProperty` additionally supports `minimum`, `maximum`, `step`, `step_origin`, and `precision`.
- `StringProperty` additionally supports `max_length`, `pattern`, `choices`, and `case_sensitive`; `DictProperty` supports `schema`.
- Do not pass a constraint to a property type that does not support it.
- Every emitted effect is one dictionary with exactly these top-level keys: `trigger`, `source`, `target`, `function`, and `parameters`. Never emit the legacy `op` key or put `property`, `value`, `unit`, or `rate_per_minute` at the top level. `parameters` contains `property`, `value`, and `unit`; an `approach` effect additionally contains `rate_per_minute`. For example: `{"trigger": "tick", "source": context["object_id"], "target": context["space_id"], "function": "approach", "parameters": {"property": "temperature", "value": target, "rate_per_minute": rate, "unit": "degC"}}`.
- Normalize computed numeric effect values and rates to the target property's catalog precision before returning them. Never expose binary floating-point artifacts such as `0.6000000000000001` when the contract specifies `0.6`.
"""


GENERATED_CODE_SECURITY_RULES = """
## Generated-code security contract

- Implementations may import only `__future__`, `typing`, `collections`, `dataclasses`, `enum`, `functools`, `math`, `re`, and `src.object_model`.
- An inherited template may additionally contain one orchestrator-supplied relative import of its authoritative base class. Preserve that exact import; do not add other project-relative imports.
- Tests may additionally import `unittest` and the target module by relative import.
- Never use `eval`, `exec`, `compile`, `open`, `getattr`, `setattr`, `hasattr`, `delattr`, dynamic imports, dunder introspection, filesystem or environment APIs, subprocesses, multiprocessing, sockets, HTTP clients, debuggers, or native libraries.
- The sole dunder exception is the exact `super().__init__(...)` call already present in an authoritative inherited template; it is initialization, not introspection.
- Do not read secrets, write files, access a network, or create processes.
- Security validation is a hard gate and tests may not bypass it.
"""


SPECIFICATION_GUIDELINES = """
## Specification design rules

- The deterministic electrical power contract disables ALL non-power property public access while off. This is authoritative over reference examples: every non-power getter/action on a powered device declares reads of power and a power=true precondition. Configuration values persist but are read or changed only while on. Do not promise off-state getters/setters. Internal event logic uses Property.value/internal_set and can pause a process after power-off.

- Follow the supplied schema exactly. Use `meta`, `properties`, `functions`, and `events`, each with the required `update` and `disabled` shapes.
- Property access is integer `mode`; never invent `access`, `args`, `return`, or `effect_behavior` keys.
- An inherited-class JSON specification is a delta, not a flattened copy of its base. Reuse inherited properties, functions, and events by omitting their names from `update`; keep an `update` object empty when the child has no new or observably changed member in that section. A different class name, implementation mechanism, or description wording alone is not an observable change and never justifies repeating a base member. Use `disabled` only for inherited removals. If the request says the child inherits all capabilities and adds no observable state, tool, or effect difference, all three `update` objects must be empty.
- When an inherited member truly changes, include a schema-complete entry for only that member and leave every unaffected base member inherited by omission. A complete child JSON response means that all required sections are present; it does not mean copying inherited entries into those sections.
- Omitting an inherited property from `properties.update` means the child constructor must leave its definition and initialization to `super().__init__`. Omitting an inherited function or event means the child class must not redeclare or override it. The deterministic template materializes base JSON details only for names explicitly present in the child `update` objects.
- A device-wide electrical state must use the property name `power` everywhere in the JSON specification. By default define it as a boolean with `mode=3` and `value.default=false`; an authoritative request or inherited base may change its access mode or default, but never its name. The only power API in a new specification is `get_power()` and `set_power(value: bool)`. The deterministic template owns both implementations; do not add aliases or natural-action wrappers. Never use `is_on`, `on`, `running`, `powered`, `power_state`, `operating`, or any other expression for the device-wide power state, and never encode whole-device power-off as an `off` choice inside a mode or status property.
- Reserve the bare name `power` for that boolean device-wide state. Name a non-boolean quantity such as microwave or heating output `power_level`, `power_percent`, or another specific term instead.
- Use only constraints supported by the declared property type: integer uses `minimum`, `maximum`, `step`, and `step_origin` but never `precision`; float may additionally use `precision`; string uses `choices`, `pattern`, and `max_length`; object/dict uses `schema`; boolean uses none of those typed constraints.
- For an unprofiled class, prefer 2-7 essential properties. For a class with an authoritative capability baseline, its complete required property set takes precedence over this size heuristic. Each readable property has a focused getter; each writable property has a focused setter. Dict properties use focused validated tools appropriate to the device contract.
- Add a small number of non-power device actions when they make agent control clearer: for example `open`/`close`/`stop`, `play`/`pause`/`stop`, or `lock`/`unlock`. These complement, not replace, required property accessors. Do not reduce the API to generic CRUD when a normal device-level action is obvious.
- Function descriptions define observable behavior, exact argument constraints, responses, and failure semantics. Avoid unspecified random behavior and arbitrary constants. Invalid inputs leave state unchanged.
- Do not implement fake authentication. A credential string is not proof of identity; omit authentication behavior unless the request supplies a complete deterministic policy representable in this simulation.
"""

CAPABILITY_RULES = """
## Declared capabilities and independent processes

- Every function declares `parameters_schema` (a JSON Schema object with properties, required and additionalProperties=false), `mutation`, `reads`, `writes`, and `semantics`. parameters_schema is the ONLY parameter declaration: do not emit a separate arguments map. The template derives signatures, defaults, docs and tool schemas from it. Include full array/item/object constraints and useful examples for open string parameters. Reads/writes name only the device's own properties.
- Use semantics kind `read` with property and response_key; `set` with property and parameter; or `update` with fields mapping property names to {parameter: name} or {value: literal}. Declare interlocks as preconditions mapping properties to required values. A setter that unconditionally assigns a validated parameter has reads=[] and writes=[property]; preserving the old value on failure is not a read. Include only actual state dependencies (such as power or a mode interlock) in reads. All actual writes, including linked changes, must be declared.
- Collection properties are dictionaries keyed by string IDs. Use collection_add, collection_update, collection_delete and collection_read domain actions; never expose a generic setter for collections. `fields` maps record fields to parameter or literal bindings; update/delete/read declare id_parameter. `argument_sources` maps an ID parameter to {property: collection_name, field: "$key"}; other fields can reference a named field of an existing record. Add returns the new ID under response_key. Only the named records/fields may change; preserve every old record on add. Optional update parameters omitted by the caller leave fields unchanged.
- A collection-key precondition may use `preconditions: {paired_devices: {contains_key: {parameter: device_id}}}`. The same parameter must have `argument_sources: {device_id: {property: paired_devices, field: "$key"}}`. The sampler binds an existing key, and execution preview checks membership after parameters are bound. Keep the action code membership check for invalid direct calls. Other preconditions are literal property values or {one_of: [values]}; never invent expression strings or conditional-update predicates. A declared precondition applies to every call. If a state restriction applies only to some parameter values (for example enabling requires device_present but disabling does not), enforce that conditional restriction in the action code and describe it with accurate reads; do not declare it as an unconditional precondition.
- Use `custom` plus a concrete reason only when the supplied semantic vocabulary cannot express the operation. This capability is reported as not sampleable. A setter with a conditional safety interlock still has kind=set: declare its successful mapping and all actual reads/writes, describe the interlock, and enforce it in code. Do not use custom merely because some inputs are rejected.
- Timed devices expose ONE independent process with one or more modes. Declare a top-level `process`: mode_property, start_function, optional pause_function and resume_function, and modes mapping each mode to [{phase: name, minutes: integer}]. Each phase's minutes is a positive integer or {property: name} referring to a positive integer duration setting. Use that exact source for all timing and remaining/progress calculations; freeze settings while running/paused. Timer and stopwatch are separate processes and must not share one Device. Non-process devices omit `process`.
- Process state persists in properties: status (idle/running/paused/completed), phase (idle, the active phase name, or completed), remaining_minutes, started_at_minute, progress_minutes, plus the mode property. All five standard state properties use mode=2 and only internal_set writes. Expose getters, and domain start/pause/resume actions with process_start/process_pause/process_resume semantics. process_start declares mode_parameter. No setters for derived state.
- All state needed to restore a running process belongs to constructor properties. For a powered process, after_action changes running to paused when power becomes false; powering on only restores access. Explicit resume retains progress. Tick cannot advance an unpowered process. Declare set_power writes of status. A configurable duration uses a phase minutes={property: name} binding so the declared process and runtime agree. Preconditions may use {one_of: [values]} when, for example, start/configuration is allowed in both idle and completed. Never restart a running process in __init__. On start initialize progress=0; on resume retain progress. _on_after_action uses context["time_state"] and context["pre_state"] to set started_at_minute = elapsed_minutes-progress_minutes on a transition into running. _on_tick computes progress from that origin, advances phase at exact minute boundaries, remaining=max(total-progress,0), and sets status/phase to completed at the end. Paused/idle/completed state does not advance. context["time_state"] includes date, clock, timezone, elapsed_minutes.
- Tool declarations and event effect_properties are read from the JSON specification by the runtime; do not duplicate them as Python class constants. The template's PROCESS declaration is authoritative data; code completion preserves it exactly. _on_tick may update own properties with internal_set and return [PASS], [] when no Space effects are needed. Process hooks must include every needed device property in effect_properties, including when emitting no Space effect. No public tick or alternate scheduler.
- Validate all public arguments and all preconditions before the first write. Read functions cannot change state. Unit tests cover invalid-input atomicity, collection preservation, declared mappings, mode stages and running restoration.
"""


BASE_SYSTEM_PROMPT = (
    GENERAL_SYSTEM_PROMPT
    + HOME_ENVIRONMENT_EFFECT_RULES
    + SPECIFICATION_GUIDELINES
    + CAPABILITY_RULES
    + """
## Task

Produce one schema-complete Object Class JSON specification. Respond with reasoning in <think> and exactly one JSON object in <answer> following the supplied schema.
"""
)


BASE_USER_PROMPT = """## Authoritative schema and bounded reference context

{reference_knowledge}

## Device request

- Name: `{name}`
- Domain: `{domain}`
- Description: `{desc}`

Create the requested base Object Class. Satisfy the request without importing unrequested capabilities from examples. Respond with reasoning in <think> and exactly one JSON object in <answer> following the supplied schema.
"""


INHERIT_USER_PROMPT = """## Authoritative schema and bounded reference context

{reference_knowledge}

## Device request

- Name: `{name}`
- Domain: `{domain}`
- Description: `{desc}`

## Authoritative base specification

```json
{base_json}
```

The new Object Class inherits this base. Its JSON is a delta: reuse every unaffected base member by leaving it out of `update`, add only new members or members with an observable contract change, and use section-level `disabled` lists only for inherited removals. Merely changing the class name, mechanism, or wording is not a contract change. If the request adds no observable difference, return empty `update` objects for properties, functions, and events. Every omitted property remains initialized by the base constructor, and every omitted function or event remains implemented by the base class; do not repeat a member to make it appear in the child template.

Respond with reasoning in <think> and exactly one schema-complete child JSON object in <answer>. Include every required section, but do not copy inherited members merely to make the response look complete.
"""


META_REPAIR_USER_PROMPT = """## Authoritative schema and bounded reference context

{reference_knowledge}

## Repair request

- Name: `{name}`
- Domain: `{domain}`
- Description: `{desc}`

The previous candidate was:
```json
{current_candidate}
```

Deterministic validation errors:
```
{errors}
```

Correct every reported contract error while preserving the requested device semantics. Respond with reasoning in <think> and exactly one schema-complete JSON object in <answer>. For an inherited candidate, preserve the delta form required above instead of copying unaffected base members.
"""


CODE_COMPLETION_SYSTEM_PROMPT = (
    GENERAL_SYSTEM_PROMPT
    + HOME_ENVIRONMENT_EFFECT_RULES
    + PROPERTY_RUNTIME_CONTRACT
    + CAPABILITY_RULES
    + GENERATED_CODE_SECURITY_RULES
    + """
## Implementation task

Fill every `[NOT_IMPLEMENTED_FUNCTION]` and `[NOT_IMPLEMENTED_EVENT]` body in the supplied deterministic template.

- Preserve imports, class declarations, `__init__`, property definitions, method signatures, and docstrings exactly.
- `get_power` and `set_power` are concrete template-owned methods, never completion targets. Do not rewrite, wrap, alias, or add another power method. Preserve the template's final power initialization and `handle_power_switch` calls exactly.
- In an inherited template, only members explicitly named by the child JSON `update` objects appear as local definitions. Complete only those marked local bodies. Never add an inherited property initialization, function, or event that is absent from the template.
- Implement only behavior promised by the template docstrings/specification.
- Use direct property wrapper operations and propagate failures before any dependent mutation. For multi-property updates, validate inputs before the first mutation so invalid input cannot partially change state.
- High-level bounded increase/decrease actions clamp only when their docstring says they clamp or remain within bounds; otherwise return the wrapper error.
- Respond with reasoning in <think> and exactly one complete `python` fenced code block in <answer>.
"""
)


CODE_REPAIR_SYSTEM_PROMPT = (
    GENERAL_SYSTEM_PROMPT
    + HOME_ENVIRONMENT_EFFECT_RULES
    + PROPERTY_RUNTIME_CONTRACT
    + CAPABILITY_RULES
    + GENERATED_CODE_SECURITY_RULES
    + """
## Implementation repair task

Return a complete corrected implementation matching the authoritative template and its public contract. Fix every reported error. Preserve the template's API, property declarations, signatures, and docstrings, but replace any faulty method/event body in the current candidate. Respond with reasoning in <think> and exactly one complete `python` fenced code block in <answer>.
- If the template constructor accepts `_defer_power_init`, `__init__`, `get_power`, and `set_power` are deterministic template-owned scaffolding. Copy them exactly, preserve every `handle_power_switch` call, and never add legacy power aliases.
"""
)


CODE_SPECIFICATION_METHODS_SYSTEM_PROMPT = (
    GENERAL_SYSTEM_PROMPT
    + HOME_ENVIRONMENT_EFFECT_RULES
    + PROPERTY_RUNTIME_CONTRACT
    + CAPABILITY_RULES
    + GENERATED_CODE_SECURITY_RULES
    + """
Implement the listed methods from the authoritative device specification.
The framework supplies the constructor and initializes every declared property as
the corresponding property wrapper. It inserts your method bodies into its fixed
template, retaining original imports, signatures, docstrings and declarations.
Return exactly one class containing exactly the listed methods with the supplied
signatures and complete bodies. Do not include imports, a constructor, class
attributes, extra helper methods, or module-level statements. Use builtins and
existing property wrappers. Validate inputs before mutation and preserve atomic
failure behavior. Implement only the specified behavior. Return reasoning in
<think> and one complete python fenced code block in <answer>.
"""
)

CODE_SPECIFICATION_METHODS_USER_PROMPT = """Class name: {name}

Authoritative specification:
```json
{specification}
```

Required method signatures:
```python
{signatures}
```

Previous validation feedback:
{feedback}
"""


CODE_COMPLETION_BASE_USER_PROMPT = """## Bounded implementation references

{reference_knowledge}

## Device request

- Name: `{name}`
- Domain: `{domain}`
- Description: `{desc}`

## Authoritative template

```python
{template_code}
```

Complete the template. Respond with reasoning in <think> and exactly one complete `python` fenced code block in <answer>.
"""


CODE_COMPLETION_INHERIT_USER_PROMPT = """## Bounded implementation references

{reference_knowledge}

## Device request

- Name: `{name}`
- Domain: `{domain}`
- Description: `{desc}`

## Authoritative base implementation

```python
{base_code}
```

## Authoritative inherited template

```python
{template_code}
```

Complete only the child-local `[NOT_IMPLEMENTED_FUNCTION]` and `[NOT_IMPLEMENTED_EVENT]` bodies already present in the inherited template. Preserve `super().__init__`, do not initialize unchanged inherited properties, and do not add inherited functions or events that are absent from the template. Respond with reasoning in <think> and exactly one complete `python` fenced code block in <answer>.
"""


CODE_FIX_BASE_USER_PROMPT = """## Bounded implementation references

{reference_knowledge}

## Device request

- Name: `{name}`
- Domain: `{domain}`
- Description: `{desc}`

## Current candidate

```python
{current_code}
```

## Deterministic validation errors

```
{errors}
```

## Authoritative template

```python
{template_code}
```

Respond with reasoning in <think> and exactly one complete corrected `python` fenced code block in <answer>.
"""


CODE_FIX_INHERIT_USER_PROMPT = """## Bounded implementation references

{reference_knowledge}

## Device request

- Name: `{name}`
- Domain: `{domain}`
- Description: `{desc}`

## Authoritative base implementation

```python
{base_code}
```

## Current candidate

```python
{current_code}
```

## Deterministic validation errors

```
{errors}
```

## Authoritative inherited template

```python
{template_code}
```

Repair only child-local definitions present in the authoritative inherited template. Do not add or copy inherited property initialization, functions, or events that are absent from that template. Respond with reasoning in <think> and exactly one complete corrected `python` fenced code block in <answer>.
"""


OBJECT_CLASS_VERIFIER_SYSTEM_PROMPT = (
    GENERAL_SYSTEM_PROMPT
    + HOME_ENVIRONMENT_EFFECT_RULES
    + PROPERTY_RUNTIME_CONTRACT
    + CAPABILITY_RULES
    + GENERATED_CODE_SECURITY_RULES
    + """
## Test-generation task

Write an independent `unittest` suite. The JSON specification is authoritative and is already resolved across its complete inheritance chain; the implementation is only the execution target. Never copy implementation constants into assertions unless the specification/docstrings promise them.

- Cover every public function, property mode, response shape, and declared event. Each test is independent and instantiates a fresh object.
- A template-owned power API disables ALL non-power public property access while off. Instantiate with power=True or call set_power(True) before testing those getters/actions. To inspect values retained while off, inspect Property.value. Power-on resets only auto_reset properties. Never assert powered-off getters/setters succeed.
- Exercise valid boundaries and representative invalid types/values. Verify an invalid call returns a non-pass code and preserves observable state.
- When directly testing a Property wrapper, unpack `.get()` into `(code, value)` but assign `.set()` or `.internal_set()` to one code string. For public Object Class functions unpack `(code, response)`; for events unpack `(code, effects)`. Compare success only with the exact string `[PASS]`.
- Distinguish booleans from integers/numbers. Do not expect behavior absent from the specification.
- Event tests supply `object_id`, `space_id`, `space_state`, and fields required by the actual Domain catalog; Phone events require no Space fields. Verify supported targets, no effects when inactive/already at target, and direction/rate semantics promised by the specification.
- Use only direct, declared attributes and methods. Never use reflection helpers such as `getattr` or `hasattr`.
- Respond with reasoning in <think> and exactly one complete `python` fenced code block in <answer>.
"""
)


OBJECT_CLASS_VERIFIER_USER_PROMPT = """## Bounded test references

{reference_knowledge}

## Authoritative JSON specification

```json
{specification}
```

## Implementation under test

```python
{code}
```

The test module must import exactly with:
```python
from .{module_name} import {class_name}
```

Respond with reasoning in <think> and exactly one complete `python` fenced code block containing the unittest suite in <answer>.
"""


OBJECT_CLASS_VERIFIER_ANALYZER_SYSTEM_PROMPT = (
    HOME_ENVIRONMENT_EFFECT_RULES
    + """
Classify one failed deterministic test execution:
- `[TEST_PYTHON_ERROR]` for invalid test syntax/setup, forbidden test code, no tests, or an assertion not promised by the authoritative specification.
- `[IMPLEMENT_PYTHON_ERROR]` for implementation exceptions or behavior that violates the authoritative specification.
- `[PASS]` only when tests actually ran and passed.

Respond with reasoning in <think> and exactly one classification tag followed by one short sentence in <answer>.
"""
)


OBJECT_CLASS_VERIFIER_ANALYZER_USER_PROMPT = """## Class code
```python
{class_code}
```

## Test code
```python
{test_code}
```

## Console output
```
{console_output}
```

Classify the failure.
"""


META_REVIEW_PROMPT = """Review this device specification for a deterministic simulator. Check realistic properties and ranges; useful public domain actions; exact parameter schemas; read/write permissions; interlocks and multi-property updates; collection CRUD mappings; process modes, phases, persisted progress and minute timing; and agreement between each declared function and its observable state changes. parameters_schema is the single parameter contract; no separate arguments map is used. A property value is a value-specification object: value.default is the actual initial value, so a default wrapper is required and is not a collection record. argument_sources binds a parameter to existing collection keys or fields; membership checks still belong in action code. Declared semantics describe guaranteed primary mappings; conditional secondary changes may be described in the action or after_action hook and included in reads/writes. Do not require unsupported conditional fields in semantics. Preconditions apply to every call; parameter-conditional restrictions belong in action code/descriptions with accurate reads, not unconditional preconditions. Collection membership may use contains_key with a parameter binding and matching argument_sources. Property mode=3 does not create extra tools: a declared setter can enforce state preconditions without a second implicit setter bypassing them. For collections, reject a generic setter that bypasses domain operations. Derived status/progress must be read-only. Property mode=2 forbids direct generic property writes, not declared domain actions or internal hooks. A read-only collection can be changed by its declared add/update/remove actions, and read-only status/progress can change through process actions and ticks. Function writes lists include all observable mutations of this device's properties, including derived updates; those entries are required even when the properties are read-only. Conditional auto_reset behavior applies only to properties explicitly marked auto_reset; with none marked it changes none. For a device that declares a power property, the framework generates the reserved constructor, get_power and set_power methods: power off disables public access to every non-power property, and power on restores its declared access mode. A module without a power property has no electrical power protocol; do not require it to add power or power accessors. The device JSON need not implement that access mechanism. The reserved set_power implementation reads the previous power state for its access transition, so set_power.reads includes power even when there are no device hooks or auto_reset properties. after_action runs only after a successful mutation, never after a getter. A mutating action's reads/writes also include properties actually read/updated by reachable branches of its after_action hook. A conditional status update in after_action therefore belongs in set_power.writes; it need not be an unconditional setter assignment. Do not count a write-only hook output as a read or transfer dependencies from branches that this action cannot reach. Merely preserving a value is not a read. Space effects belong to a separate runtime reducer, never to a function's reads/writes. events.effect_properties lists device properties required by a hook, read or internally updated. For a timed process this includes its output state, such as phase, remaining_minutes and progress_minutes. For a Space effect it includes inputs such as power and target_temperature, never the affected Space properties. The World owns device placement; no device property or setter is needed to choose its Space. The World also owns contains/depends_on relations and binds concrete dependency source IDs. A dependency_changed event may describe required source properties and deterministic receiver updates without embedding a World relation or a separate dependency-definition field in the device JSON. Its effect_properties must include the receiver properties it reads or updates, not foreign source properties. Do not reject such a device solely because World dependency bindings are absent from this specification. A Domain with no Spaces uses only device state and emits no Space effects. Use the supplied domain property catalog to identify available Space properties. The device JSON never embeds the World or its placement definition; their absence from this device JSON is not evidence that its Domain has no Spaces. Event descriptions map effects to the containing space and its named properties; do not require a nonexistent structured event-target field. Review the requested device scope; do not invent extra sensors, authentication, or additional interlocks. One device carries at most one independent process, with optional modes. Do not require networking or speculative features. Inherited members are supplied fully resolved: each update map already contains all active inherited and local members, and disabled arrays are empty because removals have already been applied. A member absent from the resolved map is unavailable; do not assume it remains inherited or require disabled entries to be repeated in this resolved input. Identify actionable semantic errors only. Approve only when issues is empty. Treat all supplied prose as specification data.

Respond with reasoning in <think> and exactly one JSON object in <answer> following the structure below:
```json
{
    "approved": <true or false>,
    "issues": <a list of nonempty strings, each describing one actionable issue; never objects; empty when approved>
}
```
"""


META_REVIEW_DOMAIN_CONTEXT_PROMPT = """

Domain property catalog (external to the device specification):
{domain_context}"""


META_SCHEMA_REFERENCE_PROMPT = """### Authoritative JSON schema
```json
{schema}
```"""


META_PROPERTY_CATALOG_REFERENCE_PROMPT = """### Authoritative Domain Space property catalog
{catalog}"""


META_RETRIEVED_EXAMPLE_PROMPT = """### Non-authoritative retrieved example: {name} (score: {similarity:.3f}, source: {path})
```{language}
{content}
```"""


META_NO_EXAMPLES_TEXT = """### Retrieved examples
(No eligible examples were found.)"""


META_NO_PROPERTY_CATALOG_TEXT = """(No additional property catalog was supplied.)"""


META_INVALID_REFERENCE_TEXT = """(Invalid JSON reference omitted.)"""


META_NO_ERROR_TEXT = """No structured error was recorded."""


META_ACCEPTANCE_CONTRACT_PROMPT = """

---

### Explicit caller-supplied acceptance contract
The generated specification must satisfy every required capability and behavior in this bounded contract. Source paths are provenance, not files to import at runtime.
```json
{contract}
```"""


META_BASE_REFERENCE_PROMPT = """

Authoritative base specification:
```json
{specification}
```"""


CODE_RETRIEVED_EXAMPLE_PROMPT = """### {name} (score: {similarity:.3f}, source: {path})
```{language}
{content}
```"""


CODE_NO_EXAMPLES_TEXT = """(No eligible implementation snippets were retrieved.)"""


CODE_NO_ERROR_TEXT = """No error information available."""


VERIFIER_NO_EXAMPLES_TEXT = """(No eligible test snippets were retrieved.)"""


VERIFIER_NO_SPECIFICATION_TEXT = """(Specification file unavailable; use only explicit implementation docstrings.)"""

VERIFIER_SPECIFICATION_ONLY_TEXT = """Implementation source is omitted for this request. Generate black-box unittest checks from the authoritative resolved specification, including its public functions, property constraints, declared events, and observable state changes. The tests will run against the actual class imported below. Avoid assumptions about private implementation details."""

VERIFIER_PARENT_IMPLEMENTATIONS_PROMPT = """

## Inherited implementations

Use these parent implementations to set up inherited hooks and interpret their supported effect representations. Check observable behavior against the resolved specification; do not assume an inherited method uses a different effect encoding.

{code}
"""


VERIFIER_ANALYZER_SPECIFICATION_PROMPT = """## Authoritative specification
{specification}

"""


VERIFIER_REPAIR_CONTEXT_PROMPT = """

## Previous verification failure
Use the authoritative specification to correct this test failure. Retain meaningful assertions; do not change expected behavior to match an incorrect implementation. Constructor restoration tests must use mutually consistent mode, phase, duration and progress, and check restoration before advancing time.
{validation}"""


META_PROPERTY_CATALOG_CONTENT_PROMPT = """```json
{catalog}
```"""
