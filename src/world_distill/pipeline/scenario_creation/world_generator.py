"""Generate reusable Worlds with deterministic placement and initialization."""

from __future__ import annotations

from concurrent.futures import as_completed, ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import random
import re
from typing import Any

from src.contracts.capabilities import PROCESS_PROPERTIES
from src.runtime import DomainRuntimeCache, World
from src.runtime.loading.templates import apply_init_operations
from src.utils import progress_bar, write_json
from src.world_distill.pipeline.list_creation.object_class_placement import (
    effective_max,
    validate_placement_type_list,
)
from src.world_distill.pipeline.models import (
    GeneratedWorld,
    GenerationProvenance,
    WorldGenerationInput,
    WorldGenerationOutput,
)

from .generation_records import GenerationRecords
from .task_inventory import schema_accepts
from .world_initializer import (
    constructor_initialization_operations,
    initial_temperature_stability_operations,
    validate_initial_temperature_stability,
    _is_active_temperature_controller,
)


class WorldGenerationError(RuntimeError):
    """The world stage could not create a valid reusable world pool."""


def _snake_case(name: str) -> str:
    """Return the snake case."""
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
    return re.sub(r"[^a-z0-9_]+", "_", snake).strip("_") or "device"


def _sample_numeric(
    schema: dict[str, Any],
    current: int | float,
    rng: random.Random,
) -> int | float:
    """Return the numeric."""
    minimum = schema.get("minimum")
    maximum = schema.get("maximum")
    step = schema.get("step")
    precision = schema.get("precision")
    if step is None and precision is not None:
        step = 10 ** -int(precision)
    magnitude = max(abs(float(current)) * 0.25, float(step or 1))
    low = float(current) - magnitude
    high = float(current) + magnitude
    if minimum is not None:
        low = max(low, float(minimum))
    if maximum is not None:
        high = min(high, float(maximum))
    if low > high:
        low = high = float(current)
    sampled = rng.uniform(low, high)
    if schema.get("type") == "integer":
        sampled = round(sampled)
    if step:
        origin = float(schema.get("step_origin", minimum or 0))
        sampled = origin + round((float(sampled) - origin) / float(step)) * float(step)
    if minimum is not None:
        sampled = max(sampled, minimum)
    if maximum is not None:
        sampled = min(sampled, maximum)
    return (
        int(sampled)
        if schema.get("type") == "integer"
        else round(float(sampled), int(precision) if precision is not None else 3)
    )


def _sample_value(
    schema: dict[str, Any],
    current: Any,
    rng: random.Random,
) -> Any:
    """Return the value."""
    configured = schema.get("initial_values")
    if configured:
        return deepcopy(rng.choice(configured))
    choices = schema.get("enum")
    if choices:
        return deepcopy(rng.choice(list(choices)))
    kind = schema.get("type")
    if kind == "boolean" or isinstance(current, bool):
        return bool(rng.getrandbits(1))
    if kind in {"integer", "number"} and isinstance(current, (int, float)):
        return _sample_numeric(schema, current, rng)
    return deepcopy(current)


def _default_for_schema(schema: dict[str, Any]) -> Any:
    """Return the default for schema."""
    kind = schema["type"]
    if kind == "integer":
        minimum = schema.get("minimum", 0)
        maximum = schema.get("maximum", minimum + 100)
        return int(round((minimum + maximum) / 2))
    if kind == "number":
        minimum = schema.get("minimum", 0.0)
        maximum = schema.get("maximum", minimum + 100.0)
        return float((minimum + maximum) / 2)
    if kind == "boolean":
        return False
    return "default"


def _choose_stable_space_temperatures(
    spaces: dict[str, Any],
    objects: dict[str, Any],
    property_catalog: dict[str, Any],
    prototypes: dict[str, dict[str, Any]],
    rng: random.Random,
) -> None:
    """Choose configured ambient values accepted by every active controller."""
    configured = property_catalog["space_properties"]["temperature"][
        "initial_values"
    ]
    by_space: dict[str, list[dict[str, Any]]] = {}
    for device in objects.values():
        if _is_active_temperature_controller(device["properties"]):
            by_space.setdefault(device["space_id"], []).append(device)
    for space_id, controllers in by_space.items():
        choices = [
            value
            for value in configured
            if all(
                schema_accepts(
                    prototypes[device["class"]]["target_temperature"]["schema"],
                    value,
                )
                for device in controllers
            )
        ]
        if not choices:
            raise WorldGenerationError(
                f"no configured temperature is valid for active controllers in {space_id}"
            )
        ambient = spaces[space_id]["properties"]["temperature"]
        if ambient not in choices:
            spaces[space_id]["properties"]["temperature"] = rng.choice(choices)


