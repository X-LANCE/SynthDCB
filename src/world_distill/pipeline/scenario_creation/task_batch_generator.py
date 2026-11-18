"""Sample multiple task families and variants per effective World."""

from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import as_completed, ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import random
import re
from threading import Lock
import time
from typing import Any, Callable

from src.runtime import DomainRuntimeCache, World, WorldBlueprint
from src.utils import load_json, progress_bar, write_json
from src.world_distill.pipeline.models import (
    GeneratedTask,
    GenerationProvenance,
    TaskAuthoringInput,
    TaskGenerationInput,
    TaskGenerationOutput,
)

from .generation_records import GenerationRecords
from .task_builder import build_task_family
from .task_builders.aggregate import (
    component_paths,
    ComponentPaths,
    merge_task_artifacts,
)
from .task_common import (
    PreparedTask,
    rebind_task_artifacts,
    TaskArtifacts,
    TaskSeedError,
)
from .task_generator import generate_task, TaskAuthoringError
from .task_inventory import InventoryError, TaskInventory
from .task_sampler import (
    AGGREGATE_COMPONENTS,
    BASE_TASK_SUBTYPES,
    sample_family,
    validate_sampling_profile,
    weighted_choice,
)
from .world_initializer import derive_task_world_init


class TaskGenerationError(RuntimeError):
    """Task sampling could not finish within its bounded retries."""


@dataclass(frozen=True)
class _TaskJob:
    ordinal: int
    task_id: str
    task_family: str
    task_subtype: str
    random_seed: int
    sampling: dict[str, Any]


@dataclass(frozen=True)
class _SourceWorld:
    root: Path
    world_id: str
    blueprint: WorldBlueprint


@dataclass(frozen=True)
class _ComponentTask:
    record: dict[str, Any]
    artifacts: TaskArtifacts
    paths: ComponentPaths | None = None


@dataclass(frozen=True)
class _BuiltTask:
    job: _TaskJob
    artifacts: TaskArtifacts
    candidate_seed: int
    public_instruction: str = ""
    world_init: dict[str, Any] | None = None


@dataclass(frozen=True)
class _BatchResult:
    ordinal: int
    successes: tuple[dict[str, Any], ...]
    generated: tuple[GeneratedTask, ...]
    rejections: tuple[dict[str, Any], ...]
    provenances: tuple[GenerationProvenance, ...]
    errors: tuple[str, ...]


def _task_number(task_id: str) -> int:
    """Return the task number."""
    match = re.fullmatch(r"task_(\d{4,})", task_id)
    if match is None:
        raise TaskGenerationError(f"invalid task_id {task_id!r}")
    return int(match.group(1))


def _generated_task(record: dict[str, Any]) -> GeneratedTask:
    """Return the generated task."""
    return GeneratedTask(
        task_id=record["task_id"],
        task_family=record["task_family"],
        task_subtype=record["task_subtype"],
        sampling_profile_id=record["sampling_profile_id"],
        source_world_id=record["source_world_id"],
        effective_world_batch_id=record["effective_world_batch_id"],
        effective_world_root=Path(record["effective_world_root"]),
        task_root=Path(record["task_root"]),
        validation_metadata_path=Path(record["validation_metadata_path"]),
        instruction_style=record["instruction_style"],
        random_seed=record["random_seed"],
    )


def _task_artifact_path(task_root: Path, filename: str) -> Path:
    """Return a task artifact path."""
    return task_root / filename


def _reference_plan_from_trajectory(
    task_id: str,
    trajectory: dict[str, Any],
) -> dict[str, Any]:
    """Return the reference plan from trajectory."""
    turns: dict[str, list[dict[str, Any]]] = {}
    for record in trajectory["records"]:
        if record["kind"] != "tool_exchange":
            continue
        call = record["call"]
        turns.setdefault(call["turn_id"], []).append(
            deepcopy(call["command"])
        )
    return {"task_id": task_id, "turns": list(turns.values())}


def _component_groups(
    records: tuple[dict[str, Any], ...],
    *,
    world: World | None = None,
) -> dict[str, dict[str, tuple[_ComponentTask, ...]]]:
    """Return the component groups."""
    grouped: defaultdict[str, defaultdict[str, list[_ComponentTask]]] = (
        defaultdict(lambda: defaultdict(list))
    )
    write_cache: dict[str, ComponentPathSet] = {}
    initial_worlds: dict[str, dict[str, Any]] = {}
    for record in records:
        family = record["task_family"]
        if family not in BASE_TASK_SUBTYPES:
            continue
        task_root = Path(record["task_root"])
        initial_world = load_json(Path(record["effective_world_root"]) / "world_init.json")
        # Task bundles give the same effective World a task-specific identifier.
        initial_world.pop("world_id")
        batch_id = record["effective_world_batch_id"]
        if batch_id in initial_worlds and initial_worlds[batch_id] != initial_world:
            raise TaskGenerationError(f"component pool {batch_id} contains different initial Worlds")
        initial_worlds[batch_id] = initial_world
        metadata = load_json(
            Path(record["validation_metadata_path"])
        )["meta"]
        if metadata["expected_outcome"]["feasibility"] != "feasible":
            continue
        target = load_json(_task_artifact_path(task_root, "target.json"))
        if target.get("expected_memory_mutations", []):
            continue
        public_instruction = load_json(task_root / "task.json")["instruction"]
        memory_path = _task_artifact_path(task_root, "memory.json")
        artifacts = TaskArtifacts(
            seed=metadata,
            instruction_template=deepcopy(
                metadata["derived"].get(
                    "target_reference_templates", metadata["derived"].get("instruction_variants", [public_instruction])
                )
            ),
            target=target,
            reference_plan=_reference_plan_from_trajectory(
                record["task_id"],
                load_json(
                    _task_artifact_path(
                        task_root,
                        "reference_trajectory.json",
                    )
                ),
            ),
            memory=(
                load_json(memory_path) if memory_path.is_file() else None
            ),
        )
        action_group_id = metadata["derived"].get(
            "action_validation_reuse", {}
        ).get("group_id", record["task_id"])
        paths = None
        if world is not None:
            paths = component_paths(
                world,
                artifacts,
                validated_writes=write_cache.get(action_group_id),
            )
            write_cache.setdefault(action_group_id, paths[1])
        component = _ComponentTask(
            record=deepcopy(record),
            artifacts=artifacts,
            paths=paths,
        )
        grouped[record["effective_world_batch_id"]][family].append(component)
    return {
        batch_id: {
            family: tuple(sorted(items, key=lambda item: item.record["task_id"]))
            for family, items in families.items()
        }
        for batch_id, families in grouped.items()
    }


