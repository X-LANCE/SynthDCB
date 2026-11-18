"""Generate reusable Worlds and then task bundles."""

from __future__ import annotations

from src.runtime import DomainRuntimeCache
from src.world_distill.pipeline.models import (
    ScenarioGenerationOutput,
    ScenarioGenerationRequest,
)

from .task_batch_generator import generate_tasks
from .world_generator import generate_worlds


def generate_scenarios(
    request: ScenarioGenerationRequest,
    *,
    show_progress: bool = False,
) -> ScenarioGenerationOutput:
    """Run either stage independently or execute the two-stage DAG."""
    if (
        request.task_generation is not None
        and request.task_generation_factory is not None
    ):
        raise ValueError(
            "provide task_generation or task_generation_factory, not both"
        )
    stage_inputs = tuple(
        item
        for item in (request.world_generation, request.task_generation)
        if item is not None
    )
    if not stage_inputs:
        raise ValueError("scenario generation request has no stages")
    domains = {item.domain for item in stage_inputs}
    domain_roots = {item.domain_path.resolve() for item in stage_inputs}
    if len(domains) != 1 or len(domain_roots) != 1:
        raise ValueError("scenario stages must use one exact Domain")
    runtime_cache = DomainRuntimeCache(
        next(iter(domains)),
        next(iter(domain_roots)),
    )
    world_output = (
        generate_worlds(
            request.world_generation,
            show_progress=show_progress,
            runtime_cache=runtime_cache,
        )
        if request.world_generation is not None
        else None
    )
    task_input = request.task_generation
    if request.task_generation_factory is not None:
        if world_output is None:
            raise ValueError(
                "task_generation_factory requires world_generation output"
            )
        task_input = request.task_generation_factory(world_output)
    task_output = (
        generate_tasks(
            task_input,
            show_progress=show_progress,
            runtime_cache=runtime_cache,
        )
        if task_input is not None
        else None
    )
    return ScenarioGenerationOutput(
        world_generation=world_output,
        task_generation=task_output,
        report={
            "status": "PASS",
            "stages": {
                "world_generation": (
                    None
                    if world_output is None
                    else {
                        "status": "PASS",
                        "count": len(world_output.worlds),
                        "world_list": str(world_output.world_list_path),
                        "resumed": world_output.resumed,
                    }
                ),
                "task_generation": (
                    None
                    if task_output is None
                    else {
                        "status": "PASS",
                        "count": len(task_output.tasks),
                        "task_list": str(task_output.task_list_path),
                        "rejection_records": str(
                            task_output.rejection_records_path
                        ),
                        "resumed": task_output.resumed,
                    }
                ),
            },
        },
    )
