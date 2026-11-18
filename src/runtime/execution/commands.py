from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any

from src.utils import format_json
from src.object_model import ActionResult

from .audit import state_diff
from src.contracts.capabilities import precondition_matches
from src.contracts import strict_equal
from src.contracts.errors import EnvironmentContractError
from .errors import RuntimeExecutionError


class CommandRuntime:
    def __init__(self, world: Any) -> None:
        """Initialize the CommandRuntime."""
        self.world = world

    def execute(self, command: dict[str, Any]) -> ActionResult:
        """Execute a command against the current runtime state."""
        if self.world.terminated:
            result = ActionResult(
                str(command.get("target", "session")),
                str(command.get("function", "unknown")),
                "[SESSION_FINISHED]",
                {},
            )
            self._record_error(
                command,
                result,
                RuntimeExecutionError(
                    "[SESSION_FINISHED]",
                    "session_finished",
                    "termination has frozen the final state",
                ),
                validation_only=True,
            )
            return result

        try:
            self.world.contract.validate_command(command, self.world._tool_index)
        except EnvironmentContractError as exc:
            error = self._protocol_error(exc)
            result = ActionResult(
                str(command.get("target", "unknown")),
                str(command.get("function", "unknown")),
                error.code,
                {},
            )
            self._record_error(command, result, error, validation_only=True)
            return result

        try:
            if command["target"] == "session":
                return self._execute_session(command)
            if command["target"] == "memory":
                return self._execute_memory(command)
            if (
                self.world.require_device_tool_discovery
                and not self.world._previewing
                and self.world._device_tool_discovery_turns.get(
                    command["target"], self.world._turn_context["turn_index"]
                ) >= self.world._turn_context["turn_index"]
            ):
                raise RuntimeExecutionError(
                    "[TOOL_NOT_DISCOVERED]",
                    "tool_not_discovered",
                    f"call session_get_device_tools for {command['target']} in a preceding turn",
                    "$.target",
                )
            return self._execute_device(command)
        except RuntimeExecutionError as error:
            result = ActionResult(command["target"], command["function"], error.code, {})
            self._record_error(command, result, error, validation_only=False)
            return result

    def _execute_session(self, command: dict[str, Any]) -> ActionResult:
        """Execute the session."""
        function = command["function"]
        parameters = command["parameters"]
        before = self.world.get_state()
        if function == "get_capabilities":
            data = {"domain": before["domain"]["type"], "space": bool(before["spaces"]), "device": True, "relation": bool(before["domain"]["metadata"].get("relations")), "time_unit": "minute"}
        elif function == "get_devices":
            space_id = parameters["space_id"]
            if space_id not in self.world._state.spaces:
                raise RuntimeExecutionError(
                    "[NOT_FOUND]", "unknown_target", space_id, "$.parameters.space_id"
                )
            device_ids = self.world._state.spaces[space_id].device_ids
            data = {"devices": [
                {"device_id": key, "class": spec["class"],
                 "space_id": spec.get("space_id"),
                 "metadata": deepcopy(spec.get("metadata", {}))}
                for key, spec in sorted(before["objects"].items())
                if key in device_ids
            ]}
        elif function == "get_relations":
            data = {"relations": deepcopy(before["domain"]["metadata"].get("relations", []))}
        elif function == "get_spaces":
            data = {
                "spaces": [
                    {"space_id": space_id, "type": space.type, "virtual": bool(space.virtual)}
                    for space_id, space in sorted(self.world._state.spaces.items())
                ]
            }
        elif function == "get_space_state":
            space_id = parameters["space_id"]
            if space_id not in self.world._state.spaces:
                raise RuntimeExecutionError(
                    "[NOT_FOUND]", "unknown_target", space_id, "$.parameters.space_id"
                )
            space = self.world._state.spaces[space_id]
            data = {
                "space_id": space_id,
                "type": space.type,
                "virtual": bool(space.virtual),
                "properties": deepcopy(space.properties),
                "metadata": deepcopy(space.metadata),
            }
        elif function == "get_space_devices":
            space_id = parameters["space_id"]
            if space_id not in self.world._state.spaces:
                raise RuntimeExecutionError(
                    "[NOT_FOUND]", "unknown_target", space_id, "$.parameters.space_id"
                )
            data = {
                "space_id": space_id,
                "devices": [
                    {
                        "device_id": device_id,
                        "class": self.world._state.devices[device_id].class_path,
                    }
                    for device_id in self.world._state.spaces[space_id].device_ids
                ],
            }
        elif function == "get_device_tools":
            device_id = parameters["device_id"]
            if device_id not in self.world._state.devices:
                raise RuntimeExecutionError(
                    "[NOT_FOUND]", "unknown_target", device_id, "$.parameters.device_id"
                )
            data = {
                "device_id": device_id,
                "tools": [
                    {
                        key: deepcopy(tool[key])
                        for key in (
                            "function",
                            "description",
                            "mutation",
                            "parameters_schema",
                            "duration_minutes",
                            "reads",
                            "writes",
                            "semantics",
                        )
                        if key in tool
                    }
                    for tool in self.world._tool_catalog["tools"]
                    if tool["target_kind"] == "device"
                    and tool["target"] == device_id
                ],
            }
            self.world._device_tool_discovery_turns[device_id] = (
                self.world._turn_context["turn_index"]
            )
        elif function == "sleep_time":
            minutes = parameters.get(
                "minutes", self.world._state.time_policy["sleep_time_default_minutes"]
            )
            audit_checkpoint = self.world._audit.checkpoint()
            command_record = self.world._audit.append(
                {
                    "record_type": "command",
                    "simulation_time": deepcopy(self.world._state.time_state),
                    "status": "committed",
                    "command": deepcopy(command),
                    "result": {
                        "code": "[PASS]",
                        "data": {"minutes": minutes, "tick_count": minutes},
                    },
                    "events": [],
                    "effects": [],
                    "state_diff": [],
                }
            )
            try:
                data = self.world._time.advance(
                    minutes,
                    cause="explicit",
                    action_record_id=command_record["record_id"],
                )
            except Exception:
                self.world._audit.restore(audit_checkpoint)
                raise
            command_record["result"]["data"] = deepcopy(data)
            # Each minute's tick owns its changes and timestamp. The advance
            # command requests time but does not itself change device state.
            self.world._audit.validate(command_record)
            return ActionResult("session", function, "[PASS]", data)
        elif function == "submit_answer":
            self.world._answers.append(
                {
                    "value": deepcopy(parameters["value"]),
                    "call_id": f"answer_{len(self.world._answers) + 1}",
                }
            )
            data = {"accepted": True, "index": len(self.world._answers) - 1}
        elif function == "submit_report":
            report = {
                "status": parameters["status"],
                "reason_code": parameters["reason_code"],
                "description": parameters["description"],
                "affected_properties": deepcopy(
                    parameters.get("affected_properties", [])
                ),
                "call_id": f"report_{len(self.world._reports) + 1}",
            }
            self.world._reports.append(report)
            data = {"accepted": True, "index": len(self.world._reports) - 1}
        elif function == "finish":
            data = {"finished": True}
        else:
            raise AssertionError(function)

        after = self.world.get_state()
        tool = self.world._tool_index[f"session_{function}"]
        self.world._audit.append(
            {
                "record_type": "command",
                "simulation_time": deepcopy(self.world._state.time_state),
                "status": "committed" if tool["mutation"] else "observed",
                "command": deepcopy(command),
                "result": {"code": "[PASS]", "data": deepcopy(data)},
                "events": [],
                "effects": [],
                "state_diff": state_diff(before, after),
            }
        )
        if function == "finish":
            self.world._terminate("session_finish")
        return ActionResult("session", function, "[PASS]", data)

    def _execute_memory(self, command: dict[str, Any]) -> ActionResult:
        """Execute the memory."""
        function = command["function"]
        parameters = command["parameters"]
        if function == "read":
            data = {
                "records": [
                    {
                        "memory_id": record["memory_id"],
                        "content": record["content"],
                    }
                    for record in self.world._memory["records"]
                ]
            }
        else:
            records = deepcopy(self.world._memory["records"])
            if function == "create":
                content = parameters["content"]
                user_id = parameters.get("user_id")
                identity = format_json(
                    [self.world._memory["scope_id"], user_id, content, len(records)],
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                memory_id = "memory_" + hashlib.sha256(
                    identity.encode("utf-8")
                ).hexdigest()[:16]
                record = {"memory_id": memory_id, "content": content}
                if user_id is not None:
                    record["user_id"] = user_id
                records.append(record)
            elif function == "update":
                memory_id = parameters["memory_id"]
                index = next(
                    (
                        index
                        for index, record in enumerate(records)
                        if record["memory_id"] == memory_id
                    ),
                    None,
                )
                if index is None:
                    raise RuntimeExecutionError(
                        "[NOT_FOUND]",
                        "unknown_memory",
                        memory_id,
                        "$.parameters.memory_id",
                    )
                records[index]["content"] = parameters["content"]
                record = records[index]
            else:
                raise AssertionError(function)
            candidate = {
                "scope_id": self.world._memory["scope_id"],
                "records": records,
            }
            try:
                self.world.contract.validate_memory(candidate)
            except EnvironmentContractError as error:
                raise self._protocol_error(error) from error
            self.world._memory = candidate
            data = {
                "record": {
                    "memory_id": record["memory_id"],
                    "content": record["content"],
                }
            }
        self.world._audit.append(
            {
                "record_type": "command",
                "simulation_time": deepcopy(self.world._state.time_state),
                "status": "observed" if function == "read" else "committed",
                "command": deepcopy(command),
                "result": {"code": "[PASS]", "data": deepcopy(data)},
                "events": [],
                "effects": [],
                "state_diff": [],
            }
        )
        return ActionResult("memory", function, "[PASS]", data)

    def _execute_device(self, command: dict[str, Any]) -> ActionResult:
        """Execute the device."""
        device_id = command["target"]
        function = command["function"]
        parameters = command["parameters"]
        tool = self.world._tool_index[f"{device_id}_{function}"]
        device = self.world._state.devices[device_id]
        method = getattr(device.instance, function)
        before = self.world.get_state()

        effective_parameters = {name: spec["default"] for name, spec in tool["parameters_schema"]["properties"].items() if "default" in spec}
        effective_parameters.update(parameters)
        for prop, condition in tool.get("semantics", {}).get("preconditions", {}).items():
            if not precondition_matches(before["objects"][device_id]["properties"][prop], condition, effective_parameters):
                raise RuntimeExecutionError("[EXECUTION_ERROR]", "execution_failure", f"{device_id}_{function} requires {prop}={condition!r}")

        if not tool["mutation"]:
            checkpoint = self.world._state.checkpoint()
            try:
                code, data = self._invoke_device(method, parameters)
                if not strict_equal(before, self.world.get_state()):
                    raise RuntimeExecutionError("[EXECUTION_ERROR]", "undeclared_mutation", "an observation changed World state")
            except Exception:
                self.world._state.restore(checkpoint)
                raise
            self.world._audit.append(
                {
                    "record_type": "command",
                    "simulation_time": deepcopy(self.world._state.time_state),
                    "status": "observed",
                    "command": deepcopy(command),
                    "result": {"code": "[PASS]", "data": deepcopy(data)},
                    "events": [],
                    "effects": [],
                    "state_diff": [],
                }
            )
            return ActionResult(device_id, function, "[PASS]", data)

        state_checkpoint = self.world._state.checkpoint()
        reducer_checkpoint = self.world._reducer.checkpoint()
        audit_checkpoint = self.world._audit.checkpoint()
        try:
            code, data = self._invoke_device(method, parameters)
            changed = [
                prop
                for prop in device.property_names
                if not strict_equal(
                    before["objects"][device_id]["properties"][prop],
                    device.properties()[prop],
                )
            ]
            hook = getattr(device.instance, "_on_after_action", None)
            event = {
                "trigger": "after_action",
                "source": device_id,
                "hook": "_on_after_action",
                "status": "dispatched" if callable(hook) else "skipped",
                "changed_properties": sorted(changed),
            }
            effects: list[dict[str, Any]] = []
            dependencies = set(device.effect_properties)
            if callable(hook) and changed and dependencies.issubset(device.property_names):
                hook_code, emitted = hook(self.world._hook_context(device_id, before, None))
                if hook_code != "[PASS]":
                    raise RuntimeExecutionError("[EFFECT_ERROR]", "effect_validation", hook_code)
                for effect in emitted:
                    if (
                        effect.get("trigger") != "after_action"
                        or effect.get("source") != device_id
                    ):
                        raise RuntimeExecutionError(
                            "[EFFECT_ERROR]",
                            "effect_validation",
                            "after-action effect trigger/source does not match its hook",
                        )
                    effects.append(deepcopy(effect))
            try:
                applications = self.world._reducer.apply(effects)
            except EnvironmentContractError as exc:
                result_code = "[CONFLICT]" if exc.code == "EFFECT_CONFLICT" else "[EFFECT_ERROR]"
                kind = "effect_conflict" if result_code == "[CONFLICT]" else "effect_validation"
                raise RuntimeExecutionError(result_code, kind, exc.message, exc.path) from exc
            dependency_events = self.world._notify_dependencies(before)
            after = self.world.get_state()
            if "writes" in tool:
                changed_properties = {
                    item["property"] for item in state_diff(before, after)
                    if item["scope"] == "object" and item["target_id"] == device_id
                }
                if changed_properties - set(tool["writes"]):
                    raise RuntimeExecutionError("[EXECUTION_ERROR]", "undeclared_mutation", f"undeclared writes: {sorted(changed_properties - set(tool['writes']))}")
            action_record = self.world._audit.append(
                {
                    "record_type": "command",
                    "simulation_time": deepcopy(self.world._state.time_state),
                    "status": "committed",
                    "command": deepcopy(command),
                    "result": {"code": "[PASS]", "data": deepcopy(data)},
                    "events": [event, *dependency_events],
                    "effects": applications,
                    "state_diff": state_diff(before, after),
                }
            )
            duration = tool.get(
                "duration_minutes",
                self.world._state.time_policy["after_action_default_minutes"],
            )
            if duration:
                self.world._time.advance(
                    duration,
                    cause="after_action",
                    action_record_id=action_record["record_id"],
                )
        except Exception:
            self.world._state.restore(state_checkpoint)
            self.world._reducer.restore(reducer_checkpoint)
            self.world._audit.restore(audit_checkpoint)
            raise
        return ActionResult(device_id, function, "[PASS]", data)

    @staticmethod
    def _invoke_device(method: Any, parameters: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        result = method(**parameters)
        if not isinstance(result, tuple) or len(result) != 2 or not isinstance(result[0], str) or not isinstance(result[1], dict):
            raise RuntimeExecutionError("[EXECUTION_ERROR]", "invalid_model_result", f"device method must return (code: str, response: dict), got {result!r}")
        code, data = result
        if code != "[PASS]":
            raise RuntimeExecutionError("[EXECUTION_ERROR]", "execution_failure", code)
        return code, data

    def _record_error(
        self,
        command: dict[str, Any],
        result: ActionResult,
        error: RuntimeExecutionError,
        *,
        validation_only: bool,
    ) -> None:
        """Append one rejected or rolled-back command audit record."""
        payload: dict[str, Any] = {
            "record_type": "command",
            "simulation_time": deepcopy(self.world._state.time_state),
            "status": "rejected" if validation_only else "rolled_back",
            "result": {"code": result.code, "data": {}},
            "events": [],
            "effects": [],
            "state_diff": [],
            "error": {
                "kind": error.kind,
                "message": error.message or str(error),
                "path": error.path,
            },
        }
        try:
            self.world.contract.validate_schema(command, "urn:dcb:v2:schema:command")
        except EnvironmentContractError:
            self.world._audit.append(payload)
            return
        payload["command"] = deepcopy(command)
        self.world._audit.append(payload)

    @staticmethod
    def _protocol_error(error: EnvironmentContractError) -> RuntimeExecutionError:
        """Return the protocol error."""
        if error.code in {"UNKNOWN_TARGET", "UNKNOWN_FUNCTION"}:
            kind = "unknown_target" if error.code == "UNKNOWN_TARGET" else "unknown_function"
            return RuntimeExecutionError("[NOT_FOUND]", kind, error.message, error.path)
        kind = "invalid_parameters" if error.code == "INVALID_PARAMETERS" else "schema_validation"
        return RuntimeExecutionError("[VALIDATION_ERROR]", kind, error.message, error.path)
