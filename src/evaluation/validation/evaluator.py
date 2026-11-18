"""Compose state, answer, protocol, and metric validation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.contracts import ContractPackage, strict_equal
from src.contracts.errors import EnvironmentContractError
from src.runtime import World

from ..loading import TaskBundle
from .answers import align_answers, evaluate_exact_answers, evaluate_list_answer_recall
from .memory_judger import control_memory_bindings, evaluate_memory_access, memory_content_checks
from .reports import evaluate_exact_reports, evaluate_report_count
from .time_constraints import evaluate_time_constraint
from .assertions import evaluate_assertions
from .workflow import complete_background_simulation, evaluation_end, evaluate_workflow
from src.runtime.execution import state_diff
from .metrics import (
    accuracy,
    action_success_rate,
    time_plan_valid,
    trajectory_summary,
    unexpected_side_effect_count,
)


def build_evaluation_request(
    world: World,
    task_bundle: TaskBundle,
    *,
    replay_reference_snapshot: dict[str, Any] | None = None,
    _validate_schema: bool = True,
) -> dict[str, Any]:
    """Build a private evaluation request without storing task data in World."""
    post_simulation = complete_background_simulation(world, task_bundle)
    termination = world.termination
    if termination is None:
        raise EnvironmentContractError(
            "TERMINATION_REQUIRED",
            "$.termination",
            "evaluation requires a terminal runtime state",
        )
    request = {
        "task": deepcopy(task_bundle.task),
        "initial_snapshot": world.get_initial_state(),
        "final_snapshot": post_simulation["final_snapshot"] if post_simulation is not None else world.final_state or world.get_state(),
        "target": deepcopy(task_bundle.target),
        "termination": termination,
        "trajectory_audit": world.get_audit_records(),
        "submitted_answers": list(world.submitted_answers),
        "submitted_reports": list(world.submitted_reports),
        "initial_memory": world.get_initial_memory(),
        "final_memory": world.get_memory(),
    }
    if post_simulation is not None:
        request["post_simulation"] = post_simulation
    bindings = control_memory_bindings(task_bundle.validation_metadata, task_bundle.target)
    if bindings is not None:
        request["memory_bindings"] = bindings
    if replay_reference_snapshot is not None:
        request["replay_reference_snapshot"] = deepcopy(
            replay_reference_snapshot
        )
    if _validate_schema:
        world.contract.validate_schema(
            request,
            "urn:dcb:v2:schema:evaluation-request",
        )
    return request


def evaluate_world(
    world: World,
    task_bundle: TaskBundle,
    *,
    replay_reference_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate one runtime world against a separately loaded task bundle."""
    request = build_evaluation_request(
        world,
        task_bundle,
        replay_reference_snapshot=replay_reference_snapshot,
        _validate_schema=False,
    )
    return Evaluator(world.contract)._evaluate_validated(request)


