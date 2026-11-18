"""Normalize sampling profiles and sample families, counts, and parameters."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import math
import random
from typing import Any, Iterable

from jsonschema import Draft202012Validator
from src.contracts import strict_equal

from .task_common import TaskSeedError
from .task_inventory import InventoryError


BASE_TASK_SUBTYPES = {
    "query": (
        "property.device",
        "property.space",
        "space.person_location",
        "space.occupants",
        "target.quantity",
        "target.enum",
        "target.comparison.top1",
        "target.comparison.topk",
    ),
    "control": ("single", "multi_property", "multi_target", "complex"),
    "goal": ("single", "multi_property", "multi_target", "complex"),
}


AGGREGATE_COMPONENTS = {
    "query": ("query",),
    "control": ("control",),
    "goal": ("goal",),
    "control_query": ("control", "query"),
    "control_goal": ("control", "goal"),
    "query_goal": ("query", "goal"),
    "control_query_goal": ("control", "query", "goal"),
}


TASK_SUBTYPES = {
    **BASE_TASK_SUBTYPES,
    "aggregate": tuple(AGGREGATE_COMPONENTS),
    "workflow": ("single", "condition_follow", "condition_delay", "condition_window", "synchronize", "at", "before", "environment_deadline", "environment_before_process"),
}


TASK_TYPES = tuple(
    f"{family}.{subtype}"
    for family, subtypes in TASK_SUBTYPES.items()
    for subtype in subtypes
)


BASE_TASK_TYPES = tuple(
    f"{family}.{subtype}"
    for family, subtypes in BASE_TASK_SUBTYPES.items()
    for subtype in subtypes
)


TARGET_OUTCOMES = ("valid", "DEVICE_TARGET_NOT_FOUND", "SPACE_TARGET_NOT_FOUND",
                   "DEVICE_PROPERTY_NOT_SUPPORTED", "SPACE_PROPERTY_NOT_SUPPORTED",
                   "INVALID_VALUE", "UNREACHABLE_GOAL")


SINGLE_TARGET_METHODS = (
    "random",
    "person_location",
    "query.target.comparison.top1",
)


MULTI_TARGET_METHODS = (
    "all",
    "except",
    "within",
    "random",
    "occupied_spaces",
    "unoccupied_spaces",
    "query.target.enum",
    "query.target.comparison.topk",
)


VALUE_METHODS = {
    "control": ("random", "delta", "query.property.device", "memory"),
    "goal": ("random", "delta", "query.property.space", "memory"),
}


POST_CONTROL_OPTIONS = ("none", "query_modified_value")


QUERY_MEMORY_WRITE_OPTIONS = ("none", "create", "update")


MEMORY_SCOPES = ("user", "global")


TASK_CATEGORIES = TASK_TYPES


DEFAULT_STRUCTURE = {
    "multi_property_count": {"min": 2, "max": 3},
    "multi_target_count": {"min": 2, "max": 5},
    "complex_property_count": {"min": 2, "max": 3},
    "complex_target_count": {"min": 2, "max": 5},
    "query_candidate_count": {"min": 2, "max": 10},
    "query_topk_count": {"min": 2, "max": 3},
}


class SamplingProfileError(ValueError):
    """A preset cannot produce valid weighted sampling choices."""


def _weights(
    value: Any,
    *,
    allowed: Iterable[str],
    label: str,
    require_all: bool = False,
    require_positive_total: bool = True,
) -> dict[str, float]:
    """Return the weights."""
    if not isinstance(value, dict):
        raise SamplingProfileError(f"{label} must be an object")
    allowed_set = set(allowed)
    unknown = set(value) - allowed_set
    missing = allowed_set - set(value) if require_all else set()
    if unknown or missing:
        details = []
        if unknown:
            details.append(f"unknown={sorted(unknown)}")
        if missing:
            details.append(f"missing={sorted(missing)}")
        raise SamplingProfileError(f"{label} has invalid keys: {'; '.join(details)}")
    result: dict[str, float] = {}
    for key, weight in value.items():
        if (
            not isinstance(weight, (int, float))
            or isinstance(weight, bool)
            or not math.isfinite(float(weight))
            or float(weight) < 0
        ):
            raise SamplingProfileError(f"{label}.{key} must be a finite non-negative number")
        result[str(key)] = float(weight)
    if require_positive_total and (not result or sum(result.values()) <= 0):
        raise SamplingProfileError(f"{label} must contain positive total weight")
    return result


def validate_sampling_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize one reusable sampling preset."""
    if not isinstance(profile, dict):
        raise SamplingProfileError("sampling profile must be an object")
    required = {
        "profile_id",
        "task_type_weights",
        "target_selection",
        "property_target_value",
        "post_control_query",
        "structure",
    }
    optional = {"family_world_ordinals", "family_variants", "goal_probe_max_plans", "goal_probe_max_minutes", "query_result_memory", "memory_scope_weights", "control_groups", "capability_weights", "workflow", "aggregate_component_count", "query_dependency_weights"}
    if not required.issubset(profile) or set(profile) - required - optional:
        raise SamplingProfileError(
            "sampling profile has invalid keys"
        )
    profile_id = profile["profile_id"]
    if not isinstance(profile_id, str) or not profile_id:
        raise SamplingProfileError("profile_id must be a non-empty string")
    normalized = deepcopy(profile)
    if "family_world_ordinals" in profile:
        selections = profile["family_world_ordinals"]
        if not isinstance(selections, dict) or set(selections) - {"goal", "workflow"}:
            raise SamplingProfileError("family_world_ordinals only supports goal/workflow")
        for family, ordinals in selections.items():
            if (not isinstance(ordinals, list)
                    or any(type(i) is not int or i < 1 for i in ordinals)
                    or len(set(ordinals)) != len(ordinals)):
                raise SamplingProfileError(f"family_world_ordinals.{family} requires distinct positive indices")
        normalized["family_world_ordinals"] = deepcopy(selections)
    if "family_variants" in profile:
        counts = profile["family_variants"]
        if (not isinstance(counts, dict) or set(counts) - {"control", "goal"}
                or any(type(n) is not int or not 1 <= n <= 100 for n in counts.values())):
            raise SamplingProfileError("family_variants requires control/goal counts within [1, 100]")
        normalized["family_variants"] = deepcopy(counts)
    if "goal_probe_max_plans" in profile:
        budget = profile["goal_probe_max_plans"]
        if type(budget) is not int or budget < 1:
            raise SamplingProfileError("goal_probe_max_plans must be a positive integer")
        normalized["goal_probe_max_plans"] = budget
    normalized["goal_probe_max_minutes"] = profile.get("goal_probe_max_minutes", 240)
    if type(normalized["goal_probe_max_minutes"]) is not int or normalized["goal_probe_max_minutes"] < 60 or normalized["goal_probe_max_minutes"] % 60:
        raise SamplingProfileError("goal_probe_max_minutes must be a positive whole-hour duration")
    for key in ("control_groups", "aggregate_component_count"):
        bounds = profile.get(key, {"min": 2, "max": 5})
        lower, upper = (1, 5) if key == "control_groups" else (2, 10)
        if set(bounds) != {"min", "max"} or any(type(value) is not int for value in bounds.values()) or not lower <= bounds["min"] <= bounds["max"] <= upper:
            raise SamplingProfileError(f"{key} requires integer bounds within [{lower}, {upper}]")
        normalized[key] = deepcopy(bounds)
    normalized["capability_weights"] = {}
    for level, weights in profile.get("capability_weights", {}).items():
        if level not in {"base_family", "class", "instance", "capability"}:
            raise SamplingProfileError(f"unknown capability weight level {level}")
        normalized["capability_weights"][level] = _weights(weights, allowed=weights, label=f"capability_weights.{level}", require_positive_total=False)
    workflow = profile.get("workflow", {})
    if set(workflow) - {"subtype_weights", "initial_state_weights", "tolerance_minutes", "outcome_weights", "delay_minutes", "windows_minutes"}:
        raise SamplingProfileError("unknown Workflow setting")
    normalized["workflow"] = {
        "subtype_weights": _weights(workflow.get("subtype_weights", {key: 1 for key in TASK_SUBTYPES["workflow"]}), allowed=TASK_SUBTYPES["workflow"], label="workflow.subtype_weights"),
        "initial_state_weights": _weights(workflow.get("initial_state_weights", {"idle": 1, "running": 1}), allowed=("idle", "running"), label="workflow.initial_state_weights"),
        "tolerance_minutes": workflow.get("tolerance_minutes", 1),
        "delay_minutes": deepcopy(workflow.get("delay_minutes", [1, 5, 10])),
        "windows_minutes": deepcopy(workflow.get("windows_minutes", [[1, 5], [5, 10]])),
        "outcome_weights": _weights(workflow.get("outcome_weights", {"valid": 8, "DEVICE_TARGET_NOT_FOUND": 1, "DEVICE_PROPERTY_NOT_SUPPORTED": 1}), allowed=("valid", "DEVICE_TARGET_NOT_FOUND", "DEVICE_PROPERTY_NOT_SUPPORTED"), label="workflow.outcome_weights"),
    }
    if type(normalized["workflow"]["tolerance_minutes"]) is not int or normalized["workflow"]["tolerance_minutes"] < 0:
        raise SamplingProfileError("Workflow tolerance must be a nonnegative integer")
    delays = normalized["workflow"]["delay_minutes"]
    if not isinstance(delays, list) or not delays or any(type(value) is not int or value < 1 for value in delays):
        raise SamplingProfileError("Workflow delays must be a nonempty list of positive integer minutes")
    windows = normalized["workflow"]["windows_minutes"]
    if not isinstance(windows, list) or not windows or any(not isinstance(pair, list) or len(pair) != 2 or any(type(value) is not int for value in pair) or not 0 <= pair[0] <= pair[1] for pair in windows):
        raise SamplingProfileError("Workflow windows must be nonempty inclusive [lower, upper] minute ranges")
    normalized["task_type_weights"] = _weights(
        profile["task_type_weights"],
        allowed=BASE_TASK_TYPES,
        label="task_type_weights",
        require_all=True,
    )
    selection = profile["target_selection"]
    if not isinstance(selection, dict) or set(selection) != set(BASE_TASK_SUBTYPES):
        raise SamplingProfileError("target_selection requires query, control, and goal")
    normalized_selection: dict[str, Any] = {}
    for family in BASE_TASK_SUBTYPES:
        spec = selection[family]
        if not isinstance(spec, dict) or "outcome_weights" not in spec:
            raise SamplingProfileError(
                f"target_selection.{family} requires outcome_weights"
            )
        expected = {"outcome_weights"}
        if family in {"control", "goal"}:
            expected.update({"single_method_weights", "multi_method_weights"})
        if set(spec) != expected:
            raise SamplingProfileError(
                f"target_selection.{family} keys must be {sorted(expected)}"
            )
        item = {
            "outcome_weights": _weights(
                spec["outcome_weights"],
                allowed=TARGET_OUTCOMES,
                label=f"target_selection.{family}.outcome_weights",
            )
        }
        if family in {"control", "goal"}:
            item["single_method_weights"] = _weights(
                spec["single_method_weights"],
                allowed=SINGLE_TARGET_METHODS,
                label=f"target_selection.{family}.single_method_weights",
            )
            item["multi_method_weights"] = _weights(
                spec["multi_method_weights"],
                allowed=MULTI_TARGET_METHODS,
                label=f"target_selection.{family}.multi_method_weights",
            )
        normalized_selection[family] = item
    normalized["target_selection"] = normalized_selection

    target_values = profile["property_target_value"]
    if not isinstance(target_values, dict) or set(target_values) != set(VALUE_METHODS):
        raise SamplingProfileError("property_target_value requires control and goal")
    normalized["property_target_value"] = {
        family: _weights(
            target_values[family],
            allowed=methods,
            label=f"property_target_value.{family}",
        )
        for family, methods in VALUE_METHODS.items()
    }
    for family, weights in normalized["property_target_value"].items():
        if not any(
            weight > 0 for method, weight in weights.items()
            if method != "memory"
        ):
            raise SamplingProfileError(
                f"property_target_value.{family} needs a non-memory fallback"
            )

    post = profile["post_control_query"]
    if not isinstance(post, dict) or set(post) != {"single_target_delta"}:
        raise SamplingProfileError(
            "post_control_query requires single_target_delta"
        )
    normalized["post_control_query"] = {
        "single_target_delta": _weights(
            post["single_target_delta"],
            allowed=POST_CONTROL_OPTIONS,
            label="post_control_query.single_target_delta",
            require_all=True,
        )
    }

    normalized["query_result_memory"] = _weights(
        profile.get("query_result_memory", {"none": 1}),
        allowed=QUERY_MEMORY_WRITE_OPTIONS,
        label="query_result_memory",
    )
    normalized["memory_scope_weights"] = _weights(
        profile.get("memory_scope_weights", {"user": 4, "global": 1}),
        allowed=MEMORY_SCOPES,
        label="memory_scope_weights",
        require_all=True,
    )

    structure = profile["structure"]
    required_structure = {
        "multi_property_count",
        "multi_target_count",
        "complex_property_count",
        "complex_target_count",
        "query_candidate_count",
        "query_topk_count",
    }
    if not isinstance(structure, dict) or set(structure) != required_structure:
        raise SamplingProfileError(
            "structure keys must be exactly " + ", ".join(sorted(required_structure))
        )
    normalized_structure: dict[str, dict[str, int]] = {}
    for name, bounds in structure.items():
        if not isinstance(bounds, dict) or set(bounds) != {"min", "max"}:
            raise SamplingProfileError(f"structure.{name} requires min and max")
        lower, upper = bounds["min"], bounds["max"]
        if (
            type(lower) is not int
            or type(upper) is not int
            or lower < 1
            or upper < lower
        ):
            raise SamplingProfileError(f"structure.{name} has invalid bounds")
        normalized_structure[name] = {"min": lower, "max": upper}
    normalized["structure"] = normalized_structure
    normalized["query_dependency_weights"] = _weights(profile.get("query_dependency_weights", {"none": 1}),
        allowed={"none", "infeasible", "partial"}, label="query_dependency_weights")
    return normalized


