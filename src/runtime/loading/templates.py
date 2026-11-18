from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.contracts import ContractPackage, load_json
from src.contracts.errors import EnvironmentContractError
from .domains import DomainRegistry


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge nested mappings."""
    merged = deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _pointer_tokens(path: str) -> list[str]:
    """Return the pointer tokens."""
    return [part.replace("~1", "/").replace("~0", "~") for part in path[1:].split("/")]


def _list_index(token: str, size: int, *, allow_end: bool) -> int:
    """Return the index."""
    if token == "-" and allow_end:
        return size
    if not token.isdigit():
        raise EnvironmentContractError("INIT_PATH_INVALID", token, "array index must be an integer")
    index = int(token)
    upper = size if allow_end else size - 1
    if index < 0 or index > upper:
        raise EnvironmentContractError("INIT_PATH_NOT_FOUND", token, "array index is out of range")
    return index


def apply_init_operations(
    world: dict[str, Any], operations: list[dict[str, Any]]
) -> dict[str, Any]:
    """Apply the init operations."""
    resolved = deepcopy(world)
    for index, operation in enumerate(operations):
        path = operation["path"]
        tokens = _pointer_tokens(path)
        parent: Any = resolved
        for token in tokens[:-1]:
            if isinstance(parent, dict):
                if token not in parent:
                    raise EnvironmentContractError(
                        "INIT_PATH_NOT_FOUND", f"$.init[{index}].path", path
                    )
                parent = parent[token]
            elif isinstance(parent, list):
                parent = parent[_list_index(token, len(parent), allow_end=False)]
            else:
                raise EnvironmentContractError(
                    "INIT_PATH_NOT_FOUND", f"$.init[{index}].path", path
                )

        token = tokens[-1]
        op = operation["op"]
        if isinstance(parent, dict):
            exists = token in parent
            if op == "add":
                if exists:
                    raise EnvironmentContractError(
                        "INIT_ADD_EXISTS", f"$.init[{index}].path", path
                    )
                parent[token] = deepcopy(operation["value"])
            elif op == "replace":
                if not exists:
                    raise EnvironmentContractError(
                        "INIT_PATH_NOT_FOUND", f"$.init[{index}].path", path
                    )
                parent[token] = deepcopy(operation["value"])
            else:
                if not exists:
                    raise EnvironmentContractError(
                        "INIT_PATH_NOT_FOUND", f"$.init[{index}].path", path
                    )
                del parent[token]
        elif isinstance(parent, list):
            list_index = _list_index(token, len(parent), allow_end=op == "add")
            if op == "add":
                parent.insert(list_index, deepcopy(operation["value"]))
            elif op == "replace":
                parent[list_index] = deepcopy(operation["value"])
            else:
                del parent[list_index]
        else:
            raise EnvironmentContractError(
                "INIT_PATH_NOT_FOUND", f"$.init[{index}].path", path
            )
    return resolved


class TemplateResolver:
    def __init__(
        self,
        domain_registry: DomainRegistry,
        contract: ContractPackage,
    ) -> None:
        """Initialize the TemplateResolver."""
        self.domain_registry = domain_registry
        self.contract = contract

    def resolve(self, request: dict[str, Any]) -> dict[str, Any]:
        """Resolve a template request to a task payload."""
        domain_type = request["domain"]["type"]
        template_id = request["template"]
        base: dict[str, Any] = {
            "domain_metadata": {"info": {}, "connections": []},
            "spaces": {},
            "objects": {},
            "runtime": {},
            "scene_metadata": {},
        }
        if template_id is not None:
            domain = self.domain_registry.resolve(domain_type)
            try:
                path = domain.templates[template_id]
            except KeyError as exc:
                raise EnvironmentContractError(
                    "TEMPLATE_NOT_FOUND",
                    "$.template",
                    template_id,
                ) from exc
            template = deepcopy(
                domain.template_payloads.get(template_id)
                or load_json(path)
            )
            self.contract.validate_schema(template, "urn:dcb:v2:schema:environment-template")
            if template["template_id"] != template_id:
                raise EnvironmentContractError(
                    "TEMPLATE_ID_MISMATCH", "$.template", template["template_id"]
                )
            if template["domain_type"] != domain_type:
                raise EnvironmentContractError(
                    "TEMPLATE_DOMAIN_MISMATCH", "$.domain.type", template["domain_type"]
                )
            base = {
                "domain_metadata": deepcopy(template["domain_metadata"]),
                "spaces": deepcopy(template["spaces"]),
                "objects": deepcopy(template["objects"]),
                "runtime": deepcopy(template["runtime"]),
                "scene_metadata": deepcopy(template.get("scene_metadata", {})),
            }

        configured = deep_merge(base, request["config"])
        world = {
            "world_id": request["world_id"],
            "domain": {
                "type": domain_type,
                "metadata": {
                    "template_id": template_id,
                    **deepcopy(configured["domain_metadata"]),
                },
            },
            "spaces": deepcopy(configured["spaces"]),
            "objects": deepcopy(configured["objects"]),
            "runtime": deepcopy(configured["runtime"]),
            "scene_metadata": deepcopy(configured["scene_metadata"]),
        }
        return apply_init_operations(world, request["init"])