def _aggregate_candidates(
    job: _TaskJob,
    groups: dict[str, dict[str, tuple[_ComponentTask, ...]]],
) -> list[tuple[str, tuple[_ComponentTask, ...]]]:
    """Resolve the exact sampled IDs within their frozen World pool."""
    for batch_id, families in groups.items():
        by_id = {item.record["task_id"]: item for values in families.values() for item in values}
        if all(task_id in by_id for task_id in job.sampling["source_task_ids"]):
            return [(batch_id, tuple(by_id[task_id] for task_id in job.sampling["source_task_ids"]))]
    return []


def _rejection(
    job: _TaskJob,
    *,
    attempt: int,
    candidate_seed: int,
    source_world_id: str,
    batch_id: str,
    kind: str,
    reason: str,
    evidence_path: str | None = None,
    stage: str | None = None,
) -> dict[str, Any]:
    """Return the rejection."""
    result = {
        "rejection_id": f"{job.task_id}_{attempt:02d}",
        "task_id": job.task_id,
        "task_family": job.task_family,
        "task_subtype": job.task_subtype,
        "sampling": deepcopy(job.sampling),
        "attempt": attempt,
        "candidate_seed": candidate_seed,
        "source_world_id": source_world_id,
        "effective_world_batch_id": batch_id,
        "kind": kind,
        "reason": reason,
    }
    if evidence_path is not None:
        result["evidence_path"] = evidence_path
    if stage is not None:
        result["stage"] = stage
    return result


def _author_built_task(
    request: TaskGenerationInput,
    built: _BuiltTask,
    attempt: int,
    source: _SourceWorld,
    batch_id: str,
    world_init: dict[str, Any],
    world_blueprint: WorldBlueprint,
    tweaks: list[dict[str, Any]],
    tweak_count: int,
    inventory_snapshot: dict[str, Any],
    structure: dict[str, Any],
    runtime_cache: DomainRuntimeCache,
) -> _BatchResult:
    """Return the author built task."""
    job = built.job
    number = _task_number(job.task_id)
    authoring_run_id = (
        f"{request.generation_run_id[:36]}_{number:04d}_{attempt:02d}"
    )
    constraints = {
        "task_family": job.task_family,
        "task_subtype": job.task_subtype,
        "requirements": {"structure": deepcopy(structure)},
        "sampling": deepcopy(job.sampling),
    }
    authoring_request = TaskAuthoringInput(
        authoring_run_id=authoring_run_id,
        scenario_id=job.task_id,
        domain=request.domain,
        domain_path=request.domain_path,
        source_world_root=source.root,
        task_output_root=request.task_output_root,
        run_output_root=request.run_output_root,
        task_constraints=constraints,
        random_seed=built.candidate_seed,
        initial_tweak_count=tweak_count,
    )
    prepared_world_init = deepcopy(world_init)
    if built.world_init is not None:
        prepared_world_init = deepcopy(built.world_init)
        batch_id = f"{batch_id}_{job.task_id}_workflow"
        world_blueprint = runtime_cache.blueprint_from_world_init(request.world_output_root / "_workflow_inventory" / job.task_id, prepared_world_init)
    prepared_world_init["world_id"] = job.task_id
    prepared = PreparedTask(
        world_init=prepared_world_init,
        source_world_id=source.world_id,
        source_world_root=source.root,
        initial_tweaks=tuple(deepcopy(tweaks)),
        artifacts=built.artifacts,
        effective_world_batch_id=batch_id,
        inventory_snapshot=inventory_snapshot,
        public_instruction=built.public_instruction,
        world_blueprint=world_blueprint,
    )
    try:
        success = generate_task(
            authoring_request,
            runtime_cache=runtime_cache,
            prepared=prepared,
        )
    except TaskAuthoringError as error:
        return _BatchResult(
            ordinal=job.ordinal,
            successes=(),
            generated=(),
            rejections=(
                _rejection(
                    job,
                    attempt=attempt,
                    candidate_seed=built.candidate_seed,
                    source_world_id=source.world_id,
                    batch_id=batch_id,
                    kind="authoring_gate_failure",
                    reason=str(error),
                    evidence_path=str(error.failure_path),
                    stage=error.stage,
                ),
            ),
            provenances=(),
            errors=(),
        )

    record = deepcopy(success.success_record)
    if record["task_id"] != job.task_id:
        raise TaskGenerationError(
            "task authoring returned without a success record"
        )
    record["generation_run_id"] = request.generation_run_id
    return _BatchResult(
        ordinal=job.ordinal,
        successes=(record,),
        generated=(_generated_task(record),),
        rejections=(),
        provenances=(success.provenance,),
        errors=(),
    )


