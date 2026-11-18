from __future__ import annotations

import inspect
from copy import deepcopy
from typing import Any

from src.object_model import BaseProperty
from src.contracts.capabilities import declaration_schema, function_declaration
from src.contracts.errors import EnvironmentContractError
from jsonschema import Draft202012Validator

from src.contracts import ContractPackage


BUILTIN_TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'session_get_capabilities',
            'description': 'Return the domain, support for spaces, devices, and relations, and the simulation time unit.',
            'parameters': {},
        },
        'additional_info': {
            'target': 'session',
            'target_kind': 'session',
            'function': 'get_capabilities',
            'mutation': False,
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'session_get_devices',
            'description': 'List devices in a space with their IDs, classes, locations, and metadata.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'space_id': {
                        'type': 'string',
                        'minLength': 1,
                    },
                },
                'required': ['space_id'],
                'additionalProperties': False,
            },
        },
        'additional_info': {
            'target': 'session',
            'target_kind': 'session',
            'function': 'get_devices',
            'mutation': False,
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'session_get_relations',
            'description': 'Return the relations declared in the domain metadata.',
            'parameters': {},
        },
        'additional_info': {
            'target': 'session',
            'target_kind': 'session',
            'function': 'get_relations',
            'mutation': False,
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'session_get_spaces',
            'description': 'List space IDs, types, and whether each space is virtual.',
            'parameters': {},
        },
        'additional_info': {
            'target': 'session',
            'target_kind': 'session',
            'function': 'get_spaces',
            'mutation': False,
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'session_get_space_state',
            'description': "Read a space's properties and metadata.",
            'parameters': {
                'type': 'object',
                'properties': {
                    'space_id': {
                        'type': 'string',
                    },
                },
                'required': ['space_id'],
                'additionalProperties': False,
            },
        },
        'additional_info': {
            'target': 'session',
            'target_kind': 'session',
            'function': 'get_space_state',
            'mutation': False,
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'session_get_space_devices',
            'description': 'List the IDs and classes of devices in a space.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'space_id': {
                        'type': 'string',
                    },
                },
                'required': ['space_id'],
                'additionalProperties': False,
            },
        },
        'additional_info': {
            'target': 'session',
            'target_kind': 'session',
            'function': 'get_space_devices',
            'mutation': False,
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'session_get_device_tools',
            'description': 'Retrieve device functions, parameter schemas, and read/write semantics. Required before invoking those functions in a later turn.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'device_id': {
                        'type': 'string',
                    },
                },
                'required': ['device_id'],
                'additionalProperties': False,
            },
        },
        'additional_info': {
            'target': 'session',
            'target_kind': 'session',
            'function': 'get_device_tools',
            'mutation': False,
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'session_sleep_time',
            'description': (
                'Advance simulation by a nonnegative integer number of minutes; omission uses the configured default. '
                'Timing uses simulation timestamps from runtime updates, not wall-clock time.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'minutes': {
                        'type': 'integer',
                        'minimum': 0,
                    },
                },
                'required': [],
                'additionalProperties': False,
            },
        },
        'additional_info': {
            'target': 'session',
            'target_kind': 'session',
            'function': 'sleep_time',
            'mutation': True,
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'session_submit_answer',
            'description': (
                'Submit one typed JSON answer per answerable query, exactly once and in instruction order, using a '
                'separate call for each answer. Submitted answers retain their submission-time values. For infeasible '
                'or blocked queries, use session_submit_report without a placeholder answer.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'value': {
                        'description': (
                            "Return raw typed property values, integer counts, or a space_id string for a person's location. "
                            'Preserve raw list-property order. Return target selections as arrays of exact IDs: device_id for '
                            'devices, space_id for spaces, and person IDs for occupants. Use [] for no matches. For top-1/top-k, '
                            'include all boundary ties, even when this yields more than k targets. Nearest means absolute '
                            'distance from the requested baseline. Order top-1/top-k answer IDs by the requested ranking first. '
                            'Break equal ranking scores by ascending natural ID order. For filters and occupants, sort the '
                            'matching IDs directly in ascending natural ID order (case-insensitive text, numeric digit runs).'
                        ),
                    },
                },
                'required': ['value'],
                'additionalProperties': False,
            },
        },
        'additional_info': {
            'target': 'session',
            'target_kind': 'session',
            'function': 'submit_answer',
            'mutation': False,
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'session_submit_report',
            'description': (
                'Submit one report per infeasible or blocked request. Reports may arrive in any order. When multiple '
                'failure categories apply to one request, reporting precedence is space target, device target, '
                'property/capability, then value.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'status': {
                        'description': 'Use infeasible for an unsatisfiable request; blocked when a failed prerequisite prevents execution.',
                        'type': 'string',
                        'enum': ['infeasible', 'blocked'],
                    },
                    'reason_code': {
                        'description': (
                            'SPACE_TARGET_NOT_FOUND: requested space does not exist. DEVICE_TARGET_NOT_FOUND: requested device '
                            'does not exist in the applicable scope. SPACE_PROPERTY_NOT_SUPPORTED: existing space does not '
                            'support the requested property. DEVICE_PROPERTY_NOT_SUPPORTED: existing device does not support the '
                            'requested property or capability. INVALID_VALUE: requested value violates types, enums, bounds, step '
                            'alignment, or precision, including the resulting value of increase/decrease requests; do not round '
                            'or replace it with a supported value. UNREACHABLE_GOAL: observed evidence shows an otherwise valid '
                            'environmental goal cannot be reached. BLOCKED_BY_DEPENDENCY: a failed query prevents a dependent '
                            'request; use status blocked.'
                        ),
                        'type': 'string',
                        'pattern': '^[A-Z][A-Z0-9_]{1,63}$',
                    },
                    'affected_properties': {
                        'type': 'array',
                        'uniqueItems': True,
                        'items': {
                            'type': 'string',
                            'minLength': 1,
                        },
                    },
                    'description': {
                        'description': 'Identify the affected request and the observed evidence supporting the report.',
                        'type': 'string',
                    },
                },
                'required': ['status', 'reason_code', 'description'],
                'additionalProperties': False,
            },
        },
        'additional_info': {
            'target': 'session',
            'target_kind': 'session',
            'function': 'submit_report',
            'mutation': False,
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'session_finish',
            'description': (
                'End interaction immediately; subsequent actions cannot execute. For tasks with a fixed evaluation '
                'horizon, background simulation continues to that horizon before scoring. Other tasks are scored '
                'immediately.'
            ),
            'parameters': {},
        },
        'additional_info': {
            'target': 'session',
            'target_kind': 'session',
            'function': 'finish',
            'mutation': False,
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'memory_read',
            'description': 'Return memory records in the current scope, including their memory_id values and contents.',
            'parameters': {},
        },
        'additional_info': {
            'target': 'memory',
            'target_kind': 'memory',
            'function': 'read',
            'mutation': False,
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'memory_create',
            'description': 'Create a new natural-language memory record, optionally associated with an explicitly named user.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'content': {
                        'description': 'Clear natural-language facts to store.',
                        'type': 'string',
                        'minLength': 1,
                    },
                    'user_id': {
                        'description': (
                            "Provide only when the instruction explicitly names a user, using that user's exact ID; otherwise "
                            'omit.'
                        ),
                        'type': 'string',
                        'minLength': 1,
                    },
                },
                'required': ['content'],
                'additionalProperties': False,
            },
        },
        'additional_info': {
            'target': 'memory',
            'target_kind': 'memory',
            'function': 'create',
            'mutation': True,
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'memory_update',
            'description': 'Replace the content of an existing memory record previously returned by memory_read.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'memory_id': {
                        'description': 'Exact memory_id returned by memory_read for the record being updated.',
                        'type': 'string',
                        'minLength': 1,
                    },
                    'content': {
                        'description': 'Replacement content expressed as clear natural-language facts.',
                        'type': 'string',
                        'minLength': 1,
                    },
                },
                'required': ['memory_id', 'content'],
                'additionalProperties': False,
            },
        },
        'additional_info': {
            'target': 'memory',
            'target_kind': 'memory',
            'function': 'update',
            'mutation': True,
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'device_execute_action',
            'description': (
                'Execute a device function whose schema was returned by session_get_device_tools in an earlier turn. '
                'Use its exact target, function name, and parameter schema for queries and state changes; parameters '
                'is a JSON object.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'target': {'type': 'string'},
                    'function': {'type': 'string'},
                    'parameters': {'type': 'object', 'additionalProperties': True},
                },
                'required': ['target', 'function', 'parameters'],
                'additionalProperties': False,
            },
        },
        'additional_info': {'generic': True},
    },
]

