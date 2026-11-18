"""Public task context and per-step observations over the existing World runtime."""
from copy import deepcopy

from src.runtime.execution.tools import builtin_tools
from ..interfaces import TaskContext, Observation, ToolInvocation, ActionBatch
from .trajectory import TrajectoryExecutor, termination_result


class EvaluationEnvironment:
    def __init__(self, world, task_bundle, *, max_turns):
        if not isinstance(max_turns, int) or isinstance(max_turns, bool) or max_turns < 1:
            raise ValueError("max_turns must be a positive integer")
        self.world = world
        self.task_bundle = task_bundle
        self.max_turns = max_turns
        self.executor = TrajectoryExecutor(world, task_id=task_bundle.task_id)
        self.records = []
        self.turn_index = 1
        self.call_index = 0
        self.tool_results = []

    @property
    def terminated(self):
        return self.world.terminated

    def get_task_context(self) -> TaskContext:
        return TaskContext(
            instruction=self.task_bundle.instruction,
            domain=self.world.get_state()["domain"]["type"],
            current_user=deepcopy(self.task_bundle.task.get("current_user")),
            tools=builtin_tools(),
        )

    def observe(self) -> Observation:
        return Observation(
            tool_results=deepcopy(self.tool_results),
            turn_index=self.turn_index,
            simulation_time=deepcopy(self.world.get_state()["runtime"]["time_state"]),
        )

    def step(self, tool_calls: list[ToolInvocation]) -> None:
        """Execute a batch sequentially; never treat a failed call as an empty batch."""
        if self.terminated:
            raise RuntimeError("cannot step a terminated environment")
        turn_id = f"turn_{self.turn_index}"
        self.executor.begin_turn(turn_id=turn_id, turn_index=self.turn_index, max_turns=self.max_turns)
        self.tool_results = []
        parse_failed = isinstance(tool_calls, ActionBatch) and tool_calls.parse_error is not None
        if tool_calls == [] and not parse_failed:
            # Keep the empty turn replayable without advancing simulation time.
            boundary = {"turn_id": turn_id, "apply_after_turn": False}
            self.executor.submit_boundary(boundary)
            self.records.append({"kind": "turn_boundary", "boundary": boundary})
            self.world._terminate("agent_stopped")
        for tool_call in tool_calls:
            self.call_index += 1
            call, result = self.executor.execute_tool(tool_call, call_id=f"call_{self.call_index}", turn_id=turn_id)
            self.records.append({"kind": "tool_exchange", "call": call.to_dict(), "result": result.to_dict()})
            public_result = {"status": result.status, "code": result.code, "data": deepcopy(result.data)}
            if result.error is not None:
                public_result["error"] = deepcopy(result.error)
            self.tool_results.append(public_result)
            if self.terminated:
                break
        if not self.terminated:
            boundary = {"turn_id": turn_id, "apply_after_turn": True}
            self.executor.submit_boundary(boundary)
            self.records.append({"kind": "turn_boundary", "boundary": boundary})
        if not self.terminated and self.turn_index == self.max_turns:
            self.world.terminate_max_turns(turn_id=turn_id, turn_index=self.turn_index, max_turns=self.max_turns)
        if self.terminated:
            self.records.append({"kind": "termination", "termination": self.world.termination,
                                 "result": termination_result(self.world.termination["reason"])})
        else:
            self.turn_index += 1
