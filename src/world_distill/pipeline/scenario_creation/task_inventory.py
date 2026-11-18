"""World candidates and isolated operation previews with reusable caches."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re
from threading import Lock
import time
from typing import Any, Iterable

from src.contracts import strict_equal
from src.contracts.capabilities import collection_change_matches, precondition_matches
from src.runtime import ActionPreview, RuntimeExecutionError, World
from src.evaluation.validation.workflow import goal_evaluation_end
from src.utils import format_json


class InventoryError(ValueError):
    """The effective World does not expose a requested task candidate."""


def command(target: str, function: str, **parameters: Any) -> dict[str, Any]:
    """Return the command."""
    return {"target": target, "function": function, "parameters": parameters}


def natural_key(value: str) -> tuple[Any, ...]:
    """Return a natural-sort key for the value."""
    return tuple(
        int(part) if part.isdigit() else part.casefold()
        for part in re.split(r"(\d+)", value)
    )


def _words(value: str) -> str:
    """Return the words."""
    value = value.rsplit(".", 1)[-1]
    value = re.sub(r"(?<!^)(?=[A-Z])", " ", value)
    return value.replace("_", " ").strip().title()


def _schema_type(schema: dict[str, Any]) -> str | None:
    """Return the schema type."""
    kind = schema.get("type")
    if isinstance(kind, str):
        return kind
    return next(
        (
            branch.get("type")
            for branch in schema.get("anyOf", [])
            if branch.get("type") != "null"
        ),
        None,
    )


def schema_accepts(schema: dict[str, Any], value: Any) -> bool:
    """Return whether the schema accepts the value."""
    choices = schema.get("enum")
    if isinstance(choices, list) and value not in choices:
        return False
    kind = _schema_type(schema)
    if kind == "boolean" and type(value) is not bool:
        return False
    if kind == "integer" and (type(value) is not int):
        return False
    if kind == "number" and (
        not isinstance(value, (int, float)) or isinstance(value, bool)
    ):
        return False
    if kind == "string" and not isinstance(value, str):
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None and value < minimum:
            return False
        if maximum is not None and value > maximum:
            return False
        multiple = schema.get("multipleOf") or schema.get("step")
        if multiple:
            origin = float(minimum or 0)
            scaled = (float(value) - origin) / float(multiple)
            if abs(scaled - round(scaled)) > 1e-7:
                return False
    return True


def _normalize_numeric(schema: dict[str, Any], value: float) -> int | float:
    """Return the numeric."""
    minimum = schema.get("minimum")
    maximum = schema.get("maximum")
    if minimum is not None:
        value = max(value, float(minimum))
    if maximum is not None:
        value = min(value, float(maximum))
    step = schema.get("multipleOf") or schema.get("step")
    if step:
        origin = float(minimum or 0)
        value = origin + round((value - origin) / float(step)) * float(step)
    if _schema_type(schema) == "integer":
        return int(round(value))
    precision = schema.get("precision")
    return round(value, int(precision) if precision is not None else 3)


_LIFESTYLE_VALUES: dict[str, tuple[int | float, ...]] = {
    "brightness": (20, 40, 60, 80, 100),
    "color_temperature": (2700, 3000, 4000, 5000, 6500),
    "target_temperature": (18, 20, 22, 24, 26, 28),
    "temperature": (18, 20, 22, 24, 26, 28),
    "humidity": (40, 50, 60, 70),
    "position": (0, 25, 50, 75, 100),
    "fan_speed": (1, 2, 3, 4, 5),
    "volume": (20, 40, 60, 80),
}


def candidate_values(
    property_name: str,
    schema: dict[str, Any],
    current: Any,
) -> tuple[Any, ...]:
    """Return concise, realistic, schema-valid alternatives."""
    choices = schema.get("enum")
    if isinstance(choices, list):
        return tuple(deepcopy(value) for value in choices if not strict_equal(value, current))
    kind = _schema_type(schema)
    if kind == "boolean":
        return (not bool(current),)
    if kind in {"integer", "number"} and isinstance(current, (int, float)):
        preferred = list(_LIFESTYLE_VALUES.get(property_name, ()))
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        step = float(schema.get("multipleOf") or schema.get("step") or 1)
        preferred.extend(
            value
            for value in (
                minimum,
                maximum,
                float(current) - step,
                float(current) + step,
            )
            if value is not None
        )
        result: list[Any] = []
        for raw in preferred:
            value = _normalize_numeric(schema, float(raw))
            if (
                schema_accepts(schema, value)
                and not strict_equal(value, current)
                and value not in result
            ):
                result.append(value)
        return tuple(result)
    return ()


def delta_values(
    property_name: str,
    schema: dict[str, Any],
    current: Any,
) -> tuple[tuple[Any, str, int | float], ...]:
    """Return the delta values."""
    if (
        not isinstance(current, (int, float))
        or isinstance(current, bool)
        or _schema_type(schema) not in {"integer", "number"}
    ):
        return ()
    step = float(schema.get("multipleOf") or schema.get("step") or 1)
    common = {
        "brightness": (10, 20),
        "color_temperature": (300, 500),
        "target_temperature": (1, 2),
        "temperature": (1, 2),
        "position": (10, 25),
        "volume": (10, 20),
    }.get(property_name, (step, step * 2))
    result: list[tuple[Any, str, int | float]] = []
    for amount in common:
        for direction, sign in (("increase", 1), ("decrease", -1)):
            value = _normalize_numeric(schema, float(current) + sign * float(amount))
            actual_amount = abs(float(value) - float(current))
            if not strict_equal(value, current) and schema_accepts(schema, value):
                normalized_amount: int | float = (
                    int(actual_amount)
                    if float(actual_amount).is_integer()
                    else round(actual_amount, 3)
                )
                item = (value, direction, normalized_amount)
                if item not in result:
                    result.append(item)
    return tuple(result)


def _required_parameter_value(schema: dict[str, Any]) -> Any:
    """Return the required parameter value."""
    choices = schema.get("enum")
    if isinstance(choices, list) and choices:
        return deepcopy(choices[0])
    kind = _schema_type(schema)
    if kind == "boolean":
        return False
    if kind == "integer":
        return int(schema.get("minimum", 0))
    if kind == "number":
        return float(schema.get("minimum", 0))
    if kind == "string":
        return "value"
    raise InventoryError("cannot fill a required setter parameter")


@dataclass(frozen=True)
class PropertyValue:
    target_kind: str
    target_id: str
    target_name: str
    class_id: str | None
    space_id: str | None
    property: str
    value: Any
    query_command: dict[str, Any]


@dataclass(frozen=True)
class Setter:
    target_id: str
    target_name: str
    class_id: str
    space_id: str
    property: str
    initial_value: Any
    function: str
    parameter: str | None
    parameter_schema: dict[str, Any]
    required_parameters: dict[str, Any]

    def command_for(self, value: Any) -> dict[str, Any]:
        """Return the command associated with the action."""
        parameters = deepcopy(self.required_parameters)
        if self.parameter is not None:
            parameters[self.parameter] = deepcopy(value)
        return command(self.target_id, self.function, **parameters)


@dataclass(frozen=True)
class ControlCandidate:
    setter: Setter
    requested_value: Any
    commands: tuple[dict[str, Any], ...]
    implicit_power_on: bool


@dataclass(frozen=True)
class GoalCandidate:
    controls: tuple[ControlCandidate, ...]
    space_id: str
    space_name: str
    property: str
    initial_value: Any
    final_value: Any
    target_range: dict[str, Any]
    minutes: int

    @property
    def commands(self) -> tuple[dict[str, Any], ...]:
        return control_commands(self.controls)


def control_commands(controls: Iterable[ControlCandidate]) -> tuple[dict[str, Any], ...]:
    """Preserve control order and share implicit setup actions."""
    commands = []
    for control in controls:
        for action in control.commands:
            if action not in commands:
                commands.append(deepcopy(action))
    return tuple(commands)


@dataclass(frozen=True)
class OperationCandidate:
    tool: dict[str, Any]
    parameters: dict[str, Any]
    commands: tuple[dict[str, Any], ...]
    assertions: dict[str, dict[str, Any]]
    response: dict[str, Any]


class GoalProbeBudgetExceeded(InventoryError):
    """A bounded search stopped; this does not establish unreachability."""


class TaskInventory:
    """Cache all reusable properties, setters, and Goal previews for one World."""

    def __init__(self, world: World, *, goal_probe_max_minutes: int = 240,
                 goal_probe_max_plans: int | None = None) -> None:
        """Initialize the TaskInventory."""
        self.world = world
        self.goal_probe_max_minutes = goal_probe_max_minutes
        self.goal_probe_max_plans = goal_probe_max_plans
        self.initial = world.get_initial_state()
        self.world_spec = world.get_world_spec()
        self.space_names = self._space_names()
        self.device_names = self._device_names()
        self.device_name_variants = self._device_name_variants()
        self.people = deepcopy(
            self.world_spec.get("scene_metadata", {}).get("people", {})
        )
        self.properties = self._properties()
        self.setters = self._setters()
        self._preview_world = world if world.runtime_cache is None else None
        self._setter_index = {
            (setter.target_id, setter.property): setter for setter in self.setters
        }
        self._query_availability: dict[tuple[str, str, str], bool] = {}
        self._goal_cache: tuple[GoalCandidate, ...] | None = None
        self._goal_iterator = None
        self._goals_exhausted = False
        self._goal_probe_count = 0
        self._goal_budget_exhausted = False
        self._preview_cache: dict[tuple[str, bool], ActionPreview] = {}
        self._preview_cache_hits = 0
        self._preview_cache_misses = 0
        self._preview_seconds = 0.0
        self._query_lock = Lock()
        self._goal_lock = Lock()
        self._preview_lock = Lock()
        self.operation_tools = tuple(
            tool for tool in world.get_tool_catalog()["tools"]
            if tool["target_kind"] == "device" and "semantics" in tool
        )
        self.capability_rejections: dict[str, str] = {
            tool["tool_id"]: tool["semantics"]["reason"]
            for tool in self.operation_tools if tool["semantics"]["kind"] == "custom"
        }

    def preview_from_initial(
        self,
        actions: Iterable[dict[str, Any]],
        *,
        validate: bool = True,
    ) -> ActionPreview:
        """Memoize a preview from this effective World's initial state."""
        if type(validate) is not bool:
            raise TypeError("validate must be a boolean")
        commands = deepcopy(tuple(actions))
        key = (
            format_json(
                commands,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
            validate,
        )
        with self._preview_lock:
            cached = self._preview_cache.get(key)
            if cached is None and not validate:
                cached = self._preview_cache.get((key[0], True))
            if cached is not None:
                self._preview_cache_hits += 1
                return deepcopy(cached)
            self._preview_cache_misses += 1
            started = time.perf_counter()
            if self._preview_world is None:
                self._preview_world = World(self.world.world_dir, runtime_cache=self.world.runtime_cache, blueprint=self.world.blueprint, require_device_tool_discovery=False)
            preview = self._preview_world.preview_actions(
                commands,
                validate=validate,
            )
            self._preview_seconds += time.perf_counter() - started
            self._preview_cache[key] = deepcopy(preview)
            return preview

    def _space_names(self) -> dict[str, str]:
        """Return the space names."""
        spaces = self.initial["spaces"]
        by_type: dict[str, list[str]] = {}
        for space_id, space in spaces.items():
            by_type.setdefault(space["type"], []).append(space_id)
        result: dict[str, str] = {}
        for space_type, identifiers in by_type.items():
            ordered = sorted(identifiers, key=natural_key)
            for index, space_id in enumerate(ordered, start=1):
                metadata = spaces[space_id].get("metadata", {})
                explicit = metadata.get("name")
                if not explicit and not re.fullmatch(re.escape(space_type) + r"(?:_\d+)?", space_id):
                    result[space_id] = _words(space_id)
                    continue
                base = str(explicit).strip() if explicit else _words(space_type)
                result[space_id] = base if len(ordered) == 1 else f"{base} {index}"
        return result

    def _device_names(self) -> dict[str, str]:
        """Return the device names."""
        objects = self.initial["objects"]
        groups: dict[str, list[str]] = {}
        for target_id, spec in objects.items():
            parts = spec["class"].split(".")
            family = ".".join(parts[:2]) if len(parts) >= 3 else spec["class"]
            groups.setdefault(family, []).append(target_id)
        result: dict[str, str] = {}
        for identifiers in groups.values():
            ordered = sorted(identifiers, key=natural_key)
            for fallback_index, target_id in enumerate(ordered, start=1):
                spec = objects[target_id]
                metadata = spec.get("metadata", {})
                explicit = metadata.get("name")
                base = (
                    str(explicit).strip()
                    if explicit
                else (f"{self.space_names[spec['space_id']]} {_words(spec['class'])}"
                      if spec.get("space_id") is not None else _words(spec["class"]))
                )
                suffix = re.search(r"_(\d+)$", target_id)
                index = int(suffix.group(1)) if suffix else fallback_index
                result[target_id] = f"{base} {index}"
        return result

    def _device_name_variants(self) -> dict[str, tuple[str, ...]]:
        """Keep only references that resolve to one device in the entire World."""
        candidates, owners = {}, {}
        for target_id, spec in self.initial["objects"].items():
            labels = tuple(dict.fromkeys((_words(spec["class"]), _words(spec["class"].split(".")[1]))))
            index = self.device_names[target_id].rsplit(" ", 1)[-1]
            names = [self.device_names[target_id]]
            for label in labels:
                names.extend((label, f"{label} {index}"))
                space_id = spec.get("space_id")
                if space_id is not None:
                    for room in (self.space_names[space_id], _words(self.initial["spaces"][space_id]["type"])):
                        names.extend((f"{room} {label}", f"{room} {label} {index}"))
            explicit = spec.get("metadata", {}).get("name")
            if explicit:
                names.append(explicit.strip())
            candidates[target_id] = tuple(dict.fromkeys(names))
            for name in names:
                owners.setdefault(name.casefold(), set()).add(target_id)
        return {target_id: tuple(name for name in names if len(owners[name.casefold()]) == 1)
                for target_id, names in candidates.items()}

    def _properties(self) -> tuple[PropertyValue, ...]:
        """Return the properties."""
        result: list[PropertyValue] = []
        for tool in sorted(
            self.world.get_tool_catalog()["tools"],
            key=lambda item: item["tool_id"],
        ):
            if (
                tool["target_kind"] != "device"
                or tool["mutation"]
                or tool["parameters_schema"]["required"]
            ):
                continue
            target_id = tool["target"]
            semantic = tool.get("semantics")
            if semantic is not None:
                if semantic["kind"] != "read":
                    continue
                prop = semantic["property"]
            elif tool["function"].startswith("get_"):
                prop = tool["function"][4:]
            else:
                continue
            spec = self.initial["objects"][target_id]
            if prop not in spec["properties"]:
                continue
            query = command(target_id, tool["function"])
            result.append(
                PropertyValue(
                    target_kind="object",
                    target_id=target_id,
                    target_name=self.device_names[target_id],
                    class_id=spec["class"],
                    space_id=spec["space_id"],
                    property=prop,
                    value=deepcopy(spec["properties"][prop]),
                    query_command=query,
                )
            )
        for space_id, spec in sorted(
            self.initial["spaces"].items(), key=lambda item: natural_key(item[0])
        ):
            for prop, value in sorted(spec["properties"].items()):
                result.append(
                    PropertyValue(
                        target_kind="space",
                        target_id=space_id,
                        target_name=self.space_names[space_id],
                        class_id=spec["type"],
                        space_id=space_id,
                        property=prop,
                        value=deepcopy(value),
                        query_command=command(
                            "session", "get_space_state", space_id=space_id
                        ),
                    )
                )
        return tuple(result)

    def _setters(self) -> tuple[Setter, ...]:
        """Return the setters."""
        result: list[Setter] = []
        for tool in sorted(
            self.world.get_tool_catalog()["tools"],
            key=lambda item: item["tool_id"],
        ):
            if (
                tool["target_kind"] != "device"
                or not tool["mutation"]
            ):
                continue
            target_id = tool["target"]
            semantic = tool.get("semantics")
            if semantic is not None:
                if semantic["kind"] != "set":
                    continue
                prop = semantic["property"]
            elif tool["function"].startswith("set_"):
                prop = tool["function"][4:]
            else:
                continue
            device = self.initial["objects"][target_id]
            if prop not in device["properties"]:
                continue
            schemas = tool["parameters_schema"]["properties"]
            parameter = semantic["parameter"] if semantic is not None else prop if prop in schemas else "value" if "value" in schemas else None
            if parameter is None:
                continue
            required = {
                name: _required_parameter_value(schemas[name])
                for name in tool["parameters_schema"]["required"]
                if name != parameter
            }
            result.append(
                Setter(
                    target_id=target_id,
                    target_name=self.device_names[target_id],
                    class_id=device["class"],
                    space_id=device["space_id"],
                    property=prop,
                    initial_value=deepcopy(device["properties"][prop]),
                    function=tool["function"],
                    parameter=parameter,
                    parameter_schema=deepcopy(schemas[parameter]),
                    required_parameters=required,
                )
            )
        return tuple(result)

    def property_values(self, target_kind: str | None = None) -> tuple[PropertyValue, ...]:
        """Return the property values."""
        if target_kind is None:
            return self.properties
        return tuple(item for item in self.properties if item.target_kind == target_kind)

    def setter(self, target_id: str, prop: str) -> Setter | None:
        """Return the setter."""
        return self._setter_index.get((target_id, prop))

    def person_name(self, person_id: str) -> str:
        """Return a person's public name."""
        return str(self.people[person_id].get("name", person_id))

    def person_space(self, person_id: str) -> str:
        """Return a person's current Space ID."""
        return str(self.people[person_id]["space_id"])

    def space_occupants(self, space_id: str) -> tuple[str, ...]:
        """Return occupant IDs in natural person-ID order."""
        identifiers = self.initial["spaces"][space_id].get("metadata", {}).get(
            "occupants", []
        )
        return tuple(sorted(identifiers, key=natural_key))

    def class_type(self, class_id: str) -> type:
        """Resolve a Domain class for inheritance-aware source ranking."""
        return self.world._resolve_class(class_id)

    def query_available(self, item: PropertyValue) -> bool:
        """Check a getter only when a task needs it, then reuse the result."""
        key = (item.target_kind, item.target_id, item.property)
        with self._query_lock:
            if key not in self._query_availability:
                preview = self.preview_from_initial(
                    [item.query_command],
                    validate=False,
                )
                self._query_availability[key] = bool(
                    preview.results and preview.results[0].code == "[PASS]"
                )
                tool = self.world._tool_index[f"{item.query_command['target']}_{item.query_command['function']}"]
                if self._query_availability[key] and "semantics" in tool:
                    response_key = tool["semantics"]["response_key"]
                    response = preview.results[0].response
                    if response_key not in response or not strict_equal(response[response_key], item.value):
                        self._query_availability[key] = False
                        self.capability_rejections[tool["tool_id"]] = "declared getter mapping disagrees with execution"
            return self._query_availability[key]

    def make_control(self, setter: Setter, requested_value: Any) -> ControlCandidate:
        """Return the control."""
        if not schema_accepts(setter.parameter_schema, requested_value):
            raise InventoryError("requested setter value violates its schema")
        commands: list[dict[str, Any]] = []
        implicit_power_on = False
        device = self.initial["objects"][setter.target_id]
        if (
            setter.property != "power"
            and device["properties"].get("power") is False
        ):
            power = self.setter(setter.target_id, "power")
            if power is None or not schema_accepts(power.parameter_schema, True):
                raise InventoryError("an off device cannot be implicitly powered on")
            commands.append(power.command_for(True))
            implicit_power_on = True
        commands.append(setter.command_for(requested_value))
        return ControlCandidate(
            setter=setter,
            requested_value=deepcopy(requested_value),
            commands=tuple(deepcopy(commands)),
            implicit_power_on=implicit_power_on,
        )

    def preview_controls(
        self, controls: Iterable[ControlCandidate]
    ) -> tuple[tuple[dict[str, Any], ...], dict[str, Any]]:
        """Return the preview controls."""
        ordered = tuple(controls)
        paths = [(item.setter.target_id, item.setter.property) for item in ordered]
        if len(paths) != len(set(paths)):
            raise InventoryError("multiple controls write the same property")
        commands: list[dict[str, Any]] = []
        for control in ordered:
            for item in control.commands:
                if item not in commands:
                    commands.append(deepcopy(item))
        preview = self.preview_from_initial(commands)
        if any(result.code != "[PASS]" for result in preview.results):
            raise InventoryError("joint control preview failed")
        for control in ordered:
            actual = preview.final_state["objects"][control.setter.target_id]["properties"][control.setter.property]
            if strict_equal(actual, control.setter.initial_value):
                raise InventoryError("joint controls cancel a requested change")
        return tuple(commands), preview.final_state

    def goal_candidates(self, *, limit: int = 1) -> tuple[GoalCandidate, ...]:
        """Probe only until the caller has another usable Space effect."""
        with self._goal_lock:
            if self._goal_cache is None:
                self._goal_cache = ()
                self._goal_iterator = self._iter_goal_candidates()
            while not self._goals_exhausted and len(self._goal_cache) < limit:
                try:
                    self._goal_cache += (next(self._goal_iterator),)
                except StopIteration:
                    self._goals_exhausted = True
                except GoalProbeBudgetExceeded:
                    self._goal_budget_exhausted = True
                    self._goals_exhausted = True
            if not self._goal_cache:
                raise InventoryError("no candidate reaches a configured Goal range at its fixed horizon within the probe budget")
            return self._goal_cache[:limit]

    def _goal_setters(self) -> tuple[Setter, ...]:
        """Include declared update operations, such as mode switches, in Goal search."""
        setters = list(self.setters)
        for tool in self.operation_tools:
            semantic = tool["semantics"]
            if semantic["kind"] not in {"update", "custom"}:
                continue
            device = self.initial["objects"][tool["target"]]
            schemas = tool["parameters_schema"]["properties"]
            fields = semantic.get("fields", {}) if semantic["kind"] == "update" else {
                prop: {"parameter": "value"} for prop in tool["writes"]
                if tool["function"] == f"set_{prop}" and "value" in schemas
            }
            for prop, binding in fields.items():
                if prop not in self.world._state.devices[tool["target"]].effect_properties:
                    continue
                parameter = binding.get("parameter")
                setters.append(Setter(
                    target_id=tool["target"], target_name=self.device_names[tool["target"]],
                    class_id=device["class"], space_id=device.get("space_id"), property=prop,
                    initial_value=device["properties"][prop], function=tool["function"],
                    parameter=parameter,
                    parameter_schema=schemas[parameter] if parameter else {"enum": [binding["value"]]},
                    required_parameters={name: _required_parameter_value(schemas[name])
                                         for name in tool["parameters_schema"]["required"] if name != parameter},
                ))
        return tuple(setter for setter in setters
                     if setter.property in self.world._state.devices[setter.target_id].effect_properties)

    def _iter_goal_candidates(self):
        """Find a short causal plan for each target, extending single controls as needed."""
        from .goal_bounds import environmental_invariants

        catalog = self.world.loaded_world.domain.property_catalog["space_properties"]
        invariants = {(item["space_id"], item["property"]): item
                      for prop, spec in catalog.items() if spec.get("target_ranges")
                      for item in environmental_invariants(self.world, prop)}
        targets = {}
        for space_id, space in self.initial["spaces"].items():
            for prop, initial in space["properties"].items():
                invariant = invariants.get((space_id, prop))
                for bounds in catalog[prop].get("target_ranges", []):
                    if bounds["min"] <= initial <= bounds["max"]:
                        continue
                    if invariant and (bounds["max"] < invariant["min"] or bounds["min"] > invariant["max"]):
                        continue
                    targets[(space_id, prop, bounds["min"], bounds["max"])] = bounds
        controls = {}
        for setter in self._goal_setters():
            if not any(key[0] == setter.space_id for key in targets):
                continue
            for value in candidate_values(setter.property, setter.parameter_schema, setter.initial_value):
                try:
                    control = self.make_control(setter, value)
                except InventoryError:
                    continue
                controls.setdefault(setter.space_id, []).append(control)

        start = self.initial["runtime"]["time_state"]["elapsed_minutes"]
        cap = start + self.goal_probe_max_minutes

        def probe_world():
            world = World(self.world.world_dir, runtime_cache=self.world.runtime_cache,
                          blueprint=self.world.blueprint, require_device_tool_discovery=False)
            # Same speculative mode as World.preview_actions(validate=False).
            # These private probes are discarded; selected plans still undergo
            # strict replay in _preview_goals and the task publication gate.
            world._previewing = True
            world._preview_validation_enabled = False
            world._audit._validation_enabled = False
            # These discarded probes need fresh snapshots, not live-world change
            # detection or another copy of the freshly allocated state tree.
            world._time.snapshot = world._state.snapshot
            return world

        passive = probe_world()
        passive_states, previews = {}, {}
        stationary_between_actions = not self.world._state.dynamics and not any(
            callable(getattr(device.instance, "_on_tick", None)) for device in self.world._state.devices.values()
        )

        def simulate(plan):
            commands = control_commands(plan)
            cache_key = format_json(commands, sort_keys=True)
            if cache_key in previews:
                return previews[cache_key]
            if self.goal_probe_max_plans is not None and self._goal_probe_count >= self.goal_probe_max_plans:
                raise GoalProbeBudgetExceeded('Goal plan probe budget exhausted; this is not an unreachability proof')
            self._goal_probe_count += 1
            probe = probe_world()
            results = probe.apply_actions(commands)
            if any(result.code != "[PASS]" for result in results):
                previews[cache_key] = None
                return None
            control_end = probe.get_state()["runtime"]["time_state"]["elapsed_minutes"]
            if control_end > cap:
                previews[cache_key] = None
                return None
            local_targets = {key: bounds for key, bounds in targets.items() if key[0] == plan[0].setter.space_id}
            entries, reached = {}, {}
            for minute in range(control_end, (control_end if stationary_between_actions else cap) + 1):
                if minute > control_end:
                    # A failed speculative World is discarded by preview(); no
                    # per-minute rollback checkpoint or time-advance record is needed.
                    probe._time._one_minute_tick()
                snapshot = probe._state.snapshot()
                for key, bounds in local_targets.items():
                    space_id, prop, *_ = key
                    actual = snapshot["spaces"][space_id]["properties"][prop]
                    if key in reached or not bounds["min"] <= actual <= bounds["max"]:
                        continue
                    if stationary_between_actions:
                        if goal_evaluation_end(start, control_end) <= cap:
                            reached[key] = (actual, 0)
                        continue
                    horizon = goal_evaluation_end(start, minute)
                    entries.setdefault((key, horizon), minute - control_end)
                    if (key, minute) not in entries:
                        continue
                    while minute not in passive_states:
                        passive._time.advance(60, cause="post_agent", enforce_agent_limit=False)
                        state = passive.get_state()
                        passive_states[state["runtime"]["time_state"]["elapsed_minutes"]] = state["spaces"]
                    baseline = passive_states[minute][space_id]["properties"][prop]
                    if not bounds["min"] <= baseline <= bounds["max"]:
                        reached[key] = (actual, entries[(key, minute)])
            previews[cache_key] = reached, snapshot["spaces"]
            return previews[cache_key]

        def preview(plan):
            try:
                return simulate(plan)
            except RuntimeExecutionError:
                # Conflicting effects invalidate this speculative plan. Keep
                # exploring independent candidates in the same World.
                previews[format_json(control_commands(plan), sort_keys=True)] = None
                return None

        # Discover easy effects across all properties before extending plans for
        # one hard target. One simulation can witness several valid ranges.
        yielded = set()
        for choices in controls.values():
            for control in choices:
                # Leave delayed effects to the full search below. Most declared
                # setters change settings without moving any Space property.
                quick = self.preview_from_initial((*control.commands,
                    command('session', 'sleep_time', minutes=1)), validate=False)
                space_id = control.setter.space_id
                if all(strict_equal(quick.final_state['spaces'][space_id]['properties'][key[1]],
                                    self.initial['spaces'][space_id]['properties'][key[1]])
                       for key in targets if key[0] == space_id):
                    continue
                result = preview((control,))
                if result is None:
                    continue
                for key, (actual, minutes) in result[0].items():
                    if key in yielded:
                        continue
                    yielded.add(key)
                    space_id, prop, *_ = key
                    yield GoalCandidate(
                        controls=(control,), space_id=space_id, space_name=self.space_names[space_id],
                        property=prop, initial_value=self.initial['spaces'][space_id]['properties'][prop],
                        final_value=actual, target_range=deepcopy(targets[key]), minutes=minutes,
                    )

        # Expand one depth for every remaining target before trying longer
        # plans. An unreachable range must not starve other short plans.
        beams = {key: [()] for key in targets if key not in yielded and controls.get(key[0])}
        visited_by_target = {key: set() for key in beams}
        while beams:
            for key in list(beams):
                bounds = targets[key]
                space_id, prop, *_ = key
                choices = controls[space_id]
                beam, visited = beams[key], visited_by_target[key]
                next_beam = []
                found = None
                for prefix in beam:
                    used = {(item.setter.target_id, item.setter.property) for item in prefix}
                    for control in choices:
                        if (control.setter.target_id, control.setter.property) in used:
                            continue
                        plan = (*prefix, control)
                        identity = format_json(control_commands(plan), sort_keys=True)
                        if identity in visited:
                            continue
                        visited.add(identity)
                        result = preview(plan)
                        if result is None:
                            continue
                        reached, final = result
                        if key in reached:
                            actual, minutes = reached[key]
                            found = GoalCandidate(
                                controls=plan, space_id=space_id, space_name=self.space_names[space_id],
                                property=prop, initial_value=self.initial["spaces"][space_id]["properties"][prop],
                                final_value=actual, target_range=deepcopy(bounds), minutes=minutes,
                            )
                            break
                        actual = final[space_id]["properties"][prop]
                        distance = max(bounds["min"] - actual, actual - bounds["max"], 0)
                        next_beam.append((distance, plan))
                    if found is not None:
                        break
                if found is not None:
                    del beams[key]
                    yield found
                    continue
                # ponytail: keep eight promising prefixes; wider search can recover missed combinations.
                if next_beam:
                    beams[key] = [plan for _, plan in sorted(next_beam, key=lambda item: item[0])[:8]]
                else:
                    del beams[key]

    def snapshot(self) -> dict[str, Any]:
        """Small evidence record for batch-level cache reuse."""
        return {
            "world_id": self.initial["world_id"],
            "queryable_property_count": len(self.properties),
            "setter_count": len(self.setters),
            "goal_candidate_count": (
                None if self._goal_cache is None else len(self._goal_cache)
            ),
            "checked_query_count": len(self._query_availability),
            "cached_preview_count": len(self._preview_cache),
            "preview_cache_hits": self._preview_cache_hits,
            "preview_cache_misses": self._preview_cache_misses,
            "preview_seconds": self._preview_seconds,
            "declared_operation_count": len(self.operation_tools),
            "goal_probe_count": self._goal_probe_count,
            "goal_probe_budget_exhausted": self._goal_budget_exhausted,
            "goal_probe_max_minutes": self.goal_probe_max_minutes,
            "goal_probe_max_plans": self.goal_probe_max_plans,
            "goal_search_exhausted": self._goals_exhausted,
            "unsampleable_capabilities": self.capability_rejections.copy(),
        }


def json_value(value: Any) -> str:
    """Convert the value to its JSON representation."""
    return format_json(value, ensure_ascii=False)


def preview_operation(inventory, tool: dict, parameters: dict, *, prefix=()) -> OperationCandidate:
    """Validate declared mappings against execution, including prior result bindings."""
    semantic = tool["semantics"]
    kind = semantic["kind"]
    target = tool["target"]
    before = inventory.preview_from_initial(prefix).final_state if prefix else inventory.initial
    state = before["objects"][target]["properties"]
    effective = {name: deepcopy(spec["default"]) for name, spec in tool["parameters_schema"]["properties"].items() if "default" in spec}
    effective.update(parameters)
    for prop, value in semantic.get("preconditions", {}).items():
        if not precondition_matches(state[prop], value, effective):
            raise InventoryError(f"precondition {prop}={value!r} is not satisfied")
    fields = {
        name: deepcopy(binding["value"] if "value" in binding else effective[binding["parameter"]])
        for name, binding in semantic.get("fields", {}).items()
        if "value" in binding or binding["parameter"] in effective
    }
    assertions = {}
    if kind in {"set", "update"}:
        values = {semantic["property"]: effective[semantic["parameter"]]} if kind == "set" else fields
        assertions = {prop: {"op": "eq", "value": value} for prop, value in values.items()}
    elif kind.startswith("collection_") and kind != "collection_read":
        change = {"op": "collection_change", "add": [], "update": {}, "remove": []}
        if kind == "collection_add":
            if len(fields) != len(semantic["fields"]):
                raise InventoryError("collection add has an unbound record field")
            change["add"] = [fields]
        elif kind == "collection_update":
            if not fields:
                raise InventoryError("collection update changes no fields")
            change["update"] = {effective[semantic["id_parameter"]]: fields}
        elif kind == "collection_delete":
            change["remove"] = [effective[semantic["id_parameter"]]]
        assertions[semantic["property"]] = change
    elif kind in {"process_start", "process_pause", "process_resume"}:
        assertions["status"] = {"op": "eq", "value": "paused" if kind == "process_pause" else "running"}
    elif kind not in {"read", "collection_read"}:
        raise InventoryError(semantic.get("reason", f"{kind} is sampled through Workflow"))
    commands = (*deepcopy(tuple(prefix)), command(target, tool["function"], **parameters))
    preview = inventory.preview_from_initial(commands)
    if any(result.code != "[PASS]" for result in preview.results):
        raise InventoryError("declared operation failed its execution preview")
    final = preview.final_state["objects"][target]["properties"]
    for prop, assertion in assertions.items():
        matched = (
            collection_change_matches(assertion, state[prop], final[prop])
            if assertion["op"] == "collection_change"
            else strict_equal(assertion["value"], final[prop])
        )
        if not matched:
            raise InventoryError(f"declared mapping disagrees with execution for {prop}")
    response = preview.results[-1].response
    if kind in {"read", "collection_read"}:
        expected = state[semantic["property"]]
        if kind == "collection_read":
            expected = expected[effective[semantic["id_parameter"]]]
        if semantic["response_key"] not in response or not strict_equal(response[semantic["response_key"]], expected):
            raise InventoryError("declared response mapping disagrees with execution")
    if kind == "collection_add" and "response_key" in semantic:
        new_id = response.get(semantic["response_key"])
        if new_id not in set(final[semantic["property"]]) - set(state[semantic["property"]]):
            raise InventoryError("declared add response does not identify the new record")
    if assertions and all(strict_equal(state[prop], final[prop]) for prop in assertions):
        raise InventoryError("operation would leave its goals already satisfied")
    return OperationCandidate(deepcopy(tool), deepcopy(parameters), commands, assertions, deepcopy(response))
