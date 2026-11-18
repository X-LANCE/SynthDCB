"""Independent scripted agent with no model or prompt dependencies."""
from copy import deepcopy

from ..interfaces import TaskContext, Observation, ToolInvocation


class ScriptedAgent:
    def __init__(self, turns: list[list[ToolInvocation]]):
        self.turns = deepcopy(turns)

    @classmethod
    def from_commands(cls, turns):
        """Adapt stored runtime reference plans to the public builtin-tool interface."""
        return cls([[{
            "name": f"{command['target']}_{command['function']}" if command["target"] in {"session", "memory"} else "device_execute_action",
            "arguments": deepcopy(command["parameters"] if command["target"] in {"session", "memory"} else command),
        } for command in turn] for turn in turns])

    def reset(self, context: TaskContext) -> None:
        self.position = 0

    def act(self, observation: Observation) -> list[ToolInvocation]:
        if self.position == len(self.turns):
            return []
        calls = deepcopy(self.turns[self.position])
        self.position += 1
        return calls