def weighted_choice(weights: dict[str, float], rng: random.Random) -> str:
    """Select one configured value without allocating a global quota."""
    positive = [(key, weight) for key, weight in weights.items() if weight > 0]
    if not positive:
        raise SamplingProfileError("weights must contain a positive choice")
    return rng.choices(
        [key for key, _weight in positive],
        weights=[weight for _key, weight in positive],
        k=1,
    )[0]


def sampling_options(constraints: dict[str, Any]) -> dict[str, Any]:
    """Return the sampling."""
    family = constraints["task_family"]
    subtype = constraints["task_subtype"]
    raw = deepcopy(constraints.get("sampling", {}))
    raw.setdefault("profile_id", "direct_builder")
    raw.setdefault("task_type", f"{family}.{subtype}")
    raw.setdefault("target_outcome", "valid")
    raw.setdefault("target_selection_method", "random")
    if family in {"control", "goal"}:
        raw.setdefault("property_target_value_method", "random")
    else:
        raw.setdefault("property_target_value_method", None)
    raw.setdefault("post_control_query", "none")
    raw.setdefault("memory_write_method", "none")
    raw.setdefault("memory_user_scope", "user")
    return raw


def sample_bounded_count(
    available: int,
    bounds: dict[str, Any],
    *,
    floor: int,
    rng: random.Random,
) -> int:
    """Return the bounded count."""
    lower = max(floor, int(bounds["min"]))
    upper = min(available, int(bounds["max"]))
    if upper < lower:
        raise TaskSeedError(f"need at least {lower} compatible candidates")
    return rng.randint(lower, upper)


