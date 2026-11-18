"""Select and describe targets using the current World inventory."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import random
import re
from typing import Any, Iterable

from .task_common import deduplicate, instruction_templates, query_atom, TaskSeedError
from .task_inventory import command, natural_key, PropertyValue, TaskInventory


@dataclass(frozen=True)
class TargetSelection:
    method: str
    candidate_ids: tuple[str, ...]
    selected_ids: tuple[str, ...]
    atoms: tuple[dict[str, Any], ...]
    commands: tuple[dict[str, Any], ...]
    description: str
    public_anchors: tuple[str, ...]
    details: dict[str, Any]


def target_category_label(value: str) -> str:
    """Return the target category label."""
    tail = value.rsplit(".", 1)[-1].replace("_", " ")
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", tail).casefold()


def collective_target_description(
    inventory: TaskInventory,
    *,
    target_kind: str,
    selected_ids: Iterable[str],
    allow_except: bool = False,
) -> str | None:
    """Return the collective target description."""
    selected = set(selected_ids)
    if not selected:
        return None
    scope = "objects" if target_kind == "object" else "spaces"
    category_key = "class" if target_kind == "object" else "type"
    records = inventory.initial[scope]
    categories = {str(records[target_id][category_key]) for target_id in selected}
    if len(categories) != 1:
        return None
    category = next(iter(categories))
    category_ids = {
        target_id
        for target_id, record in records.items()
        if str(record[category_key]) == category
    }
    excluded = sorted(category_ids - selected, key=natural_key)
    label = target_category_label(category)
    noun = "devices" if target_kind == "object" else "spaces"
    if not excluded and selected == category_ids:
        return f"all {label} {noun}"
    if allow_except and selected | set(excluded) == category_ids:
        excluded_names = ", ".join(
            entity_name(inventory, target_kind, target_id)
            for target_id in excluded
        )
        return f"all {label} {noun} except {excluded_names}"
    return None


def selection_description_variants(
    inventory: TaskInventory,
    selection: TargetSelection,
    *,
    target_kind: str,
) -> list[str]:
    """Return the selection description variants."""
    descriptions = [selection.description]
    if selection.method in {"random", "all", "except"}:
        collective = collective_target_description(
            inventory,
            target_kind=target_kind,
            selected_ids=selection.selected_ids,
            allow_except=True,
        )
        if collective is not None:
            descriptions.append(collective)
    return instruction_templates(descriptions)


_COMPARISON_PHRASES = {
    "eq": "equal to",
    "ne": "not equal to",
    "gt": "greater than",
    "gte": "not less than",
    "lt": "less than",
    "lte": "not greater than",
}


def space_baselines(
    inventory: TaskInventory,
    prop: str,
) -> list[PropertyValue]:
    """Return queryable numeric Space baselines for one property."""
    return [
        item
        for item in inventory.property_values("space")
        if item.property == prop
        and isinstance(item.value, (int, float))
        and not isinstance(item.value, bool)
        and inventory.query_available(item)
    ]


def comparison_matches(
    group: Iterable[PropertyValue],
    operator: str,
    baseline: int | float,
) -> list[PropertyValue]:
    """Return candidates matching one comparison."""
    predicates = {
        "eq": lambda value: value == baseline,
        "ne": lambda value: value != baseline,
        "gt": lambda value: value > baseline,
        "gte": lambda value: value >= baseline,
        "lt": lambda value: value < baseline,
        "lte": lambda value: value <= baseline,
    }
    return [item for item in group if predicates[operator](item.value)]


def rank_matches(
    group: Iterable[PropertyValue],
    *,
    mode: str,
    k: int,
    baseline: int | float | None = None,
) -> list[PropertyValue]:
    """Return rank-ordered matches, breaking ties by natural ID order."""
    if mode == "nearest" and baseline is None:
        raise ValueError("nearest ranking requires a baseline")

    def score(item: PropertyValue) -> float:
        value = float(item.value)
        if mode == "highest":
            return -value
        if mode == "lowest":
            return value
        return abs(value - float(baseline))

    ordered = sorted(group, key=lambda item: (score(item), natural_key(item.target_id)))
    boundary = score(ordered[min(k, len(ordered)) - 1])
    return [item for item in ordered if score(item) <= boundary]


def class_label(class_id: str) -> str:
    """Return a readable class name."""
    name = class_id.rsplit(".", 1)[-1]
    return re.sub(r"(?<!^)(?=[A-Z])", " ", name)


def entity_name(inventory: TaskInventory, target_kind: str, target_id: str) -> str:
    """Return the entity name."""
    return (
        inventory.device_names[target_id]
        if target_kind == "object"
        else inventory.space_names[target_id]
    )


def query_values_by_target(
    inventory: TaskInventory,
    target_kind: str,
    target_ids: Iterable[str],
) -> list[list[PropertyValue]]:
    """Return the query values by target."""
    required = set(target_ids)
    by_property: dict[str, dict[str, PropertyValue]] = defaultdict(dict)
    for item in inventory.property_values(target_kind):
        if item.target_id in required and inventory.query_available(item):
            by_property[item.property][item.target_id] = item
    return [
        sorted(values.values(), key=lambda item: natural_key(item.target_id))
        for values in by_property.values()
        if len(values) >= 2
    ]


def target_selection(
    inventory: TaskInventory,
    *,
    target_kind: str,
    candidate_ids: Iterable[str],
    method: str,
    requested_count: int,
    topk_bounds: dict[str, Any],
    rng: random.Random,
    selected_count_bounds: dict[str, Any] | None = None,
) -> TargetSelection:
    """Return the target selection."""
    candidates = sorted(set(candidate_ids), key=natural_key)
    if not candidates:
        raise TaskSeedError("target selection has no candidates")
    requested_count = min(requested_count, len(candidates))
    names = {target_id: entity_name(inventory, target_kind, target_id) for target_id in candidates}
    atoms: list[dict[str, Any]] = []
    commands: list[dict[str, Any]] = []
    anchors: list[str] = []
    details: dict[str, Any] = {"method": method}

    if method == "person_location":
        if not inventory.people:
            raise TaskSeedError("person-location selection requires people")
        if target_kind == "space":
            viable = [
                person_id
                for person_id in inventory.people
                if inventory.person_space(person_id) in candidates
            ]
            if not viable:
                raise TaskSeedError("no person occupies a candidate Space")
            person_id = rng.choice(sorted(viable, key=natural_key))
            space_id = inventory.person_space(person_id)
            selected = [space_id]
            description = f"{inventory.person_name(person_id)}'s current room"
        else:
            viable_groups: list[tuple[str, str, list[str]]] = []
            for person_id in inventory.people:
                space_id = inventory.person_space(person_id)
                by_class: dict[str, list[str]] = defaultdict(list)
                for target_id in candidates:
                    item = inventory.initial["objects"][target_id]
                    if item["space_id"] == space_id:
                        by_class[item["class"]].append(target_id)
                viable_groups.extend(
                    (person_id, class_id, target_ids)
                    for class_id, target_ids in by_class.items()
                    if len(target_ids) == requested_count
                )
            if not viable_groups:
                raise TaskSeedError(
                    "no unambiguous device group in a person's room"
                )
            person_id, class_id, selected = rng.choice(viable_groups)
            selected = sorted(selected, key=natural_key)
            label = class_label(class_id).casefold()
            description = (
                f"the {label} device in {inventory.person_name(person_id)}'s current room"
            )
            space_id = inventory.person_space(person_id)
        queried_spaces = sorted(inventory.initial["spaces"], key=natural_key)
        commands = [
            command("session", "get_spaces"),
            *(
                command("session", "get_space_state", space_id=item)
                for item in queried_spaces
            ),
        ]
        atoms = [
            {
                "id": "s1",
                "kind": "query",
                "depends_on": [],
                "spec": {
                    "query_mode": "person_location",
                    "role": "target_selection",
                    "person_id": person_id,
                },
            }
        ]
        anchors.append(inventory.person_name(person_id))
        details.update({"person_id": person_id, "space_id": space_id})
    elif method in {"occupied_spaces", "unoccupied_spaces"}:
        wanted_occupied = method == "occupied_spaces"
        space_id_by_target = {
            target_id: (
                inventory.initial["objects"][target_id]["space_id"]
                if target_kind == "object"
                else target_id
            )
            for target_id in candidates
        }
        occupied_by_space = {
            space_id: bool(inventory.space_occupants(space_id))
            for space_id in set(space_id_by_target.values())
        }
        selected = [
            target_id
            for target_id in candidates
            if occupied_by_space[space_id_by_target[target_id]] is wanted_occupied
        ]
        unselected = [
            target_id for target_id in candidates if target_id not in selected
        ]
        if not selected or not unselected:
            raise TaskSeedError(
                "occupancy selection requires selected and unselected candidates"
            )
        scoped = False
        if (
            selected_count_bounds is not None
            and len(selected) > int(selected_count_bounds["max"])
        ):
            count = min(requested_count, int(selected_count_bounds["max"]))
            if count < int(selected_count_bounds["min"]):
                raise TaskSeedError(
                    "occupancy selection has too few candidates within bounds"
                )
            selected = sorted(rng.sample(selected, count), key=natural_key)
            unselected = [rng.choice(unselected)]
            candidates = sorted([*selected, *unselected], key=natural_key)
            scoped = True
        label = "occupied" if wanted_occupied else "unoccupied"
        if target_kind == "object":
            selected_class_label = class_label(
                inventory.initial["objects"][selected[0]]["class"]
            ).casefold()
            description = f"all {selected_class_label} devices in currently {label} rooms"
        else:
            description = f"all currently {label} rooms"
        if scoped:
            description = (
                f"among {', '.join(names[target_id] for target_id in candidates)}, "
                f"select {description}"
            )
        candidate_spaces = {
            space_id_by_target[target_id] for target_id in candidates
        }
        queried_spaces = sorted(candidate_spaces, key=natural_key)
        commands = [
            command("session", "get_spaces"),
            *(
                command("session", "get_space_state", space_id=item)
                for item in queried_spaces
            ),
        ]
        atoms = [
            {
                "id": "s1",
                "kind": "query",
                "depends_on": [],
                "spec": {
                    "query_mode": method,
                    "role": "target_selection",
                },
            }
        ]
        anchors.append(label)
        if scoped:
            anchors.extend(names[target_id] for target_id in candidates)
        details["selected_space_ids"] = sorted(
            {
                inventory.initial["objects"][target_id]["space_id"]
                if target_kind == "object"
                else target_id
                for target_id in selected
            },
            key=natural_key,
        )
    elif method == "random":
        selected = sorted(rng.sample(candidates, requested_count), key=natural_key)
        description = ", ".join(names[target_id] for target_id in selected)
        anchors.extend(names[target_id] for target_id in selected)
    elif method == "all":
        selected = candidates
        selected_class_label = (
            inventory.initial["objects"][selected[0]]["class"].rsplit(".", 1)[-1]
            if target_kind == "object"
            else inventory.initial["spaces"][selected[0]]["type"].replace("_", " ")
        )
        description = f"all {selected_class_label} targets: " + ", ".join(
            names[target_id] for target_id in selected
        )
        anchors.extend(names[target_id] for target_id in selected)
    elif method == "except":
        if len(candidates) < 3:
            raise TaskSeedError("except selection needs at least three candidates")
        excluded = rng.choice(candidates)
        selected = [target_id for target_id in candidates if target_id != excluded]
        description = (
            f"all of {', '.join(names[item] for item in candidates)} except "
            f"{names[excluded]}"
        )
        anchors.extend(names[target_id] for target_id in candidates)
        details["excluded_id"] = excluded
    elif method == "within":
        if target_kind == "object":
            groups: dict[str, list[str]] = defaultdict(list)
            for target_id in candidates:
                groups[inventory.initial["objects"][target_id]["space_id"]].append(target_id)
            viable = [(space_id, ids) for space_id, ids in groups.items() if len(ids) >= 2]
            if not viable:
                container_id, selected = "home", candidates
                container_name = "this home"
            else:
                container_id, selected = rng.choice(viable)
                container_name = inventory.space_names[container_id]
        else:
            groups = defaultdict(list)
            for target_id in candidates:
                metadata = inventory.initial["spaces"][target_id].get("metadata", {})
                floor = metadata.get("floor")
                group = (
                    f"floor {floor}"
                    if floor is not None
                    else inventory.initial["spaces"][target_id]["type"].replace("_", " ")
                )
                groups[str(group)].append(target_id)
            viable = [(group, ids) for group, ids in groups.items() if len(ids) >= 2]
            if not viable:
                container_id, selected = "home", candidates
                container_name = "this home"
            else:
                container_id, selected = rng.choice(viable)
                container_name = str(container_id)
        selected = sorted(selected[:requested_count], key=natural_key)
        description = f"the targets within {container_name}: " + ", ".join(
            names[target_id] for target_id in selected
        )
        anchors.extend([container_name, *(names[target_id] for target_id in selected)])
        details["container"] = container_id
    elif method in {
        "query.target.enum",
        "query.target.comparison.top1",
        "query.target.comparison.topk",
    }:
        groups = query_values_by_target(inventory, target_kind, candidates)
        groups = [
            group
            for group in groups
            if all(
                isinstance(item.value, (int, float))
                and not isinstance(item.value, bool)
                for item in group
            )
            and space_baselines(inventory, group[0].property)
        ]
        if not groups:
            raise TaskSeedError(
                "query-derived selection has no numeric property with a Space baseline"
            )
        required_group_size = (
            max(2, int(topk_bounds["min"]))
            if method == "query.target.comparison.topk"
            else 2
        )
        groups = [group for group in groups if len(group) >= required_group_size]
        if not groups:
            raise TaskSeedError("query-derived selection has too few comparable targets")
        group = rng.choice(groups)
        if len(group) > 10:
            group = rng.sample(group, 10)
        group.sort(key=lambda item: natural_key(item.target_id))
        candidates = [item.target_id for item in group]
        atoms = [
            query_atom(f"s{index}", item, role="target_selection")
            for index, item in enumerate(group, 1)
        ]
        commands = deduplicate(item.query_command for item in group)
        group_names = [item.target_name for item in group]
        anchors.extend([*group_names, group[0].property])
        baselines = space_baselines(inventory, group[0].property)
        if method == "query.target.enum":
            options = [
                (baseline, operator, comparison_matches(group, operator, baseline.value))
                for baseline in baselines
                for operator in _COMPARISON_PHRASES
            ]
            rng.shuffle(options)
            viable = [
                option
                for option in options
                if option[2]
                and (
                    selected_count_bounds is None
                    or int(selected_count_bounds["min"])
                    <= len(option[2])
                    <= int(selected_count_bounds["max"])
                )
            ]
            if not viable:
                raise TaskSeedError("enum selection has no result within bounds")
            baseline, operator, picked = rng.choice(viable)
            selected = [item.target_id for item in picked]
            description = (
                f"among {', '.join(group_names)}, select those whose "
                f"{group[0].property} is {_COMPARISON_PHRASES[operator]} the "
                f"current {group[0].property} in {baseline.target_name}"
            )
            atoms.append(
                query_atom(
                    f"s{len(atoms) + 1}",
                    baseline,
                    role="comparison_baseline",
                )
            )
            commands = deduplicate([*commands, baseline.query_command])
            anchors.append(baseline.target_name)
            details.update(
                {
                    "property": group[0].property,
                    "operator": operator,
                    "baseline_space_id": baseline.target_id,
                }
            )
        else:
            if method.endswith("topk"):
                maximum = min(
                    len(group),
                    requested_count,
                    int(topk_bounds["max"]),
                )
                minimum = max(2, int(topk_bounds["min"]))
                if maximum < minimum:
                    raise TaskSeedError("top-k selection has insufficient candidates")
                ks = range(minimum, maximum + 1)
            else:
                ks = (1,)
            options: list[tuple[str, int, PropertyValue | None, list[PropertyValue]]] = []
            for k in ks:
                for mode in ("highest", "lowest"):
                    options.append(
                        (mode, k, None, rank_matches(group, mode=mode, k=k))
                    )
                options.extend(
                    (
                        "nearest",
                        k,
                        baseline,
                        rank_matches(
                            group,
                            mode="nearest",
                            k=k,
                            baseline=baseline.value,
                        ),
                    )
                    for baseline in baselines
                )
            rng.shuffle(options)
            viable_ranks = [
                option
                for option in options
                if (option[1] != 1 or len(option[3]) == 1)
                and (
                    selected_count_bounds is None
                    or int(selected_count_bounds["min"])
                    <= len(option[3])
                    <= int(selected_count_bounds["max"])
                )
            ]
            if not viable_ranks:
                raise TaskSeedError("rank selection has no result within bounds")
            mode, k, baseline, picked = rng.choice(viable_ranks)
            selected = [item.target_id for item in picked]
            rank = (
                f"nearest to {baseline.target_name}'s current {group[0].property}"
                if baseline is not None
                else mode
            )
            comparison = (
                f"the unique {rank} target"
                if k == 1
                else f"the top {k} {rank} positions"
            )
            description = (
                f"among {', '.join(group_names)}, select {comparison} by "
                f"current {group[0].property}"
            )
            if k > 1:
                anchors.append(str(k))
            details.update(
                {"property": group[0].property, "k": k, "rank_mode": mode}
            )
            if baseline is not None:
                atoms.append(
                    query_atom(
                        f"s{len(atoms) + 1}",
                        baseline,
                        role="comparison_baseline",
                    )
                )
                commands = deduplicate([*commands, baseline.query_command])
                anchors.append(baseline.target_name)
                details["baseline_space_id"] = baseline.target_id
    else:
        raise TaskSeedError(f"unknown target selection method {method}")

    selected = sorted(set(selected), key=natural_key)
    if not selected:
        raise TaskSeedError("target selection produced an empty result")
    if selected_count_bounds is not None and not (
        int(selected_count_bounds["min"])
        <= len(selected)
        <= int(selected_count_bounds["max"])
    ):
        raise TaskSeedError(
            "target selection count is outside the configured structure bounds"
        )
    details.update(
        {
            "candidate_ids": candidates,
            "selected_ids": selected,
            "selected_ids_natural_sorted": True,
        }
    )
    return TargetSelection(
        method=method,
        candidate_ids=tuple(candidates),
        selected_ids=tuple(selected),
        atoms=tuple(atoms),
        commands=tuple(commands),
        description=description,
        public_anchors=tuple(str(item) for item in anchors),
        details=details,
    )