def _placement_inventory(
    type_list: dict[str, Any],
    placements: dict[str, dict[str, Any]],
    prototypes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Join placement classes to the active Domain model inventory."""
    class_ids = {class_id.rsplit(".", 1)[-1]: class_id for class_id in prototypes}
    expected = set(type_list)
    expected.update(
        child["class"]
        for base in type_list.values()
        for child in base["inherited_list"]
    )
    if set(class_ids) != expected:
        raise WorldGenerationError(
            "placement type list differs from the active Domain classes"
        )
    members: dict[str, dict[str, Any]] = {}
    families: dict[str, dict[str, Any]] = {}
    for base_name, base in type_list.items():
        children = [item["class"] for item in base["inherited_list"]]
        family_members = ([] if base.get("base_only") else [base_name]) + children
        families[base_name] = {
            "root": base_name,
            "members": tuple(family_members),
            "limits": placements[base_name],
            "base_only": bool(base.get("base_only")),
            "has_children": bool(children),
        }
        if not base.get("base_only"):
            members[base_name] = {
                "class_id": class_ids[base_name],
                "family": base_name,
                "allowed": tuple(placements[base_name]["allowed_space_types"]),
                "limits": None if children else placements[base_name],
            }
        for child in children:
            members[child] = {
                "class_id": class_ids[child],
                "family": base_name,
                "allowed": tuple(placements[child]["allowed_space_types"]),
                "limits": placements[child],
            }
    return {"members": members, "families": families}


def _layout_for_index(
    catalog: dict[str, Any],
    random_seed: int,
    index: int,
) -> dict[str, Any]:
    """Return a seeded layout while cycling through the complete catalog."""
    layouts = list(catalog["layouts"])
    random.Random(f"dcb-home-layouts:{random_seed}").shuffle(layouts)
    return layouts[(index - 1) % len(layouts)]


def _device_slots(
    spaces: dict[str, Any],
    inventory: dict[str, Any],
    rng: random.Random,
    *,
    soft_min: int,
    soft_max: int,
    implicit_space_max: int,
    implicit_world_max: int,
    connection_spaces: dict[str, set[str]] | None = None,
) -> list[tuple[str, str, str]]:
    """Place connection devices, satisfy minima, then fill room soft targets."""
    members = inventory["members"]
    families = inventory["families"]
    connection_spaces = connection_spaces or {}
    class_space: dict[tuple[str, str], int] = {}
    class_world: dict[str, int] = {}
    family_space: dict[tuple[str, str], int] = {}
    family_world: dict[str, int] = {}
    room_total: dict[str | None, int] = {space_id: 0 for space_id in (list(spaces) or [None])}
    slots: list[tuple[str, str, str]] = []

    def can_add(class_name: str, space_id: str) -> bool:
        member = members[class_name]
        if class_name in connection_spaces and (
            space_id not in connection_spaces[class_name]
            or class_space.get((class_name, space_id), 0) >= 1
        ):
            return False
        if space_id is not None and spaces[space_id]["type"] not in member["allowed"]:
            return False
        family_name = member["family"]
        family_limits = families[family_name]["limits"]
        if space_id is not None and family_space.get((family_name, space_id), 0) >= effective_max(
            family_limits["max_items_per_space"], implicit_space_max
        ):
            return False
        if family_world.get(family_name, 0) >= effective_max(
            family_limits["max_items_per_world"], implicit_world_max
        ):
            return False
        limits = member["limits"]
        return limits is None or (
            (space_id is None or class_space.get((class_name, space_id), 0)
            < effective_max(limits["max_items_per_space"], implicit_space_max))
            and class_world.get(class_name, 0)
            < effective_max(limits["max_items_per_world"], implicit_world_max)
        )

    def add(class_name: str, space_id: str) -> None:
        member = members[class_name]
        family_name = member["family"]
        class_space[(class_name, space_id)] = (
            class_space.get((class_name, space_id), 0) + 1
        )
        class_world[class_name] = class_world.get(class_name, 0) + 1
        family_space[(family_name, space_id)] = (
            family_space.get((family_name, space_id), 0) + 1
        )
        family_world[family_name] = family_world.get(family_name, 0) + 1
        room_total[space_id] += 1
        slots.append((class_name, member["class_id"], space_id))

    def add_from(
        class_names: list[str],
        space_ids: list[str],
        label: str,
        *,
        prefer_first: bool = False,
    ) -> None:
        candidates = [
            (class_name, space_id)
            for class_name in class_names
            for space_id in space_ids
            if can_add(class_name, space_id)
        ]
        if not candidates:
            raise WorldGenerationError(f"cannot satisfy placement minimum for {label}")
        if prefer_first:
            preferred = [item for item in candidates if item[0] == class_names[0]]
            if preferred:
                candidates = preferred
        add(*rng.choice(candidates))

    # Reserve topology requirements before random choices consume family quotas.
    for class_name, required_spaces in connection_spaces.items():
        if required_spaces and class_name not in members:
            raise WorldGenerationError(
                f"connection requires unavailable model class {class_name}"
            )
        for space_id in sorted(required_spaces):
            if space_id not in spaces or not can_add(class_name, space_id):
                raise WorldGenerationError(
                    f"connection placement conflicts with limits for {class_name} in {space_id}"
                )
            add(class_name, space_id)

    for class_name, member in members.items():
        limits = member["limits"]
        if limits is None:
            continue
        for space_id, space in spaces.items():
            if space["type"] not in member["allowed"]:
                continue
            while class_space.get((class_name, space_id), 0) < limits[
                "min_items_per_space"
            ]:
                add_from([class_name], [space_id], f"{class_name} in {space_id}")

    for family_name, family in families.items():
        if not family["has_children"]:
            continue
        limits = family["limits"]
        family_members = list(family["members"])
        for space_id, space in spaces.items():
            if space["type"] not in limits["allowed_space_types"]:
                continue
            while family_space.get((family_name, space_id), 0) < limits[
                "min_items_per_space"
            ]:
                add_from(
                    family_members,
                    [space_id],
                    f"{family_name} family in {space_id}",
                    prefer_first=not family["base_only"],
                )

    for class_name, member in members.items():
        limits = member["limits"]
        if limits is None:
            continue
        compatible = [
            space_id
            for space_id, space in spaces.items()
            if space["type"] in member["allowed"]
        ] if spaces else [None]
        while class_world.get(class_name, 0) < limits["min_items_per_world"]:
            add_from([class_name], compatible, f"{class_name} per world")

    for family_name, family in families.items():
        if not family["has_children"]:
            continue
        limits = family["limits"]
        compatible = [
            space_id
            for space_id, space in spaces.items()
            if space["type"] in limits["allowed_space_types"]
        ] if spaces else [None]
        while family_world.get(family_name, 0) < limits["min_items_per_world"]:
            add_from(
                list(family["members"]),
                compatible,
                f"{family_name} family per world",
                prefer_first=not family["base_only"],
            )

    for space_id in room_total:
        target = rng.randint(soft_min, soft_max)
        while room_total[space_id] < target:
            candidates = [
                class_name
                for class_name in members
                if can_add(class_name, space_id)
            ]
            if not candidates:
                break
            add(rng.choice(candidates), space_id)
    return slots


def _build_world_init(
    request: WorldGenerationInput,
    *,
    world_id: str,
    world_seed: int,
    layout: dict[str, Any],
    layout_catalog: dict[str, Any],
    placement_inventory: dict[str, Any],
    model_inventory: dict[str, Any],
    property_catalog: dict[str, Any],
    prototypes: dict[str, dict[str, Any]],
    class_tools: dict[str, Any],
    implicit_space_max: int,
    implicit_world_max: int,
    process_classes: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Return the world init."""
    rng = random.Random(world_seed)
    spaces: dict[str, Any] = {}
    for index, space_spec in enumerate(layout["spaces"], start=1):
        space_id = space_spec["id"]
        space_type = space_spec["type"]
        properties = {}
        for name in property_catalog["space_types"][space_type]:
            schema = property_catalog["space_properties"][name]
            prototype = _default_for_schema(schema)
            properties[name] = _sample_value(schema, prototype, rng)
        metadata = {
            "description": f"Generated {space_type.replace('_', ' ')} {index}",
            "generation_index": index,
        }
        if "floor" in space_spec:
            metadata["floor"] = space_spec["floor"]
        spaces[space_id] = {
            "type": space_type,
            "virtual": space_spec.get("virtual", False),
            "properties": properties,
            "metadata": metadata,
        }

    space_ids = [key for key, space in spaces.items() if not space["virtual"]]
    people_limit = min(5, len(space_ids), len(layout_catalog["person_names"]))
    people_count = rng.randint(min(2, people_limit), people_limit)
    people: dict[str, dict[str, str]] = {}
    for person_id in rng.sample(layout_catalog["person_names"], people_count):
        space_id = rng.choice(space_ids)
        people[person_id] = {
            "name": person_id,
            "space_id": space_id,
        }
        spaces[space_id]["metadata"].setdefault("occupants", []).append(person_id)
    for space in spaces.values():
        space["metadata"].setdefault("occupants", [])

    # A class bound in another layout must not become a free-standing device
    # when the selected layout has no connection for it (for example Tailgate).
    connection_spaces: dict[str, set[str]] = {
        connection["device_class"]: set()
        for variant in layout_catalog["layouts"]
        for connection in variant["connections"]
        if "device_class" in connection
    }
    for connection in layout["connections"]:
        if "device_class" in connection:
            connection_spaces.setdefault(connection["device_class"], set()).add(
                connection["space_1"]
            )

    device_slots = _device_slots(
        spaces,
        placement_inventory,
        rng,
        soft_min=request.min_devices_per_space,
        soft_max=request.max_devices_per_space,
        implicit_space_max=implicit_space_max,
        implicit_world_max=implicit_world_max,
        connection_spaces=connection_spaces,
    )
    family_counts: dict[str, int] = {}
    objects: dict[str, Any] = {}
    for class_name, class_id, space_id in device_slots:
        base_name = _snake_case(class_name)
        family_name = _snake_case(
            placement_inventory["members"][class_name]["family"]
        )
        family_counts[family_name] = family_counts.get(family_name, 0) + 1
        object_id = f"{base_name}_{family_counts[family_name]}"
        independent_properties = set()
        for tool in class_tools[class_id]:
            semantics = tool.get("semantics", {})
            prop = semantics.get("property")
            if (semantics.get("kind") == "set" and set(tool["writes"]) == {prop}
                and (prop == "power" or not (set(tool["reads"]) - {prop, "power"}))
                and not (set(semantics.get("preconditions", {})) - {"power"})):
                independent_properties.add(prop)
        # Coupled configurations and derived state must start from coherent
        # defaults; task-world perturbations vary them through public actions.
        properties = {
            name: deepcopy(spec["value"]) if not spaces or name not in independent_properties or (class_id in process_classes and name in PROCESS_PROPERTIES) else _sample_value(spec["schema"], spec["value"], rng)
            for name, spec in prototypes[class_id].items()
        }
        objects[object_id] = {
            "class": class_id,
            "space_id": space_id,
            "properties": properties,
            "metadata": {
                "description": f"Generated {class_id.rsplit('.', 1)[-1]} in {space_id}",
            },
        }

    if "temperature" in property_catalog["space_properties"]:
        _choose_stable_space_temperatures(
            spaces, objects, property_catalog, prototypes, rng
        )

    stabilized = apply_init_operations(
        {"spaces": spaces, "objects": objects},
        initial_temperature_stability_operations(
            {"spaces": spaces, "objects": objects}
        ),
    )
    spaces = stabilized["spaces"]
    objects = stabilized["objects"]
    validate_initial_temperature_stability(stabilized)

    runtime = deepcopy(layout_catalog["runtime"])
    domain_metadata = deepcopy(layout_catalog["domain_metadata"])
    parent_class = layout_catalog.get("containment_root_class")
    if parent_class is not None:
        parents = [key for key, obj in objects.items() if obj["class"].rsplit(".", 1)[-1] == parent_class]
        if len(parents) != 1:
            raise WorldGenerationError(f"expected one containment root {parent_class}, found {len(parents)}")
        relations = domain_metadata.setdefault("relations", [])
        children = {item["target_id"] for item in relations if item["type"] == "contains"}
        relations.extend({"type": "contains", "source_id": parents[0], "target_id": key}
                         for key in objects if key != parents[0] and key not in children)
    domain_metadata["info"] = {
        **deepcopy(domain_metadata.get("info", {})),
        "name": f"Generated {request.domain} world {world_id}",
    }
    domain_metadata["connections"] = deepcopy(layout["connections"])
    for connection in domain_metadata["connections"]:
        if "device_class" in connection:
            name = connection.pop("device_class")
            matches = [key for key, item in objects.items() if item["class"].rsplit(".", 1)[-1] == name and item["space_id"] == connection["space_1"]]
            if len(matches) != 1:
                raise WorldGenerationError(f"connection requires exactly one {name} in {connection['space_1']}")
            connection["device_id"] = matches[0]
    scene_metadata = deepcopy(layout_catalog["scene_metadata"])
    scene_metadata.update(
        {
            "generation_run_id": request.generation_run_id,
            "world_random_seed": world_seed,
            "layout_id": layout["id"],
            "model_inventory_version": model_inventory["version"],
            "people": people,
        }
    )
    return {
        "world_id": world_id,
        "domain": {"type": request.domain},
        "template": None,
        "config": {
            "domain_metadata": domain_metadata,
            "spaces": spaces,
            "objects": objects,
            "runtime": runtime,
            "scene_metadata": scene_metadata,
        },
        "init": [],
    }


def _validate_request(request: WorldGenerationInput) -> None:
    """Validate the request."""
    if request.world_count < 1:
        raise ValueError("world_count must be positive")
    if request.max_workers < 1:
        raise ValueError("max_workers must be positive")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,47}", request.world_id_prefix):
        raise ValueError("world_id_prefix must be a short valid identifier")
    if (
        request.min_devices_per_space < 1
        or request.max_devices_per_space < request.min_devices_per_space
    ):
        raise ValueError("invalid devices_per_space soft bounds")


