"""Append-only success records with strict, crash-tolerant JSONL loading."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from threading import Lock
from typing import Any, Iterable

from src.utils import append_jsonl, parse_json_object
from src.contracts import ContractPackage


class GenerationRecordError(ValueError):
    """Generation records are malformed or contain conflicting identities."""


_LOCKS_GUARD = Lock()
_LOCKS: dict[Path, Lock] = {}


def _path_lock(path: Path) -> Lock:
    """Return the path lock."""
    resolved = path.resolve()
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(resolved, Lock())


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Return the unique object."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GenerationRecordError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


class GenerationRecords:
    """Read once at startup, then append complete, flushed success rows."""

    def __init__(
        self,
        path: str | Path,
        *,
        id_field: str,
        contract: ContractPackage | None = None,
        schema_id: str | None = None,
    ) -> None:
        """Initialize the GenerationRecords."""
        self.path = Path(path).resolve()
        self.id_field = id_field
        self.contract = contract
        self.schema_id = schema_id
        self._lock = _path_lock(self.path)
        self._records: list[dict[str, Any]] = []
        self._by_id: dict[str, dict[str, Any]] = {}
        self._truncate_at: int | None = None
        self._load_once()

    def _validate(self, payload: dict[str, Any]) -> str:
        """Validate and normalize a record."""
        if self.contract is not None and self.schema_id is not None:
            self.contract.validate_schema(payload, self.schema_id)
        identifier = payload.get(self.id_field)
        if not isinstance(identifier, str) or not identifier:
            raise GenerationRecordError(
                f"record requires non-empty {self.id_field!r}"
            )
        return identifier

    def _accept_loaded(self, payload: dict[str, Any]) -> None:
        """Accept the loaded."""
        identifier = self._validate(payload)
        previous = self._by_id.get(identifier)
        if previous is None:
            copied = deepcopy(payload)
            self._records.append(copied)
            self._by_id[identifier] = copied
            return
        if previous != payload:
            raise GenerationRecordError(
                f"conflicting rows for {self.id_field}={identifier!r}"
            )

    def _load_once(self) -> None:
        """Load the once."""
        if not self.path.is_file():
            return
        raw = self.path.read_bytes()
        if not raw:
            return
        start = 0
        line_number = 0
        while start < len(raw):
            line_number += 1
            newline = raw.find(b"\n", start)
            complete = newline >= 0
            end = newline if complete else len(raw)
            line_bytes = raw[start:end]
            if line_bytes.endswith(b"\r"):
                line_bytes = line_bytes[:-1]
            try:
                text = line_bytes.decode("utf-8")
                if not text:
                    raise GenerationRecordError("blank record")
                payload = parse_json_object(text, object_pairs_hook=_unique_object)
                self._accept_loaded(payload)
            except ValueError as error:
                if not complete and end == len(raw):
                    self._truncate_at = start
                    return
                raise GenerationRecordError(
                    f"malformed JSONL row {line_number} in {self.path}: {error}"
                ) from error
            start = newline + 1 if complete else len(raw)

    @property
    def records(self) -> tuple[dict[str, Any], ...]:
        """Return the records."""
        return tuple(deepcopy(self._records))

    def get(self, identifier: str) -> dict[str, Any] | None:
        """Return the get."""
        payload = self._by_id.get(identifier)
        return None if payload is None else deepcopy(payload)

    def append(self, payload: dict[str, Any]) -> bool:
        """Append a record to the records."""
        identifier = self._validate(payload)
        copied = deepcopy(payload)
        with self._lock:
            previous = self._by_id.get(identifier)
            if previous is not None:
                if previous != copied:
                    raise GenerationRecordError(
                        f"conflicting rows for {self.id_field}={identifier!r}"
                    )
                return False
            self._prepare_append()
            append_jsonl(self.path, (copied,))
            self._records.append(copied)
            self._by_id[identifier] = copied
            return True

    def append_many(self, payloads: Iterable[dict[str, Any]]) -> int:
        """Append multiple records to the records."""
        rows = [deepcopy(payload) for payload in payloads]
        if not rows:
            return 0
        identifiers = [self._validate(payload) for payload in rows]
        if len(identifiers) != len(set(identifiers)):
            raise GenerationRecordError("append batch contains duplicate identities")
        with self._lock:
            pending: list[tuple[str, dict[str, Any]]] = []
            for identifier, payload in zip(identifiers, rows, strict=True):
                previous = self._by_id.get(identifier)
                if previous is not None:
                    if previous != payload:
                        raise GenerationRecordError(
                            f"conflicting rows for {self.id_field}={identifier!r}"
                        )
                    continue
                pending.append((identifier, payload))
            if not pending:
                return 0
            self._prepare_append()
            append_jsonl(self.path, (payload for _, payload in pending))
            for identifier, payload in pending:
                self._records.append(payload)
                self._by_id[identifier] = payload
            return len(pending)

    def _prepare_append(self) -> None:
        """Prepare the append."""
        if self._truncate_at is None:
            return
        if self.path.is_file():
            with self.path.open("r+b") as stream:
                stream.truncate(self._truncate_at)
                stream.flush()
        self._truncate_at = None
