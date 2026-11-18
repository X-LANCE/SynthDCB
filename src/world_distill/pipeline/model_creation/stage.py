"""Standard orchestration for meta, template, completion, and verification."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from src.utils import DOMAIN_CONFIG_DIR, PROJECT_ROOT, RUN_DIR, redact, write_json, write_jsonl

from ..models import (
    ModelArtifact,
    ModelCreationInput,
    ModelCreationOutput,
    StageProvenance,
)
from ..task_planner import TaskPlanner
from .sandbox import SandboxLimits
from .validator import expected_class_names, validate_model_artifacts


def _response_payload(log_data: dict[str, Any]) -> dict[str, Any]:
    """Return the response payload."""
    response = log_data.get("llm_output")
    return response if isinstance(response, dict) else {}


def _attempt_status(log_data: dict[str, Any]) -> str:
    """Return the attempt status."""
    code = str(log_data.get("code") or "[PASS]")
    validation = log_data.get("validation")
    validation_passed = not (
        isinstance(validation, dict)
        and validation.get("is_valid") is False
    )
    return "passed" if code == "[PASS]" and validation_passed else "failed"


def model_attempt_records(
    generation_report: dict[str, Any],
    *,
    evidence_root: str | Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Persist raw redacted attempts and return attempt/failure records."""

    root = Path(evidence_root).resolve()
    attempts: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for task in generation_report.get("tasks", []):
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("task_id", "unknown"))
        task_name = str(task.get("name", "unknown"))
        for index, raw_log in enumerate(task.get("log_data", []), start=1):
            if not isinstance(raw_log, dict):
                continue
            log_data = redact(raw_log)
            raw_path = (
                root
                / "attempts"
                / task_name
                / f"{task_id}.attempt-{index:02d}.json"
            )
            write_json(raw_path, log_data)
            llm_input = log_data.get("llm_input")
            response = _response_payload(log_data)
            usage = response.get("usage")
            attempt_meta = log_data.get("attempt")
            record = {
                "stage": task_name,
                "task_id": task_id,
                "attempt_index": index,
                "attempt_kind": "first_pass" if index == 1 else "repair",
                "status": _attempt_status(log_data),
                "code": str(log_data.get("code") or "[PASS]"),
                "llm_call": isinstance(llm_input, dict) or bool(response),
                "requested_model": response.get("requested_model"),
                "response_model": response.get("model"),
                "model_scenario": response.get("model_scenario"),
                "usage": usage if isinstance(usage, dict) else None,
                "usage_reported": isinstance(usage, dict) and bool(usage),
                "timing": attempt_meta if isinstance(attempt_meta, dict) else None,
                "raw_record": str(raw_path),
            }
            attempts.append(record)
            if record["status"] != "passed":
                failures.append(
                    {
                        **record,
                        "retryable": index < int(task.get("max_retries", 1)),
                        "validation": log_data.get("validation"),
                        "error": log_data.get("error"),
                    }
                )
            auxiliary_calls = log_data.get("auxiliary_llm_calls")
            if not isinstance(auxiliary_calls, list):
                continue
            for auxiliary_index, auxiliary in enumerate(
                auxiliary_calls,
                start=1,
            ):
                if not isinstance(auxiliary, dict):
                    continue
                auxiliary_path = (
                    root
                    / "attempts"
                    / task_name
                    / (
                        f"{task_id}.attempt-{index:02d}."
                        f"aux-{auxiliary_index:02d}.json"
                    )
                )
                write_json(auxiliary_path, auxiliary)
                auxiliary_response = _response_payload(auxiliary)
                auxiliary_usage = auxiliary_response.get("usage")
                attempts.append(
                    {
                        "stage": task_name,
                        "task_id": task_id,
                        "attempt_index": index,
                        "auxiliary_index": auxiliary_index,
                        "attempt_kind": "auxiliary",
                        "auxiliary_role": auxiliary.get("role"),
                        "status": (
                            "passed"
                            if auxiliary.get("code") == "[PASS]"
                            else "failed"
                        ),
                        "code": str(auxiliary.get("code") or "[PASS]"),
                        "llm_call": True,
                        "requested_model": auxiliary_response.get(
                            "requested_model"
                        ),
                        "response_model": auxiliary_response.get("model"),
                        "model_scenario": auxiliary_response.get(
                            "model_scenario"
                        ),
                        "usage": (
                            auxiliary_usage
                            if isinstance(auxiliary_usage, dict)
                            else None
                        ),
                        "usage_reported": (
                            isinstance(auxiliary_usage, dict)
                            and bool(auxiliary_usage)
                        ),
                        "timing": None,
                        "raw_record": str(auxiliary_path),
                    }
                )
    return attempts, failures


