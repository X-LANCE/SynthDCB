"""Build process Workflows and their required initial states."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta

from src.contracts import strict_equal
from src.contracts.capabilities import process_phases
from src.runtime import World
from src.evaluation.validation.workflow import evaluate_workflow, goal_evaluation_end
from src.utils import format_json

from ..task_common import (
    build_reference_plan,
    build_task_seed,
    empty_target,
    TaskArtifacts,
)
from ..task_inventory import (
    candidate_values,
    command,
    InventoryError,
    preview_operation,
    TaskInventory,
)
from ..task_sampler import sample_parameters, weighted_choice
from ..validator import validate_task_seed


def build_workflow_task(inventory, task_id, profile, rng):
    has_process = any(hasattr(device.instance, "PROCESS") for device in inventory.world._state.devices.values())
    subtype = weighted_choice({key: weight for key, weight in profile["workflow"]["subtype_weights"].items()
                               if has_process or key == "environment_deadline"}, rng)
    if subtype == "environment_deadline":
        return _environment_deadline(inventory, task_id, profile, rng)
    outcome = "valid" if subtype == "environment_before_process" else weighted_choice(profile["workflow"]["outcome_weights"], rng)
    if outcome != "valid":
        return _negative_workflow(inventory, task_id, profile, rng, outcome)
    candidates = [device_id for device_id, device in inventory.world._state.devices.items()
                  if hasattr(device.instance, "PROCESS") and inventory.initial["objects"][device_id]["properties"]["status"] in {"idle", "running"}]
    if not candidates:
        raise InventoryError("World has no idle or running process capability")
    count = 2 if subtype == "synchronize" else 1
    if len(candidates) < count:
        raise InventoryError(f"workflow.{subtype} requires {count} independent process instances")
    selected = rng.sample(sorted(candidates), count)
    initial_mode = weighted_choice(profile["workflow"]["initial_state_weights"], rng)
    resolved = inventory.world.get_world_spec()
    world_init = {
        "world_id": task_id, "domain": {"type": resolved["domain"]["type"]},
        "template": None,
        "config": {key: resolved[key] for key in ("spaces", "objects", "runtime")},
        "init": [],
    }
    world_init["config"]["domain_metadata"] = resolved["domain"]["metadata"]
    world_init["config"]["scene_metadata"] = resolved.get("scene_metadata", {})
    world_init["config"]["runtime"]["time_policy"].update(after_action_default_minutes=0, after_turn_default_minutes=0)
    world_init["config"]["runtime"]["time_policy"].pop("max_elapsed_minutes", None)
    # Workflow initial states are separate effective Worlds; Q/C/G pools retain
    # their original initial state and never receive these process fixtures.
    root = inventory.world.world_dir.parent / f"{task_id}_workflow"
    blueprint = inventory.world.runtime_cache.blueprint_from_world_init(root, world_init)
    world = World(root, runtime_cache=inventory.world.runtime_cache, blueprint=blueprint, require_device_tool_discovery=False)
    active = TaskInventory(world, goal_probe_max_minutes=profile["goal_probe_max_minutes"],
                           goal_probe_max_plans=profile.get("goal_probe_max_plans"))
    processes, modes, durations, starts = {}, {}, {}, {}
    for target_id in selected:
        process = world._state.devices[target_id].instance.PROCESS
        properties = active.initial["objects"][target_id]["properties"]
        mode = properties[process["mode_property"]] if properties["status"] == "running" else rng.choice(sorted(process["modes"]))
        tools = {tool["function"]: tool for tool in active.operation_tools if tool["target"] == target_id}
        tool = tools[process["start_function"]]
        parameters = sample_parameters(tool, active.initial, rng)
        parameters[tool["semantics"]["mode_parameter"]] = mode
        start = []
        if properties.get("power") is False:
            power = active.setter(target_id, "power")
            if power is None:
                raise InventoryError(f"{target_id}: process requires an unavailable power action")
            start.append(power.command_for(True))
        if properties["status"] == "idle":
            start.append(command(target_id, process["start_function"], **parameters))
        processes[target_id], modes[target_id] = process, mode
        durations[target_id] = sum(phase["minutes"] for phase in process_phases(process, properties, mode))
        starts[target_id] = start

    if initial_mode == "running":
        setup = [item for target_id in selected for item in starts[target_id]]
        if min(durations.values()) > 1:
            setup.append(command("session", "sleep_time", minutes=1))
        preview = active.preview_from_initial(setup)
        if any(result.code != "[PASS]" for result in preview.results):
            raise InventoryError("running Workflow initialization failed its preview")
        for scope in ("objects", "spaces"):
            for target_id, item in preview.final_state[scope].items():
                world_init["config"][scope][target_id]["properties"] = deepcopy(item["properties"])
        world_init["config"]["runtime"]["time_state"] = deepcopy(preview.final_state["runtime"]["time_state"])
        blueprint = inventory.world.runtime_cache.blueprint_from_world_init(root, world_init)
        world = World(root, runtime_cache=inventory.world.runtime_cache, blueprint=blueprint, require_device_tool_discovery=False)
        active = TaskInventory(world, goal_probe_max_minutes=profile["goal_probe_max_minutes"],
                           goal_probe_max_plans=profile.get("goal_probe_max_plans"))
        starts = {target_id: [] for target_id in selected}
    elif any(active.initial["objects"][target_id]["properties"]["status"] != "idle" for target_id in selected):
        raise InventoryError("idle Workflow sampling selected an already running process")

    initial_time = active.initial["runtime"]["time_state"]
    now = initial_time["elapsed_minutes"]
    remaining = {target_id: (active.initial["objects"][target_id]["properties"]["remaining_minutes"] if not starts[target_id] else durations[target_id]) for target_id in selected}
    if any(minutes <= 0 for minutes in remaining.values()):
        raise InventoryError("Workflow process must still require positive time to complete")
    tolerance = profile["workflow"]["tolerance_minutes"]
    target = empty_target()
    transitions, relations, scheduled, instructions = [], [], [], []
    anchors = [active.device_names[target_id] for target_id in selected]
    finish_times = {}
    for index, target_id in enumerate(selected):
        delay = max(remaining.values()) - remaining[target_id] if subtype == "synchronize" else rng.randint(1, 3) if subtype == "at" and initial_mode == "idle" else 0
        if subtype == "synchronize" and initial_mode == "running" and max(remaining.values()) - min(remaining.values()) > tolerance:
            raise InventoryError("already running processes cannot meet the sampled synchronization tolerance")
        scheduled.extend((now + delay, item) for item in starts[target_id])
        finish_times[target_id] = now + delay + remaining[target_id]
        transitions.append({"id": f"done_{index+1}", "scope": "object", "target_id": target_id, "property": "status", "from": "running", "to": "completed"})
        process = processes[target_id]
        props = active.initial["objects"][target_id]["properties"]
        target["objects"][target_id] = {"properties": {"status": {"op": "eq", "value": "completed"}, "phase": {"op": "eq", "value": "completed"}, "remaining_minutes": {"op": "eq", "value": 0}, process["mode_property"]: {"op": "eq", "value": modes[target_id]}}}
        start_tool = next(tool for tool in active.operation_tools
                          if tool["target"] == target_id and tool["function"] == process["start_function"])
        start_writes = set(start_tool["writes"])
        for prop in props:
            # Preserve user settings; process outputs and declared start effects
            # follow the model contract as the requested cycle runs.
            if active.setter(target_id, prop) is not None and prop not in start_writes | {"power", process["mode_property"]}:
                target["objects"][target_id]["properties"][prop] = {"op": "unchanged"}
        action = "Observe the already running" if initial_mode == "running" else "Run"
        instructions.append(f"{action} {modes[target_id]} cycle on {active.device_names[target_id]} to completion")

    completion = max(finish_times.values())
    if subtype == "synchronize":
        relations.append({"kind": "synchronize", "events": [event["id"] for event in transitions], "tolerance_minutes": tolerance})
        instructions.append(f"The cycles must finish within {tolerance} minute(s) of each other")
    if subtype in {"at", "before"}:
        minute = completion + (1 if subtype == "before" else 0)
        clock = datetime.strptime(f"{initial_time['date']} {initial_time['clock']}", "%Y-%m-%d %H:%M") + timedelta(minutes=minute-now)
        if subtype == "at":
            relations.append({"kind": "at", "event": "done_1", "minute": minute, "tolerance_minutes": tolerance})
            instructions.append(f"Complete at {clock:%Y-%m-%d %H:%M} {initial_time['timezone']}, within {tolerance} minute(s)")
        else:
            relations.append({"kind": "before", "event": "done_1", "minute": minute})
            instructions.append(f"Complete strictly before {clock:%Y-%m-%d %H:%M} {initial_time['timezone']}")

    commands = []
    cursor = now
    latest_follow_minute = completion
    for minute, item in sorted(scheduled, key=lambda entry: entry[0]):
        if minute > cursor:
            commands.append(command("session", "sleep_time", minutes=minute-cursor))
            cursor = minute
        commands.append(item)
    if subtype == "environment_before_process":
        index = 0
        while True:
            goals = active.goal_candidates(limit=index + 1)
            if len(goals) <= index:
                raise InventoryError("no environmental range is reached before process completion")
            goal = goals[index]
            index += 1
            if now + goal.minutes >= completion or any(item["target"] in selected for item in goal.commands):
                continue
            event = {"id": "entered_range", "scope": "space", "target_id": goal.space_id,
                     "property": goal.property, "predicate": {"op": "range", **deepcopy(goal.target_range)}}
            relation = {"kind": "ordered", "before": "entered_range", "after": "done_1",
                        "min_minutes": 1, "max_minutes": completion - now}
            check = {"workflow": {"evaluation_end_minute": completion,
                                  "transitions": [*transitions, event], "relations": [relation]}}
            # Replay both processes together; independent Goal probes can miss interacting effects.
            preview = active.preview_from_initial([*commands, *goal.commands,
                                                   command("session", "sleep_time", minutes=completion - now)])
            if (all(result.code == "[PASS]" for result in preview.results)
                    and evaluate_workflow(check, preview.audit_records)["passed"]):
                break
        commands.extend(goal.commands)
        transitions.append(event)
        relations.append(relation)
        instructions.append(f"Bring {goal.space_name}'s actual {goal.property} into the range "
                            f"{goal.target_range['min']} to {goal.target_range['max']} strictly before "
                            f"that cycle on {active.device_names[selected[0]]} completes")
        anchors.extend([goal.space_name, goal.property, str(goal.target_range["min"]), str(goal.target_range["max"])])
    if subtype.startswith("condition_"):
        if subtype == "condition_follow":
            delay, lower, upper = 0, 0, tolerance
            timing = f"within {tolerance} minute(s) after"
        elif subtype == "condition_delay":
            delay = rng.choice(profile["workflow"]["delay_minutes"])
            lower, upper = max(0, delay - tolerance), delay + tolerance
            timing = f"{delay} minute(s) after (with a tolerance of {tolerance} minute(s))"
        else:
            lower, upper = rng.choice(profile["workflow"]["windows_minutes"])
            delay = lower
            timing = f"between {lower} and {upper} minutes after"
        latest_follow_minute = completion + upper
        at = completion + delay
        commands.append(command("session", "sleep_time", minutes=at-cursor))
        cursor = at
        before = active.preview_from_initial(commands).final_state
        operations = [tool for tool in active.operation_tools if tool["target"] not in selected and tool["semantics"]["kind"] in {"set", "update"}]
        rng.shuffle(operations)
        follow = None
        for tool in operations:
            try:
                parameters = sample_parameters(tool, before, rng)
                semantic = tool["semantics"]
                if semantic["kind"] == "set":
                    values = candidate_values(semantic["property"], tool["parameters_schema"]["properties"][semantic["parameter"]], before["objects"][tool["target"]]["properties"][semantic["property"]])
                    if values:
                        parameters[semantic["parameter"]] = rng.choice(values)
                candidate = preview_operation(active, tool, parameters, prefix=commands)
                changed = {
                    prop: assertion for prop, assertion in candidate.assertions.items()
                    if not strict_equal(before["objects"][tool["target"]]["properties"][prop], assertion["value"])
                }
                # Events must also be unsatisfied in the task's initial state:
                # waiting can change a property that the action then restores.
                if not changed or any(
                    strict_equal(active.initial["objects"][tool["target"]]["properties"][prop], assertion["value"])
                    for prop, assertion in changed.items()
                ):
                    raise InventoryError("follow-up action has no change or restores an initially satisfied transition")
                follow = candidate
                break
            except InventoryError as error:
                inventory.capability_rejections[tool["tool_id"]] = str(error)
        if follow is None:
            raise InventoryError("no declared control can follow the process completion")
        commands = list(follow.commands)
        target["objects"][follow.tool["target"]] = {"properties": follow.assertions}
        for index, (prop, assertion) in enumerate(follow.assertions.items()):
            if strict_equal(before["objects"][follow.tool["target"]]["properties"][prop], assertion["value"]):
                continue
            event_id = f"follow_{index+1}"
            transitions.append({"id": event_id, "scope": "object", "target_id": follow.tool["target"], "property": prop, "from": before["objects"][follow.tool["target"]]["properties"][prop], "to": assertion["value"]})
            relations.append({"kind": "ordered", "before": "done_1", "after": event_id, "min_minutes": lower, "max_minutes": upper})
        instructions.append(f"Only {timing} completion, on {active.device_names[follow.tool['target']]} {follow.tool['function'].replace('_', ' ')} with {format_json(follow.parameters, ensure_ascii=False)}; do not perform this action early")

    horizon = max(completion, cursor, latest_follow_minute) + tolerance + 3
    target["workflow"] = {"evaluation_end_minute": horizon, "transitions": transitions, "relations": relations}
    world_init["config"]["runtime"]["time_policy"]["max_elapsed_minutes"] = horizon
    instruction = ". ".join(instructions) + ". Keep the other cycle settings unchanged. You may finish once no further action is needed; the World continues running."
    atoms = [{"id": "w1", "kind": "workflow", "depends_on": [], "spec": {"process_targets": selected, "initial_state": initial_mode, "completion_requirements": deepcopy(target["workflow"])}}]
    sampling = {"profile_id": profile["profile_id"], "task_type": f"workflow.{subtype}", "target_outcome": "valid", "initial_state": initial_mode}
    seed = build_task_seed("workflow", subtype, atoms, sampling, public_anchors=anchors, private_identifiers=selected)
    validate_task_seed(seed)
    world.contract.validate_target(target, world.get_world_spec(), active.initial)
    return TaskArtifacts(seed, instruction, target, build_reference_plan(task_id, commands), None), world_init


def _environment_deadline(inventory, task_id, profile, rng):
    """Require first entry into an environmental range before a deadline."""
    world_init = deepcopy(inventory.world.blueprint.loaded_world.world_init)
    world_init["world_id"] = task_id
    policy = world_init["config"]["runtime"]["time_policy"]
    policy.update(after_action_default_minutes=0, after_turn_default_minutes=0)
    policy.pop("max_elapsed_minutes", None)
    root = inventory.world.world_dir.parent / f"{task_id}_workflow"
    blueprint = inventory.world.runtime_cache.blueprint_from_world_init(root, world_init)
    world = World(root, runtime_cache=inventory.world.runtime_cache, blueprint=blueprint,
                  require_device_tool_discovery=False)
    active = TaskInventory(world, goal_probe_max_minutes=profile["goal_probe_max_minutes"],
                           goal_probe_max_plans=profile.get("goal_probe_max_plans"))
    goal = active.goal_candidates(limit=1)[0]
    time = active.initial["runtime"]["time_state"]
    start = time["elapsed_minutes"]
    control_end = active.preview_from_initial(goal.commands).final_state["runtime"]["time_state"]["elapsed_minutes"]
    arrival = control_end + goal.minutes
    horizon = goal_evaluation_end(start, arrival)
    target = empty_target()
    predicate = {"op": "range", **deepcopy(goal.target_range)}
    target["workflow"] = {
        "evaluation_end_minute": horizon,
        "transitions": [{"id": "entered_range", "scope": "space", "target_id": goal.space_id,
                         "property": goal.property, "predicate": predicate}],
        "relations": [{"kind": "before", "event": "entered_range", "minute": arrival + 1}],
    }
    policy["max_elapsed_minutes"] = horizon
    clock = datetime.strptime(f"{time['date']} {time['clock']}", "%Y-%m-%d %H:%M") + timedelta(minutes=arrival - start + 1)
    instruction = (f"Bring {goal.space_name}'s actual {goal.property} into the range "
                   f"{predicate['min']} to {predicate['max']} strictly before {clock:%Y-%m-%d %H:%M} "
                   f"{time['timezone']}. You may finish after setting the controls; the World continues running.")
    atoms = [{"id": "w1", "kind": "workflow", "depends_on": [],
              "spec": {"completion_requirements": deepcopy(target["workflow"])}}]
    sampling = {"profile_id": profile["profile_id"], "task_type": "workflow.environment_deadline", "target_outcome": "valid"}
    seed = build_task_seed("workflow", "environment_deadline", atoms, sampling,
                           public_anchors=[goal.space_name, goal.property, str(predicate["min"]), str(predicate["max"])],
                           private_identifiers=[goal.space_id])
    world.contract.validate_target(target, world.get_world_spec(), active.initial)
    return TaskArtifacts(seed, instruction, target, build_reference_plan(task_id, goal.commands), None), world_init


def _negative_workflow(inventory, task_id, profile, rng, outcome):
    if outcome == "DEVICE_TARGET_NOT_FOUND":
        processes = [target_id for target_id, device in inventory.world._state.devices.items() if hasattr(device.instance, "PROCESS")]
        if not processes:
            raise InventoryError("a nonexistent process target requires an existing process family")
        original = rng.choice(processes)
        target_id = original + "_unavailable"
        target_name = inventory.device_names[original] + " auxiliary unit"
        reason = "DEVICE_TARGET_NOT_FOUND"
    else:
        ordinary = [target_id for target_id, device in inventory.world._state.devices.items() if not hasattr(device.instance, "PROCESS")]
        if not ordinary:
            raise InventoryError("unsupported process tasks require a non-process device")
        target_id = rng.choice(ordinary)
        target_name = inventory.device_names[target_id]
        reason = "DEVICE_PROPERTY_NOT_SUPPORTED"
    report = {"atom_id": "w1", "status": "infeasible", "reason_code": reason, "affected_properties": ["process"], "match": "exact"}
    report["description"] = (f"The requested device {target_name} does not exist." if reason == "DEVICE_TARGET_NOT_FOUND"
                             else f"{target_name} has no automatic timed process capability.")
    target = empty_target()
    target["expected_reports"] = [report]
    horizon = inventory.initial["runtime"]["time_state"]["elapsed_minutes"] + 5
    target["workflow"] = {"evaluation_end_minute": horizon, "transitions": [], "relations": []}
    sampling = {"profile_id": profile["profile_id"], "task_type": "workflow.single", "target_outcome": outcome}
    seed = build_task_seed("workflow", "single", [{"id": "w1", "kind": "workflow", "depends_on": [], "spec": {"target_id": target_id, "property": "process", "reason_code": reason}}], sampling, public_anchors=[target_name], private_identifiers=[target_id], feasibility="infeasible")
    instruction = f"Run an automatic timed cycle on {target_name} and let it complete."
    world_init = deepcopy(inventory.world.blueprint.loaded_world.world_init)
    world_init["world_id"] = task_id
    world_init["config"]["runtime"]["time_policy"]["max_elapsed_minutes"] = horizon
    return TaskArtifacts(seed, instruction, target, build_reference_plan(task_id, [command("session", "submit_report", **{key: value for key, value in report.items() if key not in {"match", "atom_id"}})]), None), world_init