def builtin_tools() -> list[dict[str, Any]]:
    """Public entry points, independent of a world's undiscovered devices."""
    tools = []
    for definition in BUILTIN_TOOLS:
        function = deepcopy(definition["function"])
        if not function["parameters"]:
            function["parameters"] = {
                "type": "object", "properties": {}, "additionalProperties": False,
            }
        tools.append({"type": "function", "function": function})
    return tools


def _description(method: Any) -> str:
    """Return the description."""
    doc = inspect.getdoc(method) or ""
    return doc.splitlines()[0] if doc else ""


class ToolCatalogBuilder:
    def __init__(self, contract: ContractPackage) -> None:
        """Initialize the ToolCatalogBuilder."""
        self.contract = contract

    def build(
        self,
        world: dict[str, Any],
        devices: dict[str, Any],
        exposed_properties: dict[str, tuple[str, ...]],
        class_descriptors: dict[str, tuple[dict[str, Any], ...]],
    ) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        """Build the tool catalog and action map for a world."""
        # Runtime validation retains a strict empty-object schema for no-argument tools.
        definitions = []
        for tool in BUILTIN_TOOLS:
            if tool["additional_info"].get("generic"):
                continue
            function = tool["function"]
            definitions.append({
                "tool_id": function["name"],
                "description": function["description"],
                **tool["additional_info"],
                "parameters_schema": deepcopy(function["parameters"]) if function["parameters"] else {
                    "type": "object", "properties": {}, "required": [], "additionalProperties": False,
                },
            })

        for device_id in sorted(devices):
            visible = set(exposed_properties[device_id])
            class_id = world["objects"][device_id]["class"]
            descriptors = class_descriptors[class_id]
            for cached in descriptors:
                descriptor = deepcopy(cached)
                dependencies = set(descriptor.get("reads", ())) | set(descriptor.get("writes", ()))
                if not dependencies.issubset(visible):
                    continue
                function = descriptor.pop("function")
                definition = {
                    "tool_id": f"{device_id}_{function}",
                    "target": device_id,
                    "target_kind": "device",
                    "function": function,
                    **descriptor,
                }
                definitions.append(definition)

        catalog = {"world_id": world["world_id"], "tools": definitions}
        return catalog, self.contract.validate_tool_catalog(catalog, world)

    @staticmethod
    def describe_device(instance: Any, specification: dict[str, Any]) -> tuple[dict[str, Any], ...]:
        """Compile target-independent tool descriptors for one model class."""
        disabled = set(instance._disabled["functions"])
        descriptors: list[dict[str, Any]] = []
        durations = getattr(instance, "TOOL_DURATIONS", {})
        declarations = {
            name: function_declaration(item)
            for name, item in specification["functions"]["update"].items()
            if name not in specification["functions"].get("disabled", [])
        }
        validator = Draft202012Validator(declaration_schema("function"))
        for function, metadata in declarations.items():
            if function in disabled:
                raise EnvironmentContractError("FUNCTION_DECLARATION_INVALID", function, "active JSON function is disabled in the implementation")
            errors = list(validator.iter_errors(metadata))
            if errors:
                raise EnvironmentContractError("FUNCTION_DECLARATION_INVALID", function, errors[0].message)
            method = getattr(instance, function)
            parameters = metadata["parameters_schema"]
            signature = inspect.signature(method)
            if set(signature.parameters) != set(parameters["properties"]):
                raise EnvironmentContractError("FUNCTION_DECLARATION_INVALID", function, "parameter names differ from the implementation")
            required = {name for name, parameter in signature.parameters.items() if parameter.default is inspect.Signature.empty}
            if required != set(parameters["required"]):
                raise EnvironmentContractError("FUNCTION_DECLARATION_INVALID", function, "required parameters differ from the implementation")
            for prop in set(metadata["reads"]) | set(metadata["writes"]):
                if not isinstance(getattr(instance, prop, None), BaseProperty):
                    raise EnvironmentContractError("FUNCTION_DECLARATION_INVALID", function, f"unknown property {prop}")
            semantic = metadata["semantics"]
            if semantic["kind"] == "set":
                prop = getattr(instance, semantic["property"])
                if prop.mode != 3 or isinstance(prop.value, dict):
                    raise EnvironmentContractError("FUNCTION_DECLARATION_INVALID", function, "generic setters cannot expose read-only or collection properties")
            descriptor = {"function": function, "description": _description(method), **deepcopy(metadata)}
            if function in durations:
                descriptor["duration_minutes"] = durations[function]
            descriptors.append(descriptor)
        return tuple(descriptors)
