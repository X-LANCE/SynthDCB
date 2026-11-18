"""Goal tasks built from causal control plans and valid environmental targets."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from itertools import combinations
import random
from typing import Any, Iterable

from src.contracts import strict_equal
from src.evaluation.validation.workflow import goal_evaluation_end

from ..task_common import (
    build_reference_plan,
    build_task_seed,
    deduplicate,
    display_value,
    empty_target,
    instruction_templates,
    join_clauses,
    memory_identifier,
    memory_user,
    memory_value,
    query_atom,
    read_memory,
    TaskArtifacts,
    TaskSeedError,
)
from ..task_inventory import (
    command,
    control_commands,
    ControlCandidate,
    GoalCandidate,
    InventoryError,
    natural_key,
    PropertyValue,
    TaskInventory,
    schema_accepts,
)
from ..task_sampler import sample_bounded_count
from ..task_selection import (
    selection_description_variants,
    target_selection,
    TargetSelection,
)


def _goal_value_source(
    inventory: TaskInventory,
    goals: list[GoalCandidate],
    rng: random.Random,
    *,
    require_closer: bool,
) -> PropertyValue:
    """Return the goal value source."""
    sources = _goal_value_sources(
        inventory, goals, require_closer=require_closer
    )
    if not sources:
        raise TaskSeedError(
            f"no query-derived Space value for Goal {goals[0].property}"
        )
    return rng.choice(sources)


def _goal_value_sources(
    inventory: TaskInventory,
    goals: Iterable[GoalCandidate],
    *,
    require_closer: bool = False,
) -> list[PropertyValue]:
    """Return the goal value sources."""
    group = tuple(goals)
    prop = group[0].property
    return [
        item
        for item in inventory.property_values("space")
        if item.property == prop
        and item.target_id not in {goal.space_id for goal in group}
        and isinstance(item.value, (int, float))
        and not isinstance(item.value, bool)
        and (
            not require_closer
            or all(
                isinstance(goal.initial_value, (int, float))
                and isinstance(goal.final_value, (int, float))
                and abs(float(goal.final_value) - float(item.value))
                < abs(float(goal.initial_value) - float(item.value))
                for goal in group
            )
        )
    ]


def _eligible_goals(
    inventory: TaskInventory,
    value_method: str,
    limit: int,
) -> list[GoalCandidate]:
    """Return the eligible goals."""
    try:
        candidates = list(inventory.goal_candidates(limit=limit))
    except InventoryError as error:
        raise TaskSeedError(str(error)) from error
    # Reject worsening AQI before choosing a layout, so the lazy search can
    # expand to later candidates that satisfy the existing Goal rule.
    candidates = [item for item in candidates
                  if item.property != "air_quality" or item.final_value <= item.initial_value]
    if value_method in {"random", "memory"}:
        return candidates
    if value_method == "delta":
        return [
            item
            for item in candidates
            if isinstance(item.initial_value, (int, float))
            and not isinstance(item.initial_value, bool)
            and isinstance(item.final_value, (int, float))
            and not isinstance(item.final_value, bool)
        ]
    if value_method == "query.property.space":
        return [
            item
            for item in candidates
            if isinstance(item.initial_value, (int, float))
            and not isinstance(item.initial_value, bool)
            and isinstance(item.final_value, (int, float))
            and not isinstance(item.final_value, bool)
            and _goal_value_sources(inventory, [item], require_closer=False)
        ]
    raise TaskSeedError(f"unsupported Goal value method {value_method}")


def _goal_layout(
    inventory: TaskInventory,
    subtype: str,
    target_method: str,
    value_method: str,
    structure: dict[str, Any],
    rng: random.Random,
) -> tuple[TargetSelection, list[GoalCandidate]]:
    """Expand the shared probe cache only when a layout needs more effects."""
    limit = max(1, len(inventory._goal_cache or ()))
    while True:
        try:
            return _goal_layout_from_candidates(inventory, subtype, target_method, value_method, structure, rng, limit)
        except TaskSeedError:
            if inventory._goals_exhausted and limit >= len(inventory._goal_cache or ()):
                raise
            limit += 1


def _goal_layout_from_candidates(
    inventory: TaskInventory,
    subtype: str,
    target_method: str,
    value_method: str,
    structure: dict[str, Any],
    rng: random.Random,
    limit: int,
) -> tuple[TargetSelection, list[GoalCandidate]]:
    """Return the goal layout."""
    goals = _eligible_goals(inventory, value_method, limit)
    dynamic_method = target_method.startswith("query.")
    if value_method == "query.property.space" and dynamic_method:
        goals = [
            goal for goal in goals
            if _goal_value_sources(
                inventory, [goal], require_closer=True
            )
        ]
    topk = structure["query_topk_count"]
    if not goals:
        raise TaskSeedError("no Goal candidates satisfy the value method")

    if subtype == "single":
        by_space: dict[str, list[GoalCandidate]] = defaultdict(list)
        for goal in goals:
            by_space[goal.space_id].append(goal)
        selection = target_selection(
            inventory,
            target_kind="space",
            candidate_ids=by_space,
            method=target_method,
            requested_count=1,
            topk_bounds=topk,
            rng=rng,
        )
        return selection, [rng.choice(by_space[selection.selected_ids[0]])]

    if subtype == "multi_property":
        bounds = structure["multi_property_count"]
        by_space: dict[str, dict[str, GoalCandidate]] = defaultdict(dict)
        for goal in goals:
            by_space[goal.space_id].setdefault(goal.property, goal)
        eligible = {
            space_id: values
            for space_id, values in by_space.items()
            if len(values) >= int(bounds["min"])
        }
        selection = target_selection(
            inventory,
            target_kind="space",
            candidate_ids=eligible,
            method=target_method,
            requested_count=1,
            topk_bounds=topk,
            rng=rng,
        )
        values = list(eligible[selection.selected_ids[0]].values())
        count = sample_bounded_count(len(values), bounds, floor=2, rng=rng)
        return selection, rng.sample(values, count)

    if subtype == "multi_target":
        bounds = structure["multi_target_count"]
        required_targets = max(
            int(bounds["min"]),
            3 if target_method == "query.target.comparison.topk" else 2,
        )
        by_property: dict[str, dict[str, GoalCandidate]] = defaultdict(dict)
        for goal in goals:
            by_property[goal.property].setdefault(goal.space_id, goal)
        viable: list[dict[str, GoalCandidate]] = []
        for group in by_property.values():
            if len(group) < required_targets:
                continue
            if value_method != "query.property.space":
                viable.append(group)
                continue
            identifiers = sorted(group, key=natural_key)
            for count in range(
                required_targets,
                min(len(identifiers), int(bounds["max"])) + 1,
            ):
                for subset in combinations(identifiers, count):
                    candidate = {space_id: group[space_id] for space_id in subset}
                    if _goal_value_sources(
                        inventory,
                        candidate.values(),
                        require_closer=dynamic_method,
                    ):
                        viable.append(candidate)
        if not viable:
            raise TaskSeedError("no compatible multi-target Goal group")
        group = rng.choice(viable)
        count = sample_bounded_count(
            len(group), bounds, floor=required_targets, rng=rng
        )
        selection = target_selection(
            inventory,
            target_kind="space",
            candidate_ids=group,
            method=target_method,
            requested_count=count,
            topk_bounds=topk,
            selected_count_bounds=bounds,
            rng=rng,
        )
        return selection, [group[space_id] for space_id in selection.selected_ids]

    if subtype != "complex":
        raise TaskSeedError(f"unknown Goal subtype {subtype}")
    property_bounds = structure["complex_property_count"]
    target_bounds = structure["complex_target_count"]
    required_targets = max(
        int(target_bounds["min"]),
        3 if target_method == "query.target.comparison.topk" else 2,
    )
    by_space: dict[str, dict[str, GoalCandidate]] = defaultdict(dict)
    for goal in goals:
        by_space[goal.space_id].setdefault(goal.property, goal)
    identifiers = sorted(by_space, key=natural_key)
    viable_sets: list[tuple[list[str], list[str]]] = []
    maximum_targets = min(len(identifiers), int(target_bounds["max"]))
    for count in range(required_targets, maximum_targets + 1):
        for subset in combinations(identifiers, count):
            spaces = list(subset)
            common = sorted(
                set.intersection(*(set(by_space[space_id]) for space_id in spaces))
            )
            if value_method == "query.property.space":
                common = [
                    prop for prop in common
                    if _goal_value_sources(
                        inventory,
                        [by_space[space_id][prop] for space_id in spaces],
                        require_closer=dynamic_method,
                    )
                ]
            if len(common) >= int(property_bounds["min"]):
                viable_sets.append((spaces, common))
    if not viable_sets:
        raise TaskSeedError("no compatible complex Goal group")
    candidates, common_props = rng.choice(viable_sets)
    requested_count = sample_bounded_count(
        len(candidates), target_bounds, floor=required_targets, rng=rng
    )
    selection = target_selection(
        inventory,
        target_kind="space",
        candidate_ids=candidates,
        method=target_method,
        requested_count=requested_count,
        topk_bounds=topk,
        selected_count_bounds=target_bounds,
        rng=rng,
    )
    property_count = sample_bounded_count(
        len(common_props), property_bounds, floor=2, rng=rng
    )
    properties = rng.sample(common_props, property_count)
    return selection, [
        by_space[space_id][prop]
        for space_id in selection.selected_ids
        for prop in properties
    ]


def _preview_goals(
    inventory: TaskInventory,
    goals: list[GoalCandidate],
) -> tuple[list[ControlCandidate], tuple[dict[str, Any], ...], dict[str, Any]]:
    """Return the preview goals."""
    advance = command("session", "sleep_time", minutes=max(goal.minutes for goal in goals))
    controls: list[ControlCandidate] = []
    seen: set[tuple[str, str]] = set()
    for control in (control for goal in goals for control in goal.controls):
        path = (control.setter.target_id, control.setter.property)
        if path not in seen:
            controls.append(control)
            seen.add(path)
        elif not any(
            path == (item.setter.target_id, item.setter.property)
            and strict_equal(item.requested_value, control.requested_value)
            for item in controls
        ):
            raise TaskSeedError("Goal candidates require conflicting controller values")
    commands = [*control_commands(controls), advance]
    preview = inventory.preview_from_initial(commands)
    if any(result.code != "[PASS]" for result in preview.results):
        raise TaskSeedError("joint Goal preview failed")
    start = inventory.initial["runtime"]["time_state"]["elapsed_minutes"]
    reference_end = preview.final_state["runtime"]["time_state"]["elapsed_minutes"]
    horizon = goal_evaluation_end(start, reference_end)
    baseline = inventory.preview_from_initial([command("session", "sleep_time", minutes=horizon - start)])
    preview = inventory.preview_from_initial([
        *commands, command("session", "sleep_time", minutes=horizon - reference_end),
    ])
    if any(result.code != "[PASS]" for result in (*baseline.results, *preview.results)):
        raise TaskSeedError("joint Goal horizon preview failed")
    for goal in goals:
        actual = preview.final_state["spaces"][goal.space_id]["properties"][goal.property]
        baseline_actual = baseline.final_state["spaces"][goal.space_id]["properties"][
            goal.property
        ]
        bounds = goal.target_range
        if (
            not bounds["min"] <= actual <= bounds["max"]
            or bounds["min"] <= baseline_actual <= bounds["max"]
            or bounds["min"] <= goal.initial_value <= bounds["max"]
        ):
            raise TaskSeedError("joint Goal controls do not causally reach the selected target range")
    return controls, tuple(commands), preview.final_state


def _shown_number(value: float) -> int | float:
    """Return a concise JSON number."""
    return int(value) if value.is_integer() else round(value, 6)


def _goal_assertion(
    inventory: TaskInventory,
    prop: str,
    target_range: dict[str, Any],
    actual: Any,
) -> dict[str, Any]:
    """Validate the environmental value domain and the reference result."""
    spec = inventory.world.loaded_world.domain.property_catalog["space_properties"][prop]
    endpoints = (target_range["min"], target_range["max"])
    if (endpoints[0] > endpoints[1]
            or any(not schema_accepts(spec, value) for value in endpoints)
            or ("precision" in spec and any(round(value, spec["precision"]) != value for value in endpoints))):
        raise TaskSeedError(f"Goal range for {prop} violates its value domain")
    if not target_range["min"] <= actual <= target_range["max"]:
        raise TaskSeedError(f"previewed {prop} does not satisfy its Goal range")
    return {"op": "range", **deepcopy(target_range)}


def build_goal_task(
    inventory: TaskInventory,
    task_id: str,
    subtype: str,
    sampling: dict[str, Any],
    structure: dict[str, Any],
    rng: random.Random,
) -> TaskArtifacts:
    """Return the goal task."""
    value_method = sampling["property_target_value_method"]
    if value_method == "memory" and subtype != "single":
        raise TaskSeedError("memory target values are limited to goal.single")
    selection, goals = _goal_layout(
        inventory,
        subtype,
        sampling["target_selection_method"],
        value_method,
        structure,
        rng,
    )
    _controls, goal_commands, final_state = _preview_goals(inventory, goals)
    by_property: dict[str, list[GoalCandidate]] = defaultdict(list)
    for goal in goals:
        by_property[goal.property].append(goal)

    dynamic_targets = bool(selection.atoms)
    value_atoms: list[dict[str, Any]] = []
    value_commands: list[dict[str, Any]] = []
    sources: dict[str, PropertyValue] = {}
    if value_method == "query.property.space":
        for index, (prop, group) in enumerate(sorted(by_property.items()), start=1):
            source = _goal_value_source(
                inventory,
                group,
                rng,
                require_closer=dynamic_targets,
            )
            sources[prop] = source
            value_atoms.append(query_atom(f"v{index}", source, role="target_value"))
            value_commands.append(source.query_command)

    atoms: list[dict[str, Any]] = [*deepcopy(selection.atoms), *deepcopy(value_atoms)]
    target = empty_target()
    clauses: list[str] = []
    records: list[dict[str, Any]] = []
    memory_records: list[dict[str, Any]] = []
    public_anchors = list(selection.public_anchors)
    memory_user_id, memory_user_name = (
        memory_user(inventory, sampling, rng)
        if value_method == "memory"
        else (None, None)
    )
    if memory_user_name is not None:
        public_anchors.append(memory_user_name)
    private_ids = set(selection.candidate_ids)
    source_atom_by_property = {
        atom["spec"]["property"]: atom["id"] for atom in value_atoms
    }

    recipes: dict[str, dict[str, Any]] = {}
    for prop, group in sorted(by_property.items()):
        actuals = {
            goal.space_id: deepcopy(
                final_state["spaces"][goal.space_id]["properties"][prop]
            )
            for goal in group
        }
        if prop == "air_quality" and any(
            float(actuals[goal.space_id]) > float(goal.initial_value)
            for goal in group
        ):
            raise TaskSeedError("air_quality Goals may only maintain or improve AQI")
        if value_method == "query.property.space":
            source = sources[prop]
            recipes[prop] = {
                "kind": "query_range",
                "source_target_id": source.target_id,
                "source_target_name": source.target_name,
                "source_property": source.property,
                "value": deepcopy(source.value),
            }
            public_anchors.extend((source.target_name, prop))
            private_ids.add(source.target_id)
        elif value_method == "memory":
            recipes[prop] = {"kind": "memory", "ranges": {goal.space_id: deepcopy(goal.target_range) for goal in group}}
        elif value_method == "delta":
            directions = {
                "increase"
                if float(actuals[goal.space_id]) > float(goal.initial_value)
                else "decrease"
                for goal in group
            }
            if len(directions) != 1:
                raise TaskSeedError("a shared Goal delta needs one direction")
            recipes[prop] = {"kind": "delta", "direction": next(iter(directions))}
        else:
            recipes[prop] = {"kind": "direct", "ranges": {goal.space_id: deepcopy(goal.target_range) for goal in group}}

    selection_dependencies = [atom["id"] for atom in selection.atoms]
    for index, goal in enumerate(
        sorted(goals, key=lambda item: (natural_key(item.space_id), item.property)),
        start=1,
    ):
        actual = deepcopy(
            final_state["spaces"][goal.space_id]["properties"][goal.property]
        )
        dependencies = list(selection_dependencies)
        source_atom = source_atom_by_property.get(goal.property)
        if source_atom:
            dependencies.append(source_atom)
        assertion = _goal_assertion(
            inventory, goal.property, goal.target_range, actual
        )
        spec = {
            "space_id": goal.space_id,
            "space_name": goal.space_name,
            "property": goal.property,
            "controller_device_id": goal.controls[0].setter.target_id,
            "controller_device_ids": list(dict.fromkeys(control.setter.target_id for control in goal.controls)),
            "assertion": deepcopy(assertion),
        }
        memory_id = None
        if value_method == "memory":
            memory_record, binding = memory_value(
                task_id=task_id,
                target_kind="space",
                target_id=goal.space_id,
                target_name=goal.space_name,
                prop=goal.property,
                value=deepcopy(goal.target_range),
                user_id=memory_user_id,
                user_name=memory_user_name,
            )
            memory_id = memory_record["memory_id"]
            memory_records.append(memory_record)
            target["required_memory_ids"].append(memory_id)
            private_ids.add(memory_id)
            spec["memory_binding"] = binding
        atoms.append(
            {
                "id": f"g{index}",
                "kind": "goal",
                "depends_on": sorted(set(dependencies)),
                "spec": spec,
            }
        )
        target["spaces"].setdefault(goal.space_id, {"properties": {}})[
            "properties"
        ][goal.property] = deepcopy(assertion)
        private_ids.add(goal.space_id)
        private_ids.update(control.setter.target_id for control in goal.controls)
        public_anchors.append(goal.property)
        value_record = {
            "space_id": goal.space_id,
            "property": goal.property,
            "initial_value": deepcopy(goal.initial_value),
            "previewed_value": actual,
            "assertion": deepcopy(assertion),
            "controller_device_id": goal.controls[0].setter.target_id,
            "controller_device_ids": list(dict.fromkeys(control.setter.target_id for control in goal.controls)),
            "control_plan": list(goal.commands),
        }
        if memory_id is not None:
            value_record["memory_id"] = memory_id
        records.append(value_record)

    for prop, recipe in sorted(recipes.items()):
        prop_records = [record for record in records if record["property"] == prop]
        if recipe["kind"] == "query_range":
            source = sources[prop]
            for record in prop_records:
                bounds = record["assertion"]
                lower = _shown_number(float(bounds["min"]) - float(source.value))
                upper = _shown_number(float(bounds["max"]) - float(source.value))
                record["source_offsets"] = {"min": lower, "max": upper}
                clauses.append(
                    f"read the current {prop} from {source.target_name}; "
                    f"bring {inventory.space_names[record['space_id']]}'s {prop} "
                    f"between that reading {lower:+g} and that reading {upper:+g}"
                )
                public_anchors.extend((inventory.space_names[record["space_id"]], str(lower), str(upper)))
        elif recipe["kind"] == "memory":
            owner = f" of {memory_user_name}" if memory_user_name else ""
            for record in prop_records:
                clauses.append(
                    f"bring {inventory.space_names[record['space_id']]}'s {prop} "
                    f"into the saved preferred range{owner}"
                )
                public_anchors.append(inventory.space_names[record["space_id"]])
        elif recipe["kind"] == "delta":
            for record in prop_records:
                assertion = record["assertion"]
                initial = float(record["initial_value"])
                if recipe["direction"] == "increase":
                    lower, upper = assertion["min"] - initial, assertion["max"] - initial
                else:
                    lower, upper = initial - assertion["max"], initial - assertion["min"]
                clauses.append(
                    f"{recipe['direction']} {inventory.space_names[record['space_id']]}'s "
                    f"{prop} by between {lower:g} and {upper:g}, ending between "
                    f"{assertion['min']} and {assertion['max']}"
                )
                public_anchors.extend((f"{lower:g}", f"{upper:g}"))
        elif dynamic_targets:
            bounds = prop_records[0]["assertion"]
            if any(record["assertion"] != bounds for record in prop_records):
                raise TaskSeedError("query-selected Goal targets require a shared range")
            outcome = f"to {bounds['min']}" if bounds['min'] == bounds['max'] else f"between {bounds['min']} and {bounds['max']}"
            clauses.append(f"bring {prop} {outcome}")
            public_anchors.extend((str(bounds["min"]), str(bounds["max"])))
        else:
            for record in prop_records:
                assertion = record["assertion"]
                if assertion["op"] == "range":
                    outcome = (f"to {assertion['min']}" if assertion['min'] == assertion['max']
                               else f"between {assertion['min']} and {assertion['max']}")
                    clauses.append(
                        f"bring {inventory.space_names[record['space_id']]}'s "
                        f"{prop} {outcome}"
                    )
                    public_anchors.extend(
                        (
                            inventory.space_names[record["space_id"]],
                            str(assertion["min"]),
                            str(assertion["max"]),
                        )
                    )
                else:
                    value = display_value(assertion["value"])
                    clauses.append(
                        f"make {inventory.space_names[record['space_id']]}'s "
                        f"{prop} equal to {value}"
                    )
                    public_anchors.extend(
                        (inventory.space_names[record["space_id"]], value)
                    )
    outcome = join_clauses(clauses)
    instruction = instruction_templates(
        sentence
        for target_description in selection_description_variants(
            inventory,
            selection,
            target_kind="space",
        )
        for sentence in (
            f"For {target_description}, {outcome}.",
            f"Set the goal for {target_description} to {outcome}.",
            f"For {target_description}, work toward this outcome: {outcome}.",
        )
    )

    sampling["target_selection"] = deepcopy(selection.details)
    sampling["property_target_value"] = {
        "method": value_method,
        "records": records,
        "recipes": deepcopy(recipes),
    }
    sampling["post_control_query"] = {"method": "none", "answer_source": None}
    seed = build_task_seed(
        "goal",
        subtype,
        atoms,
        sampling,
        public_anchors=public_anchors,
        private_identifiers=private_ids,
        selection_plans=[deepcopy(selection.details)],
    )
    return TaskArtifacts(
        seed=seed,
        instruction_template=instruction,
        target=target,
        reference_plan=build_reference_plan(
            task_id,
            [
                *([read_memory()] if memory_records else []),
                *selection.commands,
                *deduplicate(value_commands),
                *goal_commands,
            ],
        ),
        memory=(
            {
                "scope_id": memory_identifier(task_id, "scope"),
                "records": memory_records,
            }
            if memory_records
            else None
        ),
    )
