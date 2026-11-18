"""Shared task artifacts, metadata, memory, and reference-plan helpers."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
from pathlib import Path
import random
from typing import Any, Iterable

from src.runtime import WorldBlueprint

from .task_inventory import (
    command,
    json_value,
    natural_key,
    PropertyValue,
    TaskInventory,
)


class TaskSeedError(ValueError):
    """A task slot cannot be instantiated in the supplied effective World."""


class InstructionAlignmentError(ValueError):
    """An instruction rewrite changed protected public semantics."""


@dataclass(frozen=True)
class TaskArtifacts:
    seed: dict[str, Any]
    instruction_template: str | list[str]
    target: dict[str, Any]
    reference_plan: dict[str, Any]
    memory: dict[str, Any] | None = None

    @property
    def metadata(self) -> dict[str, Any]:
        """Return the metadata."""
        return deepcopy(self.seed)


@dataclass(frozen=True)
class PreparedTask:
    """Rule-built task artifacts sharing one batch-level effective World."""

    world_init: dict[str, Any]
    source_world_id: str
    source_world_root: Path
    initial_tweaks: tuple[dict[str, Any], ...]
    artifacts: TaskArtifacts
    effective_world_batch_id: str
    inventory_snapshot: dict[str, Any]
    public_instruction: str | None = None
    world_blueprint: WorldBlueprint | None = None


def instruction_templates(templates: Iterable[str]) -> list[str]:
    """Return the instruction variants."""
    return list(dict.fromkeys(template for template in templates if template))


def empty_target() -> dict[str, Any]:
    """Return the empty target."""
    return {
        "objects": {},
        "spaces": {},
        "runtime": {},
        "expected_answers": [],
        "expected_reports": [],
        "required_memory_ids": [],
        "expected_memory_mutations": [],
        "time_constraint": None,
    }


def finish() -> dict[str, Any]:
    """Finish the current interaction."""
    return command("session", "finish")


def submit_answer(value: Any) -> dict[str, Any]:
    """Submit the agent's final answer."""
    return command("session", "submit_answer", value=deepcopy(value))


def submit_report(report: dict[str, Any]) -> dict[str, Any]:
    """Submit the agent's execution report."""
    return command(
        "session",
        "submit_report",
        status=report["status"],
        reason_code=report["reason_code"],
        description=report.get("description", ""),
        affected_properties=deepcopy(report["affected_properties"]),
    )


def read_memory() -> dict[str, Any]:
    """Return the memory."""
    return command("memory", "read")


def memory_identifier(*parts: str) -> str:
    """Return the memory identifier."""
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"memory_{digest}"


