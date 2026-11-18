"""Offline task selection: category quotas, base-family balance, coverage."""

from collections import Counter
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import random
from src.utils import load_json


def largest_remainder(count: int, ratios: dict[str, float]) -> dict[str, int]:
    if type(count) is not int or count < 0 or not ratios:
        raise ValueError("count must be nonnegative and category ratios must be nonempty")
    weights = {key: Fraction(str(value)) for key, value in ratios.items()}
    if any(value < 0 for value in weights.values()) or sum(weights.values()) <= 0:
        raise ValueError("category ratios must be finite nonnegative numbers with positive total")
    exact = {key: count * value / sum(weights.values()) for key, value in weights.items()}
    quotas = {key: value.numerator // value.denominator for key, value in exact.items()}
    order = sorted(exact, key=lambda key: (-(exact[key] - quotas[key]), key))
    for key in order[:count-sum(quotas.values())]:
        quotas[key] += 1
    return quotas


def task_coverage(record: dict) -> dict:
    root = Path(record["task_root"])
    initial = load_json(Path(record["effective_world_root"]) / "world_init.json")["config"]
    target = load_json(root / "target.json")
    trajectory = load_json(root / "reference_trajectory.json")
    metadata = load_json(Path(record["validation_metadata_path"]))
    if metadata["validated"] is not True or "validated_state_changes" not in metadata["meta"]["derived"]:
        raise ValueError(f"{record['task_id']} lacks validated state-change coverage evidence")
    families, classes, coverage = set(), set(), set()

    def add(scope, target_id, prop=None, function=None):
        if scope == "object":
            class_id = initial["objects"][target_id]["class"]
            family = class_id.split(".")[1]
        elif scope == "space":
            class_id = "Space." + initial["spaces"][target_id]["type"]
            family = "Space"
        else:
            return
        families.add(family)
        classes.add(class_id)
        if prop is not None:
            coverage.add(f"{class_id}.property.{prop}")
        if function is not None:
            coverage.add(f"{class_id}.function.{function}")

    for scope in ("object", "space"):
        for target_id, spec in target[f"{scope}s"].items():
            for prop in spec["properties"]:
                add(scope, target_id, prop)
    for change in metadata["meta"]["derived"]["validated_state_changes"]:
        add(change["scope"], change["target_id"], change["property"])
    for item in trajectory["records"]:
        if item["kind"] != "tool_exchange":
            continue
        command = item["call"]["command"]
        if command["target"] in initial["objects"]:
            add("object", command["target"], function=command["function"])
        elif command["function"] == "get_space_state":
            space_id = command["parameters"].get("space_id")
            if space_id in initial["spaces"]:
                add("space", space_id)
    for capability in metadata["meta"]["derived"].get("referenced_capabilities", []):
        for prop in {*capability["reads"], *capability["writes"]}:
            add("object", capability["target"], prop, capability["function"])
    reasons = "+".join(sorted({f"{item['status']}.{item['reason_code']}" for item in target["expected_reports"]}))
    outcome = f"{metadata['meta']['expected_outcome']['feasibility']}:{reasons}" if reasons else "feasible"
    return {"base_families": sorted(families), "classes": sorted(classes), "coverage": sorted(coverage), "outcome": outcome}


def distribution(rows, features):
    categories, families, classes, coverage = Counter(), Counter(), Counter(), set()
    outcomes = Counter()
    for row in rows:
        categories[f"{row['task_family']}.{row['task_subtype']}"] += 1
        feature = features[row["task_id"]]
        outcomes[f"{row['task_family']}.{row['task_subtype']}:{feature['outcome']}"] += 1
        families.update(feature["base_families"])
        classes.update(feature["classes"])
        coverage.update(feature["coverage"])
    return {"task_count": len(rows), "categories": dict(sorted(categories.items())), "outcomes": dict(sorted(outcomes.items())), "base_families": dict(sorted(families.items())), "classes": dict(sorted(classes.items())), "property_function_coverage_count": len(coverage), "property_function_coverage": sorted(coverage)}


def select_tasks(rows, *, count, ratios, seed, eligible=None, excluded=(), outcome_ratios=None):
    ids = [row["task_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("the task pool contains duplicate task IDs")
    known = set(ids)
    requested_ids = set(excluded) | (set(eligible) if eligible is not None else set())
    if requested_ids - known:
        raise ValueError(f"selection ID lists contain unknown IDs: {sorted(requested_ids-known)}")
    features = {row["task_id"]: task_coverage(row) for row in rows}
    candidates = [row for row in rows if (eligible is None or row["task_id"] in eligible) and row["task_id"] not in excluded]
    quotas = largest_remainder(count, ratios)
    if outcome_ratios and set(outcome_ratios) - set(ratios):
        raise ValueError("outcome ratios contain categories absent from category ratios")
    outcome_quotas = {}
    selected, shortages = [], {}
    rng = random.Random(seed)
    tie_order = sorted(ids)
    rng.shuffle(tie_order)
    tie_rank = {task_id: index for index, task_id in enumerate(tie_order)}
    for category, quota in sorted(quotas.items()):
        available = [row for row in candidates if f"{row['task_family']}.{row['task_subtype']}" == category]
        weights = (outcome_ratios or {}).get(category)
        if weights is None:
            weights = Counter(features[row["task_id"]]["outcome"] for row in available)
        group_quotas = largest_remainder(quota, weights) if weights else {}
        outcome_quotas[category] = group_quotas
        family_counts, covered = Counter(), set()
        group_shortages = {}
        for outcome, group_quota in sorted(group_quotas.items()):
            group = [row for row in available if features[row["task_id"]]["outcome"] == outcome]
            selected_count = min(group_quota, len(group))
            for _ in range(selected_count):
                def rank(row):
                    feature = features[row["task_id"]]
                    counts = [family_counts[family] for family in feature["base_families"]]
                    return (max(counts, default=0), sum(counts)/len(counts) if counts else 0, -len(set(feature["coverage"])-covered), tie_rank[row["task_id"]])
                chosen = min(group, key=rank)
                group.remove(chosen)
                selected.append(chosen)
                feature = features[chosen["task_id"]]
                family_counts.update(feature["base_families"])
                covered.update(feature["coverage"])
            if selected_count < group_quota:
                group_shortages[outcome] = {"requested": group_quota, "selected": selected_count, "shortfall": group_quota-selected_count}
        selected_count = sum(f"{row['task_family']}.{row['task_subtype']}" == category for row in selected)
        if selected_count < quota:
            shortages[category] = {"requested": quota, "selected": selected_count, "shortfall": quota-selected_count, "outcomes": group_shortages}
    return {
        "status": "partial" if shortages else "complete", "selected_ids": [row["task_id"] for row in selected],
        "config": {"count": count, "ratios": deepcopy(ratios), "outcome_ratios": deepcopy(outcome_ratios), "seed": seed, "eligible_ids": sorted(eligible) if eligible is not None else None, "excluded_ids": sorted(excluded)},
        "quotas": quotas, "outcome_quotas": outcome_quotas, "shortages": shortages,
        "before": distribution(rows, features), "eligible": distribution(candidates, features), "after": distribution(selected, features),
    }
