"""Single-Domain, read-only assets shared by generation worker threads."""

from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import re
from threading import RLock
from types import MappingProxyType, ModuleType
from typing import Any, Iterable, Mapping
from uuid import uuid4
from weakref import WeakValueDictionary

from src.contracts import ContractPackage
from src.contracts.errors import EnvironmentContractError
from src.object_model import BaseProperty, TargetRegistry

from .execution import ToolCatalogBuilder
from .loading import DomainRegistry, LoadedWorld, WorldLoader
from .loading.loader import snapshot_from_world
from .loading.modules import load_module_from_tree


def _value_schema(prop: BaseProperty[Any]) -> dict[str, Any]:
    """Return the value schema."""
    value = prop.value
    if isinstance(value, bool):
        schema: dict[str, Any] = {"type": "boolean"}
    elif isinstance(value, int):
        schema = {"type": "integer"}
    elif isinstance(value, float):
        schema = {"type": "number"}
    elif isinstance(value, str):
        schema = {"type": "string"}
    else:
        schema = {}
    choices = getattr(prop, "choices", None)
    if choices:
        schema["enum"] = list(choices)
    for name in ("minimum", "maximum", "step", "step_origin", "precision"):
        constraint = getattr(prop, name, None)
        if constraint is not None:
            schema[name] = constraint
    return schema


@dataclass(frozen=True)
class WorldBlueprint:
    """Validated immutable inputs from which each worker builds fresh state."""

    root: Path
    loaded_world: LoadedWorld
    tool_catalog: dict[str, Any]
    tool_index: dict[str, dict[str, Any]]

    @property
    def domain(self) -> str:
        """Return the domain."""
        return str(self.loaded_world.world["domain"]["type"])

    @property
    def world_id(self) -> str:
        """Return the world ID."""
        return str(self.loaded_world.world["world_id"])


