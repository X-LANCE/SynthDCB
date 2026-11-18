"""Failed device-identification Queries with dependent and independent Controls."""
from copy import deepcopy

from .control import build_control_task
from .negative import build_negative_task
from ..task_common import TaskArtifacts, TaskSeedError, build_reference_plan, build_task_seed, display_value, submit_report
from ..task_sampler import DEFAULT_STRUCTURE, sampling_options


def build_query_dependency_task(inventory, task_id, subtype, sampling, rng):
    mode = sampling["query_dependency"]
    if (subtype != "single" or mode not in {"infeasible", "partial"}
            or sampling["target_outcome"] not in {"SPACE_TARGET_NOT_FOUND", "DEVICE_TARGET_NOT_FOUND"}):
        raise TaskSeedError("Query dependency construction requires a single Control with a missing space/device")
    root = build_negative_task(inventory, task_id, "control", subtype, sampling, rng)
    spec = deepcopy(root.seed["atoms"][0]["spec"])
    assertion = spec.pop("assertion")
    name, prop = spec["target_name"], spec["property"]
    spec.update(query_kind="identify_device", result_type="device_ids")
    atoms = [{"id": "q1", "kind": "query", "depends_on": [], "spec": spec},
             {"id": "c1", "kind": "control", "depends_on": ["q1"],
              "spec": {"target_from_query": "q1", "property": prop, "assertion": assertion,
                       "expected_status": "blocked", "reason_code": "BLOCKED_BY_DEPENDENCY"}}]
    report = deepcopy(root.target["expected_reports"][0])
    report.update(atom_id="q1", affected_properties=[])
    blocked = {"atom_id": "c1", "status": "blocked", "reason_code": "BLOCKED_BY_DEPENDENCY",
               "affected_properties": [prop], "match": "exact",
               "description": f"The identification Query for {name} failed, so the device for the requested {prop} control cannot be determined."}
    target = deepcopy(root.target)
    target["expected_reports"] = [report, blocked]
    commands = [submit_report(report), submit_report(blocked)]
    templates = [f"Identify {name}, then set the identified device's {prop} to {display_value(assertion['value'])}."]
    anchors = root.seed["derived"]["public_anchors"]
    private = root.seed["derived"]["private_identifiers"]
    if mode == "partial":
        options = sampling_options({"task_family": "control", "task_subtype": "single", "sampling": {}})
        independent = build_control_task(inventory, task_id, "single", options, DEFAULT_STRUCTURE, rng)
        for atom in independent.seed["atoms"]:
            copied = deepcopy(atom)
            copied["id"] = "independent_" + atom["id"]
            copied["depends_on"] = ["independent_" + parent for parent in atom["depends_on"]]
            atoms.append(copied)
        for scope in ("objects", "spaces"):
            target[scope] = deepcopy(independent.target[scope])
        commands.extend(item for turn in independent.reference_plan["turns"] for item in turn
                        if item["target"] != "session")
        templates = [templates[0] + " Independently, " + independent.instruction_template[0]]
        anchors = [*anchors, *independent.seed["derived"]["public_anchors"]]
        private = [*private, *independent.seed["derived"]["private_identifiers"]]
    seed = build_task_seed("control", subtype, atoms, sampling, public_anchors=anchors, private_identifiers=private)
    return TaskArtifacts(seed, templates, target, build_reference_plan(task_id, commands))
