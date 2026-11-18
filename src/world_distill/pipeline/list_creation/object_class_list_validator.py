"""Schema, naming, duplication, and coverage checks for type lists."""

from __future__ import annotations

import re
from typing import Any


from jsonschema import Draft202012Validator

from src.contracts.schema import (
    DELETE_LIST_KEY,
    PASCAL_CASE_PATTERN,
    type_list_change_schema,
)


PASCAL_CASE = re.compile(PASCAL_CASE_PATTERN)
LLM_JUDGE_SCORE_KEY = "llm_judge_scores"
LLM_JUDGE_SCORE_FIELDS = (
    "generality",
    "representativeness",
    "description_completeness",
)
LLM_JUDGE_SAMPLE_COUNT = 5


def split_type_list_changes(
    generated: dict[str, Any],
    *,
    existing_types: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Split validated base-class updates from requested deletions."""
    if not isinstance(generated, dict):
        raise TypeError("LLM returned a non-object type-list change set")
    raw_deletions = generated.get(DELETE_LIST_KEY, [])
    if not isinstance(raw_deletions, list):
        raise TypeError("delete_list must be a list")
    if any(
        not isinstance(name, str) or not PASCAL_CASE.fullmatch(name)
        for name in raw_deletions
    ):
        raise ValueError("delete_list must contain PascalCase base-class keys")
    if len(raw_deletions) != len(set(raw_deletions)):
        raise ValueError("delete_list must not contain duplicate keys")

    deletions = list(raw_deletions)
    unknown = sorted(set(deletions) - set(existing_types))
    if unknown:
        raise ValueError(
            f"delete_list contains unknown base-class keys: {unknown}"
        )
    updates = {
        name: value
        for name, value in generated.items()
        if name != DELETE_LIST_KEY
    }
    conflicts = sorted(set(deletions) & set(updates))
    if conflicts:
        raise ValueError(
            "base-class keys cannot be deleted and returned in the same "
            f"change set: {conflicts}"
        )
    return updates, deletions


def validate_llm_judge_scores(
    item: dict[str, Any],
    *,
    location: str,
    required: bool = False,
) -> None:
    """Validate optional fixed-shape LLM-as-a-Judge annotations."""

    if LLM_JUDGE_SCORE_KEY not in item:
        if required:
            raise ValueError(
                f"{location}.{LLM_JUDGE_SCORE_KEY} is required"
            )
        return
    scores = item[LLM_JUDGE_SCORE_KEY]
    if not isinstance(scores, dict):
        raise TypeError(
            f"{location}.{LLM_JUDGE_SCORE_KEY} must be an object"
        )
    if set(scores) != set(LLM_JUDGE_SCORE_FIELDS):
        raise ValueError(
            f"{location}.{LLM_JUDGE_SCORE_KEY} must contain exactly "
            f"{list(LLM_JUDGE_SCORE_FIELDS)}"
        )
    for field in LLM_JUDGE_SCORE_FIELDS:
        values = scores[field]
        score_path = f"{location}.{LLM_JUDGE_SCORE_KEY}.{field}"
        if not isinstance(values, list):
            raise TypeError(f"{score_path} must be a list")
        if len(values) != LLM_JUDGE_SAMPLE_COUNT:
            raise ValueError(
                f"{score_path} must contain exactly "
                f"{LLM_JUDGE_SAMPLE_COUNT} samples"
            )
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 1 <= value <= 10
            for value in values
        ):
            raise ValueError(
                f"{score_path} values must be integers from 1 through 10"
            )


def validate_type_list(
    object_types: dict[str, Any],
    *,
    domain: str,
    coverage_requirements: tuple[str, ...] = (),
    max_object_types: int | None = None,
    require_llm_judge_scores: bool = False,
) -> dict[str, Any]:
    """Validate a list-stage result and return its coverage report."""
    if not isinstance(object_types, dict):
        raise TypeError("object type list must be a JSON object")
    if max_object_types is not None:
        if max_object_types <= 0:
            raise ValueError("max_object_types must be positive")
        if len(object_types) > max_object_types:
            raise ValueError(
                f"object type list exceeds bound {max_object_types}: "
                f"received {len(object_types)}"
            )

    inherited: list[str] = []
    declared_parent: dict[str, str] = {}
    for class_name, item in object_types.items():
        if not PASCAL_CASE.fullmatch(class_name):
            raise ValueError(
                f"invalid PascalCase object class name: {class_name!r}"
            )
        if not isinstance(item, dict):
            raise TypeError(f"{class_name} definition must be an object")
        if item.get("domain") != domain:
            raise ValueError(
                f"{class_name}.domain must equal {domain!r}"
            )
        if item.get("class") != class_name:
            raise ValueError(
                f"{class_name}.class must equal its mapping key"
            )
        if not isinstance(item.get("description"), str) or not item[
            "description"
        ].strip():
            raise ValueError(
                f"{class_name}.description must be non-empty"
            )
        if "base_only" in item and not isinstance(item["base_only"], bool):
            raise TypeError(f"{class_name}.base_only must be a boolean")
        validate_llm_judge_scores(
            item,
            location=class_name,
            required=require_llm_judge_scores,
        )
        variants = item.get("inherited_list")
        if not isinstance(variants, list):
            raise TypeError(
                f"{class_name}.inherited_list must be a list"
            )
        local_names: set[str] = set()
        for index, variant in enumerate(variants):
            if not isinstance(variant, dict):
                raise TypeError(
                    f"{class_name}.inherited_list[{index}] must be an object"
                )
            name = variant.get("class")
            if not isinstance(name, str) or not PASCAL_CASE.fullmatch(name):
                raise ValueError(
                    f"{class_name}.inherited_list[{index}].class is invalid"
                )
            description = variant.get("description")
            if not isinstance(description, str) or not description.strip():
                raise ValueError(
                    f"{class_name}.inherited_list[{index}].description "
                    "must be non-empty"
                )
            validate_llm_judge_scores(
                variant,
                location=f"{class_name}.inherited_list[{index}]",
                required=require_llm_judge_scores,
            )
            if name == class_name or name in local_names:
                raise ValueError(
                    f"duplicate or self-inherited class: {name}"
                )
            if name in object_types:
                raise ValueError(
                    f"{name} cannot be both a base class and an inherited class"
                )
            if name in declared_parent:
                raise ValueError(
                    f"{name} cannot inherit from both "
                    f"{declared_parent[name]} and {class_name}"
                )
            local_names.add(name)
            declared_parent[name] = class_name
            inherited.append(name)

    covered = set(object_types) | set(inherited)
    missing = sorted(set(coverage_requirements) - covered)
    if missing:
        raise ValueError(f"missing required object classes: {missing}")
    return {
        "base_class_count": len(object_types),
        "inherited_class_count": len(inherited),
        "total_class_count": len(covered),
        "required_classes": list(coverage_requirements),
        "missing_required_classes": missing,
        "max_object_types": max_object_types,
        "llm_judge_scores_required": require_llm_judge_scores,
    }


def validate_type_list_change_schema(value: Any, *, domain: str) -> None:
    """Raise a concise error when a generation response violates its schema."""
    validator = Draft202012Validator(type_list_change_schema(domain))
    errors = sorted(
        validator.iter_errors(value),
        key=lambda error: (
            tuple(str(part) for part in error.absolute_path),
            error.message,
        ),
    )
    if not errors:
        return
    messages: list[str] = []
    for error in errors:
        path = "$"
        for part in error.absolute_path:
            path += f"[{part}]" if isinstance(part, int) else f".{part}"
        messages.append(f"{path}: {error.message}")
    raise ValueError(
        "type-list output failed JSON Schema validation: "
        + "; ".join(messages)
    )
