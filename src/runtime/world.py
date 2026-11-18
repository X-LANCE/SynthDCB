from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from pickle import dumps, loads, HIGHEST_PROTOCOL
from types import SimpleNamespace
from typing import Any, Iterable

from src.utils import format_json
from src.contracts import ContractPackage, strict_equal
from src.contracts.errors import EnvironmentContractError
from src.contracts.capabilities import effect_properties
from src.object_model import ActionResult, BaseProperty
from src.object_model import MutableWorldState

from .execution import (
    AuditTrail,
    CommandRuntime,
    EffectReducer,
    TimeRuntime,
    ToolCatalogBuilder,
    state_diff,
)
from .cache import DomainRuntimeCache, WorldBlueprint
from .execution.errors import RuntimeExecutionError


def _copy_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Copy an internal snapshot with the C serializer, retaining nested isolation."""
    return loads(dumps(snapshot, protocol=HIGHEST_PROTOCOL))


class _ObjectsNamespace(SimpleNamespace):
    def _as_dict(self) -> dict[str, Any]:
        """Serialize the value as a dictionary."""
        return dict(self.__dict__)


@dataclass(frozen=True, slots=True)
class ActionPreview:
    """Isolated action results and the state they would produce."""

    results: tuple[ActionResult, ...]
    final_state: dict[str, Any]
    differences: tuple[dict[str, Any], ...]
    audit_records: tuple[dict[str, Any], ...]


class World:
    def __init__(
        self,
        world_dir: str | Path,
        domain_path: str | Path | None = None,
        *,
        domain: str | None = None,
        domain_config_root: str | Path | None = None,
        contract_root: str | Path | None = None,
        runtime_cache: DomainRuntimeCache | None = None,
        blueprint: WorldBlueprint | None = None,
        require_device_tool_discovery: bool = True,
    ) -> None:
        """Initialize the World."""
        if type(require_device_tool_discovery) is not bool:
            raise TypeError("require_device_tool_discovery must be a boolean")
        self.world_dir = Path(world_dir).resolve()
        if blueprint is not None and runtime_cache is None:
            raise ValueError("a World blueprint requires its DomainRuntimeCache")
        if runtime_cache is None:
            if domain is None or domain_path is None:
                raise ValueError("domain and domain_path are required")
            runtime_cache = DomainRuntimeCache(
                domain, domain_path, contract_root=contract_root,
                domain_config_root=domain_config_root,
            )
        if domain is not None:
            runtime_cache.assert_domain(domain)
        if contract_root is not None and Path(contract_root).resolve() != runtime_cache.contract.root:
            raise ValueError("contract_root differs from the runtime cache")
        if domain_path is not None and Path(domain_path).resolve() != runtime_cache.domain_path:
            raise ValueError("domain_path differs from the runtime cache")
        self.runtime_cache = runtime_cache
        self.domain_path = runtime_cache.domain_path
        self.loader = runtime_cache.world_loader
        selected = blueprint or runtime_cache.load_world_blueprint(self.world_dir)
        if selected.root != self.world_dir:
            raise ValueError("World blueprint root differs from world_dir")
        if not runtime_cache.owns_blueprint(selected):
            raise ValueError("World blueprint is not owned by its runtime cache")
        runtime_cache.assert_domain(selected.domain)
        self.blueprint = selected
        self.loaded_world = selected.loaded_world
        self.contract: ContractPackage = self.loaded_world.contract
        self.target_registry = self.loaded_world.target_registry
        self.domain_registry = self.loaded_world.domain_registry
        self._world_spec = deepcopy(self.loaded_world.world)
        self._actions: list[ActionResult] = []
        self._answers: list[dict[str, Any]] = []
        self._reports: list[dict[str, Any]] = []
        self._memory: dict[str, Any] = {
            "scope_id": "empty_memory",
            "records": [],
        }
        self._initial_memory = deepcopy(self._memory)
        self._finished = False
        self._termination: dict[str, Any] | None = None
        self._final_state: dict[str, Any] | None = None
        self._post_simulation: dict[str, Any] | None = None
        self.require_device_tool_discovery = require_device_tool_discovery
        self._device_tool_discovery_turns: dict[str, int] = {}
        self._previewing = False
        self._preview_validation_enabled = True
        self._turn_context = {
            "turn_id": "turn_1",
            "turn_index": 1,
            "max_turns": None,
        }

        self._state = MutableWorldState(self._world_spec)
        self._objects_dict: dict[str, Any] = {}
        self._instantiate_objects()
        self.objects = _ObjectsNamespace(**self._objects_dict)

        self._reducer = EffectReducer(self._state, self._world_spec, self.contract)
        self._audit = AuditTrail(self.contract)
        self._time = TimeRuntime(
            self._state,
            self._world_spec,
            self.contract,
            self._reducer,
            self._audit,
            self.get_state,
            self._hook_context,
            self._terminate,
            self._notify_dependencies,
        )
        if self.blueprint is not None:
            self._tool_catalog = deepcopy(self.blueprint.tool_catalog)
            self._tool_index = deepcopy(self.blueprint.tool_index)
        else:
            self._tool_catalog, self._tool_index = ToolCatalogBuilder(
                self.contract
            ).build(
                self._world_spec,
                self._objects_dict,
                {
                    device_id: self._state.devices[device_id].property_names
                    for device_id in self._state.devices
                },
                class_descriptors=dict(self.runtime_cache.class_tool_descriptors),
            )
        self._commands = CommandRuntime(self)
        self._current_state = self._state.snapshot()
        initial = deepcopy(self._current_state)
        self._notify_dependencies(initial, initialize=True)
        if not strict_equal(initial, self.get_state()):
            raise EnvironmentContractError("INCONSISTENT_DEPENDENCY_STATE", "$.objects", "initial module states disagree with their declared dependencies")
        if self.blueprint is None:
            self.contract.validate_snapshot(
                self._current_state, self._world_spec, label="runtime_initial"
            )
        if not strict_equal(
            self._current_state,
            self.loaded_world.initial_snapshot,
        ):
            raise EnvironmentContractError(
                "RUNTIME_INITIAL_SNAPSHOT_MISMATCH",
                "$",
                "instantiated device state differs from the resolved world",
            )
        self._init_state = deepcopy(self._current_state)

    @property
    def finished(self) -> bool:
        """Return whether the world interaction has finished."""
        return self._finished

    @property
    def terminated(self) -> bool:
        """Return whether the world interaction was terminated."""
        return self._termination is not None

    @property
    def termination(self) -> dict[str, Any] | None:
        """Return the termination."""
        return deepcopy(self._termination)

    @property
    def submitted_answers(self) -> tuple[dict[str, Any], ...]:
        """Return the submitted answers."""
        return tuple(deepcopy(self._answers))

    @property
    def submitted_reports(self) -> tuple[dict[str, Any], ...]:
        """Return the submitted reports."""
        return tuple(deepcopy(self._reports))

    def bind_memory(self, memory: dict[str, Any] | None) -> None:
        """Bind one private task scope without changing the public tool catalog."""
        payload = deepcopy(memory) if memory is not None else {
            "scope_id": "empty_memory",
            "records": [],
        }
        self.contract.validate_memory(payload)
        self._memory = payload
        self._initial_memory = deepcopy(payload)

    def read_memory(self) -> tuple[str, dict[str, Any]]:
        """Return the memory."""
        result = self.execute(
            {"target": "memory", "function": "read", "parameters": {}}
        )
        return result.code, result.response

    def get_memory(self) -> dict[str, Any]:
        """Return the memory."""
        return deepcopy(self._memory)

    def get_initial_memory(self) -> dict[str, Any]:
        """Return the initial memory."""
        return deepcopy(self._initial_memory)

    @property
    def final_state(self) -> dict[str, Any] | None:
        """Return the final state."""
        return deepcopy(self._final_state)

    def set_turn_context(
        self,
        turn_id: str,
        turn_index: int,
        *,
        max_turns: int | None,
    ) -> None:
        """Set runner-owned context used by terminal runtime evidence."""
        if not isinstance(turn_index, int) or isinstance(turn_index, bool) or turn_index < 1:
            raise ValueError("turn_index must be a positive integer")
        if max_turns is not None and (
            not isinstance(max_turns, int)
            or isinstance(max_turns, bool)
            or max_turns < turn_index
        ):
            raise ValueError("max_turns must be at least turn_index")
        self.contract.validate_schema(
            {"turn_id": turn_id, "apply_after_turn": False},
            "urn:dcb:v2:schema:turn-boundary",
        )
        self._turn_context = {
            "turn_id": turn_id,
            "turn_index": turn_index,
            "max_turns": max_turns,
        }

    def bind_evaluation_horizon(self, end_minute: int | None) -> None:
        """Apply the task's time budget without changing the reusable World."""
        self._time.evaluation_end_minute = end_minute

    def get_limits(
        self,
        *,
        max_turns: int,
        turn_index: int,
    ) -> dict[str, Any]:
        """Return the public runner and simulated-time budgets for one turn."""
        elapsed = self._state.time_state["elapsed_minutes"]
        max_elapsed = self._time.max_elapsed_minutes
        return {
            "max_turns": max_turns,
            "remaining_turns": max_turns - turn_index + 1,
            "elapsed_minutes": elapsed,
            "time_state": deepcopy(self._state.time_state),
            "max_elapsed_minutes": max_elapsed,
            "evaluation_end_minute": self._time.evaluation_end_minute,
            "remaining_minutes": (
                None if max_elapsed is None else max_elapsed - elapsed
            ),
            "device_tool_discovery": (
                "required" if self.require_device_tool_discovery else "optional"
            ),
        }

    def _terminate(self, reason: str) -> dict[str, Any]:
        """Freeze the first terminal event and append audit evidence."""
        if self._termination is not None:
            return deepcopy(self._termination)
        max_elapsed = self._time.max_elapsed_minutes
        termination = {
            "reason": reason,
            "turn_id": self._turn_context["turn_id"],
            "turn_index": self._turn_context["turn_index"],
            "elapsed_minutes": self._state.time_state["elapsed_minutes"],
            "limits": {
                "max_turns": self._turn_context["max_turns"],
                "max_elapsed_minutes": max_elapsed,
            },
        }
        self.contract.validate_schema(
            termination,
            "urn:dcb:v2:schema:termination",
        )
        final_state = self.get_state()
        self._audit.append(
            {
                "record_type": "termination",
                "simulation_time": deepcopy(self._state.time_state),
                "status": "observed",
                "links": {"turn_id": termination["turn_id"]},
                "events": [],
                "effects": [],
                "state_diff": [],
                "termination": termination,
            }
        )
        self._termination = deepcopy(termination)
        self._finished = reason == "session_finish"
        self._final_state = final_state
        return deepcopy(termination)

    def terminate_max_turns(
        self,
        *,
        turn_id: str,
        turn_index: int,
        max_turns: int,
    ) -> dict[str, Any]:
        """Let the runner record budget exhaustion without exposing a tool."""
        self.set_turn_context(
            turn_id,
            turn_index,
            max_turns=max_turns,
        )
        return self._terminate("max_turns")

    def _instantiate_objects(self) -> None:
        """Instantiate the objects."""
        for device_id, spec in self._world_spec["objects"].items():
            cls = self._resolve_class(spec["class"])
            instance = cls(**deepcopy(spec["properties"]))
            for prop, expected in spec["properties"].items():
                if not hasattr(instance, prop):
                    raise EnvironmentContractError(
                        "OBJECT_PROPERTY_MISSING",
                        f"$.objects.{device_id}.properties.{prop}",
                        spec["class"],
                    )
                container = getattr(instance, prop)
                if not isinstance(container, BaseProperty):
                    raise EnvironmentContractError(
                        "OBJECT_PROPERTY_INVALID",
                        f"$.objects.{device_id}.properties.{prop}",
                        "device properties must use BaseProperty",
                    )
                if not strict_equal(container.value, expected):
                    raise EnvironmentContractError(
                        "OBJECT_PROPERTY_INITIALIZATION_MISMATCH",
                        f"$.objects.{device_id}.properties.{prop}",
                        f"expected {expected!r}, got {container.value!r}",
                    )
            self._objects_dict[device_id] = instance
            device = self._state.attach_device(device_id, spec, instance)
            device.effect_properties = effect_properties(
                self.loaded_world.domain.specifications[spec["class"]]
            )

    def _resolve_class(self, class_path: str) -> type:
        """Resolve classes from the one fully loaded device directory."""
        return self.runtime_cache.resolve_class(class_path)

    def _hook_context(
        self,
        device_id: str,
        pre_state: dict[str, Any],
        minutes: int | None,
    ) -> dict[str, Any]:
        """Return the hook context."""
        device = self._state.devices[device_id]
        space_state = (
            deepcopy(pre_state["spaces"][device.space_id]["properties"])
            if device.space_id is not None
            else {}
        )
        context: dict[str, Any] = {
            "object_id": device_id,
            "device_id": device_id,
            "space_id": device.space_id,
            "domain_state": deepcopy(space_state),
            "space_state": space_state,
            "pre_state": _copy_snapshot(pre_state),
            "time_state": deepcopy(self._state.time_state),
        }
        if minutes is not None:
            context["minutes"] = minutes
        return context

    def _notify_dependencies(self, before: dict[str, Any], *, initialize: bool = False) -> list[dict[str, Any]]:
        """Notify receivers in dependency order inside the caller's transaction.

        A relation's source is the dependency, target is the receiver. Hooks
        update only their own properties; this interface emits no Space effects.
        Cycles are rejected when loading the World.
        """
        from graphlib import TopologicalSorter
        from src.runtime.execution.errors import RuntimeExecutionError
        graph: dict[str, set[str]] = {}
        for relation in before["domain"]["metadata"].get("relations", []):
            if relation["type"] == "depends_on":
                graph.setdefault(relation["target_id"], set()).add(relation["source_id"])
        events = []
        for receiver in TopologicalSorter(graph).static_order():
            dependencies = graph.get(receiver, set())
            current = self.get_state()
            changed = [source for source in sorted(dependencies) if initialize or not strict_equal(
                before["objects"][source]["properties"], current["objects"][source]["properties"]
            )]
            if not changed:
                continue
            instance = self._state.devices[receiver].instance
            hook = getattr(instance, "_on_dependency_changed", None)
            if not callable(hook):
                raise RuntimeExecutionError("[EXECUTION_ERROR]", "execution_failure", f"{receiver} has no dependency handler")
            code, effects = hook({
                "object_id": receiver,
                "changed_sources": changed,
                "dependencies": {source: deepcopy(current["objects"][source]["properties"]) for source in sorted(dependencies)},
                "time_state": deepcopy(self._state.time_state),
            })
            if code != "[PASS]" or effects:
                raise RuntimeExecutionError("[EXECUTION_ERROR]", "execution_failure", f"{receiver} dependency handler failed: {code}")
            updated = self.get_state()
            from src.runtime.execution.audit import state_diff
            if any(item["scope"] != "object" or item["target_id"] != receiver
                   for item in state_diff(current, updated)):
                raise RuntimeExecutionError("[EXECUTION_ERROR]", "undeclared_mutation", f"{receiver} changed state outside its own properties")
            events.append({
                "trigger": "dependency_changed", "source": receiver,
                "hook": "_on_dependency_changed", "status": "dispatched",
                "changed_properties": sorted(name for name, value in current["objects"][receiver]["properties"].items()
                    if not strict_equal(value, updated["objects"][receiver]["properties"][name])),
            })
        return events

    def get_state(self) -> dict[str, Any]:
        """Return the state."""
        snapshot = self._state.snapshot()
        if not strict_equal(snapshot, self._current_state):
            if not self._previewing or self._preview_validation_enabled:
                self.contract.validate_snapshot(
                    snapshot, self._world_spec, label="runtime_current"
                )
            self._current_state = snapshot
        return _copy_snapshot(self._current_state)

    def get_initial_state(self) -> dict[str, Any]:
        """Return the initial state."""
        return deepcopy(self._init_state)

    def get_world_spec(self) -> dict[str, Any]:
        """Return the resolved world definition used by this runtime."""
        return deepcopy(self._world_spec)

    def get_tool_catalog(self) -> dict[str, Any]:
        """Return the tool catalog."""
        return deepcopy(self._tool_catalog)

    def get_audit_records(self) -> list[dict[str, Any]]:
        """Return the audit records."""
        return self._audit.records()

    def execute(self, command: dict[str, Any]) -> ActionResult:
        """Execute one command against the world."""
        result = self._commands.execute(command)
        self._actions.append(result)
        return result

    def apply_actions(
        self, actions: Iterable[dict[str, Any]]
    ) -> list[ActionResult]:
        """Apply the actions."""
        return [self.execute(command) for command in actions]

    def preview_actions(
        self,
        actions: Iterable[dict[str, Any]],
        *,
        turn_id: str = "turn_1",
        turn_index: int = 1,
        max_turns: int = 4,
        validate: bool = True,
    ) -> ActionPreview:
        """Execute against this instance, then restore every mutable field.

        ``validate=False`` is for speculative sampling whose selected result is
        replayed through the strict task-validation gate before publication.
        """
        if type(validate) is not bool:
            raise TypeError("validate must be a boolean")
        state_checkpoint = self._state.checkpoint()
        reducer_checkpoint = self._reducer.checkpoint()
        audit_checkpoint = self._audit.checkpoint()
        local_checkpoint = {
            "actions": deepcopy(self._actions),
            "answers": deepcopy(self._answers),
            "reports": deepcopy(self._reports),
            "memory": deepcopy(self._memory),
            "finished": self._finished,
            "termination": deepcopy(self._termination),
            "final_state": deepcopy(self._final_state),
            "turn_context": deepcopy(self._turn_context),
            "current_state": deepcopy(self._current_state),
            "device_tool_discovery_turns": dict(self._device_tool_discovery_turns),
            "previewing": self._previewing,
            "preview_validation_enabled": self._preview_validation_enabled,
            "audit_validation_enabled": self._audit._validation_enabled,
        }
        before = self.get_state()
        try:
            self._previewing = True
            self._preview_validation_enabled = validate
            self._audit._validation_enabled = validate
            self.set_turn_context(
                turn_id,
                turn_index,
                max_turns=max_turns,
            )
            results = tuple(self.apply_actions(deepcopy(tuple(actions))))
            final_state = self.get_state()
            return ActionPreview(
                results=deepcopy(results),
                final_state=final_state,
                differences=tuple(state_diff(before, final_state)),
                audit_records=tuple(
                    self._audit.records()[audit_checkpoint[0] :]
                ),
            )
        finally:
            self._state.restore(state_checkpoint)
            self._reducer.restore(reducer_checkpoint)
            self._audit.restore(audit_checkpoint)
            self._actions = local_checkpoint["actions"]
            self._answers = local_checkpoint["answers"]
            self._reports = local_checkpoint["reports"]
            self._memory = local_checkpoint["memory"]
            self._finished = local_checkpoint["finished"]
            self._termination = local_checkpoint["termination"]
            self._final_state = local_checkpoint["final_state"]
            self._turn_context = local_checkpoint["turn_context"]
            self._current_state = local_checkpoint["current_state"]
            self._device_tool_discovery_turns = local_checkpoint[
                "device_tool_discovery_turns"
            ]
            self._previewing = local_checkpoint["previewing"]
            self._preview_validation_enabled = local_checkpoint[
                "preview_validation_enabled"
            ]
            self._audit._validation_enabled = local_checkpoint[
                "audit_validation_enabled"
            ]

    def get_spaces(self) -> tuple[str, dict[str, Any]]:
        """Return the spaces."""
        result = self.execute(
            {"target": "session", "function": "get_spaces", "parameters": {}}
        )
        return result.code, result.response

    def get_space_state(self, space_id: str) -> tuple[str, dict[str, Any]]:
        """Return the space state."""
        result = self.execute(
            {
                "target": "session",
                "function": "get_space_state",
                "parameters": {"space_id": space_id},
            }
        )
        return result.code, result.response

    def get_space_devices(self, space_id: str) -> tuple[str, dict[str, Any]]:
        """Return the space devices."""
        result = self.execute(
            {
                "target": "session",
                "function": "get_space_devices",
                "parameters": {"space_id": space_id},
            }
        )
        return result.code, result.response

    def get_device_tools(self, device_id: str) -> tuple[str, dict[str, Any]]:
        """Return the device tools."""
        result = self.execute(
            {
                "target": "session",
                "function": "get_device_tools",
                "parameters": {"device_id": device_id},
            }
        )
        return result.code, result.response

    def sleep_time(self, minutes: int | None = None) -> tuple[str, dict[str, Any]]:
        """Wait for the requested duration in simulated world time."""
        parameters = {} if minutes is None else {"minutes": minutes}
        result = self.execute(
            {
                "target": "session",
                "function": "sleep_time",
                "parameters": parameters,
            }
        )
        return result.code, result.response

    def submit_answer(self, value: Any) -> tuple[str, dict[str, Any]]:
        """Submit the agent's final answer."""
        result = self.execute(
            {
                "target": "session",
                "function": "submit_answer",
                "parameters": {"value": value},
            }
        )
        return result.code, result.response

    def submit_report(
        self,
        status: str,
        reason_code: str,
        description: str,
        affected_properties: list[str] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Submit the agent's execution report."""
        result = self.execute(
            {
                "target": "session",
                "function": "submit_report",
                "parameters": {
                    "status": status,
                    "reason_code": reason_code,
                    "description": description,
                    "affected_properties": affected_properties or [],
                },
            }
        )
        return result.code, result.response

    def finish(self) -> tuple[str, dict[str, Any]]:
        """Finish the current interaction."""
        result = self.execute(
            {"target": "session", "function": "finish", "parameters": {}}
        )
        return result.code, result.response

    @property
    def post_simulation(self) -> dict[str, Any] | None:
        return deepcopy(self._post_simulation)

    def simulate_until(self, end_elapsed_minutes: int) -> dict[str, Any]:
        """Stop agent interaction and complete one fixed evaluation horizon."""
        if self._post_simulation is not None:
            if self._post_simulation["end_elapsed_minutes"] != end_elapsed_minutes:
                raise ValueError("the simulation horizon cannot change after termination")
            return deepcopy(self._post_simulation)
        if not self.terminated:
            self._terminate("agent_stopped")
        before_count = len(self._audit.records())
        evidence = {
            "status": "completed", "end_elapsed_minutes": end_elapsed_minutes,
            "agent_termination": self.termination, "agent_snapshot": self.final_state,
            "background_audit": [], "final_snapshot": None, "error": None,
        }
        try:
            minutes = end_elapsed_minutes - self._state.time_state["elapsed_minutes"]
            if minutes < 0:
                raise ValueError("the fixed evaluation horizon precedes agent termination")
            self._time.advance(minutes, cause="post_agent", enforce_agent_limit=False)
            evidence["background_audit"] = self._audit.records()[before_count:]
            evidence["final_snapshot"] = self.get_state()
        except (RuntimeExecutionError, RuntimeError, EnvironmentContractError, ValueError, TypeError, ArithmeticError, LookupError, AssertionError, AttributeError, NameError) as error:
            evidence["status"] = "failed"
            evidence["error"] = {"kind": "simulation_failure", "message": str(error), "details": {"exception_type": type(error).__name__}}
        self.contract.validate_schema(evidence, "urn:dcb:v2:schema:post-simulation")
        self._post_simulation = evidence
        return deepcopy(evidence)

    def submit_turn_boundary(
        self,
        turn_id: str,
        *,
        apply_after_turn: bool,
        turn_index: int | None = None,
        max_turns: int | None = None,
    ) -> dict[str, Any]:
        """Record the boundary of an agent turn."""
        if turn_index is not None:
            self.set_turn_context(
                turn_id,
                turn_index,
                max_turns=max_turns,
            )
        return self._time.submit_turn_boundary(
            turn_id,
            apply_after_turn=apply_after_turn,
            terminated=self.terminated,
        )

    def describe_objects(self) -> dict[str, Any]:
        """Describe the objects."""
        return self.get_state()["objects"]

    def describe_spaces(self) -> dict[str, Any]:
        """Describe the spaces."""
        return self.get_state()["spaces"]

    def describe(self) -> dict[str, Any]:
        """Return a structured description of the world."""
        state = self.get_state()
        return {
            "domain": state["domain"],
            "objects": state["objects"],
            "spaces": state["spaces"],
            "runtime": state["runtime"],
            "scene_metadata": state["scene_metadata"],
        }

    def get_properties_state(self) -> dict[str, Any]:
        """Return the properties state."""
        state = self.get_state()
        return {
            "objects": {
                target_id: {"properties": data["properties"]}
                for target_id, data in state["objects"].items()
            },
            "spaces": {
                target_id: {"properties": data["properties"]}
                for target_id, data in state["spaces"].items()
            },
            "runtime": state["runtime"],
        }

    def get_objects_text(self) -> str:
        """Return the objects text."""
        lines = []
        for device_id, data in self.describe_objects().items():
            properties = ", ".join(
                f"{key}={value}" for key, value in data["properties"].items()
            )
            lines.append(f"{device_id}({data['class']}): {properties}")
        return "\n".join(lines)

    def get_state_text(self) -> str:
        """Return the state text."""
        return format_json(self.get_state(), ensure_ascii=False, sort_keys=True)

    def get_actions_text(self) -> str:
        """Return the actions text."""
        return "\n".join(
            f"{result.target}.{result.function} => {result.code}"
            for result in self._actions
        )

    def list_available_actions(self) -> list[ActionResult]:
        """Return the available actions."""
        return [
            ActionResult(tool["target"], tool["function"], "[AVAILABLE]", {})
            for tool in self._tool_catalog["tools"]
        ]

    def list_actions(self) -> list[ActionResult]:
        """Return the actions."""
        return deepcopy(self._actions) if self._actions else self.list_available_actions()

    def print_state(self) -> None:
        """Print the state."""
        print(self.get_state_text())

    def print_objects(self) -> None:
        """Print the objects."""
        print(self.get_objects_text())

    def print_actions(self) -> None:
        """Print the actions."""
        print(self.get_actions_text())

    def render_state(self) -> str:
        """Return the state."""
        text = self.get_state_text()
        print(text)
        return text