def memory_value(
    *,
    task_id: str,
    target_kind: str,
    target_id: str,
    target_name: str,
    prop: str,
    value: Any,
    user_id: str | None,
    user_name: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return the memory value."""
    memory_id = memory_identifier(
        task_id, target_kind, target_id, prop
    )
    owner = f" of {user_name}" if user_name is not None else ""
    record = {
        "memory_id": memory_id,
        "content": (
            f"The saved preference{owner} for {target_name}'s {prop} is "
            f"{display_value(value)}."
        ),
    }
    if user_id is not None:
        record["user_id"] = user_id
    binding = {
        "memory_id": memory_id,
        "target_kind": target_kind,
        "target_id": target_id,
        "property": prop,
        "value": deepcopy(value),
    }
    if user_id is not None:
        binding["user_id"] = user_id
    return record, binding


def deduplicate(commands: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return commands with duplicate entries removed."""
    result: list[dict[str, Any]] = []
    for item in commands:
        if item not in result:
            result.append(deepcopy(item))
    return result


def build_reference_plan(task_id: str, commands: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Preserve answer/report multiplicity while adding device discovery."""
    supplied = [deepcopy(item) for item in commands]
    memory_reads = deduplicate(
        item
        for item in supplied
        if item["target"] == "memory" and item["function"] == "read"
    )
    execution = [
        item
        for item in supplied
        if not (item["target"] == "memory" and item["function"] == "read")
    ]
    device_ids = sorted(
        {
            item["target"]
            for item in execution
            if item["target"] not in {"session", "memory"}
        },
        key=natural_key,
    )
    execution.append(finish())
    preparation = [
        *memory_reads,
        *[
            command("session", "get_device_tools", device_id=target_id)
            for target_id in device_ids
        ],
    ]
    if not preparation:
        return {"task_id": task_id, "turns": [execution]}
    return {"task_id": task_id, "turns": [preparation, execution]}


def graph_depth(atoms: list[dict[str, Any]]) -> int:
    """Return the graph depth."""
    pending = {atom["id"]: atom for atom in atoms}
    depths: dict[str, int] = {}
    while pending:
        ready = [
            atom_id
            for atom_id, atom in pending.items()
            if all(parent in depths for parent in atom["depends_on"])
        ]
        if not ready:
            raise TaskSeedError("atom dependency graph contains a cycle")
        for atom_id in ready:
            atom = pending.pop(atom_id)
            depths[atom_id] = 1 + max(
                (depths[parent] for parent in atom["depends_on"]), default=0
            )
    return max(depths.values())


def build_task_seed(
    family: str,
    subtype: str,
    atoms: list[dict[str, Any]],
    sampling: dict[str, Any],
    *,
    public_anchors: Iterable[str],
    private_identifiers: Iterable[str],
    answer_plans: list[dict[str, Any]] | None = None,
    selection_plans: list[dict[str, Any]] | None = None,
    feasibility: str = "feasible",
) -> dict[str, Any]:
    """Return the seed."""
    default_outcome = "infeasible" if feasibility == "infeasible" else "success"
    outcomes = {atom["id"]: atom["spec"].get("expected_status", default_outcome) for atom in atoms}
    succeeded = sum(status == "success" for status in outcomes.values())
    feasibility = "feasible" if succeeded == len(atoms) else "partial" if succeeded else "infeasible"
    return {
        "task_family": family,
        "task_subtype": subtype,
        "atoms": deepcopy(atoms),
        "constraints": {"preserve_unselected": True},
        "expected_outcome": {
            "feasibility": feasibility,
            "atoms": outcomes,
        },
        "answer_plans": deepcopy(answer_plans or []),
        "selection_plans": deepcopy(selection_plans or []),
        "sampling": deepcopy(sampling),
        "derived": {
            "atom_count": len(atoms),
            "graph_depth": graph_depth(atoms),
            "answer_count": len(answer_plans or []),
            "public_anchors": sorted(set(public_anchors), key=str.casefold),
            "private_identifiers": sorted(
                set(private_identifiers), key=natural_key
            ),
        },
    }


def query_atom(
    atom_id: str,
    item: PropertyValue,
    *,
    depends_on: Iterable[str] = (),
    role: str = "answer",
) -> dict[str, Any]:
    """Return the query atom."""
    return {
        "id": atom_id,
        "kind": "query",
        "depends_on": list(depends_on),
        "spec": {
            "target_kind": item.target_kind,
            "target_id": item.target_id,
            "target_name": item.target_name,
            "property": item.property,
            "query_mode": "current_value",
            "role": role,
        },
    }


def memory_user(
    inventory: TaskInventory,
    sampling: dict[str, Any],
    rng: random.Random,
) -> tuple[str | None, str | None]:
    """Return the configured memory owner ID and public name."""
    scope = sampling.get("memory_user_scope", "user")
    if scope == "global":
        return None, None
    if scope != "user":
        raise TaskSeedError(f"unknown memory user scope {scope}")
    if not inventory.people:
        raise TaskSeedError("user-scoped memory requires people")
    user_id = rng.choice(sorted(inventory.people, key=natural_key))
    return user_id, inventory.person_name(user_id)


def display_value(value: Any) -> str:
    """Return the display value."""
    if value is True:
        return "on"
    if value is False:
        return "off"
    return json_value(value)


def join_clauses(clauses: list[str]) -> str:
    """Join the clauses."""
    if len(clauses) == 1:
        return clauses[0]
    return ", ".join(clauses[:-1]) + ", and " + clauses[-1]


def rebind_task_artifacts(
    artifacts: TaskArtifacts,
    task_id: str,
) -> TaskArtifacts:
    """Copy rule-built artifacts onto a final deterministic task ID."""
    reference_plan = deepcopy(artifacts.reference_plan)
    reference_plan["task_id"] = task_id
    return TaskArtifacts(
        seed=deepcopy(artifacts.seed),
        instruction_template=deepcopy(artifacts.instruction_template),
        target=deepcopy(artifacts.target),
        reference_plan=reference_plan,
        memory=deepcopy(artifacts.memory),
    )


def mark_action_reuse(
    artifacts: TaskArtifacts,
    *,
    task_id: str,
    variant_key: str,
    action_group_id: str,
    strategy: str,
    instruction_template: str | list[str] | None = None,
) -> TaskArtifacts:
    """Mark the action reuse."""
    rebound = rebind_task_artifacts(artifacts, task_id)
    seed = deepcopy(rebound.seed)
    seed["sampling"]["variant_key"] = variant_key
    seed["sampling"]["action_group_id"] = action_group_id
    seed["derived"]["action_validation_reuse"] = {
        "group_id": action_group_id,
        "strategy": strategy,
        "validated_once": True,
    }
    template = deepcopy(
        rebound.instruction_template
        if instruction_template is None
        else instruction_template
    )
    templates = template if isinstance(template, list) else [template]
    seed["derived"]["public_anchors"] = [
        anchor
        for anchor in seed["derived"].get("public_anchors", [])
        if all(str(anchor).casefold() in item.casefold() for item in templates)
    ]
    return TaskArtifacts(
        seed=seed,
        instruction_template=template,
        target=deepcopy(rebound.target),
        reference_plan=deepcopy(rebound.reference_plan),
        memory=deepcopy(rebound.memory),
    )
