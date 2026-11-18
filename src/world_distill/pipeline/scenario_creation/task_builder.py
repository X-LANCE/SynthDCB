"""Dispatch task construction over an existing World and shared inventory."""

from __future__ import annotations

from copy import deepcopy
import random
from typing import Any

from src.utils import format_json
from src.runtime import World

from .task_builders.capability import build_capability_task
from .task_builders.control import build_control_task, build_control_variants
from .task_builders.dependency import build_query_dependency_task
from .task_builders.goal import build_goal_task
from .task_builders.negative import build_negative_task
from .task_builders.query import build_collection_query_task, build_query_task, build_query_variants
from .task_builders.workflow import build_workflow_task
from .task_common import TaskArtifacts, TaskSeedError
from .task_inventory import InventoryError, TaskInventory
from .task_sampler import (
    DEFAULT_STRUCTURE,
    sample_family,
    sampling_options,
    TASK_SUBTYPES,
)
from .validator import validate_task_artifacts


def build_task_variants(
    world: World,
    *,
    task_id: str,
    constraints: dict[str, Any],
    rng: random.Random | None = None,
    inventory: TaskInventory | None = None,
) -> tuple[TaskArtifacts, ...]:
    """Build one sampled Q/C/G intent and its action-sharing variants."""
    task_rng = rng or random.Random(
        f"{world.get_initial_state()['world_id']}:{task_id}:variants"
    )
    task_inventory = inventory or TaskInventory(world)
    sampling = sampling_options(constraints)
    family = constraints["task_family"]
    if family == "query" and constraints["task_subtype"].startswith("property.") and sampling["target_outcome"] == "valid":
        direct = build_task_artifacts(world, task_id=task_id, constraints=constraints,
                                      rng=task_rng, inventory=task_inventory)
        if task_inventory.initial["spaces"]:
            try:
                variants = build_query_variants(world, task_inventory, task_id=task_id,
                                                constraints=constraints, rng=task_rng)
                return (direct, *variants)
            except TaskSeedError:
                pass  # A direct query remains valid without a comparable Space baseline.
        return (direct,)
    if (
        family == "query"
        and bool(task_inventory.initial["spaces"])
        and sampling["target_outcome"] == "valid"
        and not constraints["task_subtype"].startswith("space.")
        and not constraints["task_subtype"].startswith("property.")
    ):
        return build_query_variants(
            world,
            task_inventory,
            task_id=task_id,
            constraints=constraints,
            rng=task_rng,
        )

    base = build_task_artifacts(
        world,
        task_id=task_id,
        constraints=constraints,
        rng=task_rng,
        inventory=task_inventory,
    )
    if family != "control" or sampling["target_outcome"] != "valid":
        return (base,)

    return build_control_variants(
        world, task_inventory, task_id=task_id, base=base, sampling=sampling
    )


def build_task_artifacts(
    world: World,
    *,
    task_id: str,
    constraints: dict[str, Any],
    rng: random.Random | None = None,
    inventory: TaskInventory | None = None,
) -> TaskArtifacts:
    """Build one task while optionally reusing a batch-level World inventory."""
    family = constraints.get("task_family")
    subtype = constraints.get("task_subtype")
    if family not in TASK_SUBTYPES or subtype not in TASK_SUBTYPES[family]:
        raise TaskSeedError(f"unknown task type {family}.{subtype}")
    task_rng = rng or random.Random(f"{world.get_initial_state()['world_id']}:{task_id}")
    task_inventory = inventory or TaskInventory(world)
    sampling = sampling_options(constraints)
    if (
        family == "query"
        and subtype.startswith("space.")
        and sampling["target_outcome"] != "valid"
    ):
        raise TaskSeedError("space Queries only support valid targets")
    structure = deepcopy(DEFAULT_STRUCTURE)
    structure.update(deepcopy(constraints.get("requirements", {}).get("structure", {})))

    if sampling.get("query_dependency", "none") != "none":
        if family != "control":
            raise TaskSeedError("Query dependency tasks currently belong to Control")
        artifacts = build_query_dependency_task(task_inventory, task_id, subtype, sampling, task_rng)
    elif sampling["target_outcome"] != "valid":
        artifacts = build_negative_task(
            task_inventory, task_id, family, subtype, sampling, task_rng
        )
    elif family == "query":
        artifacts = build_query_task(
            task_inventory, task_id, subtype, sampling, structure, task_rng
        )
    elif family == "control":
        artifacts = build_control_task(
            task_inventory,
            task_id,
            subtype,
            sampling,
            structure,
            task_rng,
        )
    elif family == "goal":
        artifacts = build_goal_task(
            task_inventory,
            task_id,
            subtype,
            sampling,
            structure,
            task_rng,
        )
    else:
        raise TaskSeedError(
            "Aggregate tasks must merge already validated Q/C/G components"
        )

    validate_task_artifacts(world, artifacts)
    return artifacts


