"""State assertion evaluation for object, space, and runtime targets."""

from __future__ import annotations

from typing import Any

from src.contracts import ContractPackage, is_number


def evaluate_assertions(
    contract: ContractPackage,
    target: dict[str, Any],
    initial: dict[str, Any],
    final: dict[str, Any],
) -> list[dict[str, Any]]:
    """Produce one explicit result for every private state assertion."""
    results: list[dict[str, Any]] = []
    for index, (scope, target_id, prop, assertion) in enumerate(
        contract.assertions(target),
        start=1,
    ):
        initial_status, initial_value = state_value(
            initial,
            scope,
            target_id,
            prop,
        )
        final_status, final_value = state_value(
            final,
            scope,
            target_id,
            prop,
        )
        failure_reason = assertion_failure_reason(
            assertion,
            initial_status,
            initial_value,
            final_status,
            final_value,
        )
        passed = failure_reason is None and contract.evaluate_assertion(
            assertion,
            initial_value,
            final_value,
        )
        result = {
            "assertion_id": f"assertion_{index}",
            "scope": scope,
            "target_id": target_id,
            "property": prop,
            "assertion": assertion,
            "initial_value": initial_value,
            "final_value": final_value,
            "passed": passed,
        }
        if not passed:
            result["failure_reason"] = failure_reason or "operator_failed"
        results.append(result)
    return results


def state_value(
    snapshot: dict[str, Any],
    scope: str,
    target_id: str,
    prop: str,
) -> tuple[str, Any]:
    """Read a snapshot path while preserving missing-path diagnostics."""
    targets = (
        snapshot["runtime"]
        if scope == "runtime"
        else snapshot[f"{scope}s"]
    )
    if target_id not in targets:
        return "missing_target", None
    properties = (
        targets[target_id]
        if scope == "runtime"
        else targets[target_id]["properties"]
    )
    if prop not in properties:
        return "missing_property", None
    return "present", properties[prop]


def assertion_failure_reason(
    assertion: dict[str, Any],
    initial_status: str,
    initial_value: Any,
    final_status: str,
    final_value: Any,
) -> str | None:
    """Classify structural and numeric-value failures before the operator."""
    if "missing_target" in (initial_status, final_status):
        return "missing_target"
    if "missing_property" in (initial_status, final_status):
        return "missing_property"
    op = assertion["op"]
    if op in {"range", "gte", "lte"} and not is_number(final_value):
        return "invalid_numeric_value"
    if op in {"delta_at_least", "closer_to"} and (
        not is_number(initial_value) or not is_number(final_value)
    ):
        return "invalid_numeric_value"
    return None
