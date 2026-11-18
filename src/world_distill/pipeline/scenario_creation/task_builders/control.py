"""Control tasks and instruction variants over shared validated actions."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import random
from typing import Any, Iterable

from src.contracts import EnvironmentContractError, strict_equal
from src.runtime import World

from ..task_common import (
    build_reference_plan,
    build_task_seed,
    deduplicate,
    display_value,
    empty_target,
    instruction_templates,
    join_clauses,
    mark_action_reuse,
    memory_identifier,
    memory_user,
    memory_value,
    query_atom,
    read_memory,
    submit_answer,
    TaskArtifacts,
    TaskSeedError,
)
from ..task_inventory import (
    candidate_values,
    ControlCandidate,
    delta_values,
    InventoryError,
    json_value,
    natural_key,
    schema_accepts,
    Setter,
    TaskInventory,
)
from ..task_sampler import sample_bounded_count
from ..task_selection import (
    selection_description_variants,
    target_selection,
    TargetSelection,
)
from ..validator import validate_task_seed


def _choose_shared_controls(
    inventory: TaskInventory,
    setters: list[Setter],
    method: str,
    rng: random.Random,
    *,
    allow_power_off: bool,
) -> tuple[
    list[ControlCandidate],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """Choose one value recipe per property, shared across multiple targets."""
    by_property: dict[str, list[Setter]] = defaultdict(list)
    for setter in setters:
        by_property[setter.property].append(setter)
    controls: list[ControlCandidate] = []
    query_atoms: list[dict[str, Any]] = []
    query_commands: list[dict[str, Any]] = []
    recipes: list[dict[str, Any]] = []
    for property_index, (prop, group) in enumerate(sorted(by_property.items()), start=1):
        values_by_target: dict[str, Any] = {}
        operation: dict[str, Any]
        if method in {"random", "memory"}:
            maps = [
                {
                    json_value(value): value
                    for value in candidate_values(
                        prop, setter.parameter_schema, setter.initial_value
                    )
                    if not (prop == "power" and value is False and not allow_power_off)
                }
                for setter in group
            ]
            common = set(maps[0]).intersection(*(set(item) for item in maps[1:]))
            if not common:
                raise TaskSeedError(f"no shared realistic value for {prop}")
            key = rng.choice(sorted(common))
            for setter, mapping in zip(group, maps, strict=True):
                values_by_target[setter.target_id] = deepcopy(mapping[key])
            operation = {
                "kind": "memory" if method == "memory" else "set",
                "value": deepcopy(maps[0][key]),
            }
        elif method == "delta":
            maps = []
            for setter in group:
                mapping = {
                    (direction, str(amount)): (value, amount)
                    for value, direction, amount in delta_values(
                        prop, setter.parameter_schema, setter.initial_value
                    )
                }
                maps.append(mapping)
            common = set(maps[0]).intersection(*(set(item) for item in maps[1:]))
            if not common:
                raise TaskSeedError(f"no shared delta for {prop}")
            direction, amount_key = rng.choice(sorted(common))
            amount = maps[0][(direction, amount_key)][1]
            for setter, mapping in zip(group, maps, strict=True):
                values_by_target[setter.target_id] = deepcopy(
                    mapping[(direction, amount_key)][0]
                )
            operation = {"kind": "delta", "direction": direction, "amount": amount}
        elif method == "query.property.device":
            options = _compatible_device_value_recipes(
                inventory,
                group,
                allow_power_off=allow_power_off,
            )
            if not options:
                raise TaskSeedError(f"no query-derived device value for {prop}")
            operation_kind = rng.choice(
                sorted({option["kind"] for option in options})
            )
            option = rng.choice(
                [item for item in options if item["kind"] == operation_kind]
            )
            source = option["source"]
            selected_value = deepcopy(option["selected_value"])
            for setter in group:
                values_by_target[setter.target_id] = deepcopy(selected_value)
            atom_id = f"v{property_index}"
            query_atoms.append(query_atom(atom_id, source, role="target_value"))
            query_commands.append(source.query_command)
            operation = {
                "kind": operation_kind,
                "source_atom_id": atom_id,
                "source_target_id": source.target_id,
                "source_target_name": source.target_name,
                "source_property": source.property,
                "source_class_id": source.class_id,
                "source_class_priority": option["class_priority"],
                "value": deepcopy(source.value),
                "selected_value": deepcopy(selected_value),
            }
            if operation_kind == "query_offset":
                operation.update(
                    {
                        "direction": option["direction"],
                        "amount": option["amount"],
                        "offset": option["offset"],
                    }
                )
        else:
            raise TaskSeedError(f"unsupported Control value method {method}")
        for setter in group:
            try:
                control = inventory.make_control(
                    setter, values_by_target[setter.target_id]
                )
            except InventoryError as error:
                raise TaskSeedError(str(error)) from error
            controls.append(control)
        operation["property"] = prop
        operation["target_ids"] = [setter.target_id for setter in group]
        operation["initial_values"] = {
            setter.target_id: deepcopy(setter.initial_value) for setter in group
        }
        operation["requested_values"] = deepcopy(values_by_target)
        recipes.append(deepcopy(operation))
    return controls, query_atoms, deduplicate(query_commands), recipes


def _source_class_priority(
    inventory: TaskInventory,
    source_class_id: str,
    target_class_ids: set[str],
) -> int:
    """Prefer the same class, then a shared Domain base, then other classes."""
    if source_class_id in target_class_ids:
        return 0
    try:
        source_type = inventory.class_type(source_class_id)
        target_types = [
            inventory.class_type(class_id) for class_id in target_class_ids
        ]
    except (EnvironmentContractError, ImportError, KeyError, TypeError, ValueError):
        return 2
    source_bases = set(source_type.__mro__[1:]) - {object}
    if any(
        issubclass(source_type, target_type)
        or issubclass(target_type, source_type)
        or bool(source_bases & (set(target_type.__mro__[1:]) - {object}))
        for target_type in target_types
    ):
        return 1
    return 2


def _compatible_device_value_recipes(
    inventory: TaskInventory,
    setters: Iterable[Setter],
    *,
    allow_power_off: bool,
) -> list[dict[str, Any]]:
    """Return the compatible device value recipes."""
    group = tuple(setters)
    if not group:
        return []
    prop = group[0].property
    target_ids = {setter.target_id for setter in group}
    target_class_ids = {setter.class_id for setter in group}
    sources = [
        item
        for item in inventory.property_values("object")
        if item.target_id not in target_ids
        and item.property == prop
        and inventory.query_available(item)
    ]
    options: list[dict[str, Any]] = []
    for source in sources:
        priority = _source_class_priority(
            inventory, str(source.class_id), target_class_ids
        )
        if (
            (allow_power_off or prop != "power" or source.value is not False)
            and all(
                schema_accepts(setter.parameter_schema, source.value)
                and not strict_equal(setter.initial_value, source.value)
                for setter in group
            )
        ):
            options.append(
                {
                    "kind": "query_value",
                    "source": source,
                    "selected_value": deepcopy(source.value),
                    "class_priority": priority,
                }
            )
        delta_maps = [
            {
                (direction, str(amount)): (value, amount)
                for value, direction, amount in delta_values(
                    prop, setter.parameter_schema, source.value
                )
                if not strict_equal(value, setter.initial_value)
            }
            for setter in group
        ]
        common = set(delta_maps[0]).intersection(
            *(set(mapping) for mapping in delta_maps[1:])
        )
        for direction, amount_key in sorted(common):
            values = [
                mapping[(direction, amount_key)][0] for mapping in delta_maps
            ]
            if len({json_value(value) for value in values}) != 1:
                continue
            amount = delta_maps[0][(direction, amount_key)][1]
            options.append(
                {
                    "kind": "query_offset",
                    "source": source,
                    "selected_value": deepcopy(values[0]),
                    "direction": direction,
                    "amount": amount,
                    "offset": amount if direction == "increase" else -amount,
                    "class_priority": priority,
                }
            )
    if not options:
        return []
    best = min(option["class_priority"] for option in options)
    return [option for option in options if option["class_priority"] == best]


def _query_value_recipe_possible(
    inventory: TaskInventory,
    setters: Iterable[Setter],
    *,
    allow_power_off: bool,
) -> bool:
    """Return whether the inventory supports the query-value recipe."""
    return bool(
        _compatible_device_value_recipes(
            inventory,
            setters,
            allow_power_off=allow_power_off,
        )
    )


def _control_layout(
    inventory: TaskInventory,
    subtype: str,
    method: str,
    value_method: str,
    structure: dict[str, Any],
    rng: random.Random,
) -> tuple[TargetSelection, list[Setter]]:
    """Return the control layout."""
    setters = list(inventory.setters)
    if value_method == "delta":
        setters = [
            setter for setter in setters
            if delta_values(
                setter.property, setter.parameter_schema, setter.initial_value
            )
        ]
    elif value_method in {"random", "memory"}:
        setters = [
            setter for setter in setters
            if candidate_values(
                setter.property, setter.parameter_schema, setter.initial_value
            )
        ]
    elif value_method == "query.property.device":
        setters = [
            setter for setter in setters
            if _query_value_recipe_possible(
                inventory, [setter], allow_power_off=True
            )
        ]
    topk = structure["query_topk_count"]
    if subtype == "single":
        target_ids = sorted({item.target_id for item in setters}, key=natural_key)
        selection = target_selection(
            inventory,
            target_kind="object",
            candidate_ids=target_ids,
            method=method,
            requested_count=1,
            topk_bounds=topk,
            rng=rng,
        )
        target_id = selection.selected_ids[0]
        return selection, [rng.choice([item for item in setters if item.target_id == target_id])]

    if subtype == "multi_property":
        bounds = structure["multi_property_count"]
        by_target: dict[str, list[Setter]] = defaultdict(list)
        for setter in setters:
            if setter.property != "power" or setter.initial_value is False:
                by_target[setter.target_id].append(setter)
        eligible = {
            target_id: values
            for target_id, values in by_target.items()
            if len({item.property for item in values}) >= int(bounds["min"])
        }
        selection = target_selection(
            inventory,
            target_kind="object",
            candidate_ids=eligible,
            method=method,
            requested_count=1,
            topk_bounds=topk,
            rng=rng,
        )
        options = eligible[selection.selected_ids[0]]
        count = sample_bounded_count(len(options), bounds, floor=2, rng=rng)
        rng.shuffle(options)
        return selection, options[:count]

    if subtype == "multi_target":
        bounds = structure["multi_target_count"]
        required_targets = max(
            int(bounds["min"]),
            3 if method == "query.target.comparison.topk" else 2,
        )
        groups: dict[tuple[str, str], list[Setter]] = defaultdict(list)
        for setter in setters:
            groups[(setter.class_id, setter.property)].append(setter)
        viable = [
            group for group in groups.values()
            if len({item.target_id for item in group}) >= required_targets
            and (
                value_method != "query.property.device"
                or _query_value_recipe_possible(
                    inventory, group, allow_power_off=True
                )
            )
        ]
        if not viable:
            raise TaskSeedError("no compatible multi-target Control group")
        group = rng.choice(viable)
        target_ids = sorted({item.target_id for item in group}, key=natural_key)
        count = sample_bounded_count(
            len(target_ids), bounds, floor=required_targets, rng=rng
        )
        selection = target_selection(
            inventory,
            target_kind="object",
            candidate_ids=target_ids,
            method=method,
            requested_count=count,
            topk_bounds=topk,
            selected_count_bounds=bounds,
            rng=rng,
        )
        by_target = {item.target_id: item for item in group}
        return selection, [by_target[target_id] for target_id in selection.selected_ids]

    if subtype != "complex":
        raise TaskSeedError(f"unknown Control subtype {subtype}")
    property_bounds = structure["complex_property_count"]
    target_bounds = structure["complex_target_count"]
    required_targets = max(
        int(target_bounds["min"]),
        3 if method == "query.target.comparison.topk" else 2,
    )
    by_class: dict[str, dict[str, dict[str, Setter]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for setter in setters:
        by_class[setter.class_id][setter.target_id][setter.property] = setter
    viable: list[tuple[dict[str, dict[str, Setter]], list[str]]] = []
    for targets in by_class.values():
        identifiers = sorted(targets, key=natural_key)
        common = set.intersection(*(set(targets[target_id]) for target_id in identifiers))
        if any(
            targets[target_id].get("power") is not None
            and targets[target_id]["power"].initial_value is True
            for target_id in identifiers
        ):
            common.discard("power")
        if value_method == "query.property.device":
            common = {
                prop for prop in common
                if _query_value_recipe_possible(
                    inventory,
                    [targets[target_id][prop] for target_id in identifiers],
                    allow_power_off=False,
                )
            }
        if (
            len(identifiers) >= required_targets
            and len(common) >= int(property_bounds["min"])
        ):
            viable.append((targets, sorted(common)))
    if not viable:
        raise TaskSeedError("no compatible complex Control group")
    targets, common_props = rng.choice(viable)
    target_count = sample_bounded_count(
        len(targets), target_bounds, floor=required_targets, rng=rng
    )
    selection = target_selection(
        inventory,
        target_kind="object",
        candidate_ids=targets,
        method=method,
        requested_count=target_count,
        topk_bounds=topk,
        selected_count_bounds=target_bounds,
        rng=rng,
    )
    property_count = sample_bounded_count(
        len(common_props), property_bounds, floor=2, rng=rng
    )
    properties = rng.sample(common_props, property_count)
    return selection, [
        targets[target_id][prop]
        for target_id in selection.selected_ids
        for prop in properties
    ]


def _exact_control_action(controls: list[ControlCandidate]) -> str:
    """Describe the same writes as explicit values, without replaying them."""
    by_property: dict[str, list[ControlCandidate]] = defaultdict(list)
    for control in controls:
        by_property[control.setter.property].append(control)
    clauses: list[str] = []
    for prop, group in sorted(by_property.items()):
        values = {json_value(item.requested_value) for item in group}
        if len(values) == 1:
            clauses.append(
                f"set {prop} to {display_value(group[0].requested_value)}"
            )
        else:
            clauses.extend(
                f"set {item.setter.target_name}'s {prop} to "
                f"{display_value(item.requested_value)}"
                for item in sorted(
                    group, key=lambda value: natural_key(value.setter.target_id)
                )
            )
    return join_clauses(clauses)


def _shared_delta_control_action(
    controls: list[ControlCandidate],
) -> str | None:
    """Return a delta wording only when it denotes every existing write."""
    by_property: dict[str, list[ControlCandidate]] = defaultdict(list)
    for control in controls:
        by_property[control.setter.property].append(control)
    clauses: list[str] = []
    for prop, group in sorted(by_property.items()):
        deltas: set[tuple[str, float]] = set()
        for item in group:
            initial = item.setter.initial_value
            requested = item.requested_value
            if (
                not isinstance(initial, (int, float))
                or isinstance(initial, bool)
                or not isinstance(requested, (int, float))
                or isinstance(requested, bool)
                or strict_equal(initial, requested)
            ):
                return None
            difference = float(requested) - float(initial)
            deltas.add(
                (
                    "increase" if difference > 0 else "decrease",
                    abs(difference),
                )
            )
        if len(deltas) != 1:
            return None
        direction, amount = next(iter(deltas))
        shown_amount: int | float = (
            int(amount) if amount.is_integer() else round(amount, 3)
        )
        clauses.append(f"{direction} {prop} by {shown_amount}")
    return join_clauses(clauses)


def build_control_task(
    inventory: TaskInventory,
    task_id: str,
    subtype: str,
    sampling: dict[str, Any],
    structure: dict[str, Any],
    rng: random.Random,
) -> TaskArtifacts:
    """Return the control task."""
    if (
        sampling["property_target_value_method"] == "memory"
        and subtype != "single"
    ):
        raise TaskSeedError("memory target values are limited to control.single")
    selection, setters = _control_layout(
        inventory,
        subtype,
        sampling["target_selection_method"],
        sampling["property_target_value_method"],
        structure,
        rng,
    )
    value_method = sampling["property_target_value_method"]
    controls, value_query_atoms, value_query_commands, recipes = _choose_shared_controls(
        inventory,
        setters,
        value_method,
        rng,
        allow_power_off=subtype in {"single", "multi_target"},
    )
    try:
        control_commands, final_state = inventory.preview_controls(controls)
    except InventoryError as error:
        raise TaskSeedError(str(error)) from error

    selection_dependencies = [atom["id"] for atom in selection.atoms]
    source_by_property = {
        recipe["property"]: recipe.get("source_atom_id") for recipe in recipes
    }
    atoms: list[dict[str, Any]] = [
        *deepcopy(selection.atoms),
        *deepcopy(value_query_atoms),
    ]
    control_atom_ids: list[str] = []
    private_ids = set(selection.candidate_ids)
    public_anchors = list(selection.public_anchors)
    target = empty_target()
    records: list[dict[str, Any]] = []
    memory_records: list[dict[str, Any]] = []
    memory_ids_by_path: dict[tuple[str, str], str] = {}
    memory_user_id, memory_user_name = (
        memory_user(inventory, sampling, rng)
        if value_method == "memory"
        else (None, None)
    )
    if memory_user_name is not None:
        public_anchors.append(memory_user_name)
    for index, control in enumerate(
        sorted(
            controls,
            key=lambda item: (
                natural_key(item.setter.target_id), item.setter.property
            ),
        ),
        start=1,
    ):
        setter = control.setter
        atom_id = f"c{index}"
        dependencies = list(selection_dependencies)
        source_atom = source_by_property.get(setter.property)
        if source_atom:
            dependencies.append(source_atom)
        actual = deepcopy(
            final_state["objects"][setter.target_id]["properties"][setter.property]
        )
        spec = {
            "target_id": setter.target_id,
            "target_name": setter.target_name,
            "property": setter.property,
            "assertion": {"op": "eq", "value": actual},
            "implicit_power_on": control.implicit_power_on,
        }
        memory_id = None
        if value_method == "memory":
            memory_record, binding = memory_value(
                task_id=task_id,
                target_kind="object",
                target_id=setter.target_id,
                target_name=setter.target_name,
                prop=setter.property,
                value=control.requested_value,
                user_id=memory_user_id,
                user_name=memory_user_name,
            )
            memory_id = memory_record["memory_id"]
            memory_records.append(memory_record)
            memory_ids_by_path[(setter.target_id, setter.property)] = memory_id
            target["required_memory_ids"].append(memory_id)
            private_ids.add(memory_id)
            spec["memory_binding"] = binding
        atoms.append(
            {
                "id": atom_id,
                "kind": "control",
                "depends_on": sorted(set(dependencies)),
                "spec": spec,
            }
        )
        control_atom_ids.append(atom_id)
        private_ids.add(setter.target_id)
        public_anchors.append(setter.property)
        target["objects"].setdefault(
            setter.target_id, {"properties": {}}
        )["properties"][setter.property] = {"op": "eq", "value": actual}
        value_record = {
            "target_id": setter.target_id,
            "property": setter.property,
            "initial_value": deepcopy(setter.initial_value),
            "requested_value": deepcopy(control.requested_value),
            "actual_value": actual,
            "implicit_power_on": control.implicit_power_on,
        }
        if memory_id is not None:
            value_record["memory_id"] = memory_id
        records.append(value_record)

    if value_method == "memory":
        for recipe in recipes:
            recipe["memory_ids"] = [
                memory_ids_by_path[(target_id, recipe["property"])]
                for target_id in recipe["target_ids"]
            ]

    clauses: list[str] = []
    alternate_clauses: list[str] = []
    concise_clauses: list[str] = []
    for recipe in recipes:
        prop = recipe["property"]
        if recipe["kind"] == "set":
            value = display_value(recipe["value"])
            clauses.append(f"set {prop} to {value}")
            alternate_clauses.append(f"change {prop} to {value}")
            concise_clauses.append(
                f"switch {prop} {value}"
                if isinstance(recipe["value"], bool)
                else f"adjust {prop} to {value}"
            )
            if not isinstance(recipe["value"], bool):
                public_anchors.append(str(recipe["value"]))
        elif recipe["kind"] == "delta":
            clauses.append(
                f"{recipe['direction']} {prop} by {recipe['amount']}"
            )
            alternate_clauses.append(
                f"{'raise' if recipe['direction'] == 'increase' else 'lower'} "
                f"{prop} by {recipe['amount']}"
            )
            concise_clauses.append(
                f"adjust {prop} "
                f"{'upward' if recipe['direction'] == 'increase' else 'downward'} "
                f"by {recipe['amount']}"
            )
            public_anchors.append(str(recipe["amount"]))
        elif recipe["kind"] == "memory":
            owner = f" of {memory_user_name}" if memory_user_name else ""
            clauses.append(f"set {prop} to the saved preference{owner}")
            alternate_clauses.append(
                f"use the saved {prop} preference{owner}"
            )
            concise_clauses.append(
                f"apply the remembered {prop} setting{owner}"
            )
        elif recipe["kind"] == "query_value":
            clauses.append(
                f"set {prop} to the current {recipe['source_property']} read from "
                f"{recipe['source_target_name']}"
            )
            alternate_clauses.append(
                f"match {prop} to {recipe['source_target_name']}'s current "
                f"{recipe['source_property']}"
            )
            concise_clauses.append(
                f"copy {recipe['source_target_name']}'s current "
                f"{recipe['source_property']} into {prop}"
            )
            public_anchors.extend(
                (recipe["source_target_name"], prop, recipe["source_property"])
            )
            private_ids.add(recipe["source_target_id"])
        elif recipe["kind"] == "query_offset":
            relation = "above" if recipe["direction"] == "increase" else "below"
            comparative = "higher" if recipe["direction"] == "increase" else "lower"
            clauses.append(
                f"set {prop} to {recipe['amount']} {relation} "
                f"{recipe['source_target_name']}'s current {recipe['source_property']}"
            )
            alternate_clauses.append(
                f"make {prop} {recipe['amount']} {comparative} than "
                f"{recipe['source_target_name']}'s current {recipe['source_property']}"
            )
            concise_clauses.append(
                f"keep {prop} {recipe['amount']} {relation} "
                f"{recipe['source_target_name']}'s current {recipe['source_property']}"
            )
            public_anchors.extend(
                (
                    recipe["source_target_name"],
                    recipe["source_property"],
                    prop,
                    str(recipe["amount"]),
                )
            )
            private_ids.add(recipe["source_target_id"])
        else:
            raise TaskSeedError(
                f"unsupported Control value recipe {recipe['kind']}"
            )
    action_variants = [
        (join_clauses(items), value_method)
        for items in (clauses, alternate_clauses, concise_clauses)
    ]
    if value_method == "delta":
        action_variants.append((_exact_control_action(controls), "random"))
    elif value_method == "random":
        delta_action = _shared_delta_control_action(controls)
        if delta_action is not None:
            action_variants.append((delta_action, "delta"))
    action_variants = list(dict.fromkeys(action_variants))
    target_variants = [
        (
            description,
            "except"
            if " except " in description
            else "all"
            if description.startswith("all ")
            else selection.method,
        )
        for description in selection_description_variants(
            inventory,
            selection,
            target_kind="object",
        )
    ]
    control_variants: list[dict[str, Any]] = []
    for target_description, target_method in target_variants:
        for action_index, (action, action_method) in enumerate(action_variants):
            sentence = (
                f"For {target_description}, {action}.",
                f"Apply this update to {target_description}: {action}.",
                f"Please change {target_description} as follows: {action}.",
            )[action_index % 3]
            control_variants.append(
                {
                    "instruction": sentence,
                    "target_selection_method": target_method,
                    "property_target_value_method": action_method,
                }
            )
    instruction = instruction_templates(
        item["instruction"] for item in control_variants
    )

    execution: list[dict[str, Any]] = [
        *([read_memory()] if memory_records else []),
        *selection.commands,
        *value_query_commands,
        *control_commands,
    ]
    answer_plans: list[dict[str, Any]] = []
    post_option = sampling.get("post_control_query", "none")
    if post_option == "query_modified_value":
        if subtype != "single" or value_method != "delta" or len(controls) != 1:
            raise TaskSeedError(
                "post-Control query requires control.single with delta value sampling"
            )
        control = controls[0]
        getter = next(
            (
                item
                for item in inventory.property_values("object")
                if item.target_id == control.setter.target_id
                and item.property == control.setter.property
            ),
            None,
        )
        if getter is None:
            raise TaskSeedError("modified property is not queryable after Control")
        answer = deepcopy(
            final_state["objects"][control.setter.target_id]["properties"][control.setter.property]
        )
        post_atom = query_atom(
            "qpost",
            getter,
            depends_on=control_atom_ids,
            role="post_control_answer",
        )
        atoms.append(post_atom)
        target["expected_answers"].append({"value": answer, "match": "exact"})
        execution.extend((getter.query_command, submit_answer(answer)))
        post_query_variants = (
            f"After the change, query and report the resulting {control.setter.property}.",
            f"Once complete, read back and report the new {control.setter.property}.",
            f"Then check and report the resulting {control.setter.property}.",
        )
        instruction = [
            f"{template} {post_query_variants[index % len(post_query_variants)]}"
            for index, template in enumerate(instruction)
        ]
        for index, template in enumerate(instruction):
            control_variants[index]["instruction"] = template
        answer_plans.append(
            {
                "atom_ids": ["qpost"],
                "operation": "post_control_state",
                "source_paths": [
                    f"object.{control.setter.target_id}.{control.setter.property}"
                ],
                "result": answer,
            }
        )
    elif post_option != "none":
        raise TaskSeedError(f"unknown post-Control query option {post_option}")

    sampling["target_selection"] = deepcopy(selection.details)
    sampling["property_target_value"] = {
        "method": value_method,
        "records": records,
        "recipes": deepcopy(recipes),
    }
    sampling["post_control_query"] = {
        "method": post_option,
        "answer_source": "previewed_post_control_state"
        if post_option == "query_modified_value"
        else None,
    }
    seed = build_task_seed(
        "control",
        subtype,
        atoms,
        sampling,
        public_anchors=public_anchors,
        private_identifiers=private_ids,
        answer_plans=answer_plans,
        selection_plans=[deepcopy(selection.details)],
    )
    seed["derived"]["control_variants"] = deepcopy(control_variants)
    return TaskArtifacts(
        seed=seed,
        instruction_template=instruction,
        target=target,
        reference_plan=build_reference_plan(task_id, execution),
        memory=(
            {
                "scope_id": memory_identifier(task_id, "scope"),
                "records": memory_records,
            }
            if memory_records
            else None
        ),
    )


def build_control_variants(
    world: World,
    task_inventory: TaskInventory,
    *,
    task_id: str,
    base: TaskArtifacts,
    sampling: dict[str, Any],
) -> tuple[TaskArtifacts, ...]:
    """Expand instructions and metadata around the validated control actions."""
    variants = base.seed["derived"].pop("control_variants")
    grouped: dict[tuple[str, str], list[str]] = {}
    for variant in variants:
        key = (
            variant["target_selection_method"],
            variant["property_target_value_method"],
        )
        grouped.setdefault(key, []).append(variant["instruction"])
    action_group_id = f"{task_id}_control_actions"
    result: list[TaskArtifacts] = []
    for index, ((target_method, value_method), instructions) in enumerate(
        grouped.items(), start=1
    ):
        artifacts = mark_action_reuse(
            base,
            task_id=f"{task_id}_c{index:02d}",
            variant_key=f"target_{target_method}__value_{value_method}",
            action_group_id=action_group_id,
            strategy="shared_control_actions",
            instruction_template=instruction_templates(instructions),
        )
        artifacts.seed["sampling"]["sampled_target_selection_method"] = sampling[
            "target_selection_method"
        ]
        artifacts.seed["sampling"]["sampled_property_target_value_method"] = sampling[
            "property_target_value_method"
        ]
        artifacts.seed["sampling"]["target_selection_method"] = target_method
        artifacts.seed["sampling"]["property_target_value_method"] = value_method
        selection_details = artifacts.seed["sampling"]["target_selection"]
        selection_details["method"] = target_method
        if target_method in {"all", "except"}:
            selected_ids = selection_details["selected_ids"]
            category = task_inventory.initial["objects"][selected_ids[0]]["class"]
            category_ids = sorted(
                (
                    target_id
                    for target_id, spec in task_inventory.initial["objects"].items()
                    if spec["class"] == category
                ),
                key=natural_key,
            )
            selection_details["candidate_ids"] = category_ids
            excluded_ids = [
                target_id for target_id in category_ids if target_id not in selected_ids
            ]
            if target_method == "except":
                selection_details["excluded_ids"] = excluded_ids
            else:
                selection_details.pop("excluded_id", None)
                selection_details.pop("excluded_ids", None)
        artifacts.seed["selection_plans"] = [deepcopy(selection_details)]
        value_details = artifacts.seed["sampling"]["property_target_value"]
        value_details["method"] = value_method
        if value_method == "random":
            grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for record in value_details["records"]:
                grouped[record["property"]].append(record)
            value_details["recipes"] = [
                {
                    "kind": "set",
                    "property": prop,
                    "target_ids": [record["target_id"] for record in records],
                    "requested_values": {
                        record["target_id"]: deepcopy(record["requested_value"])
                        for record in records
                    },
                }
                for prop, records in sorted(grouped.items())
            ]
        elif value_method == "delta":
            grouped = defaultdict(list)
            for record in value_details["records"]:
                grouped[record["property"]].append(record)
            recipes = []
            for prop, records in sorted(grouped.items()):
                difference = float(records[0]["requested_value"]) - float(
                    records[0]["initial_value"]
                )
                amount = abs(difference)
                recipes.append(
                    {
                        "kind": "delta",
                        "property": prop,
                        "direction": "increase" if difference > 0 else "decrease",
                        "amount": int(amount) if amount.is_integer() else round(amount, 3),
                        "target_ids": [record["target_id"] for record in records],
                        "requested_values": {
                            record["target_id"]: deepcopy(record["requested_value"])
                            for record in records
                        },
                    }
                )
            value_details["recipes"] = recipes
        validate_task_seed(artifacts.seed)
        world.contract.validate_target(
            artifacts.target,
            world.get_world_spec(),
            world.get_initial_state(),
        )
        world.contract.validate_schema(
            artifacts.reference_plan,
            "urn:dcb:v2:schema:reference-plan",
        )
        result.append(artifacts)
    return tuple(result)
