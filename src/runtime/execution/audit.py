from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.contracts import ContractPackage, strict_equal


def state_diff(
    before: dict[str, Any], after: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return the differences between two state snapshots."""
    differences: list[dict[str, Any]] = []
    for plural, singular in (("objects", "object"), ("spaces", "space")):
        for target_id in sorted(set(before[plural]) | set(after[plural])):
            old_properties = before[plural].get(target_id, {}).get("properties", {})
            new_properties = after[plural].get(target_id, {}).get("properties", {})
            for prop in sorted(set(old_properties) | set(new_properties)):
                old = old_properties.get(prop)
                new = new_properties.get(prop)
                if not strict_equal(old, new):
                    differences.append(
                        {
                            "scope": singular,
                            "target_id": target_id,
                            "property": prop,
                            "before": deepcopy(old),
                            "after": deepcopy(new),
                        }
                    )
    for runtime_scope in ("time_state", "weather_state"):
        old_properties = before["runtime"].get(runtime_scope, {})
        new_properties = after["runtime"].get(runtime_scope, {})
        for prop in sorted(set(old_properties) | set(new_properties)):
            old = old_properties.get(prop)
            new = new_properties.get(prop)
            if not strict_equal(old, new):
                differences.append(
                    {
                        "scope": "runtime",
                        "target_id": runtime_scope,
                        "property": prop,
                        "before": deepcopy(old),
                        "after": deepcopy(new),
                    }
                )
    return differences


class AuditTrail:
    """Append, validate, checkpoint, and annotate audit records."""

    def __init__(self, contract: ContractPackage) -> None:
        """Initialize the AuditTrail."""
        self.contract = contract
        self._records: list[dict[str, Any]] = []
        self._sequence = 0
        self._validation_enabled = True

    def append(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Append a record to the records."""
        self._sequence += 1
        record = {
            "record_id": f"audit_{self._sequence}",
            "sequence": self._sequence,
            **deepcopy(payload),
        }
        if self._validation_enabled:
            self.contract.validate_audit_record(record)
        self._records.append(record)
        return record

    def validate(self, record: dict[str, Any]) -> None:
        """Validate an audit record before insertion."""
        self.contract.validate_audit_record(record)

    def records(self) -> list[dict[str, Any]]:
        """Return the records."""
        return deepcopy(self._records)

    def add_links(
        self,
        record_id: str,
        *,
        call_id: str,
        turn_id: str,
    ) -> dict[str, Any]:
        """Attach runner call metadata to one existing command record."""
        record = next(
            item for item in self._records if item["record_id"] == record_id
        )
        record["links"] = {"call_id": call_id, "turn_id": turn_id}
        self.validate(record)
        return deepcopy(record)

    def checkpoint(self) -> tuple[int, int]:
        """Return the checkpoint."""
        return len(self._records), self._sequence

    def restore(self, checkpoint: tuple[int, int]) -> None:
        """Restore the audit trail to a prior checkpoint."""
        length, sequence = checkpoint
        del self._records[length:]
        self._sequence = sequence
