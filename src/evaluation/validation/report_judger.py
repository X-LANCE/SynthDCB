"""Semantic checking of unordered failure reports against task and World evidence."""

from .prompt import (
    REPORT_JUDGE_SYSTEM_PROMPT,
    REPORT_JUDGE_USER_PROMPT,
)
from copy import deepcopy
import time

from jsonschema import validate, ValidationError

from src.utils import format_json
from src.utils.llm import call_llm_api, extract_json_from_answer, get_llm_config




class ReportJudgeError(RuntimeError):
    def __init__(self, message, audit):
        super().__init__(message)
        self.audit = audit


def report_judge_context(world, bundle):
    """Include inventory plus the state, schemas and tools needed to check failures."""
    initial = world.get_initial_state()
    metadata = (bundle.validation_metadata or {}).get("meta", {})
    atoms = metadata.get("atoms", [])
    relevant = set()
    for atom in atoms:
        spec = atom["spec"]
        if spec.get("target_id") in initial["objects"]:
            relevant.add(spec["target_id"])
        relevant.update(spec.get("infeasibility_proof", {}).get("source_ids", []))
        if "space_id" in spec:
            relevant.update(key for key, value in initial["objects"].items() if value["space_id"] == spec["space_id"])
    tools = [tool for tool in world.get_tool_catalog()["tools"] if tool["target"] in relevant]
    return {
        "instruction": bundle.instruction, "expected_reports": bundle.target["expected_reports"], "atoms": atoms,
        "spaces": initial["spaces"],
        "device_inventory": [{"id": key, **{name: value[name] for name in ("class", "space_id", "metadata")}}
                             for key, value in initial["objects"].items()],
        "relevant_devices": {key: initial["objects"][key] for key in sorted(relevant)},
        "relevant_tools": tools,
        "property_schemas": {key: {name: prop["schema"] for name, prop in world.runtime_cache.model_prototypes[initial["objects"][key]["class"]].items()}
                             for key in sorted(relevant)},
        "space_property_schemas": world.loaded_world.domain.property_catalog["space_properties"],
        "submitted_reports": list(world.submitted_reports),
    }


def judge_reports(context, *, completion=None):
    """Make one judge call; malformed output is an audited evaluation error."""
    config = get_llm_config("report_judge")
    caller = completion or (lambda system, user: call_llm_api(system, user, model_scenario="report_judge"))
    started = time.monotonic()
    user = REPORT_JUDGE_USER_PROMPT.format(context=format_json(context, ensure_ascii=False))
    code, response = caller(REPORT_JUDGE_SYSTEM_PROMPT, user)
    audit = {"status": "ERROR",
             "requested_model": config["model"], "response_model": response.get("model", ""),
             "endpoint": config["base_url"], "latency_seconds": time.monotonic() - started,
             "usage": response.get("usage", {}), "request": context, "raw_response": response, "items": []}
    if code != "[PASS]":
        audit["error"] = code
        raise ReportJudgeError(code, audit)
    parse_code, payload = extract_json_from_answer(response["answer"])
    item_schema = {"type": "object", "required": ["expected_index", "submitted_index", "correct", "reason"],
                   "properties": {"expected_index": {"type": "integer", "minimum": 0},
                                  "submitted_index": {"type": ["integer", "null"], "minimum": 0},
                                  "correct": {"type": "boolean"}, "reason": {"type": "string", "minLength": 1}},
                   "additionalProperties": False}
    try:
        if parse_code != "[PASS]":
            raise ValueError(parse_code)
        validate(payload, {"type": "object", "required": ["items"], "additionalProperties": False,
                           "properties": {"items": {"type": "array", "items": item_schema}}})
        items = payload["items"]
        expected, submitted = context["expected_reports"], context["submitted_reports"]
        if sorted(item["expected_index"] for item in items) != list(range(len(expected))):
            raise ValueError("judge must cover every expected report exactly once")
        used = [item["submitted_index"] for item in items if item["submitted_index"] is not None]
        if len(set(used)) != len(used) or any(index >= len(submitted) for index in used):
            raise ValueError("judge returned duplicate or out-of-range submitted indices")
        for item in items:
            index = item["submitted_index"]
            truth = expected[item["expected_index"]]
            if item["correct"] and (index is None or any(submitted[index][key] != truth[key] for key in ("status", "reason_code"))
                                    or not submitted[index]["description"].strip()):
                raise ValueError("judge accepted a missing report, incorrect code/status or empty explanation")
    except (ValidationError, ValueError) as error:
        audit["error"] = str(error)
        raise ReportJudgeError(str(error), audit) from error
    audit.update(status="PASS" if len(expected) == len(submitted) and all(item["correct"] for item in items) else "FAIL", items=items)
    return audit


def apply_report_judge(report, judgement):
    """Keep hard results intact and attach the stricter semantic result."""
    report["report_judge"] = deepcopy(judgement)
    if judgement["status"] == "ERROR":
        return report
    context = judgement["request"]
    total = max(len(context["expected_reports"]), len(context["submitted_reports"]))
    report["metrics"]["report_semantic_accuracy"] = sum(item["correct"] for item in judgement["items"]) / total
    report["report_semantic_success"] = judgement["status"] == "PASS"
    return report