def sample_schema_value(schema: dict, rng: random.Random) -> Any:
    """Sample declared examples, finite choices, or a bounded JSON value."""
    for key in ("enum", "examples"):
        if schema.get(key):
            candidates = [value for value in schema[key] if Draft202012Validator(schema).is_valid(value)]
            if candidates:
                return deepcopy(rng.choice(candidates))
    if "const" in schema and Draft202012Validator(schema).is_valid(schema["const"]):
        return deepcopy(schema["const"])
    for key in ("oneOf", "anyOf"):
        if key in schema:
            branches = [branch for branch in schema[key] if branch.get("type") != "null"]
            for branch in rng.sample(branches, len(branches)):
                value = sample_schema_value(branch, rng)
                if Draft202012Validator(schema).is_valid(value):
                    return value
            raise InventoryError("parameter alternatives have no sampleable value")
    kind = schema.get("type")
    if isinstance(kind, list):
        kind = next(item for item in kind if item != "null")
    if kind == "boolean":
        value = rng.choice((True, False))
    elif kind in {"integer", "number"}:
        step = schema.get("multipleOf", 1)
        lower = schema.get("minimum", schema.get("exclusiveMinimum", 0) + step)
        upper = schema.get("maximum", schema.get("exclusiveMaximum", lower + step * 3) - step)
        import math
        first, last = math.ceil(lower / step), math.floor(upper / step)
        if first > last:
            raise InventoryError("numeric parameter has no value on its declared step")
        value = rng.randint(first, last) * step
        if kind == "integer":
            value = int(value)
    elif kind == "array":
        lower = schema.get("minItems", 0)
        upper = schema.get("maxItems", lower + 3)
        finite = schema["items"].get("enum")
        if schema.get("uniqueItems") and finite is not None:
            finite = [item for index, item in enumerate(finite)
                      if not any(item == prior for prior in finite[:index])
                      and Draft202012Validator(schema["items"]).is_valid(item)]
            upper = min(upper, len(finite))
        if upper < lower:
            raise InventoryError("array parameter has no sampleable cardinality")
        count = rng.randint(lower, upper)
        if schema.get("uniqueItems") and finite is not None:
            value = deepcopy(rng.sample(finite, count))
        else:
            value = []
            for _ in range(max(1, count * 10)):
                if len(value) == count:
                    break
                item = sample_schema_value(schema["items"], rng)
                if not schema.get("uniqueItems") or item not in value:
                    value.append(item)
            if len(value) != count:
                raise InventoryError("could not sample enough unique array items")
    elif kind == "object":
        value = {name: sample_schema_value(schema["properties"][name], rng) for name in schema.get("required", [])}
    elif kind == "null":
        value = None
    elif "default" in schema and Draft202012Validator(schema).is_valid(schema["default"]):
        value = deepcopy(schema["default"])
    else:
        raise InventoryError("open string/untyped parameter needs a declared example, enum or default")
    if not Draft202012Validator(schema).is_valid(value):
        raise InventoryError("declared constraints do not admit the sampled value")
    return value