def _build_single_task_family(
    world: World,
    *,
    family: str,
    task_id: str,
    profile: dict[str, Any],
    rng: random.Random,
    inventory: TaskInventory,
    property_control: bool = False,
) -> tuple[tuple[TaskArtifacts, ...], dict[str, Any] | None]:
    """Build one sampled family and its optional workflow initial-state override."""
    if family == "workflow":
        artifact, world_init = build_workflow_task(inventory, task_id, profile, rng)
        return (artifact,), world_init
    # Preserve the sampling RNG sequence even when capability construction is used.
    subtype, sampling = sample_family(profile, family, rng)
    if family == "query" and subtype == "property.device" and sampling["target_outcome"] == "valid":
        reads = [tool for tool in inventory.operation_tools if tool["semantics"]["kind"] == "collection_read"]
        if reads and rng.randrange(len(reads) + len(inventory.property_values("object"))) < len(reads):
            rng.shuffle(reads)
            for tool in reads:
                try:
                    artifact = build_collection_query_task(inventory, task_id, sampling, tool, rng)
                    validate_task_artifacts(world, artifact)
                    return (artifact,), None
                except InventoryError:
                    continue
    if family == "control" and sampling["target_outcome"] == "valid" and inventory.operation_tools and not property_control:
        return (build_capability_task(inventory, task_id, profile, rng),), None
    return build_task_variants(
        world,
        task_id=task_id,
        constraints={
            "task_family": family,
            "task_subtype": subtype,
            "requirements": {"structure": deepcopy(profile["structure"])},
            "sampling": sampling,
        },
        rng=rng,
        inventory=inventory,
    ), None


def build_task_family(
    world: World, *, family: str, task_id: str, profile: dict[str, Any],
    rng: random.Random, inventory: TaskInventory,
) -> tuple[tuple[TaskArtifacts, ...], dict[str, Any] | None]:
    """Sample distinct Control/Goal tasks; reuse existing semantic variant builders."""
    count = profile.get("family_variants", {}).get(family, 1)
    if count == 1:
        return _build_single_task_family(world, family=family, task_id=task_id,
                                        profile=profile, rng=rng, inventory=inventory)
    variants, seen = [], set()
    for draw in range(count * 16):
        draw_id = f"{task_id}_draw{draw + 1:04d}"
        try:
            candidates, override = _build_single_task_family(
                world, family=family, task_id=draw_id, profile=profile,
                rng=random.Random(rng.getrandbits(64)), inventory=inventory,
                property_control=family == "control" and draw % 2 == 1,
            )
        except (InventoryError, TaskSeedError):
            continue
        if override is not None:
            raise TaskSeedError("Control/Goal variants must share the effective World")
        for artifact in candidates:
            sampling = artifact.seed["sampling"]
            identity = format_json({
                "subtype": artifact.seed["task_subtype"],
                "target": artifact.target, "memory": artifact.memory,
                "turns": artifact.reference_plan["turns"],
                "selection_method": sampling.get("target_selection_method"),
                "value_method": sampling.get("property_target_value_method"),
            }, sort_keys=True).replace(draw_id, "candidate")
            if identity in seen:
                continue
            seen.add(identity)
            sampling["variant_key"] = f"draw_{draw + 1:04d}__{sampling.get('variant_key', 'base')}"
            variants.append(artifact)
            if len(variants) == count:
                return tuple(variants), None
    raise TaskSeedError(f"could build only {len(variants)} distinct {family} variants; requested {count}")
