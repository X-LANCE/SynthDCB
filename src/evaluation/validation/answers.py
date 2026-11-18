"""Answer scoring with order-preserving alignment across missing/extra answers."""

from __future__ import annotations

from typing import Any

from src.contracts import strict_equal


def _list_recall(truth: list[Any], predicted: Any) -> float:
    if not isinstance(predicted, list):
        return 0.0
    unique = []
    for value in truth:
        if not any(strict_equal(value, other) for other in unique):
            unique.append(value)
    return (sum(any(strict_equal(value, other) for other in predicted) for value in unique) / len(unique)
            if unique else float(not predicted))


def align_answers(expected: list[dict[str, Any]], submitted: list[dict[str, Any]]) -> dict[str, Any]:
    """Maximize pair correctness without crossing question/answer order.

    Lists use the existing set recall; other JSON values use exact correctness.
    Ties prefer exact matches, then more pairs, then earlier question/answer indices.
    """
    n, m = len(expected), len(submitted)
    scores = [[(0.0, 0, 0) for _ in range(m + 1)] for _ in range(n + 1)]
    steps = [[None for _ in range(m + 1)] for _ in range(n + 1)]
    for i, truth in enumerate(expected, 1):
        for j, prediction in enumerate(submitted, 1):
            exact = strict_equal(truth["value"], prediction["value"])
            score = _list_recall(truth["value"], prediction["value"]) if isinstance(truth["value"], list) else float(exact)
            previous = scores[i - 1][j - 1]
            pair = (previous[0] + score, previous[1] + int(exact), previous[2] + 1)
            scores[i][j], steps[i][j] = max(
                ((scores[i - 1][j], "missing"), (scores[i][j - 1], "extra"), (pair, "match")),
                key=lambda item: item[0],
            )
    matches, missing, extra = [], [], []
    i, j = n, m
    while i or j:
        step = "extra" if not i else "missing" if not j else steps[i][j]
        if step == "missing":
            missing.append(i - 1)
            i -= 1
        elif step == "extra":
            extra.append(j - 1)
            j -= 1
        else:
            truth, prediction = expected[i - 1]["value"], submitted[j - 1]["value"]
            exact = strict_equal(truth, prediction)
            matches.append({"expected_index": i - 1, "submitted_index": j - 1,
                            "score": _list_recall(truth, prediction) if isinstance(truth, list) else float(exact),
                            "exact": exact})
            i -= 1
            j -= 1
    return {"matches": list(reversed(matches)), "missing_expected_indices": list(reversed(missing)),
            "extra_submitted_indices": list(reversed(extra))}


def evaluate_list_answer_recall(
    expected: list[dict[str, Any]],
    submitted: list[dict[str, Any]],
    *, alignment: dict[str, Any] | None = None,
) -> float | None:
    """Mean list recall after alignment; each missing list question scores zero."""
    alignment = align_answers(expected, submitted) if alignment is None else alignment
    paired = {item["expected_index"]: item["submitted_index"] for item in alignment["matches"]}
    recalls = []
    for index, item in enumerate(expected):
        truth = item["value"]
        if not isinstance(truth, list):
            continue
        predicted = submitted[paired[index]]["value"] if index in paired else None
        recalls.append(_list_recall(truth, predicted))
    return sum(recalls) / len(recalls) if recalls else None


def evaluate_exact_answers(
    expected: list[dict[str, Any]],
    submitted: list[dict[str, Any]],
    *, alignment: dict[str, Any] | None = None,
) -> tuple[bool | None, float | None]:
    """Exact correctness after alignment; extra submissions retain their penalty."""
    if not expected:
        return None, None
    alignment = align_answers(expected, submitted) if alignment is None else alignment
    matches = sum(item["exact"] for item in alignment["matches"])
    accuracy = matches / max(len(expected), len(submitted))
    return (
        len(expected) == len(submitted) and matches == len(expected),
        accuracy,
    )