def _run_aggregate_job(
    request: TaskGenerationInput,
    job: _TaskJob,
    groups: dict[str, dict[str, tuple[_ComponentTask, ...]]],
    runtime_cache: DomainRuntimeCache,
) -> _BatchResult:
    """Merge already-authored base tasks and re-run deterministic gates."""
    candidates = _aggregate_candidates(job, groups)
    rejections: list[dict[str, Any]] = []
    if not candidates:
        return _BatchResult(
            ordinal=job.ordinal,
            successes=(),
            generated=(),
            rejections=(),
            provenances=(),
            errors=(
                f"no effective World has validated components for "
                f"aggregate.{job.task_subtype}",
            ),
        )

    attempt_count = min(request.max_task_attempts, len(candidates))
    for attempt, (batch_id, component_items) in enumerate(
        candidates[:attempt_count],
        start=1,
    ):
        candidate_seed = random.Random(
            f"{job.random_seed}:{attempt}:aggregate-merge"
        ).randrange(0, 2**63)
        components = list(component_items)
        source_ids = [item.record["task_id"] for item in components]
        source = components[0].record
        effective_world_root = Path(source["effective_world_root"])
        try:
            blueprint = runtime_cache.load_world_blueprint(
                effective_world_root
            )
            world = World(
                effective_world_root,
                runtime_cache=runtime_cache,
                blueprint=blueprint,
            )
            artifacts = merge_task_artifacts(
                world,
                task_id=job.task_id,
                subtype=job.task_subtype,
                parts=[item.artifacts for item in components],
                source_task_ids=source_ids,
                profile_id=job.sampling["profile_id"],
                validated_component_paths=(
                    [item.paths for item in components]
                    if all(item.paths is not None for item in components)
                    else None
                ),
            )
            artifacts.seed["sampling"].update(
                {
                    key: deepcopy(value)
                    for key, value in job.sampling.items()
                    if key
                    in {
                        "sample_id",
                        "world_sample_id",
                        "sample_round",
                        "variant_key",
                    }
                }
            )
            number = _task_number(job.task_id)
            authoring_run_id = (
                f"{request.generation_run_id[:36]}_{number:04d}_{attempt:02d}"
            )
            constraints = {
                "task_family": "aggregate",
                "task_subtype": job.task_subtype,
                "requirements": {},
                "sampling": deepcopy(artifacts.seed["sampling"]),
            }
            authoring_request = TaskAuthoringInput(
                authoring_run_id=authoring_run_id,
                scenario_id=job.task_id,
                domain=request.domain,
                domain_path=request.domain_path,
                source_world_root=Path(source["source_world_root"]),
                task_output_root=request.task_output_root,
                run_output_root=request.run_output_root,
                task_constraints=constraints,
                random_seed=candidate_seed,
                initial_tweak_count=len(source["initial_tweaks"]),
            )
            prepared = PreparedTask(
                world_init=load_json(effective_world_root / "world_init.json"),
                source_world_id=source["source_world_id"],
                source_world_root=Path(source["source_world_root"]),
                initial_tweaks=tuple(deepcopy(source["initial_tweaks"])),
                artifacts=artifacts,
                effective_world_batch_id=batch_id,
                inventory_snapshot=deepcopy(
                    components[0].artifacts.seed["derived"].get(
                        "batch_inventory", {}
                    )
                ),
                public_instruction=(
                    artifacts.instruction_template
                    if isinstance(artifacts.instruction_template, str)
                    else random.Random(
                        f"{candidate_seed}:aggregate-instruction"
                    ).choice(artifacts.instruction_template)
                ),
                world_blueprint=blueprint,
            )
            success = generate_task(
                authoring_request,
                runtime_cache=runtime_cache,
                prepared=prepared,
            )
            record = deepcopy(success.success_record)
            if record["task_id"] != job.task_id:
                raise TaskGenerationError(
                    "Aggregate authoring returned without a success record"
                )
            record["generation_run_id"] = request.generation_run_id
            return _BatchResult(
                ordinal=job.ordinal,
                successes=(record,),
                generated=(_generated_task(record),),
                rejections=tuple(rejections),
                provenances=(success.provenance,),
                errors=(),
            )
        except (
            InventoryError,
            TaskAuthoringError,
            TaskSeedError,
        ) as error:
            rejections.append(
                _rejection(
                    job,
                    attempt=attempt,
                    candidate_seed=candidate_seed,
                    source_world_id=source["source_world_id"],
                    batch_id=batch_id,
                    kind="aggregate_merge_failure",
                    reason=f"{type(error).__name__}: {error}",
                    evidence_path=(
                        str(error.failure_path)
                        if isinstance(error, TaskAuthoringError)
                        else None
                    ),
                    stage=(
                        error.stage
                        if isinstance(error, TaskAuthoringError)
                        else None
                    ),
                )
            )

    return _BatchResult(
        ordinal=job.ordinal,
        successes=(),
        generated=(),
        rejections=tuple(rejections),
        provenances=(),
        errors=(
            f"could not merge aggregate.{job.task_subtype} slot {job.task_id} "
            f"after {attempt_count} distinct attempts",
        ),
    )


@dataclass(frozen=True)
class _WorldSample:
    ordinal: int
    batch_id: str
    source: _SourceWorld
    world_init: dict[str, Any]
    tweaks: tuple[dict[str, Any], ...]
    world: World
    inventory: TaskInventory


@dataclass(frozen=True)
class _SampleJob:
    ordinal: int
    sample_id: str
    round_index: int
    world_sample: _WorldSample
    random_seed: int


@dataclass(frozen=True)
class _SampleResult:
    ordinal: int
    checkpoint: dict[str, Any] | None
    rejections: tuple[dict[str, Any], ...]
    provenances: tuple[GenerationProvenance, ...]
    errors: tuple[str, ...]


def _stable_seed(random_seed: int, *parts: Any) -> int:
    """Return the stable seed."""
    text = ":".join(
        ("dcb-unified-task", str(random_seed), *(str(part) for part in parts))
    )
    return random.Random(text).randrange(0, 2**63)


def _variant_task_id(sample_ordinal: int, slot: int) -> str:
    """Return the variant task ID."""
    if not 1 <= slot <= 999:
        raise ValueError("one unified sample supports at most 999 variants")
    return f"task_{(sample_ordinal - 1) * 1000 + slot:07d}"


