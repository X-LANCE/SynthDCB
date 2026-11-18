"""Build executable Control tasks from declared device capabilities."""

from __future__ import annotations

from copy import deepcopy

from src.contracts import strict_equal
from src.contracts.capabilities import precondition_matches
from src.utils import format_json

from ..task_common import (
    build_reference_plan,
    build_task_seed,
    empty_target,
    TaskArtifacts,
)
from ..task_inventory import candidate_values, InventoryError, preview_operation
from ..task_sampler import sample_capability, sample_parameters
from ..validator import validate_task_seed


def prepare_operation(inventory, tool, commands, rng, visiting=()):
    """Reach declared local preconditions through executable public operations."""
    if tool["tool_id"] in visiting or len(visiting) >= 8:
        raise InventoryError("cyclic or excessive operation prerequisites")
    visiting = (*visiting, tool["tool_id"])
    commands = list(commands)
    for prop, condition in tool["semantics"].get("preconditions", {}).items():
        state = inventory.preview_from_initial(commands).final_state if commands else inventory.initial
        if isinstance(condition, dict) and set(condition) == {"contains_key"}:
            # The bound key is chosen by sample_parameters after local setup.
            if not state["objects"][tool["target"]]["properties"][prop]:
                raise InventoryError(f"{prop} has no record available for the required key")
            continue
        if precondition_matches(state["objects"][tool["target"]]["properties"][prop], condition):
            continue
        choices = condition["one_of"] if isinstance(condition, dict) and set(condition) == {"one_of"} else [condition]
        candidates = []
        for other in inventory.operation_tools:
            if other["target"] != tool["target"] or other["tool_id"] in visiting:
                continue
            semantic = other["semantics"]
            if semantic["kind"] == "set" and semantic["property"] == prop:
                candidates.extend((other, {semantic["parameter"]: value}) for value in choices)
            elif semantic["kind"] == "update":
                binding = semantic["fields"].get(prop, {})
                if "value" in binding and precondition_matches(binding["value"], condition):
                    candidates.append((other, {}))
                elif "parameter" in binding:
                    candidates.extend((other, {binding["parameter"]: value}) for value in choices)
            elif prop == "status" and semantic["kind"] in {"process_start", "process_pause", "process_resume"}:
                status = "paused" if semantic["kind"] == "process_pause" else "running"
                if precondition_matches(status, condition):
                    candidates.append((other, {}))
        rng.shuffle(candidates)
        for other, overrides in candidates:
            try:
                prefix = prepare_operation(inventory, other, commands, rng, visiting)
                before = inventory.preview_from_initial(prefix).final_state if prefix else inventory.initial
                parameters = sample_parameters(other, before, rng)
                parameters.update(overrides)
                accepted = preview_operation(inventory, other, parameters, prefix=prefix)
                commands = list(accepted.commands)
                break
            except InventoryError:
                continue
        else:
            raise InventoryError(f"cannot establish {tool['function']} prerequisite {prop}={condition!r}")
    return commands


def preview_with_boolean_setup(inventory, tool, parameters, *, prefix=()):
    """Try one public Boolean setter for an interlock enforced in action code."""
    try:
        return preview_operation(inventory, tool, parameters, prefix=prefix)
    except InventoryError:
        state = inventory.preview_from_initial(prefix).final_state if prefix else inventory.initial
        for prop in sorted(set(tool['reads']) - set(tool['writes'])):
            current = state['objects'][tool['target']]['properties'][prop]
            setter = inventory.setter(tool['target'], prop)
            if type(current) is not bool or setter is None:
                continue
            try:
                return preview_operation(inventory, tool, parameters,
                    prefix=[*prefix, setter.command_for(not current)])
            except InventoryError:
                continue
        raise


