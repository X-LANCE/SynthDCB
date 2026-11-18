"""Public agent inputs and builtin tool invocations; no runtime or model dependencies."""
from dataclasses import dataclass
from typing import Any, Protocol, TypedDict


class ToolInvocation(TypedDict):
    name: str
    arguments: Any  # Untrusted model arguments are validated by the environment.


class ActionBatch(list[ToolInvocation]):
    """Ordered calls with parse status, distinguishing failed output from an explicit []."""

    def __init__(self, calls=(), *, parse_error: str | None = None):
        super().__init__(calls)
        self.parse_error = parse_error


@dataclass(frozen=True)
class TaskContext:
    instruction: str
    domain: str
    current_user: dict[str, Any] | None
    tools: list[dict[str, Any]]


@dataclass(frozen=True)
class Observation:
    tool_results: list[dict[str, Any]]
    turn_index: int
    simulation_time: dict[str, Any]


class BaseAgent(Protocol):
    def reset(self, context: TaskContext) -> None:
        """Start an independent task."""

    def act(self, observation: Observation) -> list[ToolInvocation]:
        """Return ordered calls; a valid empty batch ends interaction, a parse failure does not."""


class AgentError(RuntimeError):
    """Base error emitted by an evaluation agent."""


class AgentTransportError(AgentError):
    """The compatible endpoint failed before returning a usable response."""


class AgentProtocolError(AgentError):
    """A successful response did not contain valid tool calls."""


class AgentModelMismatchError(AgentError):
    """The endpoint returned a different model than the requested model."""


