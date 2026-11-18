"""Top-level orchestration across list and model generation stages."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .checkpoint import CheckpointStore
from .list_creation import run_list_creation
from .model_creation import run_model_creation
from .models import (
    ListCreationOutput,
    ModelArtifact,
    ModelCreationOutput,
    PipelineRequest,
    PipelineResult,
    StageProvenance,
)
from .report import build_pipeline_report


def _provenance(payload: dict[str, Any]) -> StageProvenance:
    """Return the provenance."""
    return StageProvenance(
        stage=payload["stage"],
        artifact_paths=tuple(
            Path(path) for path in payload.get("artifact_paths", [])
        ),
        model_scenario=payload.get("model_scenario"),
        requested_model=payload.get("requested_model"),
        usage=payload.get("usage", {}),
        attempts=int(payload.get("attempts", 1)),
        errors=tuple(payload.get("errors", [])),
        validated=bool(payload.get("validated")),
        response_models=tuple(payload.get("response_models", [])),
        attempt_records_path=(
            Path(payload["attempt_records_path"])
            if payload.get("attempt_records_path")
            else None
        ),
        failure_records_path=(
            Path(payload["failure_records_path"])
            if payload.get("failure_records_path")
            else None
        ),
    )


def _list_output(payload: dict[str, Any]) -> ListCreationOutput:
    """Return the output."""
    return ListCreationOutput(
        domain=payload["domain"],
        object_types=payload["object_types"],
        coverage_report=payload["coverage_report"],
        provenance=_provenance(payload["provenance"]),
    )


def _model_output(payload: dict[str, Any]) -> ModelCreationOutput:
    """Return the model output."""
    return ModelCreationOutput(
        domain=payload["domain"],
        domain_path=Path(payload["domain_path"]),
        artifacts=tuple(
            ModelArtifact(
                class_name=item["class_name"],
                implementation_path=Path(
                    item["implementation_path"]
                ),
                test_path=(
                    Path(item["test_path"])
                    if item.get("test_path")
                    else None
                ),
                specification_path=(
                    Path(item["specification_path"])
                    if item.get("specification_path")
                    else None
                ),
            )
            for item in payload["artifacts"]
        ),
        model_metadata_path=Path(payload["model_metadata_path"]),
        environment_metadata_path=Path(
            payload["environment_metadata_path"]
        ),
        validation_report=payload["validation_report"],
        provenance=_provenance(payload["provenance"]),
    )


def run_pipeline(
    request: PipelineRequest,
    *,
    list_attempt_sink: Callable[[dict[str, Any]], None] | None = None,
    list_review_attempt_sink: Callable[[dict[str, Any]], None] | None = None,
    list_iteration_sink: Callable[[dict[str, Any]], None] | None = None,
) -> PipelineResult:
    """Run configured stages and resume only validated matching checkpoints."""
    checkpoint = (
        CheckpointStore(request.checkpoint_root)
        if request.checkpoint_root is not None
        else None
    )
    list_output = None
    model_output = None

    if request.list_creation is not None:
        if checkpoint is not None and request.resume:
            list_output = checkpoint.load(
                "list_creation",
                request.list_creation,
                _list_output,
            )
        if list_output is None:
            def record_list_iteration(report: dict[str, Any]) -> None:
                iteration_index = int(report["iteration_index"])
                iteration_stage = (
                    f"list_creation.iteration_{iteration_index:03d}"
                )
                if checkpoint is not None:
                    checkpoint.save(
                        iteration_stage,
                        report["input"],
                        ListCreationOutput(
                            domain=request.list_creation.domain,
                            object_types=report["object_types"],
                            coverage_report={
                                key: value
                                for key, value in report.items()
                                if key not in {"input", "object_types"}
                            },
                            provenance=StageProvenance(
                                stage=iteration_stage,
                                model_scenario=(
                                    request.list_creation.model_scenario
                                ),
                                requested_model=request.list_creation.model,
                                attempts=int(report["attempt_count"]),
                                validated=True,
                            ),
                        ),
                        validated=True,
                    )
                if list_iteration_sink is not None:
                    list_iteration_sink(report)

            list_output = run_list_creation(
                request.list_creation,
                attempt_sink=list_attempt_sink,
                review_attempt_sink=list_review_attempt_sink,
                iteration_sink=record_list_iteration,
            )
            if checkpoint is not None:
                checkpoint.save(
                    "list_creation",
                    request.list_creation,
                    list_output,
                    validated=list_output.provenance.validated,
                )

    if request.model_creation_factory is not None:
        if list_output is None:
            raise ValueError(
                "model_creation_factory requires list_creation output"
            )
        model_input = request.model_creation_factory(list_output)
        if checkpoint is not None and request.resume:
            model_output = checkpoint.load(
                "model_creation",
                model_input,
                _model_output,
            )
        if model_output is None:
            model_output = run_model_creation(model_input)
            if checkpoint is not None:
                checkpoint.save(
                    "model_creation",
                    model_input,
                    model_output,
                    validated=model_output.provenance.validated,
                )

    report = build_pipeline_report(
        (list_output, model_output)
    )
    return PipelineResult(
        list_creation=list_output,
        model_creation=model_output,
        report=report,
    )
