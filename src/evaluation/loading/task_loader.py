"""Load public tasks and private evaluation evidence beside a runtime world."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.contracts import ContractPackage, load_json, strict_equal
from src.contracts.errors import EnvironmentContractError
from src.runtime import World


class ReferenceValidationError(ValueError):
    """A private reference violates interaction-mode execution semantics."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the ReferenceValidationError."""
        super().__init__(message)
        self.code = code
        self.details = details or {}


def _validate_reference_semantics(
    task: dict[str, Any],
    target: dict[str, Any],
    trajectory: dict[str, Any],
) -> None:
    """Validate the reference semantics."""
    tool_exchanges = [
        record
        for record in trajectory["records"]
        if record["kind"] == "tool_exchange"
    ]
    post_termination = [
        record
        for record in tool_exchanges
        if record["result"]["code"] == "[SESSION_FINISHED]"
    ]
    termination = trajectory["records"][-1]["termination"]
    if post_termination:
        raise ReferenceValidationError(
            "REFERENCE_CALL_AFTER_TERMINATION",
            "reference commands must stop at the first terminal event",
            details={
                "post_termination_tool_exchanges": post_termination,
                "termination": termination,
            },
        )

    failed_exchanges = [
        record
        for record in tool_exchanges
        if record["result"]["status"] != "success"
    ]
    expected_failures = bool(target["expected_reports"])
    if failed_exchanges and not expected_failures:
        raise ReferenceValidationError(
            "REFERENCE_TOOL_CALL_FAILED",
            f"reference contains {len(failed_exchanges)} failed tool calls",
            details={
                "failed_tool_exchanges": failed_exchanges,
                "termination": termination,
            },
        )
    if expected_failures and termination["reason"] != "session_finish":
        raise ReferenceValidationError(
            "FAILURE_TASK_NOT_FINISHED",
            "a reported infeasible task must explicitly finish",
            details={
                "failed_tool_exchanges": failed_exchanges,
                "termination": termination,
            },
        )


@dataclass(frozen=True)
class TaskBundle:
    """Validated task assets kept outside the runtime loading boundary."""

    root: Path
    task: dict[str, Any]
    target: dict[str, Any]
    memory: dict[str, Any] | None
    reference_trajectory: dict[str, Any] | None
    validation_metadata: dict[str, Any] | None
    split_metadata: dict[str, Any] | None

    @property
    def instruction(self) -> str:
        """Return the instruction."""
        return str(self.task["instruction"])

    @property
    def task_id(self) -> str:
        """Return the task ID."""
        return str(self.task["task_id"])


