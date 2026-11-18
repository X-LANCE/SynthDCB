"""Unavailable-target and unsupported-property tasks for Query, Control, and Goal."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from decimal import Decimal
import random
import re
from typing import Any

from src.object_model import FloatProperty, IntProperty

from ..task_common import (
    build_reference_plan,
    build_task_seed,
    display_value,
    empty_target,
    instruction_templates,
    submit_report,
    TaskArtifacts,
    TaskSeedError,
)
from ..task_inventory import natural_key, TaskInventory
from ..goal_bounds import temperature_invariants
from ..task_sampler import sample_schema_value
from ..task_selection import class_label


def _missing_id(*parts: str) -> str:
    """Return one synthetic identifier derived from actual inventory data."""
    value = "_".join(parts).casefold()
    return "missing_" + re.sub(r"[^a-z0-9]+", "_", value).strip("_")


def _schema_value(schema: dict[str, Any]) -> Any:
    """Return one schema-valid value for an already infeasible target."""
    choices = schema.get("enum") or schema.get("choices")
    if choices:
        return deepcopy(choices[0])
    kind = schema.get("type")
    if kind == "object":
        return sample_schema_value(schema, random.Random(0))
    if kind == "boolean":
        return True
    if kind == "integer":
        return int(schema.get("minimum", 1))
    if kind == "number":
        return float(schema.get("minimum", 1.0))
    return "value"


def _invalid_schema_value(schema: dict[str, Any]) -> Any:
    """Return one value rejected by the supplied schema."""
    choices = schema.get("enum") or schema.get("choices")
    if choices:
        value = "turbo"
        while value in choices:
            value += "_plus"
        return value
    if schema.get("minimum") is not None:
        return schema["minimum"] - 1
    if schema.get("maximum") is not None:
        return schema["maximum"] + 1
    raise ValueError("INVALID_VALUE construction requires bounds or an enum")


def _invalid_resolution_values(prop, current, parameter_schema):
    """Construct in-range off-grid values, confirmed by the property's validator."""
    if not isinstance(prop, (IntProperty, FloatProperty)) or type(current) not in (int, float):
        return
    if prop.validate(current) != "[PASS]":
        return
    quanta = []
    if prop.step is not None:
        quanta.append(("invalid_step", Decimal(str(prop.step))))
    if isinstance(prop, IntProperty):
        quanta.append(("invalid_precision", Decimal(1)))
    elif prop.precision is not None:
        quanta.append(("invalid_precision", Decimal(10) ** -prop.precision))
    for subtype, quantum in quanta:
        for sign in (1, -1):
            offset = quantum * sign / 2
            value = Decimal(str(current)) + offset
            value = int(value) if value == value.to_integral_value() else float(value)
            if any(value < bound for bound in (prop.minimum, parameter_schema.get("minimum")) if bound is not None):
                continue
            if any(value > bound for bound in (prop.maximum, parameter_schema.get("maximum")) if bound is not None):
                continue
            if prop.validate(value) == "[PASS]":
                continue
            amount = abs(offset)
            amount = int(amount) if amount == amount.to_integral_value() else float(amount)
            yield {"subtype": subtype, "value": value}
            yield {"subtype": subtype + "_delta", "value": value,
                   "delta": {"direction": "increase" if sign > 0 else "decrease", "amount": amount}}