def _generate_world(
    request: WorldGenerationInput,
    *,
    index: int,
    runtime_cache: DomainRuntimeCache,
    model_inventory: dict[str, Any],
    property_catalog: dict[str, Any],
    prototypes: dict[str, dict[str, Any]],
    layout_catalog: dict[str, Any],
    placement_inventory: dict[str, Any],
    implicit_space_max: int,
    implicit_world_max: int,
) -> tuple[int, GeneratedWorld, dict[str, Any]]:
    """Generate, validate, and publish one independent world."""
    world_id = f"{request.world_id_prefix}_{index:04d}"
    world_seed = request.random_seed + index - 1
    world_init = _build_world_init(
        request,
        world_id=world_id,
        world_seed=world_seed,
        layout=_layout_for_index(layout_catalog, request.random_seed, index),
        layout_catalog=layout_catalog,
        placement_inventory=placement_inventory,
        model_inventory=model_inventory,
        property_catalog=property_catalog,
        prototypes=prototypes,
        class_tools=runtime_cache.class_tool_descriptors,
        implicit_space_max=implicit_space_max,
        implicit_world_max=implicit_world_max,
        process_classes=frozenset(class_id for class_id, class_type in runtime_cache.class_types.items() if hasattr(class_type, "PROCESS")),
    )
    world_root = (request.world_output_root / world_id).resolve()
    world_init["config"] = apply_init_operations(
        world_init["config"], constructor_initialization_operations(world_init["config"], runtime_cache)
    )
    blueprint = runtime_cache.blueprint_from_world_init(world_root, world_init)
    validated_world = World(
        world_root,
        runtime_cache=runtime_cache,
        blueprint=blueprint,
    )
    resolved_world = validated_world.get_world_spec()
    state = validated_world.get_initial_state()
    destination_world_init = world_root / "world_init.json"
    destination_resolved = world_root / "resolved_world.json"
    write_json(destination_world_init, world_init)
    write_json(destination_resolved, resolved_world)
    artifact = GeneratedWorld(
        world_id=world_id,
        world_root=world_root,
        world_init_path=destination_world_init,
        resolved_world_path=destination_resolved,
        random_seed=world_seed,
        space_count=len(state["spaces"]),
        device_count=len(state["objects"]),
    )
    success_record = {
        "generation_run_id": request.generation_run_id,
        "world_id": world_id,
        "domain": request.domain,
        "world_root": str(world_root),
        "world_init_path": str(destination_world_init),
        "resolved_world_path": str(destination_resolved),
        "random_seed": world_seed,
        "space_count": artifact.space_count,
        "device_count": artifact.device_count,
    }
    return index, artifact, success_record


