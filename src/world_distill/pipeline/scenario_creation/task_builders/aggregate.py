"""Merge compatible validated task components and their private artifacts."""

from __future__ import annotations

from copy import deepcopy
import random
from typing import Any

from src.contracts import strict_equal
from src.runtime import World

from ..task_common import (
    build_reference_plan,
    build_task_seed,
    empty_target,
    instruction_templates,
    memory_identifier,
    TaskArtifacts,
    TaskSeedError,
)
from ..task_sampler import AGGREGATE_COMPONENTS
from ..validator import validate_task_seed


def _remap_atom_ids(value: Any, mapping: dict[str, str]) -> Any:
    """Remap the atom IDs."""
    if isinstance(value, list):
        return [_remap_atom_ids(item, mapping) for item in value]
    if not isinstance(value, dict):
        return deepcopy(value)
    return {
        key: (
            mapping.get(item, item)
            if key == "atom_id" and isinstance(item, str)
            else [mapping.get(atom_id, atom_id) for atom_id in item]
            if key == "atom_ids" and isinstance(item, list)
            else _remap_atom_ids(item, mapping)
        )
        for key, item in value.items()
    }


def _merge_component_targets(parts: list[TaskArtifacts]) -> dict[str, Any]:
    """Return the component targets."""
    merged = empty_target()
    for part in parts:
        target = part.target
        if (
            target["runtime"]
            or target["expected_reports"]
            or target["time_constraint"] is not None
            or target.get("expected_memory_mutations", [])
        ):
            raise TaskSeedError(
                "Aggregate components must be feasible tasks without runtime, "
                "report, time, or memory-write targets"
            )
        for scope in ("objects", "spaces"):
            for target_id, spec in target[scope].items():
                properties = merged[scope].setdefault(
                    target_id, {"properties": {}}
                )["properties"]
                for prop, assertion in spec["properties"].items():
                    if prop in properties and not strict_equal(
                        properties[prop], assertion
                    ):
                        raise TaskSeedError(
                            f"conflicting Aggregate target {scope}.{target_id}.{prop}"
                        )
                    properties[prop] = deepcopy(assertion)
        merged["expected_answers"].extend(
            deepcopy(target["expected_answers"])
        )
        for memory_id in target["required_memory_ids"]:
            if memory_id not in merged["required_memory_ids"]:
                merged["required_memory_ids"].append(memory_id)
    return merged


def _merge_component_memory(
    task_id: str,
    parts: list[TaskArtifacts],
) -> dict[str, Any] | None:
    """Return the component memory."""
    records: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    for part in parts:
        if part.memory is None:
            continue
        for record in part.memory["records"]:
            memory_id = record["memory_id"]
            existing = by_id.get(memory_id)
            if existing is not None and existing != record:
                raise TaskSeedError(
                    f"conflicting Aggregate memory record {memory_id}"
                )
            if existing is None:
                copied = deepcopy(record)
                by_id[memory_id] = copied
                records.append(copied)
    if not records:
        return None
    return {
        "scope_id": memory_identifier(task_id, "scope"),
        "records": records,
    }


