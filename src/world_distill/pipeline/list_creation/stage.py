"""Standard entry point for list creation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Any, Callable

from ..models import (
    ListCreationInput,
    ListCreationOutput,
    StageProvenance,
    as_jsonable,
)
from .object_class_list_creator import create_object_class_list
from .object_class_list_reviewer import (
    ListReviewError,
    review_object_class_list,
)
from .object_class_list_validator import (
    LLM_JUDGE_SAMPLE_COUNT,
    LLM_JUDGE_SCORE_FIELDS,
    LLM_JUDGE_SCORE_KEY,
    split_type_list_changes,
    validate_type_list,
    validate_type_list_change_schema,
)


ListCreator = Callable[
    [ListCreationInput],
    tuple[dict[str, Any], dict[str, Any]],
]
ListReviewer = Callable[
    [ListCreationInput, dict[str, Any]],
    tuple[dict[str, Any], list[dict[str, Any]]],
]


def _class_names(object_types: dict[str, Any]) -> set[str]:
    """Return all base and inherited class names in a type list."""
    names = set(object_types)
    for item in object_types.values():
        if not isinstance(item, dict):
            continue
        variants = item.get("inherited_list")
        if not isinstance(variants, list):
            continue
        names.update(
            variant["class"]
            for variant in variants
            if isinstance(variant, dict)
            and isinstance(variant.get("class"), str)
        )
    return names


def _default_creator(
    request: ListCreationInput,
    validation_feedback: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return the default creator."""
    return create_object_class_list(
        request.existing_types,
        domain=request.domain,
        domain_description=request.description,
        model_scenario=request.model_scenario,
        model=request.model,
        max_object_types=request.max_object_types or 3,
        external_knowledge=request.external_knowledge,
        use_rag=request.use_rag,
        validation_feedback=validation_feedback,
    )


def _usage(log_data: dict[str, Any]) -> dict[str, Any]:
    """Return the usage."""
    response = log_data.get("llm_output")
    if isinstance(response, dict) and isinstance(
        response.get("usage"),
        dict,
    ):
        return deepcopy(response["usage"])
    return {}


