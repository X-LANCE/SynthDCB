"""First-transition Workflow timing and its fixed background horizon."""

from __future__ import annotations

from typing import Any

from src.contracts import strict_equal
from src.contracts.validators import ContractValidator


def goal_evaluation_end(start_minute: int, reference_end_minute: int) -> int:
    """At least twice the reference duration, rounded up to a whole hour."""
    duration = reference_end_minute - start_minute
    return start_minute + max(60, ((2 * duration + 59) // 60) * 60)


def evaluation_end(target: dict[str, Any]) -> int | None:
    if "workflow" in target:
        return target["workflow"]["evaluation_end_minute"]
    return target.get("evaluation_end_minute")


def complete_background_simulation(world, bundle) -> dict[str, Any] | None:
    end = evaluation_end(bundle.target)
    return None if end is None else world.simulate_until(end)


def evaluate_workflow(target: dict[str, Any], audit: list[dict[str, Any]]) -> dict[str, Any] | None:
    workflow = target.get("workflow")
    if workflow is None:
        return None
    first = {}
    for record in sorted(audit, key=lambda item: item["sequence"]):
        if record["status"] != "committed":
            continue
        minute = record["simulation_time"]["elapsed_minutes"]
        if minute > workflow["evaluation_end_minute"]:
            continue
        for event in workflow["transitions"]:
            if event["id"] in first:
                continue
            if any(
                all(change[key] == event[key] for key in ("scope", "target_id", "property"))
                and ((not ContractValidator.evaluate_assertion(event["predicate"], change["before"], change["before"])
                      and ContractValidator.evaluate_assertion(event["predicate"], change["after"], change["after"]))
                     if "predicate" in event else
                     strict_equal(change["before"], event["from"]) and strict_equal(change["after"], event["to"]))
                for change in record["state_diff"]
            ):
                first[event["id"]] = {"minute": minute, "sequence": record["sequence"]}
    checks = []
    for relation in workflow["relations"]:
        kind = relation["kind"]
        ids = ([relation["before"], relation["after"]] if kind == "ordered" else
               relation["events"] if kind == "synchronize" else [relation["event"]])
        passed = all(key in first for key in ids)
        if passed:
            values = [first[key] for key in ids]
            if kind == "ordered":
                before, after = values
                delay = after["minute"] - before["minute"]
                passed = ((after["minute"], after["sequence"]) > (before["minute"], before["sequence"])
                          and relation["min_minutes"] <= delay <= relation["max_minutes"])
            elif kind == "synchronize":
                minutes = [item["minute"] for item in values]
                passed = max(minutes) - min(minutes) <= relation["tolerance_minutes"]
            elif kind == "at":
                passed = abs(values[0]["minute"] - relation["minute"]) <= relation["tolerance_minutes"]
            else:
                passed = values[0]["minute"] < relation["minute"]
        checks.append({"relation": relation, "passed": passed})
    missing = [event["id"] for event in workflow["transitions"] if event["id"] not in first]
    return {"passed": not missing and all(item["passed"] for item in checks),
            "first_transitions": first, "missing_transitions": missing, "relations": checks}