def _negative_candidates(
    inventory: TaskInventory,
    family: str,
    outcome: str,
    *, target_kind: str | None = None,
) -> list[dict[str, Any]]:
    """Derive infeasible references exclusively from the effective World."""
    candidates: list[dict[str, Any]] = []
    target_kind = target_kind or ("space" if family == "goal" else "device")
    spaces = inventory.initial["spaces"]
    objects = inventory.initial["objects"]
    domain = inventory.world_spec["domain"]["type"]
    property_catalog = inventory.world.domain_registry.resolve(domain).property_catalog
    existing_space_types = {space["type"] for space in spaces.values()}
    missing_space_types = sorted(
        set(property_catalog["space_types"]) - existing_space_types
    )

    if outcome == "UNREACHABLE_GOAL" and family == "goal":
        for invariant in temperature_invariants(inventory.world):
            space_id, prop = invariant["space_id"], invariant["property"]
            schema = invariant["schema"]
            for value in (invariant["min"] - 4, invariant["max"] + 4):
                if not schema["minimum"] <= value <= schema["maximum"]:
                    continue
                value = int(value) if float(value).is_integer() else value
                subtype = "no_temperature_control" if invariant["proof"] == "no_temperature_source" else "outside_reachable_temperature"
                candidates.append({"subtype": subtype, "target_id": space_id,
                                   "target_name": inventory.space_names[space_id], "property": prop, "value": value,
                                   "assertion": {"op": "range", "min": value, "max": value},
                                   "reason": outcome, "candidate_ids": [space_id],
                                   "proof": {key: value for key, value in invariant.items() if key != "schema"}})

    if outcome == "SPACE_TARGET_NOT_FOUND" and target_kind == "space":
        for space_type in missing_space_types:
            for prop in sorted(property_catalog["space_types"][space_type]):
                for bounds in (property_catalog["space_properties"][prop].get("target_ranges", []) if family == "goal" else [{"min": None, "max": None}]):
                    candidates.append(
                        {
                            "subtype": "nonexistent_room",
                            "target_id": _missing_id(space_type),
                            "target_name": space_type.replace("_", " ").title(),
                            "property": prop,
                            "value": bounds["min"],
                            "assertion": {"op": "range", **deepcopy(bounds)},
                            "reason": "SPACE_TARGET_NOT_FOUND",
                            "candidate_ids": [],
                        }
                    )

    if outcome in {"SPACE_TARGET_NOT_FOUND", "DEVICE_TARGET_NOT_FOUND"} and target_kind == "device":
        references: list[tuple[str, str, dict[str, Any], str]] = []
        if family == "query":
            references.extend(
                (item.class_id or "", item.property, {}, item.target_id)
                for item in inventory.properties
                if item.target_kind == "object"
            )
        else:
            references.extend(
                (item.class_id, item.property, item.parameter_schema, item.target_id)
                for item in inventory.setters
            )
        for class_id, prop, schema, source_id in references:
            value = _schema_value(schema) if family == "control" else None
            for space_type in (missing_space_types if outcome == "SPACE_TARGET_NOT_FOUND" else []):
                candidates.append(
                    {
                        "subtype": "device_in_nonexistent_room",
                        "target_id": _missing_id(space_type, class_id),
                        "target_name": (
                            f"{space_type.replace('_', ' ').title()} "
                            f"{class_label(class_id)}"
                        ),
                        "property": prop,
                        "value": value,
                        "reason": "SPACE_TARGET_NOT_FOUND",
                        "candidate_ids": [],
                    }
                )
            source_class = objects[source_id]["class"]
            source_space = objects[source_id]["space_id"]
            for space_id in (sorted(spaces, key=natural_key) if outcome == "DEVICE_TARGET_NOT_FOUND" else []):
                if space_id == source_space or any(
                    item["space_id"] == space_id and item["class"] == source_class
                    for item in objects.values()
                ):
                    continue
                candidates.append(
                    {
                        "subtype": "device_missing_from_existing_room",
                        "target_id": _missing_id(space_id, source_class),
                        "target_name": (
                            f"{inventory.space_names[space_id]} {class_label(source_class)}"
                        ),
                        "property": prop,
                        "value": value,
                        "reason": "DEVICE_TARGET_NOT_FOUND",
                        "candidate_ids": [],
                    }
                )
        grouped: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
        for target_id, item in objects.items():
            grouped[(item["space_id"], item["class"])].append(target_id)
        for (space_id, class_id), identifiers in (grouped.items() if outcome == "DEVICE_TARGET_NOT_FOUND" else []):
            matching = [item for item in references if item[0] == class_id]
            for _, prop, schema, _ in matching:
                index = len(identifiers) + 1
                candidates.append(
                    {
                        "subtype": "invalid_index",
                        "target_id": _missing_id(space_id or "", class_id, str(index)),
                        "target_name": (
                            (f"{inventory.space_names[space_id]} " if space_id is not None else "") +
                            f"{class_label(class_id)} {index}"
                        ),
                        "property": prop,
                        "value": _schema_value(schema) if family == "control" else None,
                        "reason": "DEVICE_TARGET_NOT_FOUND",
                        "candidate_ids": [],
                    }
                )

    if outcome in {"INVALID_VALUE", "SPACE_PROPERTY_NOT_SUPPORTED", "DEVICE_PROPERTY_NOT_SUPPORTED"}:
        if outcome == "INVALID_VALUE" and family == "control":
            requests = {(item.target_id, item.property): item.parameter_schema for item in inventory.setters}
            # Custom setters can accept a literal value alongside named presets.
            for tool in inventory.operation_tools:
                if tool["semantics"]["kind"] != "custom" or not tool["mutation"]:
                    continue
                for prop in tool["writes"]:
                    schemas = tool["parameters_schema"]["properties"]
                    if (tool["function"] == f"set_{prop}" and "value" in schemas
                            and prop in objects[tool["target"]]["properties"]):
                        requests[(tool["target"], prop)] = schemas["value"]
            for (target_id, property_name), schema in requests.items():
                values = []
                if schema.get("enum") or schema.get("choices") or any(schema.get(key) is not None for key in ("minimum", "maximum")):
                    values.append({"subtype": "invalid_value", "value": _invalid_schema_value(schema)})
                prop = getattr(inventory.world._state.devices[target_id].instance, property_name)
                values.extend(_invalid_resolution_values(prop, objects[target_id]["properties"][property_name], schema))
                candidates.extend({"target_id": target_id, "target_name": inventory.device_names[target_id],
                                   "property": property_name, "reason": "INVALID_VALUE",
                                   "candidate_ids": [target_id], **value} for value in values)
        elif outcome == "SPACE_PROPERTY_NOT_SUPPORTED" and target_kind == "space":
            for space_id, space in spaces.items():
                for prop, schema in property_catalog["space_properties"].items():
                    if prop in space["properties"]:
                        continue
                    for bounds in (schema.get("target_ranges", []) if family == "goal" else [{"min": None, "max": None}]):
                        candidates.append(
                            {
                                "subtype": "space_property_unavailable",
                                "target_id": space_id,
                                "target_name": inventory.space_names[space_id],
                                "property": prop,
                                "value": bounds["min"],
                                "assertion": {"op": "range", **deepcopy(bounds)},
                                "reason": "SPACE_PROPERTY_NOT_SUPPORTED",
                                "candidate_ids": [space_id],
                            }
                        )

        cache = inventory.world.runtime_cache
        if outcome == "DEVICE_PROPERTY_NOT_SUPPORTED" and target_kind == "device" and cache is not None:
            prototypes = cache.model_prototypes
            descriptors = cache.class_tool_descriptors

            def supports(tool: dict[str, Any], prop: str) -> bool:
                prefix = "get_" if family == "query" else "set_"
                mutation = family == "control"
                return (tool["mutation"] is mutation and tool["function"] == prefix + prop
                        and prop in tool["writes" if mutation else "reads"])

            for target_id, item in objects.items():
                class_id = item["class"]
                prefix = ".".join(class_id.split(".")[:2]) + "."
                target_tools = descriptors[class_id]
                sibling_properties: dict[str, dict[str, Any]] = {}
                for sibling_id, tools in descriptors.items():
                    if not sibling_id.startswith(prefix) or sibling_id == class_id:
                        continue
                    for tool in tools:
                        prop = tool["function"].removeprefix("get_" if family == "query" else "set_")
                        if (
                            not prop
                            or not supports(tool, prop)
                            or any(supports(target_tool, prop) for target_tool in target_tools)
                        ):
                            continue
                        if family == "query":
                            sibling_properties[prop] = prototypes[sibling_id][prop][
                                "schema"
                            ]
                        else:
                            schemas = tool["parameters_schema"]["properties"]
                            parameter = prop if prop in schemas else "value"
                            if parameter in schemas:
                                sibling_properties[prop] = schemas[parameter]
                for prop, schema in sibling_properties.items():
                    candidates.append(
                        {
                            "subtype": "sibling_property_unavailable",
                            "target_id": target_id,
                            "target_name": inventory.device_names[target_id],
                            "property": prop,
                            "value": _schema_value(schema) if family == "control" else None,
                            "reason": "DEVICE_PROPERTY_NOT_SUPPORTED",
                            "candidate_ids": [target_id],
                        }
                    )
    return candidates


