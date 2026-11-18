"""Declarative device, property, function, and event specifications."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PropertySpec:
    key: str
    ptype: str
    description: str = ""
    mode: int = 3
    auto_reset: bool = False
    default: Any = None
    value: Any = None
    unit: str | None = None
    minimum: int | float | None = None
    maximum: int | float | None = None
    step: int | float | None = None
    step_origin: int | float | None = None
    precision: int | None = None
    choices: list[str] | None = None
    pattern: str | None = None
    max_length: int | None = None
    schema: dict | None = None


@dataclass
class FunctionArgSpec:
    name: str
    atype: str
    description: str = ""
    default: Any = None
    minimum: int | float | None = None
    maximum: int | float | None = None
    choices: list[str] | None = None
    nullable: bool = False


@dataclass
class FunctionResSpec:
    name: str
    rtype: str
    description: str = ""


@dataclass
class FunctionErrorSpec:
    name: str
    description: str = ""


@dataclass
class FunctionSpec:
    key: str
    description: str = ""
    arguments: list[FunctionArgSpec] = field(default_factory=list)
    response: list[FunctionResSpec] = field(default_factory=list)
    errorcodes: list[FunctionErrorSpec] = field(default_factory=list)


@dataclass
class EventSpec:
    key: str
    description: str = ""
    effect_properties: list[dict[str, str]] = field(default_factory=list)


@dataclass
class DeviceSpec:
    devkey: str
    class_name: str
    description: str = ""
    version: str = ""
    properties: list[PropertySpec] = field(default_factory=list)
    functions: list[FunctionSpec] = field(default_factory=list)
    events: list[EventSpec] = field(default_factory=list)
