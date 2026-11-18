"""Pipeline usage, failure, artifact, and provenance reporting."""

from __future__ import annotations

from typing import Any, Iterable

from .models import StageProvenance, as_jsonable


def aggregate_usage(
    provenances: Iterable[StageProvenance],
) -> dict[str, dict[str, int]]:
    """Aggregate standard token fields by stage."""
    report: dict[str, dict[str, int]] = {}
    for provenance in provenances:
        usage = provenance.usage
        bucket = report.setdefault(
            provenance.stage,
            {
                "calls": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        )
        if usage:
            bucket["calls"] += int(usage.get("calls", 1))
        for field in (
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
        ):
            value = usage.get(field, 0)
            if isinstance(value, int):
                bucket[field] += value
    return report


def build_pipeline_report(
    outputs: Iterable[Any],
) -> dict[str, Any]:
    """Build one machine-readable summary from completed stage outputs."""
    present = [output for output in outputs if output is not None]
    provenances = [output.provenance for output in present]
    return {
        "status": (
            "PASS"
            if all(item.validated and not item.errors for item in provenances)
            else "FAIL"
        ),
        "completed_stages": [item.stage for item in provenances],
        "usage_by_stage": aggregate_usage(provenances),
        "errors": {
            item.stage: list(item.errors)
            for item in provenances
            if item.errors
        },
        "provenance": [as_jsonable(item) for item in provenances],
    }
