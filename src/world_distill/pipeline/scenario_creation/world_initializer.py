"""Construct stable initial states and derive effective task Worlds."""

from __future__ import annotations

from copy import deepcopy
import random
from typing import Any

from src.contracts import strict_equal
from src.runtime import World
from src.runtime.loading.templates import apply_init_operations


_ACTIVE_TEMPERATURE_MODES = {"cool", "heat", "auto"}


def constructor_initialization_operations(state, runtime_cache):
    """Make sampled initial properties agree with constructor-derived state."""
    operations = []
    for object_id, device in state["objects"].items():
        instance = runtime_cache.resolve_class(device["class"])(**deepcopy(device["properties"]))
        for name, requested in device["properties"].items():
            value = getattr(instance, name).value
            if not strict_equal(value, requested):
                operations.append({"op": "replace", "path": f"/objects/{object_id}/properties/{name}", "value": deepcopy(value)})
    return operations


def _is_active_temperature_controller(properties: dict[str, Any]) -> bool:
    """Return whether a device actively targets its containing Space temperature."""
    mode = properties.get("mode")
    return (
        properties.get("power") is True
        and "target_temperature" in properties
        and (
            mode in _ACTIVE_TEMPERATURE_MODES
            or (
                mode is None
                and "heating_mode" in properties
                and "heating_intensity" in properties
            )
        )
    )


