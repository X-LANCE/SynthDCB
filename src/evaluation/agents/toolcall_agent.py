"""Native toolcall agent; owns its prompts, conversation, and model calls."""
from copy import deepcopy
import json

from ..interfaces import TaskContext, Observation, ToolInvocation, AgentProtocolError
from ..model_io import ModelIO

SYSTEM_PROMPT = """You are a device-control assistant in SynthDCB. You need to explore the world and complete the user's task using the supplied tools, public task information, and observed tool call results.

## Tool calling format
Use the supplied builtin tools through native tool calls. Each response requests one interaction turn and may contain multiple tool calls.

## Task instructions
- Preserve the supplied tools' argument schemas and JSON types. Request execution through native tool calls.
- Calls execute in array order after your response ends. Tool call results will be provided as observations in the next turn.
- Wait for those actual observations before choosing dependent actions. Never write, simulate, or assume an Observation, a tool return value, a later conversation turn, or successful execution. Never invent space/device IDs, function names, query answers, or state changes to continue the task.
- Invoke discovered device functions through `device_execute_action`. They are not additional builtin tools. Follow each tool's documented preconditions and argument formats.
- One task might contain several atom tasks.
    - For tasks related to control, you can take actions one by one or simultaneously.
    - For tasks related to queries, you should answer them in order through `session_submit_answer`, with one tool call per query.
    - For infeasible tasks, you should submit a report for each affected atom task through `session_submit_report`, with one tool call per atom task. Continue independent executable atom tasks.
- Use builtin tools with the prefix `memory_` for tasks related to memory.
- Use the observation's simulation time and `session_sleep_time` for timed actions. Device settings change through controls, while space properties may evolve gradually.
- Use `session_finish` when you want to end the interaction. A response with no tool calls will also finish the interaction immediately. However, the simulator will continue evolving until the fixed duration has elapsed or the world's state becomes stable.

Query tasks:
- Return raw typed property values, integer counts, or a space_id/device_id string. Preserve raw list-property order.
- Return target selections as arrays of exact device_id, space_id, and person IDs. Use [] for no matches.
- For ranking tasks, always include boundary ties. Therefore, the result may contain more targets than requested.
- Order ranking target IDs by the requested ranking first. For other queries or tied ranks, use ascending natural ID order (case-insensitive text, numeric digit runs).

Infeasible tasks:
- Submit one `session_submit_report` per infeasible or blocked atom task, with status, reason code and an explanation identifying the request and evidence.
- Explore the world thoroughly and identify the matching reason code listed below:
    - SPACE_TARGET_NOT_FOUND or DEVICE_TARGET_NOT_FOUND, a requested space or device is absent;
    - SPACE_PROPERTY_NOT_SUPPORTED or DEVICE_PROPERTY_NOT_SUPPORTED, a property or capability is unsupported, e.g., you cannot change the target humidity of a fan;
    - INVALID_VALUE, a value violates the declared domain, including the resulting value of increase/decrease requests. Do not round to a supported value;
    - UNREACHABLE_GOAL, an otherwise valid environmental goal cannot be reached under any condition, e.g., cooling a room to 15 degrees when the air conditioner only supports target temperatures between 20 and 30 degrees;
    - BLOCKED_BY_DEPENDENCY, an atom task is blocked by infeasible tasks it depends on. Do not guess the missing result.
"""

USER_PROMPT = """The task information is provided below:

Domain: {domain}
User: {current_user}
Instruction: {instruction}

Current turn: {turn_index}
Current time: {simulation_time}
"""

USER_PROMPT_RUNTIME = """Current turn: {turn_index}
Current time: {simulation_time}
"""


class ToolCallAgent:
    agent_strategy = "toolcall"

    def __init__(self, *, system_prompt=None, recover_tool_call_errors=False, **model_options):
        self.io = ModelIO(**model_options)
        self.system_prompt = SYSTEM_PROMPT if system_prompt is None else system_prompt
        self.recover_tool_call_errors = recover_tool_call_errors

    @property
    def audit_records(self):
        return self.io.audit_records

    def reset(self, context: TaskContext) -> None:
        self.io.audit_records.clear()
        self.pending = []
        tools = deepcopy(context.tools)
        self.tools = ([{"type": tool["type"], **tool["function"]} for tool in tools]
                      if self.io.responses_api else tools)
        self.task_fields = {
            "instruction": context.instruction,
            "domain": context.domain,
            "current_user": json.dumps(context.current_user, ensure_ascii=False),
        }
        self.history = []

    def act(self, observation: Observation) -> list[ToolInvocation]:
        for call, result in zip(self.pending, observation.tool_results, strict=True):
            text = json.dumps(result, ensure_ascii=False)
            if call["id"] is None:
                message = {"role": "user", "content": "Observation: " + text}
            elif self.io.responses_api:
                message = {"type": "function_call_output", "call_id": call["id"], "output": text}
            else:
                message = {"role": "tool", "tool_call_id": call["id"], "content": text}
            self.history.append(message)
        prompt = USER_PROMPT if not self.history else USER_PROMPT_RUNTIME
        self.history.append({
            "role": "user",
            "content": prompt.format(
                **self.task_fields,
                turn_index=observation.turn_index,
                simulation_time=json.dumps(observation.simulation_time, ensure_ascii=False),
            ),
        })
        request = {"tools": deepcopy(self.tools)}
        if self.io.model != "kimi-k3":
            request["tool_choice"] = "auto" if self.io.model == "deepseek-v4.1-flash" else "required"
        if self.io.responses_api:
            request.update(instructions=self.system_prompt, input=deepcopy(self.history))
        else:
            request["messages"] = [{"role": "system", "content": self.system_prompt}, *deepcopy(self.history)]
        response, audit = self.io.call(request, turn_index=observation.turn_index,
                                       strategy=self.agent_strategy, tool_count=len(self.tools))
        self.history.extend(deepcopy(response["history"]))
        self.pending = deepcopy(response["tool_calls"])
        audit["native_tool_count"] = len(self.pending)
        if not response["has_output"]:
            if not self.recover_tool_call_errors:
                raise AgentProtocolError("response contains no output")
            self.pending = [{"id": None, "name": "", "arguments": "missing model output"}]
        calls = []
        for call in self.pending:
            try:
                arguments = json.loads(call["arguments"])
            except (TypeError, json.JSONDecodeError):
                arguments = call["arguments"]  # Runtime returns a validation error for malformed arguments.
            calls.append({"name": call["name"], "arguments": arguments})
        audit["tool_calls"] = deepcopy(calls)
        return calls
