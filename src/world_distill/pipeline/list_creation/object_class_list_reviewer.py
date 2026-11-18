"""Optional post-generation LLM-as-a-Judge annotation for type lists."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import dataclass
import time
from typing import Any, Collection

from src.utils import format_json
from src.utils.llm import call_llm_api, extract_json_from_answer

from . import prompt
from .object_class_list_validator import (
    LLM_JUDGE_SAMPLE_COUNT,
    LLM_JUDGE_SCORE_FIELDS,
    LLM_JUDGE_SCORE_KEY,
    validate_llm_judge_scores,
    validate_type_list,
)


@dataclass(frozen=True, slots=True)
class _ReviewTarget:
    index: int
    class_name: str
    description: str
    parent_class: str | None


@dataclass(frozen=True, slots=True)
class _TargetResult:
    target: _ReviewTarget
    scores: dict[str, list[int]] | None
    logs: tuple[dict[str, Any], ...]
    error: str | None = None


class ListReviewError(RuntimeError):
    """The optional judge could not produce five valid samples per class."""

    def __init__(self, message: str, logs: list[dict[str, Any]]) -> None:
        """Initialize the ListReviewError."""
        super().__init__(message)
        self.logs = logs


def _targets(object_types: dict[str, Any]) -> list[_ReviewTarget]:
    """Return the targets."""
    targets: list[_ReviewTarget] = []
    for base_name, item in object_types.items():
        targets.append(
            _ReviewTarget(
                index=len(targets),
                class_name=base_name,
                description=str(item["description"]),
                parent_class=None,
            )
        )
        for variant in item.get("inherited_list", []):
            targets.append(
                _ReviewTarget(
                    index=len(targets),
                    class_name=str(variant["class"]),
                    description=str(variant["description"]),
                    parent_class=base_name,
                )
            )
    return targets


def _inventory_context(targets: list[_ReviewTarget]) -> str:
    """Return the inventory context."""
    return format_json(
        [
            {
                "class": target.class_name,
                "kind": "base" if target.parent_class is None else "derived",
                "parent": target.parent_class,
            }
            for target in targets
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _validated_sample(payload: Any) -> dict[str, int]:
    """Return the validated sample."""
    if not isinstance(payload, dict):
        raise TypeError("judge response must be a JSON object")
    if set(payload) != set(LLM_JUDGE_SCORE_FIELDS):
        raise ValueError(
            "judge response must contain exactly "
            f"{list(LLM_JUDGE_SCORE_FIELDS)}"
        )
    scores: dict[str, int] = {}
    for field in LLM_JUDGE_SCORE_FIELDS:
        value = payload[field]
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 1 <= value <= 10
        ):
            raise ValueError(f"{field} must be an integer from 1 through 10")
        scores[field] = value
    return scores


def _review_target(
    target: _ReviewTarget,
    *,
    domain: str,
    domain_description: str,
    inventory_context: str,
    model_scenario: str,
    model: str | None,
    max_attempts_per_sample: int,
) -> _TargetResult:
    """Return the review target."""
    scores = {field: [] for field in LLM_JUDGE_SCORE_FIELDS}
    logs: list[dict[str, Any]] = []
    system_prompt = prompt.OBJECT_LIST_REVIEWER_SYSTEM_PROMPT
    for sample_index in range(1, LLM_JUDGE_SAMPLE_COUNT + 1):
        user_prompt = prompt.OBJECT_LIST_REVIEWER_USER_PROMPT.format(
            sample_index=sample_index,
            sample_count=LLM_JUDGE_SAMPLE_COUNT,
            domain=domain,
            domain_description=domain_description,
            class_name=target.class_name,
            class_kind=(
                "base" if target.parent_class is None else "derived"
            ),
            parent_class=target.parent_class or "None",
            class_description=target.description,
            inventory_context=inventory_context,
        )
        last_error = "judge did not return a valid score"
        for attempt_index in range(1, max_attempts_per_sample + 1):
            attempt_started = time.monotonic()
            response: dict[str, Any] = {}
            api_code = "[REVIEW_CALL_ERROR]"
            try:
                api_code, response = call_llm_api(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model_scenario=model_scenario,
                    model=model,
                )
                if api_code != "[PASS]":
                    raise RuntimeError(api_code)
                answer = response.get("answer")
                if not isinstance(answer, str):
                    raise TypeError("judge response has no string answer")
                parse_code, payload = extract_json_from_answer(answer)
                if parse_code != "[PASS]":
                    raise ValueError(parse_code)
                sample = _validated_sample(payload)
            except (KeyError, RuntimeError, TypeError, ValueError) as error:
                last_error = f"{type(error).__name__}: {error}"
                log_code = (
                    api_code
                    if api_code != "[PASS]"
                    else "[INVALID_JUDGE_SAMPLE]"
                )
                passed = False
            else:
                log_code = "[PASS]"
                passed = True
            log = {
                "stage": "list_review",
                "task_id": f"review-{target.class_name}",
                "target_index": target.index,
                "class_name": target.class_name,
                "parent_class": target.parent_class,
                "sample_index": sample_index,
                "attempt_index": attempt_index,
                "max_attempts_per_sample": max_attempts_per_sample,
                "timing": {
                    "elapsed_seconds": round(
                        time.monotonic() - attempt_started,
                        6,
                    )
                },
                "llm_input": {
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                },
                "llm_output": response,
                "code": log_code,
                "validation": {
                    "passed": passed,
                    "error": None if passed else last_error,
                },
            }
            logs.append(log)
            if passed:
                for field, value in sample.items():
                    scores[field].append(value)
                break
        else:
            return _TargetResult(
                target=target,
                scores=None,
                logs=tuple(logs),
                error=(
                    f"sample {sample_index} exhausted "
                    f"{max_attempts_per_sample} attempts: {last_error}"
                ),
            )
    return _TargetResult(
        target=target,
        scores=scores,
        logs=tuple(logs),
    )


def review_object_class_list(
    object_types: dict[str, Any],
    *,
    domain: str,
    domain_description: str,
    model_scenario: str = "judge",
    model: str | None = None,
    max_attempts_per_sample: int = 3,
    max_workers: int = 1,
    target_class_names: Collection[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Attach five judge samples to all or selected classes.

    Scores are annotations only: this function never drops, reorders, renames,
    or rewrites a class or description.  When ``target_class_names`` is
    supplied, the judge still sees the complete inventory as context, while
    only the selected base or derived classes receive score annotations.
    """

    if max_attempts_per_sample <= 0:
        raise ValueError("max_attempts_per_sample must be positive")
    if max_workers <= 0:
        raise ValueError("max_workers must be positive")
    validate_type_list(object_types, domain=domain)
    all_targets = _targets(object_types)
    if not all_targets:
        raise ValueError("cannot review an empty object type list")
    targets = all_targets
    if target_class_names is not None:
        requested = tuple(target_class_names)
        if not requested:
            raise ValueError("target_class_names cannot be empty")
        if any(not isinstance(name, str) or not name for name in requested):
            raise TypeError("target_class_names must contain non-empty strings")
        if len(set(requested)) != len(requested):
            raise ValueError("target_class_names cannot contain duplicates")
        available = {target.class_name for target in all_targets}
        unknown = sorted(set(requested) - available)
        if unknown:
            raise ValueError(f"unknown target classes: {unknown}")
        selected = set(requested)
        targets = [
            target
            for target in all_targets
            if target.class_name in selected
        ]
    context = _inventory_context(all_targets)
    results: dict[int, _TargetResult] = {}

    if max_workers == 1:
        for target in targets:
            results[target.index] = _review_target(
                target,
                domain=domain,
                domain_description=domain_description,
                inventory_context=context,
                model_scenario=model_scenario,
                model=model,
                max_attempts_per_sample=max_attempts_per_sample,
            )
    else:
        with ThreadPoolExecutor(
            max_workers=min(max_workers, len(targets))
        ) as executor:
            futures = {
                executor.submit(
                    _review_target,
                    target,
                    domain=domain,
                    domain_description=domain_description,
                    inventory_context=context,
                    model_scenario=model_scenario,
                    model=model,
                    max_attempts_per_sample=max_attempts_per_sample,
                ): target
                for target in targets
            }
            for future in as_completed(futures):
                target = futures[future]
                results[target.index] = future.result()

    ordered_results = [results[target.index] for target in targets]
    logs = sorted(
        [log for result in ordered_results for log in result.logs],
        key=lambda item: (
            int(item["target_index"]),
            int(item["sample_index"]),
            int(item["attempt_index"]),
        ),
    )
    failures = [result for result in ordered_results if result.error]
    if failures:
        details = "; ".join(
            f"{result.target.class_name}: {result.error}"
            for result in failures
        )
        raise ListReviewError(
            f"list review could not complete five samples per class: {details}",
            logs,
        )

    reviewed = deepcopy(object_types)
    locations = {
        base_name: item
        for base_name, item in reviewed.items()
    }
    locations.update(
        {
            str(variant["class"]): variant
            for item in reviewed.values()
            for variant in item.get("inherited_list", [])
        }
    )
    for result in ordered_results:
        if result.scores is None:
            raise RuntimeError(
                f"missing validated scores for {result.target.class_name}"
            )
        locations[result.target.class_name][LLM_JUDGE_SCORE_KEY] = result.scores
    validate_type_list(reviewed, domain=domain)
    for result in ordered_results:
        validate_llm_judge_scores(
            locations[result.target.class_name],
            location=result.target.class_name,
            required=True,
        )
    if len(targets) == len(all_targets):
        validate_type_list(
            reviewed,
            domain=domain,
            require_llm_judge_scores=True,
        )
    return reviewed, logs
