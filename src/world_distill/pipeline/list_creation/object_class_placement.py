"""Add room-placement and quantity constraints to an existing type list."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from src.utils import (
    RUN_DIR,
    format_json,
    load_json,
    redact,
    sha256_json,
    write_json,
    write_jsonl,
)
from src.utils.llm import call_llm_api, extract_json_from_answer, get_llm_config

from . import prompt
from .object_class_list_validator import validate_type_list


PLACEMENT_MODEL = get_llm_config("generate")["model"]
PLACEMENT_BATCH_CLASS_LIMIT = 10
PLACEMENT_FIELDS = (
    "allowed_space_types",
    "min_items_per_world",
    "max_items_per_world",
    "min_items_per_space",
    "max_items_per_space",
)


class PlacementGenerationError(RuntimeError):
    """The placement Agent exhausted its bounded attempts."""


def _definitions(
    type_list: dict[str, Any],
) -> Iterable[tuple[str, dict[str, Any], str | None]]:
    """Yield class name, definition, and optional parent name."""
    for base_name, base in type_list.items():
        yield base_name, base, None
        for derived in base.get("inherited_list", []):
            yield derived["class"], derived, base_name


_LAYOUT_CATALOG_FIELDS = {
    "domain",
    "property_catalog",
    "space_type_limits",
    "person_names",
    "runtime",
    "domain_metadata",
    "scene_metadata",
    "layouts",
}
_LAYOUT_FIELDS = {"id", "spaces", "connections"}
_CONNECTION_FIELDS = {"space_1", "space_2", "type", "current_state"}
_CONNECTION_TYPES = {"passage", "door", "window"}
_CONNECTION_STATES = {"open", "closed"}


def load_layout_catalog(
    path: str | Path,
    *,
    known_space_types: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Load the fixed Home index and its individual layout files."""
    index_path = Path(path).resolve()
    index = load_json(index_path)
    if not _LAYOUT_CATALOG_FIELDS.issubset(index) or set(index) - _LAYOUT_CATALOG_FIELDS - {"containment_root_class"}:
        raise ValueError("layout index has unexpected top-level fields")
    references = index["layouts"]
    if not isinstance(references, list):
        raise TypeError("layout index layouts must be an array")
    layouts: list[dict[str, Any]] = []
    for reference in references:
        if (
            not isinstance(reference, dict)
            or set(reference) != {"id", "path"}
        ):
            raise ValueError("each layout index entry requires id and path")
        layout_path = (index_path.parent / reference["path"]).resolve()
        layout = load_json(layout_path)
        if layout.get("id") != reference["id"]:
            raise ValueError(
                f"layout index id does not match {layout_path}"
            )
        layouts.append(layout)
    catalog = deepcopy(index)
    catalog["layouts"] = layouts
    return validate_layout_catalog(
        catalog,
        known_space_types=known_space_types,
    )


