"""Explicit inputs, outputs, provenance, and status for every pipeline stage."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Callable, Mapping


JsonObject = dict[str, Any]


def as_jsonable(value: Any) -> Any:
    """Convert pipeline values to deterministic JSON-compatible objects."""
    if is_dataclass(value):
        return as_jsonable(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {
            str(key): as_jsonable(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [as_jsonable(item) for item in value]
    return value


@dataclass(frozen=True)
class StageProvenance:
    stage: str
    artifact_paths: tuple[Path, ...] = ()
    model_scenario: str | None = None
    requested_model: str | None = None
    usage: JsonObject = field(default_factory=dict)
    attempts: int = 1
    errors: tuple[str, ...] = ()
    validated: bool = False
    response_models: tuple[str, ...] = ()
    attempt_records_path: Path | None = None
    failure_records_path: Path | None = None


@dataclass(frozen=True)
class GenerationProvenance:
    """Hash-free provenance for scenario, world, and task generation."""

    stage: str
    artifact_paths: tuple[Path, ...] = ()
    model_scenario: str | None = None
    requested_model: str | None = None
    usage: JsonObject = field(default_factory=dict)
    attempts: int = 0
    errors: tuple[str, ...] = ()
    validated: bool = False
    response_models: tuple[str, ...] = ()
    attempt_records_path: Path | None = None
    failure_records_path: Path | None = None


@dataclass(frozen=True)
class ListCreationInput:
    domain: str
    description: str
    existing_types: JsonObject
    external_knowledge: str = ""
    use_rag: bool = True
    coverage_requirements: tuple[str, ...] = ()
    expand_with_llm: bool = False
    model_scenario: str = "generate"
    model: str | None = None
    max_object_types: int | None = None
    max_generation_attempts: int = 1
    max_iterations: int = 1
    review_with_llm: bool = False
    review_model_scenario: str = "judge"
    review_model: str | None = None
    review_max_attempts_per_sample: int = 3
    review_max_workers: int = 1


@dataclass(frozen=True)
class ListCreationOutput:
    domain: str
    object_types: JsonObject
    coverage_report: JsonObject
    provenance: StageProvenance


@dataclass(frozen=True)
class ModelCreationInput:
    domain: str
    object_types: JsonObject
    output_root: Path
    property_catalog: Path | None = None
    generate_with_llm: bool = False
    use_rag: bool = True
    run_tests: bool = True
    max_workers: int = 4
    model_scenario: str = "code"
    model: str | None = None
    generation_run_id: str | None = None
    run_root: Path | None = None
    max_generation_attempts: int = 3
    max_repair_rounds: int = 1
    sandbox_limits: JsonObject = field(default_factory=dict)
    required_contracts: JsonObject = field(default_factory=dict)


@dataclass(frozen=True)
class ModelArtifact:
    class_name: str
    implementation_path: Path
    test_path: Path | None = None
    specification_path: Path | None = None


@dataclass(frozen=True)
class ModelCreationOutput:
    domain: str
    domain_path: Path
    artifacts: tuple[ModelArtifact, ...]
    environment_metadata_path: Path
    model_metadata_path: Path
    validation_report: JsonObject
    provenance: StageProvenance


@dataclass(frozen=True)
class GeneratedWorld:
    """One validated reusable world produced by the world stage."""

    world_id: str
    world_root: Path
    world_init_path: Path
    resolved_world_path: Path
    random_seed: int
    space_count: int
    device_count: int


@dataclass(frozen=True)
class WorldGenerationInput:
    """Deterministic random-world generation request."""

    generation_run_id: str
    domain: str
    domain_path: Path
    world_output_root: Path
    run_output_root: Path
    world_count: int
    random_seed: int
    max_workers: int = 1
    world_id_prefix: str = "world"
    min_devices_per_space: int = 1
    max_devices_per_space: int = 3
    template_id: str | None = None


@dataclass(frozen=True)
class WorldGenerationOutput:
    """Validated reusable world pool and its success records."""

    generation_run_id: str
    domain: str
    worlds: tuple[GeneratedWorld, ...]
    world_list_path: Path
    provenance: GenerationProvenance
    resumed: bool = False


@dataclass(frozen=True)
class TaskAuthoringInput:
    authoring_run_id: str
    scenario_id: str
    domain: str
    domain_path: Path
    source_world_root: Path
    task_output_root: Path
    run_output_root: Path
    task_constraints: JsonObject
    random_seed: int
    initial_tweak_count: int = 0


@dataclass(frozen=True)
class TaskAuthoringOutput:
    authoring_run_id: str
    scenario_id: str
    world_root: Path
    task_root: Path
    validation_metadata_path: Path
    validation_report: JsonObject
    task_list_path: Path
    success_record: JsonObject
    provenance: GenerationProvenance
    resumed: bool = False


@dataclass(frozen=True)
class GeneratedTask:
    """One validated task plus the effective world used for evaluation."""

    task_id: str
    task_family: str
    task_subtype: str
    sampling_profile_id: str
    source_world_id: str
    effective_world_batch_id: str
    effective_world_root: Path
    task_root: Path
    validation_metadata_path: Path
    instruction_style: str
    random_seed: int


@dataclass(frozen=True)
class TaskGenerationInput:
    """Task-pool request over one or more already validated worlds."""

    generation_run_id: str
    domain: str
    domain_path: Path
    world_roots: tuple[Path, ...]
    world_output_root: Path
    task_output_root: Path
    run_output_root: Path
    sampling_profile: JsonObject
    random_seed: int
    world_samples: int = 10
    samples_per_world: int = 1
    max_workers: int = 1
    max_initial_tweaks: int = 2
    max_task_attempts: int = 8
    world_sample_ordinals: tuple[int, ...] | None = None


@dataclass(frozen=True)
class TaskGenerationOutput:
    generation_run_id: str
    domain: str
    tasks: tuple[GeneratedTask, ...]
    task_list_path: Path
    rejection_records_path: Path
    provenance: GenerationProvenance
    resumed: bool = False


@dataclass(frozen=True)
class ScenarioGenerationRequest:
    """Two-stage production request: reusable worlds, then tasks."""

    world_generation: WorldGenerationInput | None = None
    task_generation: TaskGenerationInput | None = None
    task_generation_factory: (
        Callable[[WorldGenerationOutput], TaskGenerationInput] | None
    ) = None


@dataclass(frozen=True)
class ScenarioGenerationOutput:
    world_generation: WorldGenerationOutput | None
    task_generation: TaskGenerationOutput | None
    report: JsonObject


@dataclass(frozen=True)
class PipelineRequest:
    list_creation: ListCreationInput | None = None
    model_creation_factory: (
        Callable[[ListCreationOutput], ModelCreationInput] | None
    ) = None
    checkpoint_root: Path | None = None
    resume: bool = True


@dataclass(frozen=True)
class PipelineResult:
    list_creation: ListCreationOutput | None
    model_creation: ModelCreationOutput | None
    report: JsonObject