def _component_commands(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the component commands."""
    return [
        deepcopy(item)
        for turn in plan["turns"]
        for item in turn
        if not (
            item["target"] == "session"
            and item["function"] in {"get_device_tools", "finish"}
        )
    ]


ComponentPathSet = frozenset[tuple[str, str, str]]


ComponentPaths = tuple[ComponentPathSet, ComponentPathSet]


def component_read_paths(part: TaskArtifacts) -> ComponentPathSet:
    """Return the component read paths."""
    return frozenset(
        (
            atom["spec"]["target_kind"],
            atom["spec"]["target_id"],
            atom["spec"]["property"],
        )
        for atom in part.seed["atoms"]
        if atom["kind"] == "query"
        and all(
            key in atom["spec"]
            for key in ("target_kind", "target_id", "property")
        )
    )


def component_paths(
    world: World,
    part: TaskArtifacts,
    *,
    validated_writes: ComponentPathSet | None = None,
) -> ComponentPaths:
    """Return the component paths."""
    declared = [world._tool_index[f"{item['target']}_{item['function']}"] for item in _component_commands(part.reference_plan) if item["target"] not in {"session", "memory"}]
    reads = component_read_paths(part) | frozenset(("object", tool["target"], prop) for tool in declared for prop in tool.get("reads", []))
    writes = frozenset(("object", tool["target"], prop) for tool in declared for prop in tool.get("writes", []))
    if validated_writes is not None:
        return reads, validated_writes | writes
    return reads, component_write_paths(world, part) | writes


def component_write_paths(
    world: World,
    part: TaskArtifacts,
) -> ComponentPathSet:
    """Return the component write paths."""
    commands = [
        item for item in _component_commands(part.reference_plan)
        if not (
            item["target"] == "session"
            and item["function"] in {"submit_answer", "submit_report"}
        )
    ]
    preview = world.preview_actions(commands)
    if any(result.code != "[PASS]" for result in preview.results):
        raise TaskSeedError("Aggregate component replay failed")
    return frozenset(
        (
            difference["scope"],
            difference["target_id"],
            difference["property"],
        )
        for difference in preview.differences
        if difference["scope"] in {"object", "space"}
    )


def _assert_independent_components(
    world: World,
    parts: list[TaskArtifacts],
    validated_paths: list[ComponentPaths] | None = None,
) -> None:
    """Assert the independent components."""
    paths = validated_paths or [component_paths(world, part) for part in parts]
    for left_index, (left_reads, left_writes) in enumerate(paths):
        for right_reads, right_writes in paths[left_index + 1:]:
            conflicts = (
                left_writes & (right_reads | right_writes)
            ) | (right_writes & left_reads)
            if conflicts:
                names = ", ".join(
                    ".".join(path) for path in sorted(conflicts)
                )
                raise TaskSeedError(
                    f"Aggregate component paths are not independent: {names}"
                )


def _assert_merged_target(
    world: World,
    target: dict[str, Any],
    final_state: dict[str, Any],
) -> None:
    """Assert the merged target."""
    initial_state = world.get_initial_state()
    for scope in ("objects", "spaces"):
        for target_id, spec in target[scope].items():
            for prop, assertion in spec["properties"].items():
                if not world.contract.evaluate_assertion(
                    assertion,
                    initial_state[scope][target_id]["properties"][prop],
                    final_state[scope][target_id]["properties"][prop],
                ):
                    raise TaskSeedError(
                        f"joint Aggregate replay does not satisfy "
                        f"{scope}.{target_id}.{prop}"
                    )


def merge_task_artifacts(
    world: World,
    *,
    task_id: str,
    subtype: str,
    parts: list[TaskArtifacts],
    source_task_ids: list[str],
    profile_id: str,
    validated_component_paths: list[ComponentPaths] | None = None,
) -> TaskArtifacts:
    """Merge already validated Q/C/G tasks from one effective World."""
    expected_families = AGGREGATE_COMPONENTS.get(subtype)
    actual_families = tuple(part.seed["task_family"] for part in parts)
    if expected_families is None or set(actual_families) != set(expected_families) or not 2 <= len(parts) <= 10:
        raise TaskSeedError(
            f"aggregate.{subtype} requires components {expected_families}, "
            f"got {actual_families}"
        )
    if len(source_task_ids) != len(parts):
        raise TaskSeedError("Aggregate source task IDs do not match components")
    if any(
        part.seed["expected_outcome"]["feasibility"] != "feasible"
        for part in parts
    ):
        raise TaskSeedError("Aggregate components must already be feasible")
    if (
        validated_component_paths is not None
        and len(validated_component_paths) != len(parts)
    ):
        raise TaskSeedError("Aggregate component path evidence is incomplete")
    _assert_independent_components(world, parts, validated_component_paths)

    atoms: list[dict[str, Any]] = []
    answer_plans: list[dict[str, Any]] = []
    selection_plans: list[dict[str, Any]] = []
    public_anchors: list[str] = []
    private_identifiers: list[str] = []
    for index, part in enumerate(parts, start=1):
        mapping = {
            atom["id"]: f"p{index}_{atom['id']}"
            for atom in part.seed["atoms"]
        }
        for atom in part.seed["atoms"]:
            copied = deepcopy(atom)
            copied["id"] = mapping[atom["id"]]
            copied["depends_on"] = [
                mapping[parent] for parent in atom["depends_on"]
            ]
            atoms.append(copied)
        answer_plans.extend(
            _remap_atom_ids(part.seed["answer_plans"], mapping)
        )
        selection_plans.extend(
            _remap_atom_ids(part.seed["selection_plans"], mapping)
        )
        public_anchors.extend(
            part.seed["derived"].get("public_anchors", [])
        )
        private_identifiers.extend(
            part.seed["derived"].get("private_identifiers", [])
        )

    target = _merge_component_targets(parts)
    memory = _merge_component_memory(task_id, parts)
    available_memory_ids = {
        record["memory_id"]
        for record in (memory or {"records": []})["records"]
    }
    if not set(target["required_memory_ids"]).issubset(available_memory_ids):
        raise TaskSeedError(
            "Aggregate required memory IDs are missing from component fixtures"
        )
    commands = [
        item for part in parts for item in _component_commands(part.reference_plan)
    ]
    preview = world.preview_actions(
        item
        for item in commands
        if not (
            item["target"] == "session"
            and item["function"] in {"submit_answer", "submit_report"}
        )
    )
    if any(result.code != "[PASS]" for result in preview.results):
        raise TaskSeedError("joint Aggregate preview failed")
    _assert_merged_target(world, target, preview.final_state)

    sampling = {
        "profile_id": profile_id,
        "task_type": f"aggregate.{subtype}",
        "target_outcome": "valid",
        "source_families": list(actual_families),
        "component_count": len(parts),
        "source_task_ids": list(source_task_ids),
        "merge_strategy": "validated_components",
    }
    seed = build_task_seed(
        "aggregate",
        subtype,
        atoms,
        sampling,
        public_anchors=public_anchors,
        private_identifiers=private_identifiers,
        answer_plans=answer_plans,
        selection_plans=selection_plans,
    )
    seed["derived"]["source_task_ids"] = list(source_task_ids)
    instruction_options = [
        (
            [part.instruction_template]
            if isinstance(part.instruction_template, str)
            else part.instruction_template
        )
        for part in parts
    ]
    instruction_rng = random.Random(f"dcb-aggregate-instructions:{task_id}:{':'.join(source_task_ids)}")
    instructions = instruction_templates(
        " Then, ".join(instruction_rng.choice(options).strip().rstrip(".") for options in instruction_options) + "."
        for _ in range(10)
    )
    seed["derived"]["public_anchors"] = [
        anchor
        for anchor in seed["derived"].get("public_anchors", [])
        if all(str(anchor).casefold() in item.casefold() for item in instructions)
    ]
    artifacts = TaskArtifacts(
        seed=seed,
        instruction_template=instructions,
        target=target,
        reference_plan=build_reference_plan(task_id, commands),
        memory=memory,
    )
    if memory is not None:
        world.contract.validate_memory(memory)
    validate_task_seed(seed)
    world.contract.validate_target(
        target,
        world.get_world_spec(),
        world.get_initial_state(),
    )
    world.contract.validate_schema(
        artifacts.reference_plan,
        "urn:dcb:v2:schema:reference-plan",
    )
    return artifacts
