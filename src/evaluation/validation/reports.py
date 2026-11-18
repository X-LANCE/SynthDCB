"""Unordered reason-code scoring, preserving report multiplicity."""

from __future__ import annotations

from typing import Any

from collections import Counter


def evaluate_exact_reports(
    expected: list[dict[str, Any]],
    submitted: list[dict[str, Any]],
) -> tuple[bool | None, float | None]:
    """Compare reason-code multisets; missing, extra and wrong codes lose credit."""
    if not expected and not submitted:
        return None, None
    truth = Counter(item["reason_code"] for item in expected)
    prediction = Counter(item["reason_code"] for item in submitted)
    matches = sum((truth & prediction).values())
    return truth == prediction, matches / max(len(expected), len(submitted))


def evaluate_report_count(expected, submitted):
    """Count-only credit also records recognition accompanied by a wrong code."""
    total = max(len(expected), len(submitted))
    return min(len(expected), len(submitted)) / total if total else None
