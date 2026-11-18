"""Outcome, side-effect, trajectory, and time-plan metrics."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from src.contracts import ContractPackage
from src.runtime.execution import state_diff


def accuracy(results: list[dict[str, Any]]) -> float:
    """Return assertion accuracy; an empty scope is vacuously correct."""
    if not results:
        return 1.0
    return sum(result["passed"] for result in results) / len(results)


def action_success_rate(audit: list[dict[str, Any]]) -> float:
    """Measure successful command records."""
    commands = [
        record for record in audit if record["record_type"] == "command"
    ]
    if not commands:
        return 1.0
    successful = sum(
        record["result"]["code"] == "[PASS]" for record in commands
    )
    return successful / len(commands)


def trajectory_summary(
    audit: list[dict[str, Any]],
    termination: dict[str, Any],
) -> dict[str, Any]:
    """Summarize command, mutation, turn, and finish behavior."""
    commands = [
        record for record in audit if record["record_type"] == "command"
    ]
    mutation_attempts = [
        record
        for record in commands
        if record["status"] in {"committed", "rolled_back"}
    ]
    return {
        "turns": termination["turn_index"],
        "total_tool_calls": sum(
            not (record.get("command", {}).get("target") == "session"
                 and record.get("command", {}).get("function") == "finish")
            for record in commands
        ),
        "mutation_attempts": len(mutation_attempts),
        "successful_mutations": sum(
            record["status"] == "committed"
            for record in mutation_attempts
        ),
        "failed_calls": sum(
            record["result"]["code"] != "[PASS]" for record in commands
        ),
        "finish_observed": any(
            record.get("command")
            == {
                "target": "session",
                "function": "finish",
                "parameters": {},
            }
            and record["result"]["code"] == "[PASS]"
            for record in commands
        ),
        "termination_reason": termination["reason"],
    }


def unexpected_side_effect_count(
    contract: ContractPackage,
    target: dict[str, Any],
    initial: dict[str, Any],
    final: dict[str, Any],
    *,
    ignored_scopes: set[str] | None = None,
    ignored_paths: set[tuple[str, str, str]] | None = None,
) -> int:
    """Count changed property paths that have no target assertion."""
    ignored = ignored_scopes or set()
    allowed_paths = ignored_paths or set()
    target_paths = {
        (scope, target_id, prop)
        for scope, target_id, prop, _ in contract.assertions(target)
    }
    return sum(
        item["scope"] not in ignored
        and (item["scope"], item["target_id"], item["property"])
        not in allowed_paths
        and (item["scope"], item["target_id"], item["property"])
        not in target_paths
        for item in state_diff(initial, final)
    )


def time_plan_valid(
    initial: dict[str, Any],
    final: dict[str, Any],
    audit: list[dict[str, Any]],
) -> bool:
    """Cross-check elapsed time, wall-clock state, ticks, and advances."""
    initial_time = initial["runtime"]["time_state"]
    final_time = final["runtime"]["time_state"]
    advances = [
        record
        for record in audit
        if record["record_type"] == "time_advance"
        and record["status"] == "committed"
    ]
    ticks = [
        record["sequence"]
        for record in audit
        if record["record_type"] == "tick"
        and record["status"] == "committed"
    ]
    referenced_ticks = [
        sequence
        for record in advances
        for sequence in record["time_advance"]["tick_sequences"]
    ]
    elapsed = (
        final_time["elapsed_minutes"] - initial_time["elapsed_minutes"]
    )
    total_minutes = sum(
        record["time_advance"]["minutes"] for record in advances
    )
    tick_counts_match = all(
        len(record["time_advance"]["tick_sequences"])
        == record["time_advance"]["minutes"]
        for record in advances
    )
    initial_clock = datetime.strptime(
        f"{initial_time['date']} {initial_time['clock']}",
        "%Y-%m-%d %H:%M",
    )
    expected_clock = initial_clock + timedelta(minutes=elapsed)
    return (
        elapsed >= 0
        and elapsed == total_minutes
        and tick_counts_match
        and referenced_ticks == ticks
        and len(referenced_ticks) == len(set(referenced_ticks))
        and final_time["date"] == expected_clock.strftime("%Y-%m-%d")
        and final_time["clock"] == expected_clock.strftime("%H:%M")
    )