class DomainRuntimeCache:
    """Load one Domain once, then share only read-only assets across workers."""

    def __init__(
        self,
        domain: str,
        domain_path: str | Path,
        *,
        contract_root: str | Path | None = None,
        domain_config_root: str | Path | None = None,
    ) -> None:
        """Initialize the DomainRuntimeCache."""
        self.domain = str(domain)
        self.domain_path = Path(domain_path).resolve()
        self.contract = ContractPackage(contract_root)
        self.domain_registry = DomainRegistry.from_path(
            self.domain, self.domain_path, self.contract,
            domain_config_root=domain_config_root,
        )
        self.domain_definition = self.domain_registry.resolve(self.domain)
        self.world_loader = WorldLoader(
            contract=self.contract, domain=self.domain, domain_path=self.domain_path,
            domain_registry=self.domain_registry,
        )
        self.property_catalog = deepcopy(
            self.domain_definition.property_catalog
        )
        self.templates = deepcopy(
            self.domain_definition.template_payloads
        )
        (
            modules,
            classes,
            instances,
            prototypes,
            descriptors,
        ) = self._load_class_assets()
        self.class_modules: Mapping[str, ModuleType] = MappingProxyType(modules)
        self.class_types: Mapping[str, type] = MappingProxyType(classes)
        self._model_instances: Mapping[str, Any] = MappingProxyType(instances)
        self.model_prototypes: Mapping[str, dict[str, Any]] = MappingProxyType(
            prototypes
        )
        self.class_tool_descriptors: Mapping[
            str, tuple[dict[str, Any], ...]
        ] = MappingProxyType(descriptors)
        # Live Worlds retain their own blueprints. Keep only recent accesses
        # strongly cached so completed task catalogs do not grow with the corpus.
        self._blueprints: WeakValueDictionary[Path, WorldBlueprint] = WeakValueDictionary()
        self._recent_blueprints: deque[WorldBlueprint] = deque(maxlen=128)
        self._world_read_counts: dict[Path, int] = {}
        self._lock = RLock()

    def _load_class_assets(
        self,
    ) -> tuple[
        dict[str, ModuleType],
        dict[str, type],
        dict[str, Any],
        dict[str, dict[str, Any]],
        dict[str, tuple[dict[str, Any], ...]],
    ]:
        """Return the class assets."""
        modules: dict[str, ModuleType] = {}
        classes: dict[str, type] = {}
        instances: dict[str, Any] = {}
        prototypes: dict[str, dict[str, Any]] = {}
        descriptors: dict[str, tuple[dict[str, Any], ...]] = {}
        builder = ToolCatalogBuilder(self.contract)
        namespace = f"dcb_environment_{uuid4().hex}"
        for class_id, path in sorted(self.domain_definition.classes.items()):
            module = load_module_from_tree(
                path,
                tree_root=self.domain_path,
                namespace=namespace,
            )
            class_name = class_id.rsplit(".", 1)[-1]
            cls = getattr(module, class_name, None)
            if not isinstance(cls, type) or cls.__module__ != module.__name__:
                raise EnvironmentContractError(
                    "OBJECT_CLASS_LOAD_ERROR",
                    class_id,
                    class_name,
                )
            try:
                instance = cls()
            except Exception as error:
                raise EnvironmentContractError(
                    "OBJECT_CLASS_LOAD_ERROR",
                    class_id,
                    f"cannot create model prototype: {error}",
                ) from error
            disabled_properties = set(getattr(instance, "_disabled", {}).get("properties", []))
            properties = {
                name: {
                    "value": deepcopy(value.value),
                    "schema": _value_schema(value),
                }
                for name, value in vars(instance).items()
                if isinstance(value, BaseProperty) and name not in disabled_properties
            }
            if not properties:
                raise EnvironmentContractError(
                    "OBJECT_PROPERTY_MISSING",
                    class_id,
                    "model prototype exposes no BaseProperty values",
                )
            modules[class_id] = module
            classes[class_id] = cls
            instances[class_id] = instance
            prototypes[class_id] = properties
            descriptors[class_id] = builder.describe_device(
                instance, self.domain_definition.specifications[class_id]
            )
        named = {key.rsplit(".", 1)[-1]: value for key, value in classes.items()}
        for base_name, base in self.domain_definition.placement_type_list.items():
            for child in base["inherited_list"]:
                if not issubclass(named[child["class"]], named[base_name]):
                    raise ValueError(f"placement inheritance differs for {child['class']}")
        return modules, classes, instances, prototypes, descriptors

    def resolve_class(self, class_id: str) -> type:
        """Return the class."""
        try:
            return self.class_types[class_id]
        except KeyError as error:
            raise EnvironmentContractError(
                "OBJECT_CLASS_NOT_FOUND",
                "$.objects.class",
                class_id,
            ) from error

    def assert_domain(self, domain: str) -> None:
        """Assert the domain."""
        if domain != self.domain:
            raise ValueError(
                f"runtime cache Domain {self.domain!r} differs from {domain!r}"
            )

    def preload_worlds(
        self,
        world_roots: Iterable[str | Path],
    ) -> tuple[WorldBlueprint, ...]:
        """Serially read all requested source worlds before workers start."""
        return tuple(self.load_world_blueprint(root) for root in world_roots)

    def load_world_blueprint(
        self,
        world_root: str | Path,
    ) -> WorldBlueprint:
        """Return the world blueprint."""
        root = Path(world_root).resolve()
        with self._lock:
            cached = self._blueprints.get(root)
            if cached is not None:
                self._recent_blueprints.append(cached)
                return cached
            loaded = self.world_loader.load(root)
            self.assert_domain(str(loaded.world["domain"]["type"]))
            blueprint = self._make_blueprint(root, loaded)
            self._blueprints[root] = blueprint
            self._recent_blueprints.append(blueprint)
            self._world_read_counts[root] = (
                self._world_read_counts.get(root, 0) + 1
            )
            return blueprint

    def owns_blueprint(self, blueprint: WorldBlueprint) -> bool:
        """Return whether this cache owns the blueprint."""
        with self._lock:
            return self._blueprints.get(blueprint.root) is blueprint

    def blueprint_from_world_init(
        self,
        world_root: str | Path,
        world_init: dict[str, Any],
    ) -> WorldBlueprint:
        """Resolve a generated world entirely in memory."""
        root = Path(world_root).resolve()
        request = deepcopy(world_init)
        self.contract.validate_world_init(request)
        self.assert_domain(str(request["domain"]["type"]))
        world = self.world_loader.template_resolver.resolve(request)
        self.contract.validate_resolved_world(world)
        initial_snapshot = snapshot_from_world(world)
        self.contract.validate_snapshot(
            initial_snapshot,
            world,
            label="generated_initial",
        )
        loaded = LoadedWorld(
            root=root,
            world_init=request,
            world=world,
            initial_snapshot=initial_snapshot,
            domain=self.domain_definition,
            target_registry=TargetRegistry.from_world(world),
            domain_registry=self.domain_registry,
            contract=self.contract,
        )
        blueprint = self._make_blueprint(root, loaded)
        with self._lock:
            self._blueprints[root] = blueprint
            self._recent_blueprints.append(blueprint)
        return blueprint

    def rebind_world_blueprint(
        self,
        source: WorldBlueprint,
        world_root: str | Path,
        world_init: dict[str, Any],
    ) -> WorldBlueprint:
        """Reuse a validated World structure when only its ID/root changes."""
        if not self.owns_blueprint(source):
            raise ValueError("source World blueprint is not owned by this cache")
        root = Path(world_root).resolve()
        request = deepcopy(world_init)
        world_id = request.get("world_id")
        if (
            not isinstance(world_id, str)
            or re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", world_id) is None
            or world_id == "session"
        ):
            raise ValueError("rebound world_id is not a non-session identifier")
        comparable = deepcopy(request)
        comparable["world_id"] = source.world_id
        if comparable != source.loaded_world.world_init:
            raise ValueError("rebound World may only change world_id and root")
        with self._lock:
            cached = self._blueprints.get(root)
            if cached is not None:
                if cached.world_id != world_id:
                    raise ValueError("cached World root has another world_id")
                self._recent_blueprints.append(cached)
                return cached

        world = deepcopy(source.loaded_world.world)
        world["world_id"] = world_id
        initial_snapshot = deepcopy(source.loaded_world.initial_snapshot)
        initial_snapshot["world_id"] = world_id
        loaded = LoadedWorld(
            root=root,
            world_init=request,
            world=world,
            initial_snapshot=initial_snapshot,
            domain=source.loaded_world.domain,
            target_registry=source.loaded_world.target_registry,
            domain_registry=source.loaded_world.domain_registry,
            contract=source.loaded_world.contract,
        )
        tool_catalog = deepcopy(source.tool_catalog)
        tool_catalog["world_id"] = world_id
        blueprint = WorldBlueprint(
            root=root,
            loaded_world=loaded,
            tool_catalog=tool_catalog,
            tool_index=deepcopy(source.tool_index),
        )
        with self._lock:
            existing = self._blueprints.setdefault(root, blueprint)
            self._recent_blueprints.append(existing)
        if existing.world_id != world_id:
            raise ValueError("cached World root has another world_id")
        return existing

    def _make_blueprint(
        self,
        root: Path,
        loaded: LoadedWorld,
    ) -> WorldBlueprint:
        """Return the blueprint."""
        devices = {
            device_id: self._model_instances[spec["class"]]
            for device_id, spec in loaded.world["objects"].items()
        }
        exposed = {
            device_id: tuple(spec["properties"])
            for device_id, spec in loaded.world["objects"].items()
        }
        catalog, index = ToolCatalogBuilder(self.contract).build(
            loaded.world,
            devices,
            exposed,
            class_descriptors=dict(self.class_tool_descriptors),
        )
        return WorldBlueprint(
            root=root,
            loaded_world=loaded,
            tool_catalog=deepcopy(catalog),
            tool_index=deepcopy(index),
        )

    @property
    def world_read_counts(self) -> dict[Path, int]:
        """Return the world read counts."""
        return dict(self._world_read_counts)
