"""Auditable task-scoped memory access evaluation."""

from __future__ import annotations

from .prompt import (
    MEMORY_JUDGE_SYSTEM_PROMPT,
    MEMORY_JUDGE_USER_PROMPT,
)

import re
import time
from typing import Any

from src.utils import format_json
from src.contracts import strict_equal
from src.utils.llm import extract_json_from_answer, get_llm_config




class MemoryJudgeError(RuntimeError):
    """The Memory Judge did not return a usable verdict."""

    def __init__(self, message: str, audit: dict[str, Any]) -> None:
        super().__init__(message)
        self.audit = audit


def memory_driver_context(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve the driver from current driver-seat occupants, never other users."""
    seats = [
        (space_id, space)
        for space_id, space in snapshot.get("spaces", {}).items()
        if space.get("type") == "driver_seat"
    ]
    if not seats:
        return None
    occupants = sorted({
        occupant
        for _, space in seats
        for occupant in space.get("metadata", {}).get("occupants", [])
    })
    return {
        "seat_ids": sorted(space_id for space_id, _ in seats),
        "occupants": occupants,
        "user_id": occupants[0] if len(occupants) == 1 else None,
        "scope": "user" if len(occupants) == 1 else "general" if not occupants else "ambiguous",
    }


def _reference_content(mutation: dict[str, Any]) -> str:
    """Return deterministic text for the diagnostic reference."""
    if "reference_content" in mutation:
        return mutation["reference_content"]
    fact = mutation["fact"]
    owner = (
        f"{mutation['user_id']}'s"
        if "user_id" in mutation
        else "Everyone's"
    )
    return (
        f"{owner} saved {fact['subject']} {fact['property']} is "
        f"{format_json(fact['value'], ensure_ascii=False)}."
    )


def _rouge_tokens(value: str) -> list[str]:
    """Return compact English-word and CJK-character tokens."""
    return re.findall(r"[a-z0-9_]+|[\u3400-\u9fff]", value.casefold())


def rouge_l_f1(reference: str, candidate: str) -> float:
    """Return dependency-free ROUGE-L F1."""
    left = _rouge_tokens(reference)
    right = _rouge_tokens(candidate)
    if not left or not right:
        return 0.0
    row = [0] * (len(right) + 1)
    for left_token in left:
        previous = 0
        for index, right_token in enumerate(right, start=1):
            saved = row[index]
            row[index] = (
                previous + 1
                if left_token == right_token
                else max(row[index], row[index - 1])
            )
            previous = saved
    common = row[-1]
    precision = common / len(right)
    recall = common / len(left)
    return 2 * precision * recall / (precision + recall) if common else 0.0


def _response_dict(response: Any) -> dict[str, Any]:
    """Return an SDK response as JSON-compatible data."""
    if isinstance(response, dict):
        return response
    if hasattr(response, "model_dump"):
        return response.model_dump(exclude_none=True)
    return {"model": str(getattr(response, "model", "") or "")}


def judge_memory_content(
    client: Any,
    instruction: str,
    checks: list[dict[str, Any]],
    *,
    current_user: dict[str, Any] | None = None,
    driver_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return one auditable hard semantic verdict for all Memory writes."""
    config = get_llm_config("memory_judge")
    request_payload = {
        "instruction": instruction,
        "current_user": current_user,
        "driver_context": driver_context,
        "items": [
            {
                key: check[key]
                for key in (
                    "mutation_id",
                    "operation",
                    "user_id",
                    "fact",
                    "candidate_content",
                )
            }
            for check in checks
        ],
    }
    responses_api = "responses" in str(config["base_url"])
    request: dict[str, Any] = {
        "model": config["model"],
        "temperature": 0,
        "top_p": config.get("top_p", 1.0),
    }
    service_tier = config.get("service_tier")
    if service_tier:
        request["service_tier"] = service_tier
    user = MEMORY_JUDGE_USER_PROMPT.format(
        instruction=instruction,
        current_user=format_json(current_user, ensure_ascii=False),
        driver_context=format_json(driver_context, ensure_ascii=False),
        items=format_json(request_payload["items"], ensure_ascii=False),
    )
    if responses_api:
        request.update(instructions=MEMORY_JUDGE_SYSTEM_PROMPT, input=user)
    else:
        request["messages"] = [
            {"role": "system", "content": MEMORY_JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ]
    maximum = config.get("max_response_tokens")
    if maximum is not None:
        request[
            "max_output_tokens" if responses_api else "max_tokens"
        ] = min(int(maximum), 2048)
    started = time.monotonic()
    try:
        response = (
            client.responses.create(**request)
            if responses_api
            else client.chat.completions.create(**request)
        )
    except Exception as error:
        audit = {
            "status": "ERROR",
            "requested_model": config["model"],
            "response_model": "",
            "endpoint": config["base_url"],
            "latency_seconds": time.monotonic() - started,
            "usage": {},
            "request": request_payload,
            "raw_response": None,
            "items": [],
            "error": str(error),
        }
        raise MemoryJudgeError(str(error), audit) from error
    raw = _response_dict(response)
    text = (
        str(getattr(response, "output_text", "") or "")
        if responses_api
        else str(
            getattr(
                getattr((getattr(response, "choices", []) or [None])[0], "message", None),
                "content",
                "",
            )
            or ""
        )
    )
    if responses_api and not text:
        text = "".join(
            str(getattr(content, "text", "") or "")
            for output in getattr(response, "output", []) or []
            for content in getattr(output, "content", []) or []
            if getattr(content, "type", "") == "output_text"
        )
    parse_status, payload = extract_json_from_answer(text)
    expected_ids = {check["mutation_id"] for check in checks}
    items = payload.get("items") if isinstance(payload, dict) else None
    valid = (
        parse_status == "[PASS]"
        and isinstance(payload, dict)
        and set(payload) == {"items"}
        and isinstance(items, list)
        and len(items) == len(checks)
        and {
            item.get("mutation_id")
            for item in items
            if isinstance(item, dict)
        }
        == expected_ids
        and all(
            isinstance(item, dict)
            and set(item) == {"mutation_id", "pass", "reason"}
            and type(item["pass"]) is bool
            and isinstance(item["reason"], str)
            and bool(item["reason"])
            for item in items
        )
    )
    audit = {
        "status": (
            "PASS" if valid and all(item["pass"] for item in items) else "FAIL"
        ) if valid else "ERROR",
        "requested_model": config["model"],
        "response_model": str(getattr(response, "model", "") or ""),
        "endpoint": config["base_url"],
        "latency_seconds": time.monotonic() - started,
        "usage": raw.get("usage", {}),
        "request": request_payload,
        "raw_response": raw,
        "items": items if valid else [],
        "error": (
            None
            if valid
            else parse_status
            if parse_status != "[PASS]"
            else "invalid response payload"
        ),
    }
    if not valid:
        raise MemoryJudgeError("Memory Judge returned invalid JSON", audit)
    return audit


def apply_memory_judge(
    report: dict[str, Any],
    checks: list[dict[str, Any]],
    judgement: dict[str, Any],
) -> dict[str, Any]:
    """Apply a completed Judge verdict to an evaluator report."""
    updated = report
    updated["memory_judge"] = judgement
    updated["metrics"]["memory_rouge_l_f1"] = (
        sum(check["rouge_l_f1"] for check in checks) / len(checks)
    )
    updated["memory_success"] = bool(
        updated["memory_success"]
        and judgement["status"] == "PASS"
    )
    updated["task_success"] = all(
        updated[key] is not False
        for key in (
            "state_success",
            "answer_success",
            "report_success",
            "memory_success",
            "time_constraint_success",
        )
    )
    updated["metrics"]["false_complete"] = bool(
        updated["trajectory_summary"]["finish_observed"]
        and not updated["task_success"]
    )
    return updated


def memory_content_checks(
    expected: list[dict[str, Any]],
    initial_memory: dict[str, Any] | None,
    final_memory: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Pair expected mutations with final user IDs and free-text content."""
    if not expected:
        return []
    if initial_memory is None or final_memory is None:
        return []
    initial = {
        record["memory_id"]: record for record in initial_memory["records"]
    }
    final = {
        record["memory_id"]: record for record in final_memory["records"]
    }
    update_ids = {
        mutation["memory_id"]
        for mutation in expected
        if mutation["operation"] == "update"
    }
    if set(initial) - set(final) or any(
        memory_id not in update_ids
        and not strict_equal(record, final[memory_id])
        for memory_id, record in initial.items()
    ):
        return []
    added = [
        record
        for memory_id, record in final.items()
        if memory_id not in initial
    ]
    if len(added) != sum(
        mutation["operation"] == "create" for mutation in expected
    ):
        return []
    unmatched = list(added)
    checks: list[dict[str, Any]] = []
    for index, mutation in enumerate(expected, start=1):
        if mutation["operation"] == "update":
            memory_id = mutation["memory_id"]
            if memory_id not in initial or memory_id not in final:
                return []
            record = final[memory_id]
            if (
                strict_equal(record, initial[memory_id])
                or record.get("user_id")
                != initial[memory_id].get("user_id")
            ):
                return []
        else:
            record = next(
                (
                    item
                    for item in unmatched
                    if item.get("user_id") == mutation.get("user_id")
                ),
                None,
            )
            if record is None:
                return []
            unmatched.remove(record)
            memory_id = record["memory_id"]
        if record.get("user_id") != mutation.get("user_id"):
            return []
        reference = _reference_content(mutation)
        checks.append(
            {
                "mutation_id": f"memory_mutation_{index}",
                "operation": mutation["operation"],
                "memory_id": memory_id,
                "user_id": mutation.get("user_id"),
                "fact": mutation["fact"],
                "reference_content": reference,
                "candidate_content": record["content"],
                "rouge_l_f1": rouge_l_f1(reference, record["content"]),
            }
        )
    return checks if not unmatched else []


def _memory_write_success(
    expected: list[dict[str, Any]],
    initial_memory: dict[str, Any] | None,
    final_memory: dict[str, Any] | None,
) -> bool:
    """Return whether every expected write has a structurally matching record."""
    return not expected or len(
        memory_content_checks(expected, initial_memory, final_memory)
    ) == len(expected)


def _query_observation_sequences(
    mutation: dict[str, Any],
    audit: list[dict[str, Any]],
) -> list[int]:
    """Return the query observation sequences."""
    source = mutation["source"]
    result: list[int] = []
    for record in audit:
        if (
            record["record_type"] != "command"
            or record.get("result", {}).get("code") != "[PASS]"
        ):
            continue
        command = record.get("command", {})
        data = record["result"]["data"]
        if source["scope"] == "object":
            observed = (
                command.get("target") == source["target_id"]
                and isinstance(data, dict)
                and source["property"] in data
            )
        else:
            observed = (
                command.get("target") == "session"
                and command.get("function") == "get_space_state"
                and command.get("parameters", {}).get("space_id")
                == source["target_id"]
                and isinstance(data, dict)
                and isinstance(data.get("properties"), dict)
                and source["property"] in data.get("properties", {})
            )
        if observed:
            result.append(record["sequence"])
    return result


def _memory_write_sequence(
    mutation: dict[str, Any],
    audit: list[dict[str, Any]],
) -> int | None:
    """Return the memory write sequence."""
    for record in audit:
        if (
            record["record_type"] != "command"
            or record.get("result", {}).get("code") != "[PASS]"
        ):
            continue
        command = record.get("command", {})
        if (
            command.get("target") != "memory"
            or command.get("function") != mutation["operation"]
        ):
            continue
        parameters = command.get("parameters", {})
        if mutation["operation"] == "create":
            matches = (
                parameters.get("user_id") == mutation.get("user_id")
                and isinstance(parameters.get("content"), str)
                and bool(parameters["content"])
            )
        else:
            matches = (
                parameters.get("memory_id") == mutation["memory_id"]
                and isinstance(parameters.get("content"), str)
                and bool(parameters["content"])
            )
        if matches:
            return record["sequence"]
    return None


def _memory_write_order_success(
    expected: list[dict[str, Any]],
    audit: list[dict[str, Any]],
) -> bool:
    """Return whether required memory writes occurred in order."""
    boundaries = {
        record["sequence"]
        for record in audit
        if record["record_type"] == "turn_boundary"
    }
    for mutation in expected:
        write_sequence = _memory_write_sequence(mutation, audit)
        observations = _query_observation_sequences(mutation, audit)
        if write_sequence is None or not any(
            observation < boundary < write_sequence
            for observation in observations
            for boundary in boundaries
        ):
            return False
    return True


def control_memory_bindings(metadata: dict[str, Any] | None, target: dict[str, Any]) -> list[dict[str, str]] | None:
    """Use complete, unambiguous object-control bindings; retain legacy rules otherwise."""
    required = set(target.get("required_memory_ids", []))
    if not required or target.get("expected_memory_mutations"):
        return None
    bindings = []
    for atom in (metadata or {}).get("meta", {}).get("atoms", []):
        binding = atom.get("spec", {}).get("memory_binding")
        if not binding:
            continue
        if atom.get("kind") != "control" or binding.get("target_kind") != "object":
            return None
        path = (binding["target_id"], binding["property"])
        # A repeated operation on the same path needs an explicit occurrence policy.
        if sum(a.get("spec", {}).get("target_id") == path[0]
               and a.get("spec", {}).get("property") == path[1]
               for a in (metadata or {}).get("meta", {}).get("atoms", [])) != 1:
            return None
        bindings.append({key: binding[key] for key in ("memory_id", "target_kind", "target_id", "property")})
    return bindings if {b["memory_id"] for b in bindings} == required else None


def evaluate_memory_access(
    task: dict[str, Any],
    target: dict[str, Any],
    audit: list[dict[str, Any]],
    *,
    initial_memory: dict[str, Any] | None = None,
    final_memory: dict[str, Any] | None = None,
    memory_bindings: list[dict[str, str]] | None = None,
) -> bool | None:
    """Return the memory access."""
    expected_mutations = target.get("expected_memory_mutations", [])
    if not target["required_memory_ids"] and not expected_mutations:
        return None
    write_success = _memory_write_success(
        expected_mutations,
        initial_memory,
        final_memory,
    ) and _memory_write_order_success(expected_mutations, audit)
    if not target["required_memory_ids"]:
        return write_success
    required_ids = set(target["required_memory_ids"])
    if memory_bindings is not None:
        if not memory_bindings or {b["memory_id"] for b in memory_bindings} != required_ids:
            raise ValueError("Memory bindings must cover exactly the required memory IDs")
        boundaries = [r["sequence"] for r in audit if r["record_type"] == "turn_boundary"]
        for binding in memory_bindings:
            reads = [r["sequence"] for r in audit
                     if r["record_type"] == "command"
                     and r.get("command", {}).get("target") == "memory"
                     and r["command"].get("function") == "read"
                     and r.get("result", {}).get("code") == "[PASS]"
                     and any(item.get("memory_id") == binding["memory_id"]
                             for item in r["result"].get("data", {}).get("records", []))]
            dependencies = [r["sequence"] for r in audit
                            if any(d.get("scope") == binding["target_kind"]
                                   and d.get("target_id") == binding["target_id"]
                                   and d.get("property") == binding["property"]
                                   for d in r.get("state_diff", []))]
            if not dependencies or not any(read < boundary < min(dependencies)
                                           for read in reads for boundary in boundaries):
                return False
        return write_success
    returned_ids: set[str | None] = set()
    completed_read_sequence: int | None = None
    for record in audit:
        if (
            record["record_type"] == "command"
            and record.get("command", {}).get("target") == "memory"
            and record.get("command", {}).get("function") == "read"
            and record.get("result", {}).get("code") == "[PASS]"
        ):
            returned_ids.update(
                item.get("memory_id")
                for item in record["result"]["data"].get("records", [])
            )
            if required_ids.issubset(returned_ids):
                completed_read_sequence = record["sequence"]
                break
    if completed_read_sequence is None:
        return False

    target_paths = {
        (scope[:-1], target_id, prop)
        for scope in ("objects", "spaces")
        for target_id, spec in target[scope].items()
        for prop in spec["properties"]
    }
    dependency_sequences = [
        record["sequence"]
        for record in audit
        if any(
            (
                difference["scope"],
                difference["target_id"],
                difference["property"],
            ) in target_paths
            for difference in record.get("state_diff", [])
        )
    ]
    if not dependency_sequences and expected_mutations:
        dependency_sequences = [
            record["sequence"]
            for record in audit
            if record["record_type"] == "command"
            and record.get("command", {}).get("target") == "memory"
            and record.get("command", {}).get("function") in {"create", "update"}
            and record.get("result", {}).get("code") == "[PASS]"
        ]
    if not dependency_sequences:
        return False
    first_dependency_sequence = min(dependency_sequences)
    if completed_read_sequence >= first_dependency_sequence:
        return False
    ordered_read = any(
        record["record_type"] == "turn_boundary"
        and completed_read_sequence < record["sequence"] < first_dependency_sequence
        for record in audit
    )
    return ordered_read and write_success
