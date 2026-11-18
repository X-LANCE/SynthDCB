"""Contract manifest, schema inventory, and JSON Schema registry."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from threading import Lock
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .errors import EnvironmentContractError
from .jsonio import load_json
from .validators import ContractValidator, validate_property_catalog
from src.utils import format_json


DEFAULT_CONTRACT_ROOT = Path(__file__).resolve().parent
VALIDATION_CACHE_SIZE = 8192


def _json_path(error: Any) -> str:
    """Return the JSON path."""
    return "$" + "".join(f"[{part!r}]" for part in error.absolute_path)


class ContractPackage:
    """A Domain-neutral contract package shipped beside this module."""

    def __init__(self, root: str | Path | None = None) -> None:
        """Initialize the ContractPackage."""
        self.root = Path(root).resolve() if root is not None else DEFAULT_CONTRACT_ROOT
        self.schema_dir = self.root / "schemas"
        self.manifest_path = self.root / "manifest.json"
        if not self.manifest_path.is_file():
            raise EnvironmentContractError(
                "CONTRACT_PACKAGE_NOT_FOUND",
                str(self.root),
                "manifest.json is missing",
            )

        self.schemas: dict[str, dict[str, Any]] = {}
        self._validators: dict[str, Draft202012Validator] = {}
        self._validation_cache: OrderedDict[tuple[str, str], None] = OrderedDict()
        self._validation_cache_lock = Lock()
        self._validation_cache_hits = 0
        self._validation_cache_misses = 0
        resources: list[tuple[str, Resource[Any]]] = []
        self.schema_paths = sorted(self.schema_dir.glob("*.schema.json"))
        for path in self.schema_paths:
            schema = load_json(path)
            Draft202012Validator.check_schema(schema)
            schema_id = schema.get("$id")
            if not isinstance(schema_id, str):
                raise EnvironmentContractError(
                    "SCHEMA_ID_MISSING",
                    str(path),
                    "$id is required",
                )
            if schema_id in self.schemas:
                raise EnvironmentContractError(
                    "SCHEMA_ID_DUPLICATE",
                    str(path),
                    schema_id,
                )
            self.schemas[schema_id] = schema
            resources.append((schema_id, Resource.from_contents(schema)))

        self.registry = Registry().with_resources(resources)
        self.format_checker = FormatChecker()
        self.manifest = load_json(self.manifest_path)
        self.validate_schema(
            self.manifest,
            "urn:dcb:v2:schema:contract-manifest",
            code="MANIFEST_SCHEMA_VALIDATION_ERROR",
        )
        self._validate_manifest_inventory()
        self.semantics = ContractValidator(self)
        for schema_id in self.schemas:
            self.validator(schema_id)

    @property
    def contract_version(self) -> str:
        """Return the contract version."""
        return str(self.manifest["contract_version"])

    @property
    def catalogs(self) -> dict[str, dict[str, Any]]:
        """Return the catalogs."""
        return self.semantics.catalogs

    @property
    def REQUIRED_SESSION_TOOLS(self) -> set[str]:
        """Return the REQUIRED SESSION TOOLS."""
        return self.semantics.REQUIRED_SESSION_TOOLS

    def load_contract_json(self, relative_path: str) -> Any:
        """Return the contract JSON."""
        return load_json(self.root / relative_path)

    def validator(self, schema_id: str) -> Draft202012Validator:
        """Return the validator."""
        cached = self._validators.get(schema_id)
        if cached is not None:
            return cached
        try:
            schema = self.schemas[schema_id]
        except KeyError as error:
            raise EnvironmentContractError(
                "UNKNOWN_SCHEMA_ID",
                "$",
                schema_id,
            ) from error
        validator = Draft202012Validator(
            schema,
            registry=self.registry,
            format_checker=self.format_checker,
        )
        self._validators[schema_id] = validator
        return validator

    def validate_schema(
        self,
        instance: Any,
        schema_id: str,
        *,
        code: str = "SCHEMA_VALIDATION_ERROR",
    ) -> None:
        """Validate the schema."""
        try:
            payload = format_json(
                instance,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            cache_key = (schema_id, payload)
        except (TypeError, ValueError):
            cache_key = None
        with self._validation_cache_lock:
            if cache_key is not None and cache_key in self._validation_cache:
                self._validation_cache.move_to_end(cache_key)
                self._validation_cache_hits += 1
                return
            self._validation_cache_misses += 1
        errors = sorted(
            self.validator(schema_id).iter_errors(instance),
            key=lambda error: (list(error.absolute_path), error.message),
        )
        if errors:
            error = errors[0]
            raise EnvironmentContractError(
                code,
                _json_path(error),
                error.message,
            )
        if cache_key is not None:
            with self._validation_cache_lock:
                self._validation_cache[cache_key] = None
                self._validation_cache.move_to_end(cache_key)
                if len(self._validation_cache) > VALIDATION_CACHE_SIZE:
                    self._validation_cache.popitem(last=False)

    @property
    def validation_cache_stats(self) -> dict[str, int]:
        """Return the validation cache stats."""
        with self._validation_cache_lock:
            return {
                "entries": len(self._validation_cache),
                "hits": self._validation_cache_hits,
                "misses": self._validation_cache_misses,
                "max_entries": VALIDATION_CACHE_SIZE,
            }

    def _validate_manifest_inventory(self) -> None:
        """Validate the manifest inventory."""
        entries = self.manifest["schemas"]
        manifest_paths = {entry["path"] for entry in entries}
        disk_paths = {
            path.relative_to(self.root).as_posix()
            for path in self.schema_paths
        }
        if manifest_paths != disk_paths:
            raise EnvironmentContractError(
                "MANIFEST_SCHEMA_INVENTORY_MISMATCH",
                "$.schemas",
                f"missing={sorted(disk_paths - manifest_paths)}, "
                f"extra={sorted(manifest_paths - disk_paths)}",
            )
        for entry in entries:
            schema = self.load_contract_json(entry["path"])
            if schema["$id"] != entry["id"]:
                raise EnvironmentContractError(
                    "MANIFEST_SCHEMA_ID_MISMATCH",
                    entry["path"],
                    entry["id"],
                )

    def bind_domain_catalogs(
        self,
        catalogs: dict[str, dict[str, Any]],
    ) -> None:
        """Bind the domain catalogs."""
        for domain_type, catalog in catalogs.items():
            self.validate_schema(
                catalog,
                "urn:dcb:v2:schema:property-catalog",
            )
            if catalog["domain_type"] != domain_type:
                raise EnvironmentContractError(
                    "CATALOG_DOMAIN_MISMATCH",
                    domain_type,
                    catalog["domain_type"],
                )
            validate_property_catalog(catalog, domain_type)
        self.semantics.bind_domain_catalogs(catalogs)

    def __getattr__(self, name: str) -> Any:
        """Return the getattr."""
        semantics = self.__dict__.get("semantics")
        if semantics is not None and hasattr(semantics, name):
            return getattr(semantics, name)
        raise AttributeError(name)