def initial_temperature_stability_operations(
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    """Align active temperature controllers to their containing Space at t=0."""
    by_space: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for target_id, device in state["objects"].items():
        properties = device["properties"]
        if (
            _is_active_temperature_controller(properties)
            and device.get("space_id") in state["spaces"]
            and "temperature"
            in state["spaces"][device["space_id"]]["properties"]
        ):
            by_space.setdefault(device["space_id"], []).append(
                (target_id, properties)
            )

    operations: list[dict[str, Any]] = []
    for space_id, controllers in sorted(by_space.items()):
        controllers.sort(key=lambda item: item[0])
        ambient = state["spaces"][space_id]["properties"]["temperature"]
        for target_id, properties in controllers:
            if strict_equal(properties["target_temperature"], ambient):
                continue
            operations.append(
                {
                    "op": "replace",
                    "path": (
                        f"/objects/{target_id}/properties/target_temperature"
                    ),
                    "value": deepcopy(ambient),
                }
            )
    return operations


def validate_initial_temperature_stability(state: dict[str, Any]) -> None:
    """Validate the initial temperature stability."""
    if initial_temperature_stability_operations(state):
        raise ValueError(
            "t=0 requires every active temperature controller and its Space "
            "to share one temperature"
        )


def _schema_type(schema: dict[str, Any]) -> str | None:
    """Return the schema type."""
    kind = schema.get("type")
    if isinstance(kind, str):
        return kind
    for branch in schema.get("anyOf", []):
        if branch.get("type") != "null":
            return branch.get("type")
    return None


def _rounded_numeric(schema: dict[str, Any], value: Any) -> Any:
    """Return the rounded numeric."""
    kind = _schema_type(schema)
    if kind not in {"integer", "number"} or not isinstance(value, (int, float)):
        return deepcopy(value)
    if kind == "integer":
        return int(round(float(value)))
    precision = schema.get("precision")
    return round(float(value), int(precision) if precision is not None else 3)


def _micro_adjustment(
    schema: dict[str, Any],
    current: Any,
    rng: random.Random,
) -> Any | None:
    """Return the micro adjustment."""
    configured = schema.get("initial_values")
    if isinstance(configured, list):
        alternatives = [
            value for value in configured if not strict_equal(value, current)
        ]
        return deepcopy(rng.choice(alternatives)) if alternatives else None
    choices = schema.get("enum")
    if isinstance(choices, list):
        alternatives = [
            value for value in choices if not strict_equal(value, current)
        ]
        return deepcopy(rng.choice(alternatives)) if alternatives else None
    kind = _schema_type(schema)
    if kind == "boolean" and isinstance(current, bool):
        return not current
    if kind in {"integer", "number"} and isinstance(current, (int, float)):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        precision = schema.get("precision")
        span = (
            float(maximum) - float(minimum)
            if minimum is not None and maximum is not None
            else max(abs(float(current)), 10.0)
        )
        step = (
            schema.get("step")
            or schema.get("multipleOf")
            or (
                1
                if kind == "integer"
                else 10 ** -int(precision)
                if precision is not None
                else 0.1
            )
        )
        distance = max(float(step), span * 0.05)
        candidate = float(current) + rng.choice((-distance, distance))
        if minimum is not None:
            candidate = max(candidate, float(minimum))
        if maximum is not None:
            candidate = min(candidate, float(maximum))
        if strict_equal(candidate, current):
            candidate = float(current) - rng.choice((-distance, distance))
        if minimum is not None:
            candidate = max(candidate, float(minimum))
        if maximum is not None:
            candidate = min(candidate, float(maximum))
        if step:
            origin = float(minimum or 0)
            candidate = origin + round(
                (candidate - origin) / float(step)
            ) * float(step)
        value = _rounded_numeric(schema, candidate)
        return None if strict_equal(value, current) else value
    return None


def derive_task_world_init(
    source_world: World,
    *,
    task_id: str,
    rng: random.Random,
    tweak_count: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Copy a world, normalize Space precision, and optionally micro-adjust it."""
    if tweak_count < 0:
        raise ValueError("tweak_count cannot be negative")
    payload = deepcopy(source_world.loaded_world.world_init)
    source_world_id = payload["world_id"]
    payload["world_id"] = task_id
    payload.setdefault("config", {}).setdefault("scene_metadata", {})[
        "source_world_id"
    ] = source_world_id

    initial = source_world.get_initial_state()
    candidates: list[dict[str, Any]] = []
    normalizations: list[dict[str, Any]] = []
    active_temperature_spaces = {
        device["space_id"]
        for device in initial["objects"].values()
        if _is_active_temperature_controller(device["properties"])
    }
    property_catalog = source_world.loaded_world.domain.property_catalog
    for space_id, space in initial["spaces"].items():
        for prop, current in space["properties"].items():
            schema = property_catalog["space_properties"].get(prop)
            if schema is None:
                continue
            configured = schema.get("initial_values")
            normalized = (
                min(configured, key=lambda value: abs(float(value) - float(current)))
                if configured
                else _rounded_numeric(schema, current)
            )
            if not strict_equal(normalized, current):
                normalizations.append(
                    {
                        "op": "replace",
                        "path": f"/spaces/{space_id}/properties/{prop}",
                        "value": normalized,
                    }
                )
            value = (
                None
                if prop == "temperature" and space_id in active_temperature_spaces
                else _micro_adjustment(schema, normalized, rng)
            )
            if value is not None:
                candidates.append(
                    {
                        "op": "replace",
                        "path": f"/spaces/{space_id}/properties/{prop}",
                        "value": value,
                    }
                )

    # Public actions diversify collections/processes as well as scalar settings.
    # Import locally because task builders also use World initialization helpers.
    from .task_builders.capability import prepare_operation, preview_with_boolean_setup
    from .task_inventory import InventoryError, TaskInventory
    from .task_sampler import sample_parameters

    inventory = TaskInventory(source_world)
    for tool in inventory.operation_tools:
        if not tool["mutation"] or tool["semantics"]["kind"] not in {
            "set", "update", "collection_add", "collection_update",
            "collection_delete", "process_start", "process_pause", "process_resume",
        }:
            continue
        properties = initial["objects"][tool["target"]]["properties"]
        if "target_temperature" in properties and set(tool["writes"]) & {
            "power", "mode", "target_temperature", "heating_mode", "heating_intensity",
        }:
            continue
        candidates.append({"tool": tool})

    # Balance action kinds so numerous scalar setters do not crowd out the
    # collection/process states needed by later delete, reset, and stop tasks.
    by_kind = {}
    for candidate in candidates:
        kind = candidate["tool"]["semantics"]["kind"] if "tool" in candidate else "space"
        by_kind.setdefault(kind, []).append(candidate)
    candidates = []
    for group in by_kind.values():
        rng.shuffle(group)
    while by_kind:
        kind = rng.choice(list(by_kind))
        candidates.append(by_kind[kind].pop())
        if not by_kind[kind]:
            del by_kind[kind]
    selected, commands = [], []
    accepted_count = 0
    for candidate in candidates:
        if accepted_count >= tweak_count:
            break
        if "tool" not in candidate:
            selected.append(candidate)
            accepted_count += 1
            continue
        tool = candidate["tool"]
        try:
            prefix = prepare_operation(inventory, tool, commands, rng)
            before = inventory.preview_from_initial(prefix).final_state if prefix else initial
            parameters = sample_parameters(tool, before, rng)
            semantic = tool["semantics"]
            if semantic["kind"] == "set":
                parameter = semantic["parameter"]
                value = _micro_adjustment(tool["parameters_schema"]["properties"][parameter],
                    before["objects"][tool["target"]]["properties"][semantic["property"]], rng)
                if value is not None:
                    parameters[parameter] = value
            accepted = preview_with_boolean_setup(inventory, tool, parameters, prefix=prefix)
            if not any(item['scope'] == 'object'
                       for item in inventory.preview_from_initial(accepted.commands).differences):
                # A start followed by a reset can otherwise exhaust the tweak
                # budget while restoring the complete original device state.
                continue
        except InventoryError:
            continue
        commands = list(accepted.commands)
        accepted_count += 1
    if commands:
        preview = inventory.preview_from_initial(commands)
        for item in preview.differences:
            # A new World rebuilds its effect ledger from the Space baseline.
            # Baking action contributions into that baseline would count them twice.
            if item["scope"] == "object":
                selected.append({"op": "replace",
                    "path": f"/objects/{item['target_id']}/properties/{item['property']}",
                    "value": deepcopy(item["after"])})
    candidate_state = apply_init_operations(
        initial,
        [*normalizations, *deepcopy(selected)],
    )
    constructor_updates = constructor_initialization_operations(candidate_state, source_world.runtime_cache)
    selected.extend(constructor_updates)
    candidate_state = apply_init_operations(candidate_state, constructor_updates)
    stability = initial_temperature_stability_operations(candidate_state)
    validate_initial_temperature_stability(
        apply_init_operations(candidate_state, stability)
    )
    payload["init"] = [
        *deepcopy(payload["init"]),
        *normalizations,
        *deepcopy(selected),
        *stability,
    ]
    source_world.contract.validate_world_init(payload)
    return payload, selected
