from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from src.contracts.errors import EnvironmentContractError


@dataclass(frozen=True, slots=True)
class TargetEntry:
    target_id: str
    kind: str
    value: Any


class TargetRegistry:
    """Resolved global ID registry ordered as session -> spaces -> devices."""

    def __init__(self) -> None:
        """Initialize the TargetRegistry."""
        self._entries: dict[str, TargetEntry] = {}
        self.register("session", "session", None)

    @classmethod
    def from_world(cls, world: dict[str, Any]) -> "TargetRegistry":
        """Create the value from a runtime world."""
        registry = cls()
        for space_id, spec in world["spaces"].items():
            registry.register(space_id, "space", spec)
        for device_id, spec in world["objects"].items():
            registry.register(device_id, "device", spec)
        return registry

    def register(self, target_id: str, kind: str, value: Any) -> TargetEntry:
        """Register a target and return its entry."""
        if target_id in self._entries:
            existing = self._entries[target_id]
            raise EnvironmentContractError(
                "TARGET_ID_COLLISION",
                f"$.{kind}.{target_id}",
                f"already registered as {existing.kind}",
            )
        entry = TargetEntry(target_id=target_id, kind=kind, value=value)
        self._entries[target_id] = entry
        return entry

    def resolve(self, target_id: str, *, expected_kind: str | None = None) -> TargetEntry:
        """Resolve a target by ID and expected kind."""
        try:
            entry = self._entries[target_id]
        except KeyError as exc:
            raise EnvironmentContractError("UNKNOWN_TARGET", "$.target", target_id) from exc
        if expected_kind is not None and entry.kind != expected_kind:
            raise EnvironmentContractError(
                "TARGET_KIND_MISMATCH",
                "$.target",
                f"expected {expected_kind}, got {entry.kind}",
            )
        return entry

    def contains(self, target_id: str) -> bool:
        """Return whether a target ID is registered."""
        return target_id in self._entries

    def ids(self, kind: str | None = None) -> tuple[str, ...]:
        """Return the IDs."""
        return tuple(
            target_id
            for target_id, entry in self._entries.items()
            if kind is None or entry.kind == kind
        )

    def entries(self, kind: str | None = None) -> Iterable[TargetEntry]:
        """Return the entries."""
        return tuple(
            entry for entry in self._entries.values() if kind is None or entry.kind == kind
        )


@dataclass(frozen=True, slots=True)
class DomainDefinition:
    domain_type: str
    version: str
    root: Path
    property_catalog: dict[str, Any]
    templates: dict[str, Path]
    classes: dict[str, Path]
    specifications: dict[str, dict[str, Any]] = field(default_factory=dict)
    template_payloads: dict[str, dict[str, Any]] = field(default_factory=dict)
    layout_catalog: dict[str, Any] = field(default_factory=dict)
    placement_type_list: dict[str, Any] = field(default_factory=dict)
    placements: dict[str, dict[str, Any]] = field(default_factory=dict)