def _artifact_from_record(record: dict[str, Any]) -> GeneratedWorld:
    """Return the artifact from record."""
    return GeneratedWorld(
        world_id=record["world_id"],
        world_root=Path(record["world_root"]),
        world_init_path=Path(record["world_init_path"]),
        resolved_world_path=Path(record["resolved_world_path"]),
        random_seed=record["random_seed"],
        space_count=record["space_count"],
        device_count=record["device_count"],
    )


def _missing_world_indices(
    records: tuple[dict[str, Any], ...],
    request: WorldGenerationInput,
) -> list[int]:
    """Return the missing world indices."""
    needed = max(0, request.world_count - len(records))
    used: set[int] = set()
    pattern = re.compile(rf"^{re.escape(request.world_id_prefix)}_(\d+)$")
    for record in records:
        match = pattern.fullmatch(record["world_id"])
        if match is not None:
            used.add(int(match.group(1)))
    result: list[int] = []
    candidate = 1
    while len(result) < needed:
        if candidate not in used:
            result.append(candidate)
        candidate += 1
    return result


def generate_worlds(
    request: WorldGenerationInput,
    *,
    show_progress: bool = False,
    runtime_cache: DomainRuntimeCache | None = None,
    implicit_space_max: int = 3,
    implicit_world_max: int = 20,
) -> WorldGenerationOutput:
    """Create a reusable world pool using seeded random sampling only."""
    _validate_request(request)
    cache = runtime_cache or DomainRuntimeCache(
        request.domain,
        request.domain_path,
    )
    cache.assert_domain(request.domain)
    if cache.domain_path != request.domain_path.resolve():
        raise ValueError("domain_path differs from the runtime cache")
    if implicit_space_max < 1 or implicit_world_max < 1:
        raise ValueError("implicit placement maxima must be positive")
    if request.domain == "Home" and request.template_id is not None:
        raise ValueError("Home world generation uses the layout catalog, not a template")
    model_inventory = {"version": cache.domain_definition.version}
    property_catalog = deepcopy(cache.property_catalog)
    layout_catalog = deepcopy(cache.domain_definition.layout_catalog)
    type_list = deepcopy(cache.domain_definition.placement_type_list)
    placements = validate_placement_type_list(
        type_list,
        layout_catalog,
        implicit_space_max=implicit_space_max,
        implicit_world_max=implicit_world_max,
    )
    prototypes = deepcopy(dict(cache.model_prototypes))
    placement_inventory = _placement_inventory(
        type_list,
        placements,
        prototypes,
    )
    run_root = (
        request.run_output_root / request.generation_run_id / "world_generation"
    ).resolve()
    world_list_path = run_root / "world_list.jsonl"
    world_records = GenerationRecords(
        world_list_path,
        id_field="world_id",
        contract=cache.contract,
        schema_id="urn:dcb:v2:schema:world-list-record",
    )
    existing = world_records.records
    for record in existing:
        if record["domain"] != request.domain:
            raise WorldGenerationError("world records contain another Domain")
    indices = _missing_world_indices(existing, request)

    results: list[tuple[int, GeneratedWorld, dict[str, Any]]] = []
    worker_count = min(request.max_workers, len(indices)) if indices else 0
    if indices:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [
                executor.submit(
                    _generate_world,
                    request,
                    index=index,
                    runtime_cache=cache,
                    model_inventory=model_inventory,
                    property_catalog=property_catalog,
                    prototypes=prototypes,
                    layout_catalog=layout_catalog,
                    placement_inventory=placement_inventory,
                    implicit_space_max=implicit_space_max,
                    implicit_world_max=implicit_world_max,
                )
                for index in indices
            ]
            with progress_bar(
                total=len(indices),
                description=f"World generation ({worker_count} workers)",
                unit="world",
                enabled=show_progress,
            ) as progress:
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        world_records.append(result[2])
                        results.append(result)
                    finally:
                        progress.update(1)

    records = world_records.records
    artifacts = sorted(
        (_artifact_from_record(record) for record in records),
        key=lambda artifact: artifact.world_id,
    )
    return WorldGenerationOutput(
        generation_run_id=request.generation_run_id,
        domain=request.domain,
        worlds=tuple(artifacts),
        world_list_path=world_list_path,
        provenance=GenerationProvenance(
            stage="world_generation",
            artifact_paths=tuple(
                path
                for artifact in artifacts
                for path in (
                    artifact.world_init_path,
                    artifact.resolved_world_path,
                )
            ) + (world_list_path,),
            model_scenario=None,
            requested_model=None,
            attempts=len(indices),
            validated=True,
        ),
        resumed=bool(existing),
    )