def _validate_request(request: TaskGenerationInput) -> dict[str, Any]:
    """Validate the request."""
    if not request.world_roots:
        raise ValueError("task generation requires source Worlds")
    if type(request.world_samples) is not int or request.world_samples < 1:
        raise ValueError("world_samples must be positive")
    if type(request.samples_per_world) is not int or request.samples_per_world < 1:
        raise ValueError("samples_per_world must be positive")
    if request.world_sample_ordinals is not None:
        selected = request.world_sample_ordinals
        if (not selected or any(type(i) is not int or not 1 <= i <= request.world_samples for i in selected)
                or len(set(selected)) != len(selected)):
            raise ValueError("world_sample_ordinals must be distinct indices within world_samples")
    if request.max_workers < 1:
        raise ValueError("max_workers must be positive")
    if request.max_task_attempts < 1:
        raise ValueError("max_task_attempts must be positive")
    if 300 + request.max_task_attempts > 799:
        raise ValueError("max_task_attempts exceeds the Aggregate task ID range")
    if request.max_initial_tweaks < 1:
        raise ValueError("max_initial_tweaks must be positive")
    profile = validate_sampling_profile(request.sampling_profile)
    for ordinals in profile.get("family_world_ordinals", {}).values():
        if any(i > request.world_samples for i in ordinals):
            raise ValueError("family_world_ordinals indices must be within world_samples")
    return profile


def _load_sources(
    request: TaskGenerationInput,
    runtime_cache: DomainRuntimeCache,
) -> tuple[_SourceWorld, ...]:
    """Return the sources."""
    sources: list[_SourceWorld] = []
    for root in request.world_roots:
        blueprint = runtime_cache.load_world_blueprint(root.resolve())
        if blueprint.domain != request.domain:
            raise ValueError("source World Domain differs from task request")
        sources.append(_SourceWorld(blueprint.root, blueprint.world_id, blueprint))
    return tuple(sources)


def _prepare_world_samples(
    request: TaskGenerationInput,
    sources: tuple[_SourceWorld, ...],
    runtime_cache: DomainRuntimeCache,
    existing: tuple[dict[str, Any], ...] = (),
) -> tuple[_WorldSample, ...]:
    """Return the world samples."""
    source_order = list(sources)
    random.Random(f"{request.random_seed}:source-order").shuffle(source_order)
    samples: list[_WorldSample] = []
    published_worlds = {}
    for row in existing:
        if row['task_family'] in BASE_TASK_SUBTYPES:
            published_worlds.setdefault(row['effective_world_batch_id'], row)
    for ordinal in range(1, request.world_samples + 1):
        if request.world_sample_ordinals is not None and ordinal not in request.world_sample_ordinals:
            continue
        source = source_order[(ordinal - 1) % len(source_order)]
        batch_id = f"world_sample_{ordinal:04d}"
        published = published_worlds.get(batch_id)
        if published is not None:
            if (published['source_world_id'] != source.world_id
                or Path(published['source_world_root']).resolve() != source.root):
                raise TaskGenerationError(f'{batch_id} belongs to a different source World')
            # Published base tasks share one immutable initial World. Restore it
            # directly so recovery cannot resample already-published task state.
            world_init = load_json(Path(published['effective_world_root']) / 'world_init.json')
            world_init['world_id'] = batch_id
            tweaks = deepcopy(published['initial_tweaks'])
        else:
            rng = random.Random(_stable_seed(request.random_seed, batch_id, "tweak"))
            requested_tweaks = rng.randint(1, request.max_initial_tweaks)
            source_world = World(source.root, runtime_cache=runtime_cache, blueprint=source.blueprint)
            world_init, tweaks = derive_task_world_init(source_world, task_id=batch_id,
                rng=rng, tweak_count=requested_tweaks)
        if not tweaks:
            raise TaskGenerationError(
                f"source World {source.world_id} has no valid small perturbation"
            )
        world_init.setdefault("config", {}).setdefault("scene_metadata", {}).update(
            {
                "effective_world_batch_id": batch_id,
                "world_sample_ordinal": ordinal,
                "source_world_id": source.world_id,
            }
        )
        root = (request.world_output_root / "_sample_inventory" / batch_id).resolve()
        blueprint = runtime_cache.blueprint_from_world_init(root, world_init)
        world = World(root, runtime_cache=runtime_cache, blueprint=blueprint)
        samples.append(
            _WorldSample(
                ordinal=ordinal,
                batch_id=batch_id,
                source=source,
                world_init=world_init,
                tweaks=tuple(deepcopy(tweaks)),
                world=world,
                inventory=TaskInventory(world, goal_probe_max_minutes=request.sampling_profile.get("goal_probe_max_minutes", 240), goal_probe_max_plans=request.sampling_profile.get("goal_probe_max_plans")),
            )
        )
    return tuple(samples)


def _sample_jobs(
    request: TaskGenerationInput,
    worlds: tuple[_WorldSample, ...],
) -> tuple[_SampleJob, ...]:
    """Return the jobs."""
    jobs: list[_SampleJob] = []
    for world_sample in worlds:
        for round_index in range(1, request.samples_per_world + 1):
            ordinal = (world_sample.ordinal - 1) * request.samples_per_world + round_index
            sample_id = f"sample_{ordinal:06d}"
            jobs.append(
                _SampleJob(
                    ordinal=ordinal,
                    sample_id=sample_id,
                    round_index=round_index,
                    world_sample=world_sample,
                    random_seed=_stable_seed(request.random_seed, sample_id),
                )
            )
    return tuple(jobs)