def build_capability_task(inventory, task_id, profile, rng):
    tools = [tool for tool in inventory.operation_tools if tool["semantics"]["kind"] in {"set", "update", "collection_add", "collection_update", "collection_delete", "process_start", "process_pause", "process_resume"}]
    if not tools:
        raise InventoryError("World has no declared Control operations")
    group_count = rng.randint(profile["control_groups"]["min"], profile["control_groups"]["max"])
    commands, selected, used = [], [], set()
    state = inventory.initial
    for _ in range(group_count):
        remaining = [tool for tool in tools if tool["tool_id"] not in used]
        untouched = [tool for tool in remaining if all(tool["target"] != prior.tool["target"] for prior in selected)]
        if untouched:
            remaining = untouched
        accepted = None
        for _ in range(min(30, max(1, len(remaining) * 3))):
            if not remaining:
                break
            tool = sample_capability(remaining, inventory, profile["capability_weights"], rng)
            prefix = list(commands)
            properties = state["objects"][tool["target"]]["properties"]
            if tool["function"] != "set_power" and properties.get("power") is False:
                power = inventory.setter(tool["target"], "power")
                if power is not None:
                    prefix.append(power.command_for(True))
            try:
                prefix = prepare_operation(inventory, tool, prefix, rng)
                before = inventory.preview_from_initial(prefix).final_state if prefix else inventory.initial
                parameters = sample_parameters(tool, before, rng)
                semantic = tool["semantics"]
                if semantic["kind"] == "set":
                    prop = semantic["property"]
                    values = candidate_values(prop, tool["parameters_schema"]["properties"][semantic["parameter"]], before["objects"][tool["target"]]["properties"][prop])
                    if values:
                        parameters[semantic["parameter"]] = rng.choice(values)
                accepted = preview_with_boolean_setup(inventory, tool, parameters, prefix=prefix)
                break
            except InventoryError as error:
                inventory.capability_rejections[tool["tool_id"]] = str(error)
                remaining = [item for item in remaining if item["tool_id"] != tool["tool_id"]]
        if accepted is None:
            raise InventoryError(f"could construct only {len(selected)} of {group_count} requested Control groups")
        selected.append(accepted)
        used.add(accepted.tool["tool_id"])
        commands = list(accepted.commands)
        state = inventory.preview_from_initial(commands).final_state

    target = empty_target()
    atoms = []
    for device_id in sorted({item.tool["target"] for item in selected}):
        initial = inventory.initial["objects"][device_id]["properties"]
        final = state["objects"][device_id]["properties"]
        assertions = {}
        collections = {item.tool["semantics"]["property"] for item in selected if item.tool["target"] == device_id and item.tool["semantics"]["kind"].startswith("collection_")}
        for prop, value in final.items():
            if strict_equal(value, initial[prop]):
                continue
            if prop in collections:
                old = initial[prop]
                assertion = {"op": "collection_change", "add": [deepcopy(value[key]) for key in sorted(value.keys() - old.keys())],
                             "update": {key: {field: deepcopy(content) for field, content in value[key].items() if not strict_equal(content, old[key].get(field))} for key in sorted(value.keys() & old.keys()) if not strict_equal(value[key], old[key])}, "remove": sorted(old.keys() - value.keys())}
            else:
                assertion = {"op": "eq", "value": deepcopy(value)}
            assertions[prop] = assertion
            atoms.append({"id": f"c{len(atoms)+1}", "kind": "control", "depends_on": [], "spec": {"target_id": device_id, "target_name": inventory.device_names[device_id], "property": prop, "assertion": assertion}})
        if assertions:
            target["objects"][device_id] = {"properties": assertions}
    if not atoms:
        raise InventoryError("the complete Control sequence restores every initial goal")
    target_count = len(target["objects"])
    properties = {atom["spec"]["property"] for atom in atoms}
    subtype = "complex" if target_count > 1 and len(properties) > 1 else "multi_target" if target_count > 1 else "multi_property" if len(properties) > 1 else "single"
    instructions = []
    by_command = {(tool["target"], tool["function"]): tool for tool in inventory.operation_tools}
    for command in commands:
        tool = by_command[(command["target"], command["function"])]
        name = inventory.device_names[tool["target"]]
        verb = tool["function"].replace("_", " ")
        parameters = ", ".join(f"{key}={format_json(value, ensure_ascii=False)}" for key, value in command["parameters"].items())
        instructions.append(f"On {name}, {verb} ({parameters})")
    operations = [{"target_id": item.tool["target"], "function": item.tool["function"], "reads": item.tool["reads"], "writes": item.tool["writes"], "parameters": item.parameters} for item in selected]
    instruction = "First, " + "; then ".join(instructions) + ". Turn on a device first when required. Preserve all unrelated settings and collection records."
    sampling = {"profile_id": profile["profile_id"], "task_type": f"control.{subtype}", "target_outcome": "valid", "operation_groups": operations, "group_count": group_count, "hierarchy": ["base_family", "class", "instance", "capability"]}
    seed = build_task_seed("control", subtype, atoms, sampling, public_anchors=[inventory.device_names[item.tool["target"]] for item in selected], private_identifiers=[item.tool["target"] for item in selected])
    validate_task_seed(seed)
    inventory.world.contract.validate_target(target, inventory.world_spec, inventory.initial)
    return TaskArtifacts(seed, instruction, target, build_reference_plan(task_id, commands), None)