class TaskLoader:
    """Load task, target, reference, and split assets for one runtime world."""

    REQUIRED_FILES = ("task.json", "target.json")

    def __init__(
        self,
        contract_root: str | Path | None = None,
        *,
        contract: ContractPackage | None = None,
    ) -> None:
        """Initialize the TaskLoader."""
        self.contract = contract or ContractPackage(contract_root)

    def load(
        self,
        task_root: str | Path,
        world: World,
    ) -> TaskBundle:
        """Load and validate one task bundle."""
        root = Path(task_root).resolve()
        flat_target = root / "target.json"
        legacy_target = root / "private" / "target.json"
        if flat_target.is_file() and legacy_target.is_file():
            raise EnvironmentContractError(
                "TASK_FILE_AMBIGUOUS",
                str(root),
                "target.json, private/target.json",
            )
        task_path = root / "task.json"
        if not task_path.is_file():
            raise EnvironmentContractError(
                "TASK_FILE_MISSING",
                str(task_path),
                "task.json",
            )
        evidence_root = root if flat_target.is_file() else root / "private"
        target_path = evidence_root / "target.json"
        if not target_path.is_file():
            raise EnvironmentContractError(
                "TASK_FILE_MISSING",
                str(target_path),
                "target.json",
            )

        task = load_json(task_path)
        target = load_json(target_path)
        self.contract.validate_task(task)
        user = task.get('current_user')
        if user is not None and user.get('space_id') is not None:
            if user['space_id'] not in world.get_initial_state()['spaces']:
                raise ValueError('current_user.space_id does not exist in this World')
        self.contract.validate_target(
            target,
            world.get_world_spec(),
            world.get_initial_state(),
        )
        memory = self._load_optional_json(evidence_root, ("memory.json",))
        if memory is not None:
            self.contract.validate_memory(memory)
        self._validate_structural_contract(target, memory)
        world.bind_memory(memory)
        from ..validation.workflow import evaluation_end
        world.bind_evaluation_horizon(evaluation_end(target))

        reference_trajectory = self._load_optional_reference(evidence_root)
        if reference_trajectory is not None:
            self.contract.validate_trajectory(reference_trajectory)
            if reference_trajectory["world_id"] != world.get_state()["world_id"]:
                raise EnvironmentContractError(
                    "WORLD_ID_MISMATCH",
                    "$.world_id",
                    reference_trajectory["world_id"],
                )
            if reference_trajectory["task_id"] != task["task_id"]:
                raise EnvironmentContractError(
                    "TASK_ID_MISMATCH",
                    "$.task_id",
                    reference_trajectory["task_id"],
                )
            _validate_reference_semantics(task, target, reference_trajectory)
            if "evaluation_end_minute" in target:
                from ..validation.workflow import goal_evaluation_end
                start = world.get_initial_state()["runtime"]["time_state"]["elapsed_minutes"]
                reference_end = reference_trajectory["records"][-1]["termination"]["elapsed_minutes"]
                end = target["evaluation_end_minute"]
                if end < goal_evaluation_end(start, reference_end) or (end - start) % 60:
                    raise ReferenceValidationError("INVALID_GOAL_HORIZON", "Goal horizon must be a whole-hour duration at least twice the reference duration")

        split_metadata = self._load_optional_json(root, ("split.json",))
        validation_metadata = self._load_optional_json(
            evidence_root,
            ("validation_metadata.json",),
        )
        if validation_metadata is not None:
            self._validate_metadata(
                validation_metadata,
                root=evidence_root,
                world=world,
                reference_trajectory=reference_trajectory,
            )
        return TaskBundle(
            root=root,
            task=deepcopy(task),
            target=deepcopy(target),
            memory=deepcopy(memory),
            reference_trajectory=deepcopy(reference_trajectory),
            validation_metadata=deepcopy(validation_metadata),
            split_metadata=deepcopy(split_metadata),
        )

    @staticmethod
    def _validate_structural_contract(
        target: dict[str, Any],
        memory: dict[str, Any] | None,
    ) -> None:
        """Validate the structural contract."""
        available_memory_ids = {
            record["memory_id"]
            for record in (memory or {"records": []})["records"]
        }
        missing_memory_ids = sorted(
            set(target["required_memory_ids"]) - available_memory_ids
        )
        if missing_memory_ids:
            raise EnvironmentContractError(
                "TASK_MEMORY_RECORD_MISSING",
                "$.required_memory_ids",
                ", ".join(missing_memory_ids),
            )
        missing_update_sources = sorted(
            mutation["memory_id"]
            for mutation in target.get("expected_memory_mutations", [])
            if mutation["operation"] == "update"
            and mutation["memory_id"] not in available_memory_ids
        )
        if missing_update_sources:
            raise EnvironmentContractError(
                "TASK_MEMORY_UPDATE_SOURCE_MISSING",
                "$.expected_memory_mutations",
                ", ".join(missing_update_sources),
            )
        unread_update_sources = sorted(
            mutation["memory_id"]
            for mutation in target.get("expected_memory_mutations", [])
            if mutation["operation"] == "update"
            and mutation["memory_id"] not in target["required_memory_ids"]
        )
        if unread_update_sources:
            raise EnvironmentContractError(
                "TASK_MEMORY_UPDATE_READ_NOT_REQUIRED",
                "$.required_memory_ids",
                ", ".join(unread_update_sources),
            )
        if target["time_constraint"] is not None:
            raise EnvironmentContractError(
                "STRUCTURAL_TASK_TIME_NOT_ALLOWED",
                "$.time_constraint",
                "structural tasks do not use time constraints",
            )

    @staticmethod
    def _load_optional_reference(root: Path) -> dict[str, Any] | None:
        """Return the optional reference."""
        return TaskLoader._load_optional_json(root, ("reference_trajectory.json",))

    def _validate_metadata(
        self,
        metadata: dict[str, Any],
        *,
        root: Path,
        world: World,
        reference_trajectory: dict[str, Any] | None,
    ) -> None:
        """Validate the metadata."""
        self.contract.validate_schema(
            metadata,
            "urn:dcb:v2:schema:validation-metadata",
        )
        if metadata["scenario_id"] != world.get_state()["world_id"]:
            raise EnvironmentContractError(
                "WORLD_ID_MISMATCH",
                "$.scenario_id",
                metadata["scenario_id"],
            )
        if reference_trajectory is None:
            raise EnvironmentContractError(
                "VALIDATION_REFERENCE_MISSING",
                str(root / "reference_trajectory.json"),
                "validation metadata requires reference evidence",
            )
        required_gates = {
            "schema",
            "privacy",
            "atom_graph",
            "instruction_alignment",
            "target_semantics",
            "reference_replay",
            "evaluation",
            "termination",
        }
        missing_gates = required_gates - set(metadata["gates"])
        failed_gates = {
            name
            for name, status in metadata["gates"].items()
            if status != "PASS"
        }
        if missing_gates or failed_gates:
            raise EnvironmentContractError(
                "VALIDATION_GATE_NOT_PASSED",
                "$.gates",
                f"missing={sorted(missing_gates)}, failed={sorted(failed_gates)}",
            )
        if not strict_equal(
            metadata["termination"],
            reference_trajectory["records"][-1]["termination"],
        ):
            raise EnvironmentContractError(
                "VALIDATION_TERMINATION_MISMATCH",
                "$.termination",
                "metadata and reference trajectory differ",
            )
        if metadata["reference_source"] != reference_trajectory["source"]:
            raise EnvironmentContractError(
                "VALIDATION_REFERENCE_SOURCE_MISMATCH",
                "$.reference_source",
                "metadata and reference trajectory differ",
            )
        if (
            metadata["reference_source"] == "ground_truth"
            and metadata["reference_repairs"] != 0
        ) or (
            metadata["reference_source"] == "repair"
            and metadata["reference_repairs"] < 1
        ):
            raise EnvironmentContractError(
                "VALIDATION_REFERENCE_REPAIR_MISMATCH",
                "$.reference_repairs",
                "reference source and repair count are inconsistent",
            )

    @staticmethod
    def _load_optional_json(
        root: Path,
        filenames: tuple[str, ...],
    ) -> dict[str, Any] | None:
        """Return the optional JSON."""
        existing = [root / filename for filename in filenames if (root / filename).is_file()]
        if len(existing) > 1:
            raise EnvironmentContractError(
                "TASK_FILE_AMBIGUOUS",
                str(root),
                ", ".join(path.name for path in existing),
            )
        if not existing:
            return None
        payload = load_json(existing[0])
        if not isinstance(payload, dict):
            raise EnvironmentContractError(
                "TASK_FILE_INVALID",
                str(existing[0]),
                "expected a JSON object",
            )
        return payload
