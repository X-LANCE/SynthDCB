from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from .properties import BaseProperty


@dataclass
class SpaceState:
    space_id: str | None
    type: str
    properties: dict[str, Any]
    metadata: dict[str, Any]
    device_ids: list[str] = field(default_factory=list)
    virtual: bool | None = None


@dataclass
class DeviceState:
    device_id: str
    class_path: str
    space_id: str
    property_names: tuple[str, ...]
    metadata: dict[str, Any] | None
    instance: Any
    effect_properties: tuple[str, ...] = ()

    def properties(self) -> dict[str, Any]:
        """Return the properties."""
        values: dict[str, Any] = {}
        for name in self.property_names:
            value = getattr(self.instance, name)
            values[name] = deepcopy(value.value if isinstance(value, BaseProperty) else value)
        return values

    def snapshot(self) -> dict[str, Any]:
        """Return the snapshot."""
        result: dict[str, Any] = {
            "class": self.class_path,
            "space_id": self.space_id,
            "properties": self.properties(),
        }
        if self.metadata is not None:
            result["metadata"] = deepcopy(self.metadata)
        return result


class MutableWorldState:
    def __init__(self, world: dict[str, Any]) -> None:
        """Initialize the MutableWorldState."""
        self.world_id = world["world_id"]
        self.domain_type = world["domain"]["type"]
        self.domain_metadata = deepcopy(world["domain"]["metadata"])
        self.spaces = {
            space_id: SpaceState(
                space_id=space_id,
                type=spec["type"],
                virtual=spec.get("virtual"),
                properties=deepcopy(spec["properties"]),
                metadata=deepcopy(spec["metadata"]),
            )
            for space_id, spec in world["spaces"].items()
        }
        self.devices: dict[str, DeviceState] = {}
        self.time_policy = deepcopy(world["runtime"]["time_policy"])
        self.time_state = deepcopy(world["runtime"]["time_state"])
        self.weather_state = deepcopy(world["runtime"]["weather_state"])
        self.dynamics = deepcopy(world["runtime"]["dynamics"])
        self.scene_metadata = deepcopy(world.get("scene_metadata", {}))

    def attach_device(
        self, device_id: str, spec: dict[str, Any], instance: Any
    ) -> DeviceState:
        """Attach a device to the state."""
        state = DeviceState(
            device_id=device_id,
            class_path=spec["class"],
            space_id=spec.get("space_id"),
            property_names=tuple(spec["properties"]),
            metadata=deepcopy(spec["metadata"]) if "metadata" in spec else None,
            instance=instance,
        )
        self.devices[device_id] = state
        if state.space_id is not None:
            self.spaces[state.space_id].device_ids.append(device_id)
        return state

    def advance_clock_one_minute(self) -> None:
        """Advance the state clock by one minute."""
        current = datetime.strptime(
            f"{self.time_state['date']} {self.time_state['clock']}",
            "%Y-%m-%d %H:%M",
        )
        advanced = current + timedelta(minutes=1)
        self.time_state["date"] = advanced.strftime("%Y-%m-%d")
        self.time_state["clock"] = advanced.strftime("%H:%M")
        self.time_state["elapsed_minutes"] += 1

    def snapshot(self) -> dict[str, Any]:
        """Return the snapshot."""
        snapshot: dict[str, Any] = {
            "world_id": self.world_id,
            "domain": {
                "type": self.domain_type,
                "metadata": deepcopy(self.domain_metadata),
            },
            "objects": {
                device_id: device.snapshot()
                for device_id, device in self.devices.items()
            },
            "spaces": {
                space_id: {
                    "type": space.type,
                    **({"virtual": space.virtual} if space.virtual is not None else {}),
                    "properties": deepcopy(space.properties),
                    "metadata": deepcopy(space.metadata),
                }
                for space_id, space in self.spaces.items()
            },
            "runtime": {
                "time_state": deepcopy(self.time_state),
                "weather_state": deepcopy(self.weather_state),
            },
        }
        snapshot["scene_metadata"] = deepcopy(self.scene_metadata)
        return snapshot

    def checkpoint(self) -> dict[str, Any]:
        """Return the checkpoint."""
        return {
            "spaces": deepcopy(self.spaces),
            "time_state": deepcopy(self.time_state),
            "weather_state": deepcopy(self.weather_state),
            "devices": {
                device_id: deepcopy(device.instance.__dict__)
                for device_id, device in self.devices.items()
            },
        }

    def restore(self, checkpoint: dict[str, Any]) -> None:
        """Restore a previously captured world-state checkpoint."""
        for space_id, restored in checkpoint["spaces"].items():
            current = self.spaces[space_id]
            current.type = restored.type
            current.virtual = restored.virtual
            current.properties = deepcopy(restored.properties)
            current.metadata = deepcopy(restored.metadata)
            current.device_ids = list(restored.device_ids)
        self.time_state = deepcopy(checkpoint["time_state"])
        self.weather_state = deepcopy(checkpoint["weather_state"])
        for device_id, values in checkpoint["devices"].items():
            instance = self.devices[device_id].instance
            instance.__dict__.clear()
            instance.__dict__.update(deepcopy(values))
