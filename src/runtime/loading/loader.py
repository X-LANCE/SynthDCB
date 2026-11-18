"""Load and resolve world assets without reading evaluation data."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.contracts import ContractPackage, load_json, strict_equal
from src.contracts.errors import EnvironmentContractError
from src.object_model import DomainDefinition, TargetRegistry

from .domains import DomainRegistry
from .templates import TemplateResolver


def snapshot_from_world(world: dict[str, Any]) -> dict[str, Any]:
    """Build a state snapshot from the resolved world."""
    snapshot: dict[str, Any] = {
        "world_id": world["world_id"],
        "domain": deepcopy(world["domain"]),
        "objects": deepcopy(world["objects"]),
        "spaces": deepcopy(world["spaces"]),
        "runtime": {
            "time_state": deepcopy(world["runtime"]["time_state"]),
            "weather_state": deepcopy(world["runtime"]["weather_state"]),
        },
    }
    if "scene_metadata" in world:
        snapshot["scene_metadata"] = deepcopy(world["scene_metadata"])
    return snapshot


@dataclass(frozen=True)
class LoadedWorld:
    root: Path
    world_init: dict[str, Any]
    world: dict[str, Any]
    initial_snapshot: dict[str, Any]
    domain: DomainDefinition
    target_registry: TargetRegistry
    domain_registry: DomainRegistry
    contract: ContractPackage


class WorldLoader:
    REQUIRED_FILES = ("world_init.json",)

    def __init__(
        self,
        contract_root: str | Path | None = None,
        *,
        domain_path: str | Path | None = None,
        contract: ContractPackage | None = None,
        domain_registry: DomainRegistry | None = None,
        domain: str | None = None,
        domain_config_root: str | Path | None = None,
    ) -> None:
        """Initialize the WorldLoader."""
        self.contract = contract or ContractPackage(contract_root)
        if domain_registry is None:
            if domain is None or domain_path is None:
                raise ValueError("domain and domain_path are required")
            domain_registry = DomainRegistry.from_path(
                domain, domain_path, self.contract, domain_config_root=domain_config_root,
            )
        self.domain_registry = domain_registry
        self.domain = domain or domain_registry.domain_types()[0]
        self.domain_path = domain_registry.resolve(self.domain).root
        self.template_resolver = TemplateResolver(
            self.domain_registry,
            self.contract,
        )

    def load(self, world_root: str | Path) -> LoadedWorld:
        """Load and validate a world from disk."""
        root = Path(world_root).resolve()
        world_init_path = root / "world_init.json"
        if not world_init_path.is_file():
            raise EnvironmentContractError(
                "WORLD_FILE_MISSING",
                str(world_init_path),
                "world_init.json",
            )

        world_init = load_json(world_init_path)
        self.domain_registry.resolve(world_init["domain"]["type"])
        self.contract.validate_world_init(world_init)
        resolved = self.template_resolver.resolve(world_init)
        self.contract.validate_resolved_world(resolved)

        resolved_path = root / "resolved_world.json"
        if resolved_path.is_file():
            stored_resolved = load_json(resolved_path)
            self.contract.validate_resolved_world(stored_resolved)
            if not strict_equal(stored_resolved, resolved):
                raise EnvironmentContractError(
                    "RESOLVED_WORLD_MISMATCH",
                    str(resolved_path),
                    "stored resolved world differs from world_init resolution",
                )
            world = stored_resolved
        else:
            world = resolved

        domain = self.domain_registry.resolve(world["domain"]["type"])
        target_registry = TargetRegistry.from_world(world)
        initial_snapshot = snapshot_from_world(world)
        self.contract.validate_snapshot(
            initial_snapshot,
            world,
            label="generated_initial",
        )

        fixture_path = root / "initial_snapshot.json"
        if fixture_path.is_file():
            fixture = load_json(fixture_path)
            self.contract.validate_snapshot(
                fixture,
                world,
                label="initial_snapshot",
            )
            if not strict_equal(fixture, initial_snapshot):
                raise EnvironmentContractError(
                    "INITIAL_SNAPSHOT_MISMATCH",
                    str(fixture_path),
                    "resolved world differs from initial_snapshot.json",
                )

        return LoadedWorld(
            root=root,
            world_init=world_init,
            world=world,
            initial_snapshot=initial_snapshot,
            domain=domain,
            target_registry=target_registry,
            domain_registry=self.domain_registry,
            contract=self.contract,
        )