def sample_parameters(tool: dict, state: dict, rng: random.Random) -> dict:
    schema = tool["parameters_schema"]
    semantic = tool["semantics"]
    names = list(schema["required"])
    optional = sorted(set(schema["properties"]) - set(names))
    if semantic["kind"] == "collection_update":
        field_parameters = {item["parameter"] for item in semantic["fields"].values() if "parameter" in item}
        optional = [name for name in optional if name in field_parameters]
        if optional:
            names.append(rng.choice(optional))
    else:
        names.extend(optional)
    parameters = {}
    for name in names:
        source = tool.get("argument_sources", {}).get(name)
        if source is None:
            parameters[name] = sample_schema_value(schema["properties"][name], rng)
        else:
            records = state["objects"][tool["target"]]["properties"][source["property"]]
            if not records:
                raise InventoryError(f"{name}: referenced collection is empty")
            key = rng.choice(sorted(records))
            parameters[name] = key if source["field"] == "$key" else deepcopy(records[key][source["field"]])
    if semantic["kind"] == "collection_update":
        id_parameter = semantic["id_parameter"]
        source = tool.get("argument_sources", {}).get(id_parameter)
        if source == {"property": semantic["property"], "field": "$key"}:
            records = state["objects"][tool["target"]]["properties"][semantic["property"]]
            fields = {field: binding["value"] if "value" in binding else parameters[binding["parameter"]]
                      for field, binding in semantic["fields"].items()
                      if "value" in binding or binding["parameter"] in parameters}
            changed = [key for key in sorted(records)
                       if any(not strict_equal(records[key].get(field), value) for field, value in fields.items())]
            if changed:
                parameters[id_parameter] = rng.choice(changed)
    return parameters


