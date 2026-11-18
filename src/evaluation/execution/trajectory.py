"""ToolCall/ToolResult types and the shared trajectory executor."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from typing import Any

from jsonschema import Draft202012Validator
from src.runtime.execution.tools import BUILTIN_TOOLS

from src.contracts import strict_equal
from src.contracts.errors import EnvironmentContractError
from src.runtime import World


@dataclass(frozen=True)
class ToolCall:
    """One provider-issued command."""

    call_id: str
    turn_id: str
    command: dict[str, Any]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ToolCall:
        """Create a ToolCall from its schema representation."""
        return cls(
            call_id=payload["call_id"],
            turn_id=payload["turn_id"],
            command=deepcopy(payload["command"]),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the schema representation."""
        return {
            "call_id": self.call_id,
            "turn_id": self.turn_id,
            "command": deepcopy(self.command),
        }


@dataclass(frozen=True)
class ToolResult:
    """One runtime result linked to a ToolCall and audit sequence."""

    call_id: str
    turn_id: str
    sequence: int
    status: str
    code: str
    data: Any
    mutation_committed: bool
    audit_sequence: int | None
    error: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ToolResult:
        """Create a ToolResult from its schema representation."""
        return cls(
            call_id=payload["call_id"],
            turn_id=payload["turn_id"],
            sequence=payload["sequence"],
            status=payload["status"],
            code=payload["code"],
            data=deepcopy(payload["data"]),
            mutation_committed=payload["mutation_committed"],
            audit_sequence=payload["audit_sequence"],
            error=deepcopy(payload.get("error")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the schema representation."""
        payload = {
            "call_id": self.call_id,
            "turn_id": self.turn_id,
            "sequence": self.sequence,
            "status": self.status,
            "code": self.code,
            "data": deepcopy(self.data),
            "mutation_committed": self.mutation_committed,
            "audit_sequence": self.audit_sequence,
        }
        if self.error is not None:
            payload["error"] = deepcopy(self.error)
        return payload


class TrajectoryExecutor:
    """Execute both agent and reference records through the same World methods."""

    def __init__(
        self,
        world: World,
        *,
        task_id: str | None = None,
    ) -> None:
        """Bind a fresh trajectory sequence to one World instance."""
        self.world = world
        self.task_id = task_id
        self._tool_sequence = 0

    def execute_tool(self, invocation, *, call_id: str, turn_id: str):
        """Validate the public builtin call and dispatch through the existing runtime."""
        try:
            if not isinstance(invocation, dict) or set(invocation) != {"name", "arguments"}:
                raise ValueError("tool call requires name and arguments")
            definition = next((tool for tool in BUILTIN_TOOLS
                               if tool["function"]["name"] == invocation["name"]), None)
            if definition is None:
                raise ValueError(f"unknown builtin tool: {invocation['name']!r}")
            arguments = invocation["arguments"]
            schema = definition["function"]["parameters"] or {
                "type": "object", "properties": {}, "additionalProperties": False,
            }
            error = next(Draft202012Validator(schema).iter_errors(arguments), None)
            if error is not None:
                raise ValueError(error.message)
            info = definition["additional_info"]
            if info.get("generic") and arguments["target"] in {"session", "memory"}:
                raise ValueError("device_execute_action requires a device target")
            command = (deepcopy(arguments) if info.get("generic") else {
                "target": info["target"], "function": info["function"], "parameters": deepcopy(arguments),
            })
            self.world.contract.validate_schema(command, "urn:dcb:v2:schema:command")
        except (ValueError, EnvironmentContractError) as error:
            command = {"target": "session", "function": "tool_call_error", "parameters": {
                "message": str(error), "provider_tool": invocation.get("name", "") if isinstance(invocation, dict) else "",
                "raw_arguments": json.dumps(invocation, ensure_ascii=False), "action_executed": False,
            }}
        call = ToolCall(call_id=call_id, turn_id=turn_id, command=command)
        return call, self.execute_call(call)

    def execute_call(self, call: ToolCall) -> ToolResult:
        """Execute one call and convert its command audit into a ToolResult."""
        if (
            call.command.get("target") == "session"
            and call.command.get("function") == "tool_call_error"
            and call.command.get("parameters", {}).get("action_executed")
            is False
        ):
            return self._record_tool_call_error(call)
        before_count = len(self.world.get_audit_records())
        action = self.world.execute(call.command)
        new_records = self.world.get_audit_records()[before_count:]
        command_record = next(
            record
            for record in new_records
            if record["record_type"] == "command"
        )
        command_record = self.world._audit.add_links(
            command_record["record_id"],
            call_id=call.call_id,
            turn_id=call.turn_id,
        )
        if (
            action.code == "[PASS]"
            and call.command["target"] == "session"
            and call.command["function"] == "submit_answer"
        ):
            self.world._answers[-1]["call_id"] = call.call_id
        if (
            action.code == "[PASS]"
            and call.command["target"] == "session"
            and call.command["function"] == "submit_report"
        ):
            self.world._reports[-1]["call_id"] = call.call_id

        self._tool_sequence += 1
        status = "success" if action.code == "[PASS]" else "error"
        return ToolResult(
            call_id=call.call_id,
            turn_id=call.turn_id,
            sequence=self._tool_sequence,
            status=status,
            code=action.code,
            data=deepcopy(action.response),
            mutation_committed=(
                command_record["status"] == "committed"
                and (
                    bool(command_record["state_diff"])
                    or call.command["target"] == "memory"
                    and call.command["function"] in {"create", "update"}
                )
            ),
            audit_sequence=command_record["sequence"],
            error=(
                deepcopy(command_record["error"])
                if status == "error"
                else None
            ),
        )

    def _record_tool_call_error(self, call: ToolCall) -> ToolResult:
        """Record the tool call error."""
        parameters = call.command["parameters"]
        error = {
            "kind": "schema_validation",
            "message": parameters["message"],
            "path": "$.tool_calls",
            "details": {
                "provider_tool": parameters["provider_tool"],
                "raw_arguments": parameters["raw_arguments"],
            },
        }
        data = {"action_executed": False}
        command_record = self.world._audit.append(
            {
                "record_type": "command",
                "simulation_time": deepcopy(
                    self.world.get_state()["runtime"]["time_state"]
                ),
                "status": "rejected",
                "command": deepcopy(call.command),
                "result": {
                    "code": "[VALIDATION_ERROR]",
                    "data": deepcopy(data),
                },
                "events": [],
                "effects": [],
                "state_diff": [],
                "error": deepcopy(error),
            }
        )
        command_record = self.world._audit.add_links(
            command_record["record_id"],
            call_id=call.call_id,
            turn_id=call.turn_id,
        )
        self._tool_sequence += 1
        return ToolResult(
            call_id=call.call_id,
            turn_id=call.turn_id,
            sequence=self._tool_sequence,
            status="error",
            code="[VALIDATION_ERROR]",
            data=data,
            mutation_committed=False,
            audit_sequence=command_record["sequence"],
            error=error,
        )

    def begin_turn(
        self,
        *,
        turn_id: str,
        turn_index: int,
        max_turns: int | None,
    ) -> None:
        """Bind runtime termination evidence to the current runner turn."""
        self.world.set_turn_context(
            turn_id,
            turn_index,
            max_turns=max_turns,
        )

    def submit_boundary(self, boundary: dict[str, Any]) -> dict[str, Any]:
        """Submit one turn boundary to the same World runtime."""
        return self.world.submit_turn_boundary(
            boundary["turn_id"],
            apply_after_turn=boundary["apply_after_turn"],
        )

    def replay(
        self,
        trajectory: dict[str, Any],
        *,
        verify_results: bool = True,
        validate_input: bool = True,
    ) -> dict[str, Any]:
        """Replay stored records and optionally require byte-semantic result equality."""
        if validate_input:
            self.world.contract.validate_trajectory(trajectory)
        if trajectory["world_id"] != self.world.get_state()["world_id"]:
            raise EnvironmentContractError(
                "WORLD_ID_MISMATCH",
                "$.world_id",
                trajectory["world_id"],
            )
        if (
            self.task_id is not None
            and trajectory["task_id"] != self.task_id
        ):
            raise EnvironmentContractError(
                "TASK_ID_MISMATCH",
                "$.task_id",
                trajectory["task_id"],
            )

        expected_termination = trajectory["records"][-1]["termination"]
        max_turns = expected_termination["limits"]["max_turns"]
        turn_indices: dict[str, int] = {}
        for record in trajectory["records"][:-1]:
            turn_id = (
                record["call"]["turn_id"]
                if record["kind"] == "tool_exchange"
                else record["boundary"]["turn_id"]
            )
            if turn_id not in turn_indices:
                turn_indices[turn_id] = len(turn_indices) + 1

        observed_records: list[dict[str, Any]] = []
        for index, record in enumerate(trajectory["records"]):
            if record["kind"] == "tool_exchange":
                call = ToolCall.from_dict(record["call"])
                self.begin_turn(
                    turn_id=call.turn_id,
                    turn_index=turn_indices[call.turn_id],
                    max_turns=max_turns,
                )
                result = self.execute_call(call)
                actual = result.to_dict()
                if verify_results and not strict_equal(actual, record["result"]):
                    raise EnvironmentContractError(
                        "TRAJECTORY_RESULT_MISMATCH",
                        f"$.records[{index}].result",
                        f"expected {record['result']!r}, got {actual!r}",
                    )
                observed_records.append(
                    {
                        "kind": "tool_exchange",
                        "call": call.to_dict(),
                        "result": actual,
                    }
                )
            elif record["kind"] == "turn_boundary":
                boundary = deepcopy(record["boundary"])
                self.begin_turn(
                    turn_id=boundary["turn_id"],
                    turn_index=turn_indices[boundary["turn_id"]],
                    max_turns=max_turns,
                )
                self.submit_boundary(boundary)
                observed_records.append(
                    {"kind": "turn_boundary", "boundary": boundary}
                )
            else:
                if not self.world.terminated:
                    if record["termination"]["reason"] not in {"max_turns", "agent_stopped"}:
                        raise EnvironmentContractError(
                            "TRAJECTORY_TERMINATION_MISSING",
                            f"$.records[{index}]",
                            "runtime did not reproduce the stored terminal event",
                        )
                    self.begin_turn(
                        turn_id=record["termination"]["turn_id"],
                        turn_index=record["termination"]["turn_index"],
                        max_turns=max_turns,
                    )
                    self.world._terminate(record["termination"]["reason"])
                actual_termination = self.world.termination
                if verify_results and not strict_equal(
                    actual_termination,
                    record["termination"],
                ):
                    raise EnvironmentContractError(
                        "TRAJECTORY_TERMINATION_MISMATCH",
                        f"$.records[{index}].termination",
                        f"expected {record['termination']!r}, got {actual_termination!r}",
                    )
                observed_records.append(
                    {
                        "kind": "termination",
                        "termination": deepcopy(actual_termination),
                        **({"result": termination_result(actual_termination["reason"])} if "result" in record else {}),
                    }
                )

        observed = {
            "trajectory_id": trajectory["trajectory_id"],
            "world_id": trajectory["world_id"],
            "task_id": trajectory["task_id"],
            "source": trajectory["source"],
            "records": observed_records,
        }
        self.world.contract.validate_trajectory(observed)
        return observed


TERMINATION_CODES = {
    "agent_stopped": "EMPTY_TOOL_CALL_LIST",
    "session_finish": "SESSION_FINISH",
    "max_turns": "TURN_LIMIT_REACHED",
    "elapsed_time_limit": "TIME_LIMIT_REACHED",
}


def termination_result(reason: str) -> dict[str, Any]:
    """Session execution outcome, separate from agent-issued tool calls."""
    return {"status": "ended", "code": TERMINATION_CODES[reason]}