def _default_reviewer(
    request: ListCreationInput,
    object_types: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return the default reviewer."""
    return review_object_class_list(
        object_types,
        domain=request.domain,
        domain_description=request.description,
        model_scenario=request.review_model_scenario,
        model=request.review_model or request.model,
        max_attempts_per_sample=request.review_max_attempts_per_sample,
        max_workers=request.review_max_workers,
    )


def _without_review_scores(
    object_types: dict[str, Any],
) -> dict[str, Any]:
    """Return the without review scores."""
    normalized = deepcopy(object_types)
    for item in normalized.values():
        if not isinstance(item, dict):
            continue
        item.pop(LLM_JUDGE_SCORE_KEY, None)
        variants = item.get("inherited_list")
        if not isinstance(variants, list):
            continue
        for variant in variants:
            if isinstance(variant, dict):
                variant.pop(LLM_JUDGE_SCORE_KEY, None)
    return normalized


def run_list_creation(
    request: ListCreationInput,
    *,
    creator: ListCreator | None = None,
    reviewer: ListReviewer | None = None,
    attempt_sink: Callable[[dict[str, Any]], None] | None = None,
    review_attempt_sink: Callable[[dict[str, Any]], None] | None = None,
    iteration_sink: Callable[[dict[str, Any]], None] | None = None,
) -> ListCreationOutput:
    """Create or validate the Domain object-type inventory."""
    object_types = deepcopy(request.existing_types)
    log_data: dict[str, Any] = {}
    attempt_logs: list[dict[str, Any]] = []
    iteration_reports: list[dict[str, Any]] = []
    if request.expand_with_llm:
        if request.max_generation_attempts <= 0:
            raise ValueError("max_generation_attempts must be positive")
        if request.max_iterations <= 0:
            raise ValueError("max_iterations must be positive")
        converged = False
        initial_class_names = _class_names(object_types)
        for iteration_index in range(1, request.max_iterations + 1):
            existing_class_names = _class_names(object_types)
            iteration_request = replace(
                request,
                existing_types=deepcopy(object_types),
            )
            validation_feedback = "No preceding validation failure."
            last_error: Exception | None = None
            iteration_attempts = 0
            for iteration_attempts in range(
                1,
                request.max_generation_attempts + 1,
            ):
                if creator is None:
                    generated, log_data = _default_creator(
                        iteration_request,
                        validation_feedback,
                    )
                else:
                    generated, log_data = creator(iteration_request)
                new_base_classes: list[str] = []
                modified_base_classes: list[str] = []
                deleted_base_classes: list[str] = []
                inventory_changed = False
                try:
                    creator_code = log_data.get("code")
                    if creator_code != "[PASS]":
                        raise ValueError(
                            str(creator_code or "[LIST_CREATION_FAILED]")
                        )
                    validate_type_list_change_schema(
                        generated,
                        domain=request.domain,
                    )
                    updates, deleted_base_classes = split_type_list_changes(
                        generated,
                        existing_types=object_types,
                    )
                    if (
                        not updates
                        and not deleted_base_classes
                        and not object_types
                    ):
                        raise ValueError("LLM returned no candidate object types")
                    new_base_classes = sorted(
                        set(updates) - set(object_types)
                    )
                    modified_base_classes = sorted(
                        name
                        for name in set(updates) & set(object_types)
                        if updates[name] != object_types[name]
                    )
                    if (
                        request.max_object_types is not None
                        and len(new_base_classes) > request.max_object_types
                    ):
                        raise ValueError(
                            "LLM added more new base object classes than the "
                            f"per-iteration bound {request.max_object_types}: "
                            f"received {len(new_base_classes)}"
                        )
                    candidate = deepcopy(object_types)
                    for name in deleted_base_classes:
                        del candidate[name]
                    candidate.update(updates)
                    inventory_changed = candidate != object_types
                    coverage_report = validate_type_list(
                        candidate,
                        domain=request.domain,
                        coverage_requirements=request.coverage_requirements,
                    )
                    new_classes = sorted(
                        _class_names(candidate) - existing_class_names
                    )
                    deleted_classes = sorted(
                        existing_class_names - _class_names(candidate)
                    )
                    coverage_report = {
                        **coverage_report,
                        "iteration_index": iteration_index,
                        "max_new_base_classes": request.max_object_types,
                        "new_class_count": len(new_classes),
                        "new_classes": new_classes,
                        "new_base_class_count": len(new_base_classes),
                        "new_base_classes": new_base_classes,
                        "modified_base_classes": modified_base_classes,
                        "deleted_class_count": len(deleted_classes),
                        "deleted_classes": deleted_classes,
                        "deleted_base_class_count": len(
                            deleted_base_classes
                        ),
                        "deleted_base_classes": deleted_base_classes,
                        "converged": not inventory_changed,
                    }
                except (TypeError, ValueError) as error:
                    last_error = error
                    validation_feedback = str(error)
                    log_data = deepcopy(log_data)
                    log_data["validation"] = {
                        "passed": False,
                        "error": str(error),
                    }
                else:
                    object_types = candidate
                    converged = not inventory_changed
                    log_data = deepcopy(log_data)
                    log_data["validation"] = {
                        "passed": True,
                        "coverage_report": coverage_report,
                    }
                log_data["iteration_index"] = iteration_index
                log_data["attempt_index"] = iteration_attempts
                attempt_logs.append(log_data)
                if attempt_sink is not None:
                    attempt_sink(deepcopy(log_data))
                if log_data["validation"]["passed"]:
                    break
            else:
                raise ValueError(
                    "list creation exhausted bounded attempts in iteration "
                    f"{iteration_index}: {last_error}"
                )
            iteration_report = {
                "iteration_index": iteration_index,
                "attempt_count": iteration_attempts,
                "new_class_count": coverage_report["new_class_count"],
                "new_classes": coverage_report["new_classes"],
                "new_base_class_count": len(new_base_classes),
                "new_base_classes": new_base_classes,
                "modified_base_classes": modified_base_classes,
                "deleted_class_count": coverage_report[
                    "deleted_class_count"
                ],
                "deleted_classes": coverage_report["deleted_classes"],
                "deleted_base_class_count": len(deleted_base_classes),
                "deleted_base_classes": deleted_base_classes,
                "total_class_count": coverage_report["total_class_count"],
                "converged": converged,
            }
            iteration_reports.append(iteration_report)
            if iteration_sink is not None:
                iteration_sink(
                    {
                        **deepcopy(iteration_report),
                        "input": as_jsonable(iteration_request),
                        "object_types": deepcopy(object_types),
                    }
                )
            if converged:
                break
        all_new_base_classes = sorted(
            set(object_types) - set(request.existing_types)
        )
        all_new_classes = sorted(
            _class_names(object_types) - initial_class_names
        )
        all_deleted_base_classes = sorted(
            set(request.existing_types) - set(object_types)
        )
        all_deleted_classes = sorted(
            initial_class_names - _class_names(object_types)
        )
        coverage_report = {
            **coverage_report,
            "max_iterations": request.max_iterations,
            "iterations_completed": len(iteration_reports),
            "iteration_limit_reached": (
                not converged
                and len(iteration_reports) == request.max_iterations
            ),
            "iteration_reports": iteration_reports,
            "new_class_count": len(all_new_classes),
            "new_classes": all_new_classes,
            "new_base_class_count": len(all_new_base_classes),
            "new_base_classes": all_new_base_classes,
            "deleted_class_count": len(all_deleted_classes),
            "deleted_classes": all_deleted_classes,
            "deleted_base_class_count": len(all_deleted_base_classes),
            "deleted_base_classes": all_deleted_base_classes,
            "converged": converged,
        }
    else:
        coverage_report = validate_type_list(
            object_types,
            domain=request.domain,
            coverage_requirements=request.coverage_requirements,
            max_object_types=request.max_object_types,
        )
    review_logs: list[dict[str, Any]] = []
    if request.review_with_llm:
        if request.review_max_attempts_per_sample <= 0:
            raise ValueError(
                "review_max_attempts_per_sample must be positive"
            )
        if request.review_max_workers <= 0:
            raise ValueError("review_max_workers must be positive")
        review_baseline = _without_review_scores(object_types)
        try:
            if reviewer is None:
                object_types, review_logs = _default_reviewer(
                    request,
                    object_types,
                )
            else:
                object_types, review_logs = reviewer(request, object_types)
        except ListReviewError as error:
            review_logs = error.logs
            for log in review_logs:
                if review_attempt_sink is not None:
                    review_attempt_sink(deepcopy(log))
            raise
        for log in review_logs:
            if review_attempt_sink is not None:
                review_attempt_sink(deepcopy(log))
        reviewed_without_scores = _without_review_scores(object_types)
        if (
            list(reviewed_without_scores) != list(review_baseline)
            or reviewed_without_scores != review_baseline
        ):
            raise ValueError(
                "list review may only attach llm_judge_scores; it cannot "
                "filter, reorder, rename, or rewrite classes"
            )
        reviewed_coverage = validate_type_list(
            object_types,
            domain=request.domain,
            coverage_requirements=request.coverage_requirements,
            require_llm_judge_scores=True,
        )
        review_requested_models = sorted(
            {
                str(log["llm_output"]["requested_model"])
                for log in review_logs
                if isinstance(log.get("llm_output"), dict)
                and log["llm_output"].get("requested_model")
            }
        )
        coverage_report = {
            **coverage_report,
            "base_class_count": reviewed_coverage["base_class_count"],
            "inherited_class_count": reviewed_coverage[
                "inherited_class_count"
            ],
            "total_class_count": reviewed_coverage["total_class_count"],
            "llm_judge_scores_required": True,
            "llm_judge_review": {
                "enabled": True,
                "score_key": LLM_JUDGE_SCORE_KEY,
                "score_fields": list(LLM_JUDGE_SCORE_FIELDS),
                "samples_per_class": LLM_JUDGE_SAMPLE_COUNT,
                "model_scenario": request.review_model_scenario,
                "requested_models": review_requested_models,
                "reviewed_class_count": reviewed_coverage[
                    "total_class_count"
                ],
                "valid_sample_count": (
                    reviewed_coverage["total_class_count"]
                    * LLM_JUDGE_SAMPLE_COUNT
                ),
                "attempt_count": len(review_logs),
                "filtering_applied": False,
            },
        }
    usage = {
        "calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }
    response_models: list[str] = []
    usage_by_scenario: dict[str, dict[str, int]] = {}
    for item in attempt_logs + review_logs:
        item_usage = _usage(item)
        response = item.get("llm_output")
        if isinstance(response, dict):
            usage["calls"] += 1
        for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
            value = item_usage.get(field)
            if isinstance(value, int):
                usage[field] += value
        if isinstance(response, dict) and isinstance(response.get("model"), str):
            response_models.append(response["model"])
        scenario = (
            response.get("model_scenario")
            if isinstance(response, dict)
            else None
        )
        if isinstance(scenario, str):
            bucket = usage_by_scenario.setdefault(
                scenario,
                {
                    "calls": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
            )
            bucket["calls"] += 1
            for field in (
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
            ):
                value = item_usage.get(field)
                if isinstance(value, int):
                    bucket[field] += value
    if usage_by_scenario:
        usage["by_model_scenario"] = usage_by_scenario
    return ListCreationOutput(
        domain=request.domain,
        object_types=object_types,
        coverage_report=coverage_report,
        provenance=StageProvenance(
            stage="list_creation",
            model_scenario=(
                request.model_scenario
                if request.expand_with_llm
                else (
                    request.review_model_scenario
                    if request.review_with_llm
                    else None
                )
            ),
            requested_model=(
                request.model
                if request.expand_with_llm
                else (
                    (request.review_model or request.model)
                    if request.review_with_llm
                    else None
                )
            ),
            usage=usage,
            attempts=len(attempt_logs) + len(review_logs),
            validated=True,
            response_models=tuple(response_models),
        ),
    )
