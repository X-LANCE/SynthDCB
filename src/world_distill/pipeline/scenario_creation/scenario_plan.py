"""Load scenario generation plans and construct stage requests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.contracts import ContractPackage, load_json
from src.world_distill.pipeline.models import (
    ScenarioGenerationRequest,
    TaskGenerationInput,
    WorldGenerationInput,
)

from .generation_records import GenerationRecords
from .task_sampler import validate_sampling_profile


def _path(plan_root: Path, value: str) -> Path:
    """Return the path."""
    path = Path(value)
    return (path if path.is_absolute() else plan_root / path).resolve()


def _world_input(
    plan: dict[str, Any],
    plan_root: Path,
    max_workers: int | None,
) -> WorldGenerationInput:
    """Return the world input."""
    worlds = plan["worlds"]
    return WorldGenerationInput(
        generation_run_id=plan["generation_run_id"],
        domain=plan["domain"],
        domain_path=_path(plan_root, plan["domain_path"]),
        world_output_root=_path(plan_root, plan["world_output_root"]),
        run_output_root=_path(plan_root, plan["run_output_root"]),
        world_count=int(worlds["count"]),
        random_seed=int(plan["random_seed"]),
        max_workers=int(
            worlds.get("max_workers", 1)
            if max_workers is None
            else max_workers
        ),
        world_id_prefix=worlds.get("id_prefix", "world"),
        min_devices_per_space=int(worlds["min_devices_per_space"]),
        max_devices_per_space=int(worlds["max_devices_per_space"]),
        template_id=worlds.get("template_id"),
    )


def _task_input(
    plan: dict[str, Any],
    plan_root: Path,
    world_roots: tuple[Path, ...],
    max_workers: int | None,
) -> TaskGenerationInput:
    """Return the task input."""
    tasks = plan["tasks"]
    sampling_profile = validate_sampling_profile(
        load_json(_path(plan_root, tasks["sampling_profile"]))
    )
    task_output_root = _path(plan_root, plan["task_output_root"])
    return TaskGenerationInput(
        generation_run_id=plan["generation_run_id"],
        domain=plan["domain"],
        domain_path=_path(plan_root, plan["domain_path"]),
        world_roots=world_roots,
        world_output_root=task_output_root,
        task_output_root=task_output_root,
        run_output_root=_path(plan_root, plan["run_output_root"]),
        sampling_profile=sampling_profile,
        random_seed=int(plan["random_seed"]),
        world_samples=int(tasks.get("world_samples", 10)),
        samples_per_world=int(tasks["samples_per_world"]),
        max_workers=int(
            tasks.get("max_workers", 1)
            if max_workers is None
            else max_workers
        ),
        max_initial_tweaks=int(tasks.get("max_initial_tweaks", 2)),
        max_task_attempts=int(tasks.get("max_task_attempts", 8)),
        world_sample_ordinals=(tuple(tasks["world_sample_ordinals"])
                               if "world_sample_ordinals" in tasks else None),
    )


def _world_list_roots(
    plan: dict[str, Any],
    plan_root: Path,
    contract: ContractPackage,
) -> tuple[Path, ...]:
    """Return the world list roots."""
    tasks = plan["tasks"]
    if "source_world_list" in tasks:
        path = _path(plan_root, tasks["source_world_list"])
    else:
        path = (
            _path(plan_root, plan["run_output_root"])
            / plan["generation_run_id"]
            / "world_generation"
            / "world_list.jsonl"
        )
    world_records = GenerationRecords(
        path,
        id_field="world_id",
        contract=contract,
        schema_id="urn:dcb:v2:schema:world-list-record",
    )
    return tuple(
        Path(item["world_root"]).resolve() for item in world_records.records
    )


def load_scenario_plan(
    plan_path: Path,
    *,
    stage: str,
    max_workers: int | None = None,
) -> ScenarioGenerationRequest:
    """Build a production request for all, worlds-only, or tasks-only."""
    path = plan_path.resolve()
    plan = load_json(path)
    contract = ContractPackage()
    contract.validate_schema(
        plan,
        "urn:dcb:v2:schema:scenario-generation-plan",
    )
    plan_root = path.parent
    if stage == "worlds":
        return ScenarioGenerationRequest(
            world_generation=_world_input(plan, plan_root, max_workers)
        )
    if stage == "tasks":
        return ScenarioGenerationRequest(
            task_generation=_task_input(
                plan,
                plan_root,
                _world_list_roots(plan, plan_root, contract),
                max_workers,
            )
        )
    if stage != "all":
        raise ValueError(f"unknown generation stage {stage!r}")
    return ScenarioGenerationRequest(
        world_generation=_world_input(plan, plan_root, max_workers),
        task_generation_factory=lambda output: _task_input(
            plan,
            plan_root,
            tuple(item.world_root for item in output.worlds),
            max_workers,
        ),
    )
