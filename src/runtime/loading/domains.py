"""Load one domain's configuration and scan an independent device directory."""

from pathlib import Path
import re
from typing import Any, Iterable

from src.contracts.errors import EnvironmentContractError
from src.contracts.jsonio import load_json
from src.object_model.registry import DomainDefinition
from src.utils.config import DOMAIN_CONFIG_DIR


def discover_model_files(domain_path: str | Path, domain: str) -> dict[str, Path]:
    """Discover ClassName/ClassName.py implementations, never templates/tests."""
    root = Path(domain_path).resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)
    classes = {}
    names = set()
    for path in sorted(root.rglob("*.py")):
        if path.name != f"{path.parent.name}.py" or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(root).with_suffix("")
        if not all(part.isidentifier() for part in relative.parts):
            raise ValueError(f"invalid model module path: {path}")
        if path.stem in names:
            raise ValueError(f"duplicate model class {path.stem}: {path}")
        names.add(path.stem)
        classes[f"{domain}." + ".".join(relative.parts)] = path
    if not classes:
        raise ValueError(f"no model implementations in {root}")
    return classes


class DomainRegistry:
    def __init__(self, definitions: Iterable[DomainDefinition]) -> None:
        definitions = tuple(definitions)
        if len(definitions) != 1:
            raise ValueError("a World must load exactly one domain")
        self._definitions = {item.domain_type: item for item in definitions}

    @classmethod
    def from_path(
        cls,
        domain: str,
        domain_path: str | Path,
        contract: Any,
        *,
        domain_config_root: str | Path | None = None,
    ) -> "DomainRegistry":
        if not isinstance(domain, str) or not re.fullmatch(
            r"[A-Za-z][A-Za-z0-9_-]{0,63}", domain
        ):
            raise ValueError(f"invalid domain: {domain!r}")
        root = Path(domain_path).resolve()
        config = Path(domain_config_root or DOMAIN_CONFIG_DIR).resolve() / domain
        catalog = load_json(config / f"{domain.lower()}.property-specs.json")
        contract.validate_schema(catalog, "urn:dcb:v2:schema:property-catalog")
        if catalog["domain_type"] != domain:
            raise ValueError(f"property catalog does not belong to {domain}")

        # Import lazily: generation also imports the runtime package.
        from src.world_distill.pipeline.list_creation.object_class_placement import (
            load_layout_catalog,
            validate_placement_type_list,
        )
        layouts = load_layout_catalog(
            config / f"{domain.lower()}_layouts.json",
            known_space_types=catalog["space_types"],
        )
        if layouts["domain"] != domain:
            raise ValueError(f"layout catalog does not belong to {domain}")
        type_list = load_json(root / "type_list_with_placement.json")
        placements = validate_placement_type_list(type_list, layouts)
        classes = discover_model_files(root, domain)
        from src.world_distill.pipeline.model_creation.specification import resolve_specification
        from src.contracts.capabilities import validate_capability_spec
        specifications = {}
        for class_id, path in classes.items():
            specification, _ = resolve_specification(path.with_suffix(".json"))
            if specification["meta"]["name"] != path.stem:
                raise ValueError(f"specification class differs from implementation: {path}")
            errors = validate_capability_spec(specification)
            if errors:
                raise ValueError(f"invalid specification {path.with_suffix('.json')}: {errors}")
            specifications[class_id] = specification
        if {key.rsplit(".", 1)[-1] for key in classes} != set(placements):
            raise ValueError("placement class coverage differs from scanned models")

        templates = {}
        payloads = {}
        for path in sorted((config / "templates").glob("*.json")):
            payload = load_json(path)
            contract.validate_schema(payload, "urn:dcb:v2:schema:environment-template")
            key = payload["template_id"]
            if payload["domain_type"] != domain or key in templates:
                raise ValueError(f"invalid or duplicate domain template: {path}")
            templates[key], payloads[key] = path, payload
        contract.bind_domain_catalogs({domain: catalog})
        return cls([DomainDefinition(
            domain_type=domain, version=contract.contract_version, root=root,
            property_catalog=catalog, templates=templates, classes=classes,
            specifications=specifications,
            template_payloads=payloads, layout_catalog=layouts,
            placement_type_list=type_list, placements=placements,
        )])

    def resolve(self, domain_type: str) -> DomainDefinition:
        try:
            return self._definitions[domain_type]
        except KeyError as error:
            raise EnvironmentContractError("UNKNOWN_DOMAIN", "$.domain.type", domain_type) from error

    def domain_types(self) -> tuple[str, ...]:
        return tuple(self._definitions)
