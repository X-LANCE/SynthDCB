"""Select the built-in benchmark agent outside the execution loop."""
from .agents import ReActAgent, ToolCallAgent
from .agents.react_agent import SYSTEM_PROMPT as REACT_PROMPT
from .agents.toolcall_agent import SYSTEM_PROMPT as TOOLCALL_PROMPT

AGENTS = {"react": ReActAgent, "toolcall": ToolCallAgent}


def create_agent(*, agent_strategy="react", **options):
    try:
        implementation = AGENTS[agent_strategy]
    except KeyError:
        raise ValueError(f"unknown agent_strategy: {agent_strategy!r}") from None
    if agent_strategy == "react":
        # ReAct always maps unparseable output to an empty action list.
        options.pop("recover_tool_call_errors", None)
    return implementation(**options)


def agent_system_prompt(strategy):
    return {"react": REACT_PROMPT, "toolcall": TOOLCALL_PROMPT}[strategy]