def sample_capability(items, inventory, weights, rng):
    """Choose a family, class, instance, then capability without count bias."""
    candidates = []
    for item in items:
        class_id = inventory.initial["objects"][item["target"]]["class"]
        keys = {"base_family": class_id.split(".")[1], "class": class_id,
                "instance": item["target"], "capability": item["semantics"].get("property", item["function"])}
        if all(weights.get(level, {}).get(key, 1) > 0 for level, key in keys.items()):
            candidates.append(item)
    if not candidates:
        raise InventoryError("no Control capability has positive sampling weight")
    for level in ("base_family", "class", "instance", "capability"):
        groups = defaultdict(list)
        for item in candidates:
            class_id = inventory.initial["objects"][item["target"]]["class"]
            key = {"base_family": class_id.split(".")[1], "class": class_id,
                   "instance": item["target"], "capability": item["semantics"].get("property", item["function"])}[level]
            groups[key].append(item)
        selected = weighted_choice({key: weights.get(level, {}).get(key, 1) for key in groups}, rng)
        candidates = groups[selected]
    return rng.choice(candidates)


def sample_family(
    profile: dict[str, Any],
    family: str,
    rng: random.Random,
) -> tuple[str, dict[str, Any]]:
    """Return the family sampling."""
    task_type = weighted_choice(
        {
            key: weight
            for key, weight in profile["task_type_weights"].items()
            if key.startswith(f"{family}.")
        },
        rng,
    )
    subtype = task_type.split(".", 1)[1]
    if family == "goal":
        allowed = {"valid", "SPACE_TARGET_NOT_FOUND", "SPACE_PROPERTY_NOT_SUPPORTED", "UNREACHABLE_GOAL"}
    elif family == "query" and subtype.startswith("space."):
        allowed = {"valid"}
    elif family == "query" and subtype == "property.space":
        allowed = {"valid", "SPACE_TARGET_NOT_FOUND", "SPACE_PROPERTY_NOT_SUPPORTED"}
    else:
        allowed = {"valid", "SPACE_TARGET_NOT_FOUND", "DEVICE_TARGET_NOT_FOUND", "DEVICE_PROPERTY_NOT_SUPPORTED"}
        if family == "control":
            allowed.add("INVALID_VALUE")
    outcome = weighted_choice({key: value for key, value in profile["target_selection"][family]["outcome_weights"].items()
                               if key in allowed}, rng)
    sampling: dict[str, Any] = {
        "profile_id": profile["profile_id"],
        "task_type": task_type,
        "target_outcome": outcome,
        "target_selection_method": "task_defined",
        "property_target_value_method": None,
        "post_control_query": "none",
        "memory_write_method": "none",
    }
    if family == "query":
        if outcome == "valid" and task_type in {
            "query.property.device",
            "query.property.space",
        }:
            sampling["memory_write_method"] = weighted_choice(
                profile["query_result_memory"], rng
            )
            if sampling["memory_write_method"] != "none":
                sampling["memory_user_scope"] = weighted_choice(
                    profile["memory_scope_weights"], rng
                )
        return subtype, sampling
    if family not in {"control", "goal"}:
        return subtype, sampling

    target_weights = profile["target_selection"][family][
        "single_method_weights"
        if subtype in {"single", "multi_property"}
        else "multi_method_weights"
    ]
    target_method = weighted_choice(target_weights, rng)
    value_method = weighted_choice(profile["property_target_value"][family], rng)
    if value_method == "memory" and (
        subtype != "single" or outcome != "valid"
    ):
        value_method = weighted_choice(
            {
                key: weight
                for key, weight in profile["property_target_value"][family].items()
                if key != "memory"
            },
            rng,
        )
    if value_method == "memory":
        sampling["memory_user_scope"] = weighted_choice(
            profile["memory_scope_weights"], rng
        )
    if (
        family == "goal"
        and value_method == "query.property.space"
        and target_method.startswith("query.")
    ):
        static = {
            key: weight
            for key, weight in target_weights.items()
            if not key.startswith("query.")
        }
        if sum(static.values()) > 0:
            target_method = weighted_choice(static, rng)
    sampling["target_selection_method"] = target_method
    sampling["property_target_value_method"] = value_method
    if family == "control" and subtype == "single" and outcome in {"SPACE_TARGET_NOT_FOUND", "DEVICE_TARGET_NOT_FOUND"}:
        sampling["query_dependency"] = weighted_choice(profile["query_dependency_weights"], rng)
    if (
        family == "control"
        and subtype == "single"
        and outcome == "valid"
        and value_method == "delta"
    ):
        sampling["post_control_query"] = weighted_choice(
            profile["post_control_query"]["single_target_delta"], rng
        )
    return subtype, sampling
