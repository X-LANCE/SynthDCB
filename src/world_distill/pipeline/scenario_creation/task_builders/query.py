"""Property, space, and target Queries with shared-action variants."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import random
from typing import Any, Iterable

from src.runtime import World

from ..task_common import (
    build_reference_plan,
    build_task_seed,
    deduplicate,
    empty_target,
    finish,
    instruction_templates,
    mark_action_reuse,
    memory_identifier,
    memory_user,
    query_atom,
    read_memory,
    submit_answer,
    TaskArtifacts,
    TaskSeedError,
)
from ..task_inventory import (
    command,
    json_value,
    natural_key,
    PropertyValue,
    preview_operation,
    TaskInventory,
)
from ..task_sampler import DEFAULT_STRUCTURE, sample_bounded_count, sample_parameters, sampling_options
from ..task_selection import (
    collective_target_description,
    comparison_matches,
    rank_matches,
    space_baselines,
    _COMPARISON_PHRASES,
)
from ..validator import validate_task_seed


def build_collection_query_task(inventory, task_id, sampling, tool, rng):
    """Query an existing collection record through its declared read action."""
    parameters = sample_parameters(tool, inventory.initial, rng)
    candidate = preview_operation(inventory, tool, parameters)
    semantic = tool["semantics"]
    record_id = parameters[semantic["id_parameter"]]
    answer = candidate.response[semantic["response_key"]]
    name = inventory.device_names[tool["target"]]
    prop = semantic["property"]
    instruction = f"Report record {json_value(record_id)} from {prop} on {name}."
    atom = {"id": "q1", "kind": "query", "depends_on": [], "spec": {
        "target_kind": "object", "target_id": tool["target"], "target_name": name,
        "property": prop, "record_id": record_id, "query_mode": "collection_record", "role": "answer",
    }}
    sampling = {**deepcopy(sampling), "memory_write_method": "none", "query_operation": {
        "target_id": tool["target"], "function": tool["function"], "parameters": parameters,
    }}
    seed = build_task_seed("query", "property.device", [atom], sampling,
        public_anchors=[name, prop, str(record_id)], private_identifiers=[tool["target"]],
        answer_plans=[{"atom_ids": ["q1"], "operation": "identity",
                       "source_paths": [f"object.{tool['target']}.{prop}.{record_id}"], "result": deepcopy(answer)}])
    target = empty_target()
    target["expected_answers"] = [{"value": deepcopy(answer), "match": "exact"}]
    return TaskArtifacts(seed, instruction, target,
        build_reference_plan(task_id, [*candidate.commands, submit_answer(answer)]), None)


def _property_groups(
    inventory: TaskInventory,
    *,
    numeric: bool = False,
) -> list[list[PropertyValue]]:
    """Return the property groups."""
    groups: dict[tuple[str, str, str | None], list[PropertyValue]] = defaultdict(list)
    for item in inventory.properties:
        if not inventory.query_available(item):
            continue
        if numeric and (
            not isinstance(item.value, (int, float)) or isinstance(item.value, bool)
        ):
            continue
        class_key = item.class_id if item.target_kind == "object" else None
        groups[(item.target_kind, item.property, class_key)].append(item)
    return [
        sorted(group, key=lambda item: natural_key(item.target_id))
        for group in groups.values()
        if len(group) >= 2
    ]


def _memory_content(
    user_name: str | None,
    subject: str,
    prop: str,
    value: Any,
) -> str:
    """Return the memory content."""
    owner = f" of {user_name}" if user_name is not None else ""
    return f"The saved preference{owner} for {subject}'s {prop} is {json_value(value)}."


def _previous_memory_value(value: Any) -> Any:
    """Return the previous memory value."""
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, float):
        return round(value + 1, 3)
    if isinstance(value, str):
        return f"previous {value}"
    return None


def _query_memory_reference_plan(
    task_id: str,
    *,
    query_commands: Iterable[dict[str, Any]],
    answer: Any,
    write_command: dict[str, Any],
    read_before_update: bool,
) -> dict[str, Any]:
    """Return the query memory reference plan."""
    queries = deduplicate(query_commands)
    device_ids = sorted(
        {
            item["target"]
            for item in queries
            if item["target"] not in {"session", "memory"}
        },
        key=natural_key,
    )
    preparation = [
        *([read_memory()] if read_before_update else []),
        *[
            command("session", "get_device_tools", device_id=device_id)
            for device_id in device_ids
        ],
    ]
    turns = [
        [*queries, submit_answer(answer)],
        [deepcopy(write_command), finish()],
    ]
    if preparation:
        turns.insert(0, preparation)
    return {"task_id": task_id, "turns": turns}


def build_property_query_task(
    inventory: TaskInventory,
    task_id: str,
    subtype: str,
    sampling: dict[str, Any],
    rng: random.Random,
) -> TaskArtifacts:
    """Return the query property task."""
    target_kind = "object" if subtype == "property.device" else "space"
    shared = deepcopy(sampling.pop("_shared_query_property", None))
    if shared is None:
        candidates = list(inventory.property_values(target_kind))
        candidates = [item for item in candidates if inventory.query_available(item)]
        if not candidates:
            raise TaskSeedError(f"no queryable {target_kind} property")
        item = rng.choice(candidates)
        query_commands = [item.query_command]
    else:
        indexed = {
            (candidate.target_id, candidate.property): candidate
            for candidate in inventory.property_values(target_kind)
        }
        candidates = [
            indexed[(target_id, shared["property"])]
            for target_id in shared["candidate_ids"]
        ]
        item = indexed[(shared["selected_id"], shared["property"])]
        query_commands = deduplicate(
            candidate.query_command for candidate in candidates
        )
    sampling["target_selection"] = {
        "method": "random",
        "candidate_ids": sorted(
            {candidate.target_id for candidate in candidates}, key=natural_key
        ),
        "selected_ids": [item.target_id],
        "selected_ids_natural_sorted": True,
    }
    sampling["property_target_value"] = {"method": None, "records": []}
    sampling["post_control_query"] = {"method": "none", "answer_source": None}
    atom = query_atom("q1", item)
    atoms = [atom]
    target = empty_target()
    target["expected_answers"] = [{"value": deepcopy(item.value), "match": "exact"}]
    phrase = "device" if target_kind == "object" else "space"
    instruction = instruction_templates(
        [
            f"Tell me the current {item.property} of the {phrase} named {item.target_name}.",
            f"What is the current {item.property} for {item.target_name}?",
            f"Check {item.target_name} and report its current {item.property}.",
            f"I want to know the {item.property} status for {item.target_name}?",
            f"Let me know the current value of {item.property} for {item.target_name}.",
        ]
    )
    memory: dict[str, Any] | None = None
    write_method = sampling.get("memory_write_method", "none")
    if write_method not in {"none", "create", "update"}:
        raise TaskSeedError(f"unknown memory write method {write_method}")
    reference_plan = build_reference_plan(
        task_id, [*query_commands, submit_answer(item.value)]
    )
    private_identifiers = {item.target_id}
    if write_method != "none":
        user_id, user_name = memory_user(inventory, sampling, rng)
        expected_fact = {
            "subject": item.target_name,
            "property": item.property,
            "value": deepcopy(item.value),
        }
        mutation = {
            "operation": write_method,
            "source": {
                "scope": item.target_kind,
                "target_id": item.target_id,
                "property": item.property,
            },
            "fact": deepcopy(expected_fact),
        }
        if user_id is not None:
            mutation["user_id"] = user_id
        content = _memory_content(
            user_name, item.target_name, item.property, item.value
        )
        owner = f" for {user_name}" if user_name else ""
        if write_method == "create":
            parameters = {"content": content}
            if user_id is not None:
                parameters["user_id"] = user_id
            write_command = command("memory", "create", **parameters)
            suffixes = (
                f"Remember this preference{owner}.",
                f"Save this preference{owner}.",
            )
        else:
            old_value = _previous_memory_value(item.value)
            old_id = memory_identifier(
                task_id, "query-memory-update", item.target_id, item.property
            )
            old_record = {
                "memory_id": old_id,
                "content": _memory_content(
                    user_name, item.target_name, item.property, old_value
                ),
            }
            if user_id is not None:
                old_record["user_id"] = user_id
            memory = {
                "scope_id": memory_identifier(task_id, "scope"),
                "records": [old_record],
            }
            target["required_memory_ids"] = [old_id]
            mutation["memory_id"] = old_id
            private_identifiers.add(old_id)
            write_command = command(
                "memory",
                "update",
                memory_id=old_id,
                content=content,
            )
            suffixes = (
                f"Update the saved preference{owner} to this value.",
                f"Replace the saved preference{owner} with this value.",
            )
        target["expected_memory_mutations"] = [mutation]
        atoms.append(
            {
                "id": "m1",
                "kind": "memory",
                "depends_on": ["q1"],
                "spec": deepcopy(mutation),
            }
        )
        instruction = instruction_templates(
            f"{template.rstrip('.')}. {suffix}"
            for template in instruction
            for suffix in suffixes
        )
        sampling["memory_write"] = {
            "method": write_method,
            "source_atom_id": "q1",
            "source_path": (
                f"{item.target_kind}.{item.target_id}.{item.property}"
            ),
        }
        reference_plan = _query_memory_reference_plan(
            task_id,
            query_commands=query_commands,
            answer=item.value,
            write_command=write_command,
            read_before_update=write_method == "update",
        )
    else:
        sampling["memory_write"] = {
            "method": "none",
            "source_atom_id": None,
            "source_path": None,
        }

    seed = build_task_seed(
        "query",
        subtype,
        atoms,
        sampling,
        public_anchors=(item.target_name, item.property),
        private_identifiers=private_identifiers,
        answer_plans=[
            {
                "atom_ids": ["q1"],
                "operation": "identity",
                "source_paths": [
                    f"{item.target_kind}.{item.target_id}.{item.property}"
                ],
                "result": deepcopy(item.value),
            }
        ],
    )
    return TaskArtifacts(
        seed=seed,
        instruction_template=instruction,
        target=target,
        reference_plan=reference_plan,
        memory=memory,
    )


def build_space_query_task(
    inventory: TaskInventory,
    task_id: str,
    subtype: str,
    sampling: dict[str, Any],
    rng: random.Random,
) -> TaskArtifacts:
    """Return a person-location or occupied-room Query task."""
    if sampling.get("memory_write_method", "none") != "none":
        raise TaskSeedError("space Queries do not write memory")
    spaces = inventory.initial["spaces"]
    if subtype == "space.person_location":
        if not inventory.people:
            raise TaskSeedError("the World has no people")
        person_id = rng.choice(sorted(inventory.people, key=natural_key))
        person_name = inventory.person_name(person_id)
        space_id = inventory.person_space(person_id)
        result: Any = space_id
        queried_spaces = sorted(spaces, key=natural_key)
        instruction = instruction_templates(
            (
                f"Which room is {person_name} currently in?",
                f"Find {person_name} and tell me the room they are in.",
                f"Report {person_name}'s current room.",
            )
        )
        public_anchors = [person_name]
        operation = "person_location"
    elif subtype == "space.occupants":
        occupied = [
            space_id
            for space_id in sorted(spaces, key=natural_key)
            if inventory.space_occupants(space_id)
        ]
        if not occupied:
            raise TaskSeedError("the World has no occupied room")
        space_id = rng.choice(occupied)
        space_name = inventory.space_names[space_id]
        result = list(inventory.space_occupants(space_id))
        queried_spaces = [space_id]
        instruction = instruction_templates(
            (
                f"Who is currently in {space_name}?",
                f"List everyone currently in {space_name}.",
                f"Check {space_name} and report its occupants.",
            )
        )
        public_anchors = [space_name]
        operation = "occupants_natural_sort"
    else:
        raise TaskSeedError(f"unknown space Query subtype {subtype}")

    commands = [
        command("session", "get_spaces"),
        *(
            command("session", "get_space_state", space_id=space_id)
            for space_id in queried_spaces
        ),
    ]
    atom = {
        "id": "q1",
        "kind": "query",
        "depends_on": [],
        "spec": {
            "query_mode": subtype.rsplit(".", 1)[-1],
            "role": "answer",
            "source_space_ids": queried_spaces,
        },
    }
    target = empty_target()
    target["expected_answers"] = [{"value": deepcopy(result), "match": "exact"}]
    sampling["target_selection"] = {
        "method": operation,
        "candidate_ids": queried_spaces,
        "selected_ids": [space_id],
        "selected_ids_natural_sorted": True,
    }
    sampling["property_target_value"] = {"method": None, "records": []}
    sampling["post_control_query"] = {"method": "none", "answer_source": None}
    sampling["memory_write"] = {
        "method": "none",
        "source_atom_id": None,
        "source_path": None,
    }
    seed = build_task_seed(
        "query",
        subtype,
        [atom],
        sampling,
        public_anchors=public_anchors,
        private_identifiers=queried_spaces,
        answer_plans=[
            {
                "atom_ids": ["q1"],
                "operation": operation,
                "source_paths": [
                    f"space.{item}.metadata.occupants" for item in queried_spaces
                ],
                "result": deepcopy(result),
            }
        ],
    )
    return TaskArtifacts(
        seed=seed,
        instruction_template=instruction,
        target=target,
        reference_plan=build_reference_plan(
            task_id, [*commands, submit_answer(result)]
        ),
    )


def build_target_query_task(
    inventory: TaskInventory,
    task_id: str,
    subtype: str,
    sampling: dict[str, Any],
    structure: dict[str, Any],
    rng: random.Random,
) -> TaskArtifacts:
    """Return the target query task."""
    if sampling.get("memory_write_method", "none") != "none":
        raise TaskSeedError(
            "memory writes are limited to query.property.device/space"
        )
    shared = deepcopy(sampling.pop("_shared_query", None))
    if shared is not None:
        wanted = list(shared["candidate_ids"])
        indexed = {
            (item.target_kind, item.target_id, item.property): item
            for item in inventory.properties
        }
        candidates = [
            indexed[(shared["target_kind"], target_id, shared["property"])]
            for target_id in wanted
        ]
    else:
        groups = _property_groups(inventory, numeric=True)
        required = 2
        groups = [group for group in groups if len(group) >= required
                  and space_baselines(inventory, group[0].property)]
        if not groups:
            raise TaskSeedError(f"no compatible group for query.{subtype}")
        group = rng.choice(groups)
        count = sample_bounded_count(
            len(group),
            structure["query_candidate_count"],
            floor=required,
            rng=rng,
        )
        candidates = rng.sample(group, count)
    candidates.sort(key=lambda item: natural_key(item.target_id))
    baselines = space_baselines(inventory, candidates[0].property)
    if not baselines:
        raise TaskSeedError(
            f"query.{subtype} has no same-property Space baseline"
        )
    names = [item.target_name for item in candidates]
    scopes = [", ".join(names)]
    collective_scope = collective_target_description(
        inventory,
        target_kind=candidates[0].target_kind,
        selected_ids=(item.target_id for item in candidates),
    )
    if collective_scope is not None:
        scopes.append(collective_scope)
    scopes = instruction_templates(scopes)
    baseline: PropertyValue | None = None

    if subtype in {"target.quantity", "target.enum"}:
        operator = shared["operator"] if shared is not None else rng.choice(
            tuple(_COMPARISON_PHRASES)
        )
        baseline_id = shared.get("baseline_space_id") if shared is not None else None
        baseline = (
            rng.choice(baselines)
            if baseline_id is None
            else next(
                (item for item in baselines if item.target_id == baseline_id),
                None,
            )
        )
        if baseline is None:
            raise TaskSeedError("shared Query baseline is unavailable")
        selected = comparison_matches(candidates, operator, baseline.value)
        selected = sorted(selected, key=lambda item: natural_key(item.target_id))
        result: Any = len(selected) if subtype == "target.quantity" else [
            item.target_id for item in selected
        ]
        condition = (
            f"{_COMPARISON_PHRASES[operator]} the current "
            f"{candidates[0].property} in {baseline.target_name}"
        )
        if subtype == "target.quantity":
            instruction = instruction_templates(
                sentence
                for scope in scopes
                for sentence in (
                    f"Among {scope}, how many have {candidates[0].property} {condition}?",
                    f"Read {baseline.target_name}'s current {candidates[0].property}, then count the targets in {scope} whose {candidates[0].property} is {_COMPARISON_PHRASES[operator]} it.",
                )
            )
        else:
            instruction = instruction_templates(
                sentence
                for scope in scopes
                for sentence in (
                    f"Among {scope}, list every target whose {candidates[0].property} is {condition}.",
                    f"Read {baseline.target_name}'s current {candidates[0].property}, then return all targets in {scope} whose {candidates[0].property} is {_COMPARISON_PHRASES[operator]} it.",
                )
            )
        operation = (
            "count_by_space_baseline"
            if subtype == "target.quantity"
            else "filter_by_space_baseline_and_natural_sort"
        )
        selection = {
            "method": "space_baseline_condition",
            "candidate_ids": [item.target_id for item in candidates],
            "selected_ids": [item.target_id for item in selected],
            "property": candidates[0].property,
            "operator": operator,
            "baseline_space_id": baseline.target_id,
        }
        public_anchors = [*names, candidates[0].property, baseline.target_name]
    else:
        mode = shared["rank_mode"] if shared is not None else rng.choice(
            ("highest", "lowest", "nearest")
        )
        if subtype.endswith("topk"):
            if shared is not None:
                k = int(shared["k"])
            else:
                topk_bounds = structure["query_topk_count"]
                maximum = min(len(candidates), int(topk_bounds["max"]))
                minimum = max(2, int(topk_bounds["min"]))
                if maximum < minimum:
                    raise TaskSeedError("top-k query has too few candidates")
                ks = list(range(minimum, maximum + 1))
                weights = [2 ** (-k) for k in ks]
                k = rng.choices(ks, weights=weights, k=1)[0]
        else:
            k = 1
        if mode == "nearest":
            baseline_id = shared.get("baseline_space_id") if shared is not None else None
            baseline = (
                rng.choice(baselines)
                if baseline_id is None
                else next(
                    (item for item in baselines if item.target_id == baseline_id),
                    None,
                )
            )
            if baseline is None:
                raise TaskSeedError("nearest Query baseline is unavailable")
        selected = rank_matches(
            candidates,
            mode=mode,
            k=k,
            baseline=None if baseline is None else baseline.value,
        )
        result = [item.target_id for item in selected]
        rank = (
            f"nearest to the current {candidates[0].property} in {baseline.target_name}"
            if mode == "nearest" and baseline is not None
            else mode
        )
        count = "top one position" if k == 1 else f"top {k} positions"
        instruction = instruction_templates(
            sentence
            for scope in scopes
            for sentence in (
                f"Compare current {candidates[0].property} among {scope}; list every target in the {count} for {rank}.",
                f"Using current {candidates[0].property}, return the targets from {scope} in the {count} ranked {rank}.",
            )
        )
        operation = f"{mode}_{'top1' if k == 1 else 'topk'}_with_ties"
        selection = {
            "method": subtype,
            "candidate_ids": [item.target_id for item in candidates],
            "selected_ids": [item.target_id for item in selected],
            "property": candidates[0].property,
            "k": k,
            "rank_mode": mode,
        }
        public_anchors = [*names, candidates[0].property]
        if baseline is not None:
            selection["baseline_space_id"] = baseline.target_id
            public_anchors.append(baseline.target_name)
        if k > 1:
            public_anchors.append(str(k))

    atoms = [
        query_atom(f"q{index}", item)
        for index, item in enumerate(candidates, 1)
    ]
    commands = deduplicate(item.query_command for item in candidates)
    private_identifiers = [item.target_id for item in candidates]
    if baseline is not None:
        atoms.append(
            query_atom(
                f"q{len(atoms) + 1}",
                baseline,
                role="comparison_baseline",
            )
        )
        commands = deduplicate([*commands, baseline.query_command])
        private_identifiers.append(baseline.target_id)
    answer_depends = [atom["id"] for atom in atoms]
    atoms.append(
        {
            "id": f"q{len(atoms) + 1}",
            "kind": "query",
            "depends_on": answer_depends,
            "spec": {
                "query_mode": subtype.rsplit(".", 1)[-1],
                "role": "answer",
            },
        }
    )
    target = empty_target()
    target["expected_answers"] = [{"value": deepcopy(result), "match": "exact"}]
    commands.extend([submit_answer(result)])
    source_items = [*candidates, *([baseline] if baseline is not None else [])]
    answer_plan = {
        "atom_ids": answer_depends,
        "operation": operation,
        "source_paths": [
            f"{item.target_kind}.{item.target_id}.{item.property}"
            for item in source_items
        ],
        "result": deepcopy(result),
    }
    sampling["target_selection"] = deepcopy(selection)
    sampling["property_target_value"] = {"method": None, "records": []}
    sampling["post_control_query"] = {"method": "none", "answer_source": None}
    seed = build_task_seed(
        "query",
        subtype,
        atoms,
        sampling,
        public_anchors=public_anchors,
        private_identifiers=private_identifiers,
        answer_plans=[answer_plan],
        selection_plans=[selection],
    )
    return TaskArtifacts(
        seed=seed,
        instruction_template=instruction,
        target=target,
        reference_plan=build_reference_plan(task_id, commands),
    )


def build_query_variants(
    world: World,
    inventory: TaskInventory,
    *,
    task_id: str,
    constraints: dict[str, Any],
    rng: random.Random,
) -> tuple[TaskArtifacts, ...]:
    """Return the shared query variants."""
    sampling = sampling_options(constraints)
    structure = deepcopy(DEFAULT_STRUCTURE)
    structure.update(
        deepcopy(constraints.get("requirements", {}).get("structure", {}))
    )
    sampled_task_type = sampling["task_type"]
    sampled_subtype = sampled_task_type.split(".", 1)[1]
    groups = [
        group
        for group in _property_groups(inventory, numeric=True)
        if len(group) >= 2 and space_baselines(inventory, group[0].property)
    ]
    if sampled_subtype == "property.device":
        groups = [group for group in groups if group[0].target_kind == "object"]
    elif sampled_subtype == "property.space":
        groups = [group for group in groups if group[0].target_kind == "space"]
    if not groups:
        raise TaskSeedError(
            "no numeric property group with a same-property Space baseline"
        )
    group = rng.choice(groups)
    floor = 2
    candidate_bounds = deepcopy(structure["query_candidate_count"])
    candidate_bounds["min"] = min(int(candidate_bounds["min"]), len(group))
    count = sample_bounded_count(
        len(group),
        candidate_bounds,
        floor=floor,
        rng=rng,
    )
    candidates = sorted(
        rng.sample(group, count), key=lambda item: natural_key(item.target_id)
    )
    commands = deduplicate(item.query_command for item in candidates)
    preview = inventory.preview_from_initial(commands)
    if any(result.code != "[PASS]" for result in preview.results):
        raise TaskSeedError("shared Query getter validation failed")
    baselines = space_baselines(inventory, candidates[0].property)
    comparisons = [
        (baseline, operator)
        for baseline in baselines
        for operator in _COMPARISON_PHRASES
    ]
    rng.shuffle(comparisons)
    action_group_id = f"{task_id}_query_actions"
    shared = {
        "candidate_ids": [item.target_id for item in candidates],
        "target_kind": candidates[0].target_kind,
        "property": candidates[0].property,
    }
    property_subtype = (
        "property.device"
        if candidates[0].target_kind == "object"
        else "property.space"
    )
    variants: list[tuple[str, str, dict[str, Any]]] = [
        (
            property_subtype.replace(".", "_"),
            property_subtype,
            {"selected_id": rng.choice(candidates).target_id},
        ),
    ]
    for comparison_index, (baseline, operator) in enumerate(
        comparisons[:3], start=1
    ):
        overrides = {
            "operator": operator,
            "baseline_space_id": baseline.target_id,
        }
        variants.extend(
            (
                (
                    f"condition_{comparison_index:02d}_count",
                    "target.quantity",
                    overrides,
                ),
                (
                    f"condition_{comparison_index:02d}_list",
                    "target.enum",
                    overrides,
                ),
            )
        )

    variants.extend(
        (
            ("highest", "target.comparison.top1", {"rank_mode": "highest"}),
            ("lowest", "target.comparison.top1", {"rank_mode": "lowest"}),
        )
    )
    nearest_baseline = rng.choice(baselines)
    variants.append(
        (
            "nearest",
            "target.comparison.top1",
            {
                "rank_mode": "nearest",
                "baseline_space_id": nearest_baseline.target_id,
            },
        )
    )
    topk_bounds = structure["query_topk_count"]
    minimum = max(2, int(topk_bounds["min"]))
    maximum = min(len(candidates), int(topk_bounds["max"]))
    if maximum >= minimum:
        ks = list(range(minimum, maximum + 1))
        weights = [2 ** (-value) for value in ks]
        k = rng.choices(ks, weights=weights, k=1)[0]
        variants.extend(
            (
                (
                    "topk_highest",
                    "target.comparison.topk",
                    {"rank_mode": "highest", "k": k},
                ),
                (
                    "topk_lowest",
                    "target.comparison.topk",
                    {"rank_mode": "lowest", "k": k},
                ),
                (
                    "topk_nearest",
                    "target.comparison.topk",
                    {
                        "rank_mode": "nearest",
                        "baseline_space_id": nearest_baseline.target_id,
                        "k": k,
                    },
                ),
            )
        )

    result: list[TaskArtifacts] = []
    for index, (variant_key, subtype, overrides) in enumerate(variants, start=1):
        variant_sampling = deepcopy(sampling)
        variant_sampling["task_type"] = f"query.{subtype}"
        variant_sampling["sampled_task_type"] = sampled_task_type
        if not subtype.startswith("property."):
            variant_sampling["memory_write_method"] = "none"
        if subtype.startswith("property."):
            variant_sampling["_shared_query_property"] = {
                "candidate_ids": deepcopy(shared["candidate_ids"]),
                "property": shared["property"],
                "selected_id": overrides["selected_id"],
            }
            artifacts = build_property_query_task(
                inventory,
                f"{task_id}_q{index:02d}",
                subtype,
                variant_sampling,
                random.Random(f"{task_id}:{variant_key}"),
            )
        else:
            variant_sampling["_shared_query"] = {
                **deepcopy(shared),
                **overrides,
            }
            artifacts = build_target_query_task(
                inventory,
                f"{task_id}_q{index:02d}",
                subtype,
                variant_sampling,
                structure,
                random.Random(f"{task_id}:{variant_key}"),
            )
        artifacts = mark_action_reuse(
            artifacts,
            task_id=f"{task_id}_q{index:02d}",
            variant_key=variant_key,
            action_group_id=action_group_id,
            strategy="shared_query_getters",
        )
        validate_task_seed(artifacts.seed)
        world.contract.validate_target(
            artifacts.target,
            world.get_world_spec(),
            world.get_initial_state(),
        )
        if artifacts.memory is not None:
            world.contract.validate_memory(artifacts.memory)
        world.contract.validate_schema(
            artifacts.reference_plan,
            "urn:dcb:v2:schema:reference-plan",
        )
        result.append(artifacts)
    return tuple(result)


def build_query_task(
    inventory: TaskInventory,
    task_id: str,
    subtype: str,
    sampling: dict[str, Any],
    structure: dict[str, Any],
    rng: random.Random,
) -> TaskArtifacts:
    """Build the selected property, space, or target Query."""
    if subtype.startswith("property."):
        return build_property_query_task(inventory, task_id, subtype, sampling, rng)
    if subtype.startswith("space."):
        return build_space_query_task(inventory, task_id, subtype, sampling, rng)
    return build_target_query_task(inventory, task_id, subtype, sampling, structure, rng)