def _run_config(
    request: TaskGenerationInput,
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Run the config."""
    return {
        **({"world_sample_ordinals": list(request.world_sample_ordinals)}
           if request.world_sample_ordinals is not None else {}),
        "version": 5,
        "generation_run_id": request.generation_run_id,
        "domain": request.domain,
        "source_world_roots": [str(path.resolve()) for path in request.world_roots],
        "world_samples": request.world_samples,
        "samples_per_world": request.samples_per_world,
        "random_seed": request.random_seed,
        "max_initial_tweaks": request.max_initial_tweaks,
        "max_task_attempts": request.max_task_attempts,
        "instruction_source": "rule_template",
        "sampling_profile": deepcopy(profile),
    }


def _ensure_run_config(path: Path, payload: dict[str, Any]) -> None:
    """Ensure the run config."""
    if path.is_file():
        if load_json(path) != payload:
            raise TaskGenerationError(
                "task generation run config differs from the existing checkpoint"
            )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, payload)


def _failure_row(
    sample: _SampleJob,
    *,
    family: str,
    subtype: str,
    attempt: int,
    kind: str,
    reason: str,
) -> dict[str, Any]:
    """Return the failure row."""
    slot = {"query": 1, "control": 101, "goal": 201, "workflow": 801}.get(family, 301)
    return {
        "rejection_id": f"{sample.sample_id}_{family}_{attempt:02d}",
        "task_id": _variant_task_id(sample.ordinal, slot),
        "task_family": family,
        "task_subtype": subtype,
        "sampling": {"sample_id": sample.sample_id},
        "attempt": attempt,
        "candidate_seed": _stable_seed(sample.random_seed, family, attempt),
        "source_world_id": sample.world_sample.source.world_id,
        "effective_world_batch_id": sample.world_sample.batch_id,
        "kind": kind,
        "reason": reason,
    }


def _build_family(
    request: TaskGenerationInput,
    profile: dict[str, Any],
    sample: _SampleJob,
    family: str,
    attempt: int,
) -> tuple[_BuiltTask, ...]:
    """Return the family."""
    profile = deepcopy(profile)
    stratum_seed = _stable_seed(sample.random_seed, family, "stratum")
    if attempt > 1:
        stratum_seed = _stable_seed(stratum_seed, attempt)
    stratum_rng = random.Random(stratum_seed)
    if family == "workflow":
        has_process = any(hasattr(device.instance, "PROCESS") for device in sample.world_sample.world._state.devices.values())
        subtype = weighted_choice({key: weight for key, weight in profile["workflow"]["subtype_weights"].items()
                                   if has_process or key == "environment_deadline"}, stratum_rng)
        outcome = "valid" if subtype in {"environment_deadline", "environment_before_process"} else weighted_choice(profile["workflow"]["outcome_weights"], stratum_rng)
        profile["workflow"]["subtype_weights"] = {subtype: 1}
        profile["workflow"]["outcome_weights"] = {outcome: 1}
    elif profile.get("family_variants", {}).get(family, 1) == 1:
        subtype, sampling = sample_family(profile, family, stratum_rng)
        profile["task_type_weights"] = {f"{family}.{subtype}": 1}
        profile["target_selection"][family]["outcome_weights"] = {sampling["target_outcome"]: 1}
        if "query_dependency" in sampling:
            profile["query_dependency_weights"] = {sampling["query_dependency"]: 1}
    rng = random.Random(_stable_seed(sample.random_seed, family, attempt))
    artifacts, workflow_init = build_task_family(
        sample.world_sample.world,
        family=family,
        task_id=f"{sample.sample_id}_{family}_{attempt:02d}",
        profile=profile,
        rng=rng,
        inventory=sample.world_sample.inventory,
    )
    first_slot = {"query": 1, "control": 101, "goal": 201, "workflow": 801}[family]
    built: list[_BuiltTask] = []
    for index, artifact in enumerate(artifacts):
        task_id = _variant_task_id(sample.ordinal, first_slot + index)
        rebound = rebind_task_artifacts(artifact, task_id)
        rebound.seed["sampling"].update(
            {
                "sample_id": sample.sample_id,
                "world_sample_id": sample.world_sample.batch_id,
                "sample_round": sample.round_index,
                "variant_key": rebound.seed["sampling"].get(
                    "variant_key", "base"
                ),
            }
        )
        task_type = rebound.seed["sampling"]["task_type"]
        candidate_seed = _stable_seed(
            request.random_seed, task_id, task_type, attempt
        )
        job = _TaskJob(
            ordinal=_task_number(task_id),
            task_id=task_id,
            task_family=rebound.seed["task_family"],
            task_subtype=rebound.seed["task_subtype"],
            random_seed=candidate_seed,
            sampling=deepcopy(rebound.seed["sampling"]),
        )
        built.append(
            _BuiltTask(
                job=job,
                artifacts=rebound,
                candidate_seed=candidate_seed,
                world_init=workflow_init,
                public_instruction=(
                    rebound.instruction_template
                    if isinstance(rebound.instruction_template, str)
                    else rebound.instruction_template[0]
                ),
            )
        )
    return tuple(built)


def _same_variant(record: dict[str, Any], built: _BuiltTask) -> bool:
    """Return whether a persisted record matches the generated variant."""
    actual = record["sampling"]
    expected = built.job.sampling
    return (
        record["task_family"] == built.job.task_family
        and record["task_subtype"] == built.job.task_subtype
        and record["sampling_profile_id"] == expected["profile_id"]
        and record["random_seed"] == built.candidate_seed
        and actual.get("sample_id") == expected.get("sample_id")
        and actual.get("world_sample_id") == expected.get("world_sample_id")
        and actual.get("variant_key") == expected.get("variant_key")
        and actual.get("task_type") == expected.get("task_type")
    )


def _author_family(
    request: TaskGenerationInput,
    profile: dict[str, Any],
    sample: _SampleJob,
    family: str,
    records: dict[str, dict[str, Any]],
    runtime_cache: DomainRuntimeCache,
    task_executor: ThreadPoolExecutor,
    publish: Callable[[tuple[dict[str, Any], ...]], None],
) -> tuple[
    tuple[GenerationProvenance, ...],
    tuple[dict[str, Any], ...],
    str | None,
]:
    """Return the author family."""
    existing = {
        task_id: record
        for task_id, record in records.items()
        if record["task_family"] == family
    }
    rejections: list[dict[str, Any]] = []
    provenances: list[GenerationProvenance] = []
    last_subtype = "unknown"
    for attempt in range(1, request.max_task_attempts + 1):
        try:
            built = _build_family(request, profile, sample, family, attempt)
            last_subtype = built[0].job.task_subtype
        except (InventoryError, TaskSeedError) as error:
            rejections.append(
                _failure_row(
                    sample,
                    family=family,
                    subtype=last_subtype,
                    attempt=attempt,
                    kind="rule_sampling_failure",
                    reason=f"{type(error).__name__}: {error}",
                )
            )
            continue

        expected = {item.job.task_id: item for item in built}
        if set(existing) - set(expected) or any(
            not _same_variant(record, expected[task_id])
            for task_id, record in existing.items()
            if task_id in expected
        ):
            continue
        missing = [item for item in built if item.job.task_id not in existing]
        futures = [
            task_executor.submit(
                _author_built_task,
                request,
                item,
                attempt,
                sample.world_sample.source,
                sample.world_sample.batch_id,
                sample.world_sample.world_init,
                sample.world_sample.world.blueprint,
                list(sample.world_sample.tweaks),
                len(sample.world_sample.tweaks),
                sample.world_sample.inventory.snapshot(),
                profile["structure"],
                runtime_cache,
            )
            for item in missing
        ]
        new_records: list[dict[str, Any]] = []
        failed = False
        for future in as_completed(futures):
            result = future.result()
            new_records.extend(result.successes)
            rejections.extend(result.rejections)
            provenances.extend(result.provenances)
            failed = failed or bool(result.errors) or not result.successes
        if failed or len(new_records) != len(missing):
            continue
        ordered = tuple(
            sorted(new_records, key=lambda row: _task_number(row["task_id"]))
        )
        publish(ordered)
        records.update((row["task_id"], row) for row in ordered)
        return tuple(provenances), tuple(rejections), None

    return tuple(provenances), tuple(rejections), (
        f"{sample.sample_id} could not produce a coherent {family} variant group "
        f"after {request.max_task_attempts} attempts (last subtype: {last_subtype})"
    )


def _author_aggregates(
    request: TaskGenerationInput,
    profile: dict[str, Any],
    sample: _SampleJob,
    records: dict[str, dict[str, Any]],
    runtime_cache: DomainRuntimeCache,
    task_executor: ThreadPoolExecutor,
    publish: Callable[[tuple[dict[str, Any], ...]], None],
    groups: dict[str, dict[str, tuple[_ComponentTask, ...]]],
) -> tuple[tuple[GenerationProvenance, ...], tuple[dict[str, Any], ...]]:
    """Return the author aggregates."""
    jobs: list[tuple[_TaskJob, dict[str, Any]]] = []
    rejections: list[dict[str, Any]] = []
    rng = random.Random(_stable_seed(request.random_seed, sample.sample_id, "aggregate-components"))
    bounds = profile["aggregate_component_count"]
    viable = [(batch_id, families) for batch_id, families in sorted(groups.items()) if sum(len(items) for items in families.values()) >= bounds["min"]]
    seen = set()
    for combination_index in range(request.max_task_attempts):
        if not viable:
            break
        batch_id, families = rng.choice(viable)
        available = [item for family in sorted(families) for item in families[family]]
        count = rng.randint(bounds["min"], min(bounds["max"], len(available)))
        components = []
        for _ in range(count):
            # Families are sampled before individual components; repeated
            # families remain possible and the category is derived afterwards.
            family = rng.choice(sorted({item.record["task_family"] for item in available}))
            component = rng.choice([item for item in available if item.record["task_family"] == family])
            components.append(component)
            available.remove(component)
        source_task_ids = [item.record["task_id"] for item in components]
        identity = (batch_id, *sorted(source_task_ids))
        if identity in seen:
            continue
        seen.add(identity)
        family_set = {item.record["task_family"] for item in components}
        subtype = next(key for key, values in AGGREGATE_COMPONENTS.items() if set(values) == family_set)
        task_id = _variant_task_id(sample.ordinal, 301 + combination_index)
        variant_key = f"combination_{combination_index + 1:02d}"
        sampling = {
            "profile_id": profile["profile_id"], "task_type": f"aggregate.{subtype}",
            "source_families": [item.record["task_family"] for item in components],
            "component_count": len(components), "source_task_ids": source_task_ids,
            "sample_id": sample.sample_id, "world_sample_id": sample.world_sample.batch_id,
            "sample_round": sample.round_index, "variant_key": variant_key,
        }
        existing = records.get(task_id)
        if existing is not None:
            if any(existing["sampling"].get(key) != value for key, value in sampling.items()):
                raise TaskGenerationError(f"aggregate record {task_id} differs from its frozen component selection")
            continue
        job = _TaskJob(_task_number(task_id), task_id, "aggregate", subtype, _stable_seed(request.random_seed, task_id, *source_task_ids), sampling)
        candidate_group = {batch_id: {family: tuple(item for item in components if item.record["task_family"] == family) for family in family_set}}
        jobs.append((job, candidate_group))

    futures = {
        task_executor.submit(
            _run_aggregate_job,
            request,
            job,
            candidate_group,
            runtime_cache,
        ): job
        for job, candidate_group in jobs
    }
    new_records: list[dict[str, Any]] = []
    provenances: list[GenerationProvenance] = []
    for future in as_completed(futures):
        job = futures[future]
        result = future.result()
        new_records.extend(result.successes)
        rejections.extend(result.rejections)
        provenances.extend(result.provenances)
        for error in result.errors:
            rejections.append(
                _failure_row(
                    sample,
                    family="aggregate",
                    subtype=job.task_subtype,
                    attempt=1,
                    kind="aggregate_unavailable",
                    reason=error,
                )
            )
    ordered = tuple(
        sorted(new_records, key=lambda row: _task_number(row["task_id"]))
    )
    publish(ordered)
    records.update((row["task_id"], row) for row in ordered)
    return tuple(provenances), tuple(rejections)


def _run_sample(
    request: TaskGenerationInput,
    profile: dict[str, Any],
    sample: _SampleJob,
    existing: tuple[dict[str, Any], ...],
    runtime_cache: DomainRuntimeCache,
    task_executor: ThreadPoolExecutor,
    publish: Callable[[tuple[dict[str, Any], ...]], None],
) -> _SampleResult:
    """Run the sample."""
    records = {row["task_id"]: deepcopy(row) for row in existing}
    rejections: list[dict[str, Any]] = []
    provenances: list[GenerationProvenance] = []
    errors: list[str] = []
    family_worlds = profile.get("family_world_ordinals", {})
    for family in ("query", "control", "goal"):
        if family in family_worlds and sample.world_sample.ordinal not in family_worlds[family]:
            continue
        if not any(weight > 0 and key.startswith(f"{family}.") for key, weight in profile["task_type_weights"].items()):
            continue
        family_provenance, family_rejections, error = _author_family(
            request,
            profile,
            sample,
            family,
            records,
            runtime_cache,
            task_executor,
            publish,
        )
        provenances.extend(family_provenance)
        rejections.extend(family_rejections)
        if error is not None:
            errors.append(error)
    if (("workflow" not in family_worlds or sample.world_sample.ordinal in family_worlds["workflow"])
            and (profile["workflow"]["subtype_weights"].get("environment_deadline", 0) > 0
                 or any(hasattr(device.instance, "PROCESS") for device in sample.world_sample.world._state.devices.values()))):
        provenance, rejected, error = _author_family(request, profile, sample, "workflow", records, runtime_cache, task_executor, publish)
        provenances.extend(provenance)
        rejections.extend(rejected)
        if error is not None:
            rejections.append(_failure_row(sample, family="workflow", subtype="unavailable", attempt=request.max_task_attempts, kind="workflow_unavailable", reason=error))
    sample_records = [
        row
        for row in records.values()
        if row["sampling"].get("sample_id") == sample.sample_id
    ]
    counts = Counter(row["task_family"] for row in sample_records)
    checkpoint = None
    if not errors:
        checkpoint = {
            "sample_id": sample.sample_id,
            "sample_ordinal": sample.ordinal,
            "world_sample_id": sample.world_sample.batch_id,
            "source_world_id": sample.world_sample.source.world_id,
            "sample_round": sample.round_index,
            "task_ids": sorted(
                (row["task_id"] for row in sample_records), key=_task_number
            ),
            "counts": {
                family: counts.get(family, 0)
                for family in ("query", "control", "goal", "workflow", "aggregate")
            },
            "completed": True,
        }
    return _SampleResult(
        ordinal=sample.ordinal,
        checkpoint=checkpoint,
        rejections=tuple(rejections),
        provenances=tuple(provenances),
        errors=tuple(errors),
    )


def generate_tasks(
    request: TaskGenerationInput,
    *,
    show_progress: bool = False,
    runtime_cache: DomainRuntimeCache | None = None,
) -> TaskGenerationOutput:
    """Generate a task pool from n*m unified sampling rounds."""
    started = time.perf_counter()
    profile = _validate_request(request)
    cache = runtime_cache or DomainRuntimeCache(request.domain, request.domain_path)
    cache.assert_domain(request.domain)
    if cache.domain_path != request.domain_path.resolve():
        raise ValueError("domain_path differs from the runtime cache")
    run_root = (
        request.run_output_root / request.generation_run_id / "task_generation"
    ).resolve()
    config_path = run_root / "run_config.json"
    task_list_path = run_root / "task_list.jsonl"
    sample_list_path = run_root / "sample_list.jsonl"
    rejection_path = run_root / "failures.jsonl"
    _ensure_run_config(config_path, _run_config(request, profile))

    task_records = GenerationRecords(
        task_list_path,
        id_field="task_id",
        contract=cache.contract,
        schema_id="urn:dcb:v2:schema:task-list-record",
    )
    sample_records = GenerationRecords(sample_list_path, id_field="sample_id")
    existing = task_records.records
    for record in existing:
        if record["domain"] != request.domain:
            raise TaskGenerationError("task records contain another Domain")
        _task_number(record["task_id"])
        if not record["sampling"].get("sample_id"):
            raise TaskGenerationError(
                "task record is missing sampling.sample_id"
            )

    sources = _load_sources(request, cache)
    worlds = _prepare_world_samples(request, sources, cache, existing)
    prepared_at = time.perf_counter()
    jobs = _sample_jobs(request, worlds)
    expected_sample_ids = {job.sample_id for job in jobs}
    unknown_task_samples = {
        row["sampling"]["sample_id"] for row in existing
    } - expected_sample_ids
    if unknown_task_samples:
        raise TaskGenerationError(
            "task records are incompatible with this n*m request: "
            + ", ".join(sorted(unknown_task_samples))
        )
    checkpoints = {row["sample_id"]: row for row in sample_records.records}
    unknown = set(checkpoints) - expected_sample_ids
    if unknown:
        raise TaskGenerationError(
            "sample records are incompatible with this n*m request: "
            + ", ".join(sorted(unknown))
        )
    existing_ids = {row["task_id"] for row in existing}
    for checkpoint in checkpoints.values():
        missing = set(checkpoint["task_ids"]) - existing_ids
        if missing:
            raise TaskGenerationError(
                f"completed {checkpoint['sample_id']} is missing task rows: "
                + ", ".join(sorted(missing))
            )

    pending = [job for job in jobs if job.sample_id not in checkpoints]
    existing_by_sample = {
        job.sample_id: tuple(
            row
            for row in existing
            if row["sampling"].get("sample_id") == job.sample_id
        )
        for job in pending
    }
    counts = Counter(row["task_family"] for row in existing)
    results: list[_SampleResult] = []
    progress_lock = Lock()
    sample_workers = min(len(pending), request.max_workers) if pending else 0

    with progress_bar(
        total=len(jobs),
        initial=len(checkpoints),
        description=(
            f"Unified Q/C/G/W/A sampling ({request.max_workers} task workers, "
            f"{sample_workers} sample coordinators)"
        ),
        unit="sample",
        enabled=show_progress,
    ) as progress:
        progress.set_postfix(
            Q=counts["query"],
            C=counts["control"],
            G=counts["goal"],
            W=counts["workflow"],
            A=counts["aggregate"],
            refresh=show_progress,
        )

        def publish(rows: tuple[dict[str, Any], ...]) -> None:
            """Publish the completed task family."""
            if not rows:
                return
            new_rows = tuple(
                row for row in rows if task_records.get(row["task_id"]) is None
            )
            task_records.append_many(rows)
            with progress_lock:
                counts.update(row["task_family"] for row in new_rows)
                progress.set_postfix(
                    Q=counts["query"],
                    C=counts["control"],
                    G=counts["goal"],
                    W=counts["workflow"],
                    A=counts["aggregate"],
                    refresh=show_progress,
                )

        if pending:
            with ThreadPoolExecutor(
                max_workers=request.max_workers
            ) as task_executor, ThreadPoolExecutor(
                max_workers=sample_workers
            ) as sample_executor:
                futures = [
                    sample_executor.submit(
                        _run_sample,
                        request,
                        profile,
                        job,
                        existing_by_sample[job.sample_id],
                        cache,
                        task_executor,
                        publish,
                    )
                    for job in pending
                ]
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    if result.checkpoint is not None:
                        sample_records.append(result.checkpoint)
                    with progress_lock:
                        progress.update(1)

        base_finished_at = time.perf_counter()
        if not any(result.errors for result in results):
            frozen_records = tuple(row for row in task_records.records if row["task_family"] in BASE_TASK_SUBTYPES)
            pool_path = run_root / "component_pool.json"
            pool = {
                "generation_run_id": request.generation_run_id,
                "worlds": {world.batch_id: sorted(row["task_id"] for row in frozen_records if row["effective_world_batch_id"] == world.batch_id) for world in worlds},
            }
            _ensure_run_config(pool_path, pool)
            aggregate_records = GenerationRecords(run_root / "aggregate_sample_list.jsonl", id_field="sample_id")
            current_ids = {row["task_id"] for row in task_records.records}
            for checkpoint in aggregate_records.records:
                if checkpoint["sample_id"] not in expected_sample_ids:
                    raise TaskGenerationError("aggregate checkpoint contains an unknown sample")
                missing = set(checkpoint["task_ids"]) - current_ids
                if missing:
                    raise TaskGenerationError("completed aggregate sample is missing task rows: " + ", ".join(sorted(missing)))
            pending_aggregate_worlds = {
                job.world_sample.batch_id for job in jobs
                if aggregate_records.get(job.sample_id) is None
            }
            groups_by_world = {
                world.batch_id: _component_groups(tuple(row for row in frozen_records if row["effective_world_batch_id"] == world.batch_id), world=world.world)
                for world in worlds
                if world.batch_id in pending_aggregate_worlds
            }
            records_by_sample = defaultdict(dict)
            for row in task_records.records:
                records_by_sample[row["sampling"]["sample_id"]][row["task_id"]] = row
            with ThreadPoolExecutor(max_workers=request.max_workers) as task_executor:
                for job in jobs:
                    if aggregate_records.get(job.sample_id) is not None:
                        continue
                    records = records_by_sample[job.sample_id]
                    provenance, rejections = _author_aggregates(request, profile, job, records, cache, task_executor, publish, groups_by_world[job.world_sample.batch_id])
                    aggregate_records.append({"sample_id": job.sample_id, "task_ids": sorted(row["task_id"] for row in records.values() if row["task_family"] == "aggregate"), "completed": True})
                    results.append(_SampleResult(job.ordinal, None, rejections, provenance, ()))

    rejection_records = GenerationRecords(rejection_path, id_field="rejection_id")
    rejected = [
        deepcopy(row)
        for result in sorted(results, key=lambda item: item.ordinal)
        for row in result.rejections
    ]
    offset = len(rejection_records.records)
    for index, row in enumerate(rejected, start=offset + 1):
        row["rejection_id"] = f"failure_{index:08d}"
    rejection_records.append_many(rejected)
    finished_at = time.perf_counter()
    new_task_count = len(task_records.records) - len(existing)
    performance = {
        "stage_seconds": {
            "prepare_worlds": prepared_at - started,
            "base_tasks": base_finished_at - prepared_at,
            "freeze_pool_and_aggregate": finished_at - base_finished_at,
        },
        "total_seconds": finished_at - started,
        "successful_tasks": len(task_records.records),
        "new_tasks": new_task_count,
        "resumed_tasks": len(existing),
        "tasks_per_second": new_task_count / (finished_at - started),
        "rejection_reasons": dict(Counter(row["reason"] for row in rejection_records.records)),
        "inventories": [world.inventory.snapshot() for world in worlds],
    }
    write_json(run_root / "performance.json", performance)
    errors = [error for result in results for error in result.errors]
    if errors:
        raise TaskGenerationError(errors[0])

    generated = sorted(
        (_generated_task(row) for row in task_records.records),
        key=lambda item: _task_number(item.task_id),
    )
    current_provenance = [
        provenance
        for result in results
        for provenance in result.provenances
    ]
    usage: dict[str, int] = {}
    response_models: set[str] = set()
    for provenance in current_provenance:
        for key, value in provenance.usage.items():
            usage[key] = usage.get(key, 0) + int(value)
        response_models.update(provenance.response_models)
    return TaskGenerationOutput(
        generation_run_id=request.generation_run_id,
        domain=request.domain,
        tasks=tuple(generated),
        task_list_path=task_list_path,
        rejection_records_path=rejection_path,
        provenance=GenerationProvenance(
            stage="task_generation",
            artifact_paths=tuple(
                [config_path, task_list_path, sample_list_path, rejection_path]
                + [task.validation_metadata_path for task in generated]
            ),
            model_scenario=None,
            requested_model=None,
            usage=usage,
            attempts=sum(item.attempts for item in current_provenance),
            validated=True,
            response_models=tuple(sorted(response_models)),
            attempt_records_path=run_root,
            failure_records_path=rejection_path,
        ),
        resumed=bool(existing or checkpoints),
    )
