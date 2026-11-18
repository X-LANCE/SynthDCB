"""Deterministic v1 at/by/within/for/synchronize evaluation."""

from __future__ import annotations

from typing import Any

from src.contracts import ContractPackage


def _key(ref: dict[str, Any]) -> tuple[str, str, str]:
    """Return the key."""
    return ref["scope"], ref["target_id"], ref["property"]


def _assertion(
    contract: ContractPackage,
    target: dict[str, Any],
    key: tuple[str, str, str],
) -> dict[str, Any]:
    """Return the assertion."""
    return next(
        assertion
        for scope, target_id, prop, assertion in contract.assertions(target)
        if (scope, target_id, prop) == key
    )


def _completion_time(
    contract: ContractPackage,
    target: dict[str, Any],
    initial: dict[str, Any],
    audit: list[dict[str, Any]],
    ref: dict[str, Any],
) -> int | None:
    """Return the completion time."""
    key = _key(ref)
    assertion = _assertion(contract, target, key)
    initial_value = contract.state_value(initial, *key)
    for record in audit:
        for diff in record.get("state_diff", []):
            if (
                diff["scope"],
                diff["target_id"],
                diff["property"],
            ) != key:
                continue
            if contract.evaluate_assertion(
                assertion,
                initial_value,
                diff["after"],
            ):
                return int(record["simulation_time"]["elapsed_minutes"])
    return None


def _remains_satisfied(
    contract: ContractPackage,
    target: dict[str, Any],
    initial: dict[str, Any],
    audit: list[dict[str, Any]],
    ref: dict[str, Any],
    start: int,
) -> bool:
    """Return whether the constraint remains satisfied through the audit window."""
    key = _key(ref)
    assertion = _assertion(contract, target, key)
    initial_value = contract.state_value(initial, *key)
    for record in audit:
        elapsed = int(record["simulation_time"]["elapsed_minutes"])
        if elapsed < start:
            continue
        for diff in record.get("state_diff", []):
            if (
                diff["scope"],
                diff["target_id"],
                diff["property"],
            ) == key and not contract.evaluate_assertion(
                assertion,
                initial_value,
                diff["after"],
            ):
                return False
    return True


def evaluate_time_constraint(
    contract: ContractPackage,
    task: dict[str, Any],
    target: dict[str, Any],
    initial: dict[str, Any],
    final: dict[str, Any],
    audit: list[dict[str, Any]],
) -> bool | None:
    """Return the time constraint."""
    constraint = target["time_constraint"]
    if constraint is None:
        return None
    kind = constraint["kind"]
    if kind == "synchronize":
        completions: list[int] = []
        for item in constraint["targets"]:
            times = [
                _completion_time(contract, target, initial, audit, ref)
                for ref in item["target_paths"]
            ]
            if any(value is None for value in times):
                return False
            completions.append(max(value for value in times if value is not None))
        return max(completions) - min(completions) <= constraint["window_minutes"]

    times = [
        _completion_time(contract, target, initial, audit, ref)
        for ref in constraint["target_paths"]
    ]
    if any(value is None for value in times):
        return False
    completed = max(value for value in times if value is not None)
    if kind == "at":
        return all(value == constraint["elapsed_minutes"] for value in times)
    if kind in {"by", "within"}:
        return completed <= constraint["deadline_elapsed_minutes"]
    duration = constraint["duration_minutes"]
    final_elapsed = int(final["runtime"]["time_state"]["elapsed_minutes"])
    return (
        final_elapsed - completed >= duration
        and all(
            _remains_satisfied(
                contract,
                target,
                initial,
                audit,
                ref,
                completed,
            )
            for ref in constraint["target_paths"]
        )
    )