class ModelGenerationError(RuntimeError):
    """Raised after a failed DAG has written its complete evidence."""

    def __init__(
        self,
        message: str,
        *,
        report: dict[str, Any],
        run_root: Path,
    ) -> None:
        """Initialize the ModelGenerationError."""
        super().__init__(message)
        self.report = report
        self.run_root = run_root


def summarize_generation_usage(
    generation_report: dict[str, Any],
) -> dict[str, int]:
    """Flatten per-task-stage usage into one model-stage usage record."""
    totals = {
        "calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }
    usage_by_stage = generation_report.get("usage_by_stage", {})
    if not isinstance(usage_by_stage, dict):
        return totals
    for usage in usage_by_stage.values():
        if not isinstance(usage, dict):
            continue
        for field in totals:
            value = usage.get(field, 0)
            if isinstance(value, int):
                totals[field] += value
    return totals


def _generate(
    request: ModelCreationInput,
    required_contracts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Generate one object-class artifact through the configured LLM."""
    from ..parallel_pipeline import TaskManager

    jobs_root = (
        request.run_root.resolve()
        if request.run_root is not None
        else (
            RUN_DIR
            / f"{request.domain}-{request.generation_run_id or 'default'}"
            / "model_creation"
        ).resolve()
    )
    jobs_root.mkdir(parents=True, exist_ok=True)
    type_list_path = jobs_root / "type_list.json"
    write_json(type_list_path, request.object_types)
    planner = TaskPlanner(
        jobs_root,
        output_root=request.output_root,
        model=request.model,
        llm_scenarios={
            "create_meta": request.model_scenario,
            "complete_code": request.model_scenario,
            "verify_code": request.model_scenario,
        },
        generation_run_id=request.generation_run_id,
        max_generation_attempts=request.max_generation_attempts,
        use_rag=request.use_rag,
        property_catalog=request.property_catalog,
        required_contracts=required_contracts,
    )
    plan_path = planner.create_task_plan(type_list_path)
    manager = TaskManager(
        plan_path,
        on_failure="retry_parent",
        report_file=jobs_root / "model_creation.report.json",
        max_parent_reruns=request.max_repair_rounds,
    )
    manager.execute_tasks(max_workers=request.max_workers)
    report = manager.build_report()
    report["run_root"] = str(jobs_root)
    return report


def _final_gate_repair_targets(
    request: ModelCreationInput,
    validation_report: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Map independent validation failures back to the earliest repair stage."""

    by_class = {
        str(item.get("class_name")): item
        for item in validation_report.get("artifacts", [])
        if isinstance(item, dict) and item.get("class_name")
    }
    global_errors = [
        str(error) for error in validation_report.get("errors", [])
    ]
    repairs: dict[str, dict[str, Any]] = {}
    for class_name in expected_class_names(request.object_types):
        item = by_class.get(class_name)
        class_errors = [
            error for error in global_errors if class_name in error
        ]
        if item is None:
            repairs[class_name] = {
                "target_stage": "complete_code",
                "errors": class_errors or ["independent validator found no artifact"],
            }
            continue

        schema_report = item.get("schema_report")
        case_contract = item.get("case_contract")
        specification_failure = (
            not item.get("specification_path")
            or (
                isinstance(schema_report, dict)
                and schema_report.get("code") != "[PASS]"
            )
            or (
                isinstance(case_contract, dict)
                and case_contract.get("code") != "[PASS]"
            )
        )
        contract_report = item.get("contract_report")
        security_report = item.get("security_report")
        sandbox_report = item.get("sandbox_report")
        implementation_failure = any(
            (
                isinstance(report, dict)
                and report.get("code") != "[PASS]"
            )
            for report in (
                contract_report,
                sandbox_report,
            )
        ) or (
            isinstance(security_report, dict)
            and security_report.get("passed") is not True
        ) or item.get("test_passed") is False
        if specification_failure or implementation_failure:
            repairs[class_name] = {
                "target_stage": (
                    "create_meta" if specification_failure else "complete_code"
                ),
                "errors": class_errors or global_errors,
            }

    if global_errors and not repairs:
        repairs = {
            class_name: {
                "target_stage": "complete_code",
                "errors": global_errors,
            }
            for class_name in expected_class_names(request.object_types)
        }
    return repairs


def _run_final_gate_repair(
    request: ModelCreationInput,
    validation_report: dict[str, Any],
    evidence_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run the final gate repair."""
    from ..parallel_pipeline import TaskManager

    plan_path = evidence_root / "plans.json"
    manager = TaskManager(
        plan_path,
        on_failure="retry_parent",
        report_file=evidence_root / "model_creation.report.json",
        max_parent_reruns=request.max_repair_rounds,
    )
    dispatch = manager.request_final_gate_repairs(
        _final_gate_repair_targets(request, validation_report)
    )
    if dispatch["requested"]:
        manager.execute_tasks(max_workers=request.max_workers)
    report = manager.build_report()
    report["run_root"] = str(evidence_root)
    return report, dispatch


def run_model_creation(
    request: ModelCreationInput,
) -> ModelCreationOutput:
    """Generate when requested, then validate deterministic Domain models."""
    from .environment_loader import environment_loader

    effective_required_contracts = deepcopy(request.required_contracts)
    generation_report: dict[str, Any] = {}
    attempts = 0
    evidence_root = (
        request.run_root.resolve()
        if request.run_root is not None
        else (
            RUN_DIR
            / f"{request.domain}-{request.generation_run_id or 'default'}"
            / "model_creation"
        ).resolve()
    )
    attempt_records_path: Path | None = None
    failure_records_path: Path | None = None
    def persist_generation_evidence() -> None:
        """Persist the generation evidence."""
        nonlocal attempts, attempt_records_path, failure_records_path
        attempt_records, failure_records = model_attempt_records(
            generation_report,
            evidence_root=evidence_root,
        )
        attempt_records_path = write_jsonl(
            evidence_root / "attempts.jsonl",
            attempt_records,
        )
        failure_records_path = write_jsonl(
            evidence_root / "failures.jsonl",
            failure_records,
        )
        attempts = len(attempt_records)

    if request.generate_with_llm:
        protected_domains = (PROJECT_ROOT / "domains").resolve()
        if request.output_root.resolve() == protected_domains:
            raise ValueError(
                "LLM generation cannot target protected domains; use an isolated candidate root"
            )
        generation_report = _generate(request, effective_required_contracts)
        persist_generation_evidence()
        summary = generation_report["summary"]
        if any(
            summary[field]
            for field in ("failed", "pending", "running")
        ):
            raise ModelGenerationError(
                "model creation DAG did not complete: "
                f"failed={summary['failed']}, "
                f"pending={summary['pending']}, "
                f"running={summary['running']}",
                report=generation_report,
                run_root=evidence_root,
            )

    domain_path = (request.output_root / request.domain).resolve()
    property_catalog = request.property_catalog
    if property_catalog is None:
        candidate = (
            DOMAIN_CONFIG_DIR
            / request.domain
            / f"{request.domain.lower()}.property-specs.json"
        )
        if candidate.is_file():
            property_catalog = candidate

    limits = (
        SandboxLimits(**request.sandbox_limits)
        if request.sandbox_limits
        else SandboxLimits()
    )
    validation_rounds: list[dict[str, Any]] = []
    final_gate_repairs: list[dict[str, Any]] = []
    validation_report: dict[str, Any] = {}
    for round_index in range(request.max_repair_rounds + 1):
        validation_report = validate_model_artifacts(
            domain_path,
            request.object_types,
            property_catalog=property_catalog,
            run_tests=request.run_tests,
            sandbox_limits=limits,
            required_contracts=effective_required_contracts,
        )
        round_path = write_json(
            evidence_root
            / f"independent_validation.round-{round_index + 1:02d}.json",
            validation_report,
        )
        validation_rounds.append(
            {
                "round": round_index + 1,
                "code": validation_report["code"],
                "path": str(round_path),
            }
        )
        if validation_report["code"] == "[PASS]":
            break
        if not request.generate_with_llm or round_index >= request.max_repair_rounds:
            message = (
                "model validation failed: "
                + "; ".join(validation_report["errors"])
            )
            if request.generate_with_llm:
                generation_report["independent_validation_rounds"] = validation_rounds
                generation_report["final_gate_repairs"] = final_gate_repairs
                generation_report["final_validation"] = validation_report
                raise ModelGenerationError(
                    message,
                    report=generation_report,
                    run_root=evidence_root,
                )
            raise ValueError(message)
        generation_report, dispatch = _run_final_gate_repair(
            request,
            validation_report,
            evidence_root,
        )
        final_gate_repairs.append(dispatch)
        persist_generation_evidence()
        summary = generation_report["summary"]
        if not dispatch["requested"] or any(
            summary[field]
            for field in ("failed", "pending", "running")
        ):
            generation_report["independent_validation_rounds"] = validation_rounds
            generation_report["final_gate_repairs"] = final_gate_repairs
            generation_report["final_validation"] = validation_report
            raise ModelGenerationError(
                "independent final gate repair could not complete: "
                f"requested={len(dispatch['requested'])}, "
                f"exhausted={len(dispatch['exhausted'])}, "
                f"unmatched={len(dispatch['unmatched'])}",
                report=generation_report,
                run_root=evidence_root,
            )

    generation_report["independent_validation_rounds"] = validation_rounds
    generation_report["final_gate_repairs"] = final_gate_repairs

    from .environment_loader import write_model_summary

    write_json(domain_path / "type_list.json", request.object_types)
    entries = [
        entry for base in request.object_types.values()
        for entry in [base, *base.get("inherited_list", [])]
    ]
    if all("placement" in entry for entry in entries):
        write_json(domain_path / "type_list_with_placement.json", request.object_types)
    summary_path = write_model_summary(request.domain, domain_path)
    metadata_path = domain_path / "environment_metas.json"
    _, loader_report = environment_loader(domain_path, metadata_path)
    if loader_report["code"] != "[PASS]":
        raise ValueError(
            f"environment metadata extraction failed: {loader_report}"
        )
    validation_report["environment_loader"] = loader_report

    artifacts = tuple(
        ModelArtifact(
            class_name=item["class_name"],
            implementation_path=Path(item["implementation_path"]),
            test_path=(
                Path(item["test_path"])
                if item["test_path"] is not None
                else None
            ),
            specification_path=(
                Path(item["specification_path"])
                if item["specification_path"] is not None
                else None
            ),
        )
        for item in validation_report["artifacts"]
    )
    usage = summarize_generation_usage(generation_report)
    response_models = tuple(
        sorted(
            {
                str(item["response_model"])
                for item in generation_report.get("llm_calls", [])
                if item.get("response_model")
            }
        )
    )
    return ModelCreationOutput(
        domain=request.domain,
        domain_path=domain_path,
        artifacts=artifacts,
        environment_metadata_path=metadata_path,
        model_metadata_path=summary_path,
        validation_report=validation_report,
        provenance=StageProvenance(
            stage="model_creation",
            artifact_paths=tuple(
                path
                for artifact in artifacts
                for path in (
                    artifact.specification_path,
                    artifact.implementation_path,
                    artifact.test_path,
                )
                if path is not None
            )
            + (metadata_path, summary_path)
            + tuple(
                path
                for path in (
                    attempt_records_path,
                    failure_records_path,
                )
                if path is not None
            ),
            model_scenario=(
                request.model_scenario
                if request.generate_with_llm
                else None
            ),
            requested_model=(
                request.model
                if request.generate_with_llm
                else None
            ),
            usage=usage,
            attempts=attempts,
            validated=True,
            response_models=response_models,
            attempt_records_path=attempt_records_path,
            failure_records_path=failure_records_path,
        ),
    )