class Evaluator:
    """Evaluate one schema-valid request and return a schema-valid report."""

    def __init__(self, contract: ContractPackage) -> None:
        """Initialize the Evaluator."""
        self.contract = contract

    def evaluate(self, request: dict[str, Any]) -> dict[str, Any]:
        """Evaluate a completed agent run."""
        self.contract.validate_schema(
            request,
            "urn:dcb:v2:schema:evaluation-request",
        )
        return self._evaluate_validated(request)

    def _evaluate_validated(self, request: dict[str, Any]) -> dict[str, Any]:
        """Return the validated."""
        self._validate_world_ids(request)
        self._validate_termination(request)

        post_simulation = request.get("post_simulation")
        simulation_failed = post_simulation is not None and post_simulation["status"] == "failed"
        final_snapshot = request["final_snapshot"]
        # A failed simulation has no final snapshot; assertions show the actual
        # agent-end state, and the simulation failure prevents success.
        assertion_snapshot = post_simulation["agent_snapshot"] if simulation_failed else final_snapshot

        assertions = evaluate_assertions(
            self.contract,
            request["target"],
            request["initial_snapshot"],
            assertion_snapshot,
        )
        state_success = not simulation_failed and all(result["passed"] for result in assertions)
        answer_alignment = align_answers(request["target"]["expected_answers"], request["submitted_answers"])
        answer_success, answer_accuracy = evaluate_exact_answers(
            request["target"]["expected_answers"],
            request["submitted_answers"],
            alignment=answer_alignment,
        )
        report_success, report_accuracy = evaluate_exact_reports(
            request["target"]["expected_reports"],
            request["submitted_reports"],
        )
        memory_success = evaluate_memory_access(
            request["task"],
            request["target"],
            request["trajectory_audit"],
            initial_memory=request.get("initial_memory"),
            final_memory=request.get("final_memory"),
            memory_bindings=request.get("memory_bindings"),
        )
        memory_checks = memory_content_checks(
            request["target"].get("expected_memory_mutations", []),
            request.get("initial_memory"),
            request.get("final_memory"),
        )
        time_constraint_success = evaluate_time_constraint(
            self.contract,
            request["task"],
            request["target"],
            request["initial_snapshot"],
            assertion_snapshot,
            request["trajectory_audit"],
        )
        workflow_result = evaluate_workflow(request["target"], request["trajectory_audit"])
        workflow_success = None if workflow_result is None else not simulation_failed and workflow_result["passed"]
        task_success = (
            state_success
            and answer_success is not False
            and report_success is not False
            and memory_success is not False
            and time_constraint_success is not False
            and workflow_success is not False
        )

        summary = trajectory_summary(
            request["trajectory_audit"],
            request["termination"],
        )
        object_results = [
            result for result in assertions if result["scope"] == "object"
        ]
        space_results = [
            result for result in assertions if result["scope"] == "space"
        ]
        replay_snapshot = request.get("replay_reference_snapshot")
        effect_replay_pass = (
            None
            if replay_snapshot is None
            else not simulation_failed and strict_equal(final_snapshot, replay_snapshot)
        )
        goal_device_paths = self._goal_device_paths(
            request["target"],
            request["trajectory_audit"],
        )
        agent_snapshot = post_simulation["agent_snapshot"] if post_simulation is not None else final_snapshot
        if post_simulation is not None:
            command_paths = {(d["scope"], d["target_id"], d["property"]) for r in request["trajectory_audit"] if r["record_type"] == "command" and r["status"] == "committed" for d in r["state_diff"]}
            tick_paths = {(d["scope"], d["target_id"], d["property"]) for r in request["trajectory_audit"] if r["record_type"] == "tick" for d in r["state_diff"]}
            goal_device_paths |= tick_paths - command_paths

        report = {
            "world_id": request["initial_snapshot"]["world_id"],
            "task_id": request["task"]["task_id"],
            "task_success": task_success,
            "state_success": state_success,
            "answer_success": answer_success,
            "answer_alignment": answer_alignment,
            "report_success": report_success,
            "report_semantic_success": False if report_success is False and not (request["target"]["expected_reports"] and request["submitted_reports"]) else None,
            "report_judge": None,
            "memory_success": memory_success,
            "memory_judge": None,
            "time_constraint_success": time_constraint_success,
            "workflow_success": workflow_success,
            "workflow": workflow_result,
            "termination": deepcopy(request["termination"]),
            "assertions": assertions,
            "metrics": {
                "object_property_accuracy": accuracy(object_results),
                "space_state_pass": (
                    all(result["passed"] for result in space_results)
                    if space_results
                    else None
                ),
                "space_property_accuracy": (
                    accuracy(space_results) if space_results else None
                ),
                "action_success_rate": action_success_rate(
                    request["trajectory_audit"]
                ),
                "answer_accuracy": answer_accuracy,
                "list_answer_recall": evaluate_list_answer_recall(request["target"]["expected_answers"], request["submitted_answers"], alignment=answer_alignment),
                "report_accuracy": report_accuracy,
                "report_count_accuracy": evaluate_report_count(request["target"]["expected_reports"], request["submitted_reports"]),
                "report_semantic_accuracy": 0.0 if report_success is False and not (request["target"]["expected_reports"] and request["submitted_reports"]) else None,
                "memory_rouge_l_f1": (
                    sum(item["rouge_l_f1"] for item in memory_checks)
                    / len(memory_checks)
                    if memory_checks
                    else None
                ),
                "effect_replay_pass": effect_replay_pass,
                "unexpected_side_effect_count": unexpected_side_effect_count(
                    self.contract,
                    request["target"],
                    request["initial_snapshot"],
                    agent_snapshot,
                    ignored_paths=goal_device_paths,
                ),
                "background_change_count": (sum(d["scope"] != "runtime" for d in state_diff(agent_snapshot, final_snapshot)) if post_simulation is not None and not simulation_failed else 0),
                "false_complete": (
                    summary["finish_observed"] and not task_success
                ),
                "time_plan_valid": not simulation_failed and time_plan_valid(
                    request["initial_snapshot"],
                    assertion_snapshot,
                    request["trajectory_audit"],
                ),
            },
            "trajectory_summary": summary,
            "errors": self._evaluation_errors(
                assertions,
                request["target"]["expected_answers"],
                request["submitted_answers"],
                answer_success,
                request["target"]["expected_reports"],
                request["submitted_reports"],
                report_success,
            ),
        }
        if simulation_failed:
            report["errors"].append(deepcopy(post_simulation["error"]))
        if workflow_success is False:
            report["errors"].append({"kind": "assertion_failure", "message": "Workflow transition or timing requirement failed", "path": "$.workflow", "details": workflow_result})
        self.contract.validate_schema(
            report,
            "urn:dcb:v2:schema:evaluation-report",
        )
        return report

    @staticmethod
    def _goal_device_paths(
        target: dict[str, Any],
        audit: list[dict[str, Any]],
    ) -> set[tuple[str, str, str]]:
        """Return the goal device paths."""
        goal_paths = {
            (space_id, prop)
            for space_id, spec in target["spaces"].items()
            for prop in spec["properties"]
        }
        sources = {
            application["effect"]["source"]
            for record in audit
            for application in record.get("effects", [])
            if application["status"] == "applied"
            and (
                application["effect"]["target"],
                application["effect"]["parameters"]["property"],
            ) in goal_paths
        }
        return {
            ("object", difference["target_id"], difference["property"])
            for record in audit
            for difference in record.get("state_diff", [])
            if difference["scope"] == "object"
            and difference["target_id"] in sources
        }

    @staticmethod
    def _validate_world_ids(request: dict[str, Any]) -> None:
        """Validate the world IDs."""
        world_ids = {
            request["initial_snapshot"]["world_id"],
            (request["final_snapshot"] or request["post_simulation"]["agent_snapshot"])["world_id"],
        }
        if "replay_reference_snapshot" in request:
            world_ids.add(request["replay_reference_snapshot"]["world_id"])
        if len(world_ids) != 1:
            raise EnvironmentContractError(
                "WORLD_ID_MISMATCH",
                "$",
                "evaluation snapshots use different world IDs: "
                f"{sorted(world_ids)}",
            )

    @staticmethod
    def _validate_termination(request: dict[str, Any]) -> None:
        """Validate the termination."""
        end = evaluation_end(request["target"])
        post = request.get("post_simulation")
        if end is not None:
            if post is None or post["end_elapsed_minutes"] != end:
                raise EnvironmentContractError("EVALUATION_HORIZON_MISMATCH", "$.post_simulation", "task requires its fixed horizon evidence")
            if not strict_equal(post["agent_termination"], request["termination"]) or not strict_equal(post["final_snapshot"], request["final_snapshot"]):
                raise EnvironmentContractError("EVALUATION_EVIDENCE_MISMATCH", "$.post_simulation", "post-simulation evidence differs from evaluation request")
            if post["status"] == "completed" and post["final_snapshot"]["runtime"]["time_state"]["elapsed_minutes"] != end:
                raise EnvironmentContractError("EVALUATION_HORIZON_MISMATCH", "$.final_snapshot", "final state did not reach the fixed horizon")
        elif post is not None or request["final_snapshot"] is None:
            raise EnvironmentContractError("UNEXPECTED_POST_SIMULATION", "$.post_simulation", "task has no post-agent evaluation horizon")
        terminal_records = [
            record
            for record in request["trajectory_audit"]
            if record["record_type"] == "termination"
        ]
        if len(terminal_records) != 1:
            raise EnvironmentContractError(
                "TERMINATION_AUDIT_COUNT_MISMATCH",
                "$.trajectory_audit",
                f"expected one termination record, got {len(terminal_records)}",
            )
        if not strict_equal(
            terminal_records[0]["termination"],
            request["termination"],
        ):
            raise EnvironmentContractError(
                "TERMINATION_AUDIT_MISMATCH",
                "$.termination",
                "request termination differs from runtime audit",
            )
        if (
            request.get("post_simulation", {}).get("agent_snapshot", request["final_snapshot"])["runtime"]["time_state"][
                "elapsed_minutes"
            ]
            != request["termination"]["elapsed_minutes"]
        ):
            raise EnvironmentContractError(
                "TERMINATION_SNAPSHOT_MISMATCH",
                "$.final_snapshot.runtime.time_state.elapsed_minutes",
                "final snapshot and termination elapsed time differ",
            )

    @staticmethod
    def _evaluation_errors(
        assertions: list[dict[str, Any]],
        expected: list[dict[str, Any]],
        submitted: list[dict[str, Any]],
        answer_success: bool | None,
        expected_reports: list[dict[str, Any]],
        submitted_reports: list[dict[str, Any]],
        report_success: bool | None,
    ) -> list[dict[str, Any]]:
        """Return the evaluation errors."""
        errors = [
            {
                "kind": "assertion_failure",
                "message": (
                    f"{result['assertion_id']} failed: "
                    f"{result['failure_reason']}"
                ),
                "path": (
                    f"$.{result['scope']}.{result['target_id']}."
                    f"{result['property']}"
                ),
                "details": {
                    "assertion_id": result["assertion_id"],
                    "initial_value": result["initial_value"],
                    "final_value": result["final_value"],
                },
            }
            for result in assertions
            if not result["passed"]
        ]
        if answer_success is False:
            errors.append(
                {
                    "kind": "assertion_failure",
                    "message": (
                        "submitted answers do not exactly match the "
                        "expected sequence"
                    ),
                    "path": "$.submitted_answers",
                    "details": {
                        "expected": [item["value"] for item in expected],
                        "submitted": [item["value"] for item in submitted],
                    },
                }
            )
        if report_success is False:
            errors.append(
                {
                    "kind": "assertion_failure",
                    "message": "submitted reason-code counts do not match the expected multiset",
                    "path": "$.submitted_reports",
                    "details": {
                        "expected": expected_reports,
                        "submitted": submitted_reports,
                    },
                }
            )
        return errors