def validate_layout_catalog(
    catalog: dict[str, Any],
    *,
    known_space_types: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Validate and return one fixed-layout catalog."""
    if not _LAYOUT_CATALOG_FIELDS.issubset(catalog) or set(catalog) - _LAYOUT_CATALOG_FIELDS - {"containment_root_class"}:
        raise ValueError("layout catalog has unexpected top-level fields")
    parent_class = catalog.get("containment_root_class")
    if parent_class is not None and (not isinstance(parent_class, str) or not parent_class.isidentifier()):
        raise ValueError("containment_root_class must name a device class")
    if (
        not isinstance(catalog["domain"], str)
        or not isinstance(catalog["property_catalog"], str)
        or any(
            not isinstance(catalog[name], dict)
            for name in ("runtime", "domain_metadata", "scene_metadata")
        )
    ):
        raise TypeError("layout catalog metadata fields are invalid")
    limits = catalog["space_type_limits"]
    if not isinstance(limits, dict):
        raise TypeError("space_type_limits must be an object")
    if any(type(value) is not int or value < 1 for value in limits.values()):
        raise ValueError("every space type limit must be a positive integer")
    if known_space_types is not None and set(limits) != set(known_space_types):
        raise ValueError("layout space types differ from the Domain catalog")
    names = catalog["person_names"]
    if (
        not isinstance(names, list)
        or len(set(names)) != len(names)
        or any(not isinstance(name, str) or not name for name in names)
    ):
        raise ValueError("person_names must contain unique non-empty names")
    layouts = catalog["layouts"]
    if not isinstance(layouts, list) or not layouts:
        raise ValueError("layouts must contain at least one layout")
    layout_ids: set[str] = set()
    for layout in layouts:
        if not isinstance(layout, dict) or set(layout) != _LAYOUT_FIELDS:
            raise ValueError("each layout requires id, spaces, and connections")
        layout_id = layout["id"]
        if not isinstance(layout_id, str) or not layout_id or layout_id in layout_ids:
            raise ValueError(f"invalid or duplicate layout id {layout_id!r}")
        layout_ids.add(layout_id)
        spaces = layout["spaces"]
        if not isinstance(spaces, list) or bool(spaces) != bool(limits):
            raise ValueError(f"{layout_id}.spaces must match the spatial capability")
        space_ids: set[str] = set()
        type_counts: dict[str, int] = {}
        for space in spaces:
            if not isinstance(space, dict):
                raise ValueError(f"{layout_id} has an invalid space")
            space_id = space["id"]
            space_type = space["type"]
            expected_space_fields = (
                {"id", "type"}
                if space_type == "stairs" or (catalog["domain"] != "Home" and "floor" not in space)
                else {"id", "type", "floor"}
            )
            if (
                set(space) - {"virtual"} != expected_space_fields
                or not isinstance(space_id, str)
                or not space_id
                or space_id in space_ids
                or space_type not in limits
            ):
                raise ValueError(f"{layout_id} has an invalid space id or type")
            if "virtual" in space and type(space["virtual"]) is not bool:
                raise TypeError(f"{layout_id}.{space_id}.virtual must be a boolean")
            if "floor" in expected_space_fields and type(space["floor"]) is not int:
                raise TypeError(f"{layout_id}.{space_id}.floor must be an integer")
            if space_type == "entryway" and space["floor"] != 1:
                raise ValueError(f"{layout_id}.entryway must be on floor 1")
            if space_type == "basement" and space["floor"] != -1:
                raise ValueError(f"{layout_id}.basement must be on floor -1")
            if space_type == "attic":
                if layout_id != "large_family_house":
                    raise ValueError("attic is only allowed in large_family_house")
                if space["floor"] != 3:
                    raise ValueError(f"{layout_id}.attic must be on floor 3")
            space_ids.add(space_id)
            type_counts[space_type] = type_counts.get(space_type, 0) + 1
        if any(type_counts[name] > limits[name] for name in type_counts):
            raise ValueError(f"{layout_id} exceeds a same-type room limit")
        connections = layout["connections"]
        if not isinstance(connections, list):
            raise TypeError(f"{layout_id}.connections must be an array")
        edges: set[tuple[str, str]] = set()
        for connection in connections:
            if (
                not isinstance(connection, dict)
                or set(connection) not in (
                    _CONNECTION_FIELDS,
                    {"space_1", "space_2", "type", "device_class"},
                )
            ):
                raise ValueError(f"{layout_id} has an invalid connection")
            left = connection["space_1"]
            right = connection["space_2"]
            if (
                not isinstance(left, str)
                or not isinstance(right, str)
                or left not in space_ids
                or right not in space_ids
                or left == right
                or connection["type"] not in _CONNECTION_TYPES
                or ("current_state" in connection and connection["current_state"] not in _CONNECTION_STATES)
                or ("device_class" in connection and (
                    connection["type"] not in {"door", "window"}
                    or not isinstance(connection["device_class"], str)
                    or not connection["device_class"].isidentifier()
                ))
            ):
                raise ValueError(f"{layout_id} has an invalid connection")
            edge = (*sorted((left, right)), connection["type"])
            if edge in edges:
                raise ValueError(f"{layout_id} has a duplicate connection")
            edges.add(edge)
        physical_ids = {space["id"] for space in spaces if not space.get("virtual", False)}
        if any(left not in physical_ids or right not in physical_ids for left, right, _ in edges):
            raise ValueError(f"{layout_id} connects a virtual space with a physical passage")
        reached = set(list(physical_ids)[:1])
        while True:
            expanded = reached | {
                endpoint
                for edge in edges
                if reached.intersection(edge[:2])
                for endpoint in edge[:2]
            }
            if expanded == reached:
                break
            reached = expanded
        if reached != physical_ids:
            raise ValueError(f"{layout_id} is not connected")
    return catalog


def effective_max(value: int, implicit: int) -> int:
    """Resolve the JSON sentinel only while calculating generation limits."""
    return implicit if value == -1 else value


def _validated_placements(
    payload: Any,
    type_list: dict[str, Any],
    catalog: dict[str, Any],
    *,
    implicit_space_max: int = 3,
    implicit_world_max: int = 20,
) -> dict[str, dict[str, Any]]:
    """Return a normalized placement mapping."""
    if not isinstance(payload, dict) or set(payload) != {"placements"}:
        raise ValueError("response must contain exactly the placements object")
    placements = payload["placements"]
    definitions = {
        name: (item, parent)
        for name, item, parent in _definitions(type_list)
    }
    if not isinstance(placements, dict) or set(placements) != set(definitions):
        missing = sorted(set(definitions) - set(placements or {}))
        extra = sorted(set(placements or {}) - set(definitions))
        raise ValueError(
            f"placement class coverage differs: missing={missing}, extra={extra}"
        )
    room_order = {
        name: index
        for index, name in enumerate(catalog["space_type_limits"])
    }
    normalized: dict[str, dict[str, Any]] = {}
    for class_name, raw in placements.items():
        if not isinstance(raw, dict) or set(raw) != set(PLACEMENT_FIELDS):
            raise ValueError(f"{class_name}.placement has unexpected fields")
        allowed = raw["allowed_space_types"]
        if (
            not isinstance(allowed, list)
            or (not allowed and bool(room_order))
            or len(set(allowed)) != len(allowed)
            or any(name not in room_order for name in allowed)
        ):
            raise ValueError(f"{class_name}.allowed_space_types is invalid")
        values = {name: raw[name] for name in PLACEMENT_FIELDS[1:]}
        if not room_order and (values["min_items_per_space"] != 0 or values["max_items_per_space"] != -1):
            raise ValueError(f"{class_name}: a spaceless device uses per-world limits only")
        for name, value in values.items():
            if type(value) is not int:
                raise TypeError(f"{class_name}.{name} must be an integer")
            if name.startswith("min_") and value < 0:
                raise ValueError(f"{class_name}.{name} must be non-negative")
            if name.startswith("max_") and value != -1 and value < 1:
                raise ValueError(f"{class_name}.{name} must be positive or -1")
        if values["min_items_per_space"] > effective_max(
            values["max_items_per_space"], implicit_space_max
        ):
            raise ValueError(f"{class_name} has incompatible per-space limits")
        if values["min_items_per_world"] > effective_max(
            values["max_items_per_world"], implicit_world_max
        ):
            raise ValueError(f"{class_name} has incompatible per-world limits")
        normalized[class_name] = {
            "allowed_space_types": sorted(allowed, key=room_order.__getitem__),
            **values,
        }

    for class_name, (definition, parent) in definitions.items():
        if parent is None and definition["inherited_list"]:
            continue
        limits = normalized[class_name]
        for layout in catalog["layouts"]:
            room_count = sum(
                space["type"] in limits["allowed_space_types"]
                for space in layout["spaces"]
            )
            required = max(
                limits["min_items_per_world"],
                limits["min_items_per_space"] * room_count,
            )
            capacity = min(
                effective_max(limits["max_items_per_world"], implicit_world_max),
                effective_max(limits["max_items_per_space"], implicit_space_max) * room_count
                if room_order else implicit_world_max,
            )
            if required > capacity:
                raise ValueError(
                    f"{class_name} cannot satisfy {layout['id']} placement limits"
                )

    for base_name, base in type_list.items():
        children = [item["class"] for item in base["inherited_list"]]
        if not children:
            continue
        base_allowed = set(normalized[base_name]["allowed_space_types"])
        for child in children:
            if not set(normalized[child]["allowed_space_types"]).issubset(base_allowed):
                raise ValueError(f"{child} allows a room outside {base_name}")
        family_space_max = effective_max(
            normalized[base_name]["max_items_per_space"], implicit_space_max
        )
        family_world_max = effective_max(
            normalized[base_name]["max_items_per_world"], implicit_world_max
        )
        for layout in catalog["layouts"]:
            layout_types = [space["type"] for space in layout["spaces"]]
            space_floor = 0
            for space_type in layout_types:
                if space_type not in base_allowed:
                    continue
                child_floor = sum(
                    normalized[child]["min_items_per_space"]
                    for child in children
                    if space_type in normalized[child]["allowed_space_types"]
                )
                required = max(
                    normalized[base_name]["min_items_per_space"],
                    child_floor,
                )
                if required > family_space_max:
                    raise ValueError(
                        f"{base_name} family cannot satisfy {layout['id']} space limits"
                    )
                if base.get("base_only") and required:
                    capacity = sum(
                        effective_max(
                            normalized[child]["max_items_per_space"],
                            implicit_space_max,
                        )
                        for child in children
                        if space_type in normalized[child]["allowed_space_types"]
                    )
                    if capacity < required:
                        raise ValueError(
                            f"{base_name} base_only family has no room capacity"
                        )
                space_floor += required
            child_world_floor = sum(
                max(
                    normalized[child]["min_items_per_world"],
                    normalized[child]["min_items_per_space"]
                    * sum(
                        space_type in normalized[child]["allowed_space_types"]
                        for space_type in layout_types
                    ),
                )
                for child in children
            )
            required_world = max(
                normalized[base_name]["min_items_per_world"],
                space_floor,
                child_world_floor,
            )
            if required_world > family_world_max:
                raise ValueError(
                    f"{base_name} family cannot satisfy {layout['id']} world limits"
                )
            family_room_count = sum(
                space_type in base_allowed for space_type in layout_types
            )
            family_capacity = min(
                family_world_max,
                family_space_max * family_room_count if room_order else implicit_world_max,
            )
            if base.get("base_only"):
                child_capacity = sum(
                    min(
                        effective_max(
                            normalized[child]["max_items_per_world"],
                            implicit_world_max,
                        ),
                        effective_max(
                            normalized[child]["max_items_per_space"],
                            implicit_space_max,
                        )
                        * sum(
                            space_type in normalized[child]["allowed_space_types"]
                            for space_type in layout_types
                        ) if room_order else implicit_world_max,
                    )
                    for child in children
                )
                if child_capacity < required_world:
                    raise ValueError(
                        f"{base_name} base_only family lacks world capacity in "
                        f"{layout['id']}"
                    )
                family_capacity = min(family_capacity, child_capacity)
            if required_world > family_capacity:
                raise ValueError(
                    f"{base_name} family has no capacity in {layout['id']}"
                )
    return normalized


def merge_placements(
    type_list: dict[str, Any],
    placements: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Attach placements without changing any existing type-list field."""
    enriched = deepcopy(type_list)
    for class_name, definition, _ in _definitions(enriched):
        definition["placement"] = deepcopy(placements[class_name])
    return enriched


def _without_placements(type_list: dict[str, Any]) -> dict[str, Any]:
    """Return the original type-list fields only."""
    stripped = deepcopy(type_list)
    for _, definition, _ in _definitions(stripped):
        definition.pop("placement", None)
    return stripped


def validate_placement_type_list(
    type_list: dict[str, Any],
    catalog: dict[str, Any],
    *,
    implicit_space_max: int = 3,
    implicit_world_max: int = 20,
) -> dict[str, dict[str, Any]]:
    """Validate an enriched list and return its placement mapping."""
    validate_type_list(type_list, domain=catalog["domain"])
    validate_layout_catalog(catalog)
    placements = {
        name: deepcopy(definition.get("placement"))
        for name, definition, _ in _definitions(type_list)
    }
    return _validated_placements(
        {"placements": placements},
        type_list,
        catalog,
        implicit_space_max=implicit_space_max,
        implicit_world_max=implicit_world_max,
    )


def _prompt_payload(
    type_list: dict[str, Any],
    catalog: dict[str, Any],
    feedback: str,
) -> str:
    """Return the placement request body."""
    return format_json(
        {
            "domain": catalog["domain"],
            "type_list": type_list,
            "space_type_limits": catalog["space_type_limits"],
            "layouts": [
                {
                    "id": layout["id"],
                    "spaces": layout["spaces"],
                    "connections": layout["connections"],
                }
                for layout in catalog["layouts"]
            ],
            "validation_feedback": feedback,
        },
        ensure_ascii=False,
        indent=2,
    )


def _placement_batches(
    type_list: dict[str, Any],
    class_limit: int = PLACEMENT_BATCH_CLASS_LIMIT,
) -> list[dict[str, Any]]:
    """Group complete base families into bounded placement requests."""
    batches: list[dict[str, Any]] = []
    batch: dict[str, Any] = {}
    class_count = 0
    for base_name, definition in type_list.items():
        family_count = 1 + len(definition["inherited_list"])
        if batch and class_count + family_count > class_limit:
            batches.append(batch)
            batch = {}
            class_count = 0
        batch[base_name] = definition
        class_count += family_count
    if batch:
        batches.append(batch)
    return batches


def create_placement_type_list(
    type_list_path: str | Path,
    layout_catalog_path: str | Path,
    output_root: str | Path,
    *,
    run_root: str | Path | None = None,
    model: str = PLACEMENT_MODEL,
    max_generation_attempts: int = 2,
) -> Path:
    """Run the bounded placement Agent and return the enriched-list path."""
    if max_generation_attempts not in {1, 2}:
        raise ValueError("placement generation allows one or two attempts")
    source_path = Path(type_list_path).resolve()
    catalog_path = Path(layout_catalog_path).resolve()
    destination = Path(output_root).resolve()
    log_root = (
        Path(run_root) if run_root is not None else RUN_DIR / destination.name / "placement"
    ).resolve()
    type_list = load_json(source_path)
    catalog = load_layout_catalog(catalog_path)
    validate_type_list(type_list, domain=catalog["domain"])
    batches = _placement_batches(type_list)
    llm_config = get_llm_config("generate")
    request_path = log_root / "request.json"
    attempts_path = log_root / "attempts.jsonl"
    output_path = destination / "type_list_with_placement.json"
    write_json(
        request_path,
        {
            "stage": "placement_generation",
            "model_scenario": "generate",
            "requested_model": model,
            "resolved_model": model,
            "base_url": llm_config["base_url"],
            "temperature": llm_config["temperature"],
            "max_generation_attempts_per_batch": max_generation_attempts,
            "max_transport_attempts": 1,
            "batch_class_limit": PLACEMENT_BATCH_CLASS_LIMIT,
            "planned_requests": len(batches),
            "maximum_requests": len(batches) * max_generation_attempts,
            "source_type_list": str(source_path),
            "layout_catalog": str(catalog_path),
            "system_prompt": prompt.PLACEMENT_SYSTEM_PROMPT,
            "batches": [
                {
                    "batch_index": index,
                    "class_names": [
                        name for name, _definition, _parent in _definitions(batch)
                    ],
                    "user_prompt": _prompt_payload(
                        batch,
                        catalog,
                        "No preceding failure.",
                    ),
                }
                for index, batch in enumerate(batches, start=1)
            ],
        },
    )
    attempts: list[dict[str, Any]] = []
    combined: dict[str, dict[str, Any]] = {}
    for batch_index, batch in enumerate(batches, start=1):
        feedback = "No preceding failure."
        batch_placements: dict[str, dict[str, Any]] | None = None
        for batch_attempt in range(1, max_generation_attempts + 1):
            user_prompt = _prompt_payload(batch, catalog, feedback)
            code, response = call_llm_api(
                prompt.PLACEMENT_SYSTEM_PROMPT,
                user_prompt,
                model_scenario="generate",
                model=model,
                max_transport_attempts=1,
            )
            error: str | None = None
            if code == "[PASS]":
                parse_code, payload = extract_json_from_answer(
                    response.get("answer", "")
                )
                try:
                    if parse_code != "[PASS]":
                        raise ValueError(parse_code)
                    batch_placements = _validated_placements(
                        payload,
                        batch,
                        catalog,
                    )
                except (KeyError, TypeError, ValueError) as validation_error:
                    error = (
                        f"{type(validation_error).__name__}: {validation_error}"
                    )
            else:
                error = str(response.get("error") or code)
            attempts.append(
                redact(
                    {
                        "stage": "placement_generation",
                        "attempt_index": len(attempts) + 1,
                        "batch_index": batch_index,
                        "batch_count": len(batches),
                        "batch_attempt": batch_attempt,
                        "class_names": [
                            name
                            for name, _definition, _parent in _definitions(batch)
                        ],
                        "code": (
                            "[PASS]" if batch_placements is not None else code
                        ),
                        "llm_input": {
                            "system_prompt": prompt.PLACEMENT_SYSTEM_PROMPT,
                            "user_prompt": user_prompt,
                        },
                        "llm_output": response,
                        "validation": {
                            "passed": batch_placements is not None,
                            "error": error,
                        },
                    }
                )
            )
            write_jsonl(attempts_path, attempts)
            if batch_placements is not None:
                combined.update(batch_placements)
                break
            feedback = error or "Unknown placement validation failure."
        if batch_placements is None:
            raise PlacementGenerationError(
                f"placement batch {batch_index}/{len(batches)} failed after "
                f"{max_generation_attempts} attempts: {feedback}"
            )

    placements = _validated_placements(
        {"placements": combined},
        type_list,
        catalog,
    )
    enriched = merge_placements(type_list, placements)
    validate_placement_type_list(enriched, catalog)
    write_json(output_path, enriched)
    if sha256_json(_without_placements(enriched)) != sha256_json(type_list):
        raise PlacementGenerationError("placement merge changed source fields")
    return output_path