def build_negative_task(
    inventory: TaskInventory,
    task_id: str,
    family: str,
    subtype: str,
    sampling: dict[str, Any],
    rng: random.Random,
) -> TaskArtifacts:
    """Return one inventory-derived infeasible task."""
    outcome = sampling["target_outcome"]
    candidates = _negative_candidates(inventory, family, outcome, target_kind="space" if family == "goal" or subtype == "property.space" else "device")
    requested_subtype = sampling.get("negative_subtype")
    if requested_subtype is not None:
        candidates = [item for item in candidates if item["subtype"] == requested_subtype]
    if not candidates:
        raise TaskSeedError(
            f"no {requested_subtype or outcome} candidate for {family}.{subtype}"
        )
    selected = rng.choice(candidates)
    target_id = selected["target_id"]
    target_name = selected["target_name"]
    prop = selected["property"]
    requested_value = selected["value"]
    reason = selected["reason"]
    atom_id = {"query": "q1", "control": "c1", "goal": "g1"}[family]
    if family == "query":
        instruction = instruction_templates(
            [
                f"Tell me the current {prop} of {target_name}.",
                f"What is {target_name}'s current {prop}?",
                f"Read {target_name}'s {prop} and give me its current value.",
            ]
        )
    elif family == "control":
        if "delta" in selected:
            delta = selected["delta"]
            displayed_value = display_value(delta["amount"])
            instruction = instruction_templates([
                f"{delta['direction'].capitalize()} {target_name}'s {prop} by {displayed_value}.",
                f"On {target_name}, {delta['direction']} {prop} by {displayed_value}.",
            ])
        else:
            displayed_value = display_value(requested_value)
            instruction = instruction_templates(
                [
                    f"Set {target_name}'s {prop} to {displayed_value}.",
                    f"Change {target_name}'s {prop} to {displayed_value}.",
                    f"Make {target_name}'s {prop} {displayed_value}.",
                ]
            )
    else:
        bounds = selected["assertion"]
        instruction = instruction_templates([
            f"Bring {target_name}'s actual {prop} to {bounds['min']}.",
            f"Make the actual {prop} in {target_name} reach {bounds['min']}.",
        ]) if bounds["min"] == bounds["max"] else instruction_templates(
            [
                f"Bring {target_name}'s {prop} between {bounds['min']} and {bounds['max']}.",
                f"Bring {target_name}'s {prop} into the range {bounds['min']} to {bounds['max']}.",
            ]
        )
    report = {
        "atom_id": atom_id,
        "status": "infeasible",
        "reason_code": reason,
        "affected_properties": [prop],
        "match": "exact",
    }
    report["description"] = {
        "SPACE_TARGET_NOT_FOUND": f"The requested space in {target_name} does not exist in this World.",
        "DEVICE_TARGET_NOT_FOUND": f"The requested device {target_name} does not exist in the specified space.",
        "DEVICE_PROPERTY_NOT_SUPPORTED": f"{target_name} does not support the requested {prop} operation.",
        "SPACE_PROPERTY_NOT_SUPPORTED": f"{target_name} does not provide the environmental property {prop}.",
        "INVALID_VALUE": f"The requested {prop} value {display_value(requested_value)} violates {target_name}'s declared value constraints.",
        "UNREACHABLE_GOAL": f"The requested actual {prop} value {requested_value} lies outside the proven reachable bounds.",
    }[reason]
    if "proof" in selected:
        if selected["proof"]["proof"] == "no_temperature_source":
            report["description"] += " No device effect or world dynamics can change this room's temperature."
        report["description"] += f" The interval is [{selected['proof']['min']}, {selected['proof']['max']}]."
    target = empty_target()
    target["expected_reports"] = [report]
    sampling["negative_subtype"] = selected["subtype"]
    sampling["target_selection"] = {
        "method": sampling["target_selection_method"],
        "outcome": outcome,
        "negative_subtype": selected["subtype"],
        "candidate_ids": selected["candidate_ids"],
        "selected_ids": [target_id],
        "selected_ids_natural_sorted": True,
    }
    sampling["property_target_value"] = {
        "method": sampling.get("property_target_value_method"),
        "records": [],
    }
    if "delta" in selected:
        sampling["property_target_value"].update(method="delta", recipes=[
            {"kind": "delta", "property": prop, **selected["delta"]},
        ])
    sampling["post_control_query"] = {"method": "none", "answer_source": None}
    atom_spec = {
        ("space_id" if family == "goal" or subtype == "property.space" else "target_id"): target_id,
        "target_name": target_name,
        "property": prop,
        "expected_status": "infeasible",
        "reason_code": reason,
    }
    if family != "query":
        atom_spec["assertion"] = (
            deepcopy(selected["assertion"]) if family == "goal"
            else {"op": "eq", "value": deepcopy(requested_value)}
        )
    if "delta" in selected:
        atom_spec["request_delta"] = deepcopy(selected["delta"])
    if "proof" in selected:
        atom_spec["infeasibility_proof"] = deepcopy(selected["proof"])
    atom = {"id": atom_id, "kind": family, "depends_on": [], "spec": atom_spec}
    public_anchors = [target_name, prop]
    if family != "query" and not isinstance(requested_value, bool):
        public_value = selected["delta"]["amount"] if "delta" in selected else requested_value
        public_anchors.append(display_value(public_value) if isinstance(public_value, (dict, list)) else str(public_value))
    if family == "goal":
        public_anchors.append(str(bounds["max"]))
    seed = build_task_seed(
        family,
        subtype,
        [atom],
        sampling,
        public_anchors=public_anchors,
        private_identifiers=(target_id,),
        feasibility="infeasible",
    )
    return TaskArtifacts(
        seed=seed,
        instruction_template=instruction,
        target=target,
        reference_plan=build_reference_plan(task_id, [submit_report(report)]),
    )
