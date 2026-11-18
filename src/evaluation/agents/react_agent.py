"""Text ReAct agent; owns its prompts, conversation, and model calls."""
from copy import deepcopy
import json
import re

from ..interfaces import TaskContext, Observation, ToolInvocation, ActionBatch, AgentProtocolError
from ..model_io import ModelIO

SYSTEM_PROMPT = """You are a device-control assistant in SynthDCB. You need to explore the world and complete the user's task using the supplied tools, public task information, and observed tool call results.

## ReAct format
You will work under the ReAct framework. The response of each turn must be wrapped in <answer> tags and contain exactly one Thought section and one Action section, following the structure below:
<answer>
Thought:
<Analyze the task based on the interaction history and the latest observation, and determine which tools to call in this turn.>
Action:
[{{"name": "<builtin tool name 1>", "arguments": {{"<argument name 1>": "<argument value 1>", "<argument name 2>": "<argument value 2>", ...}}}}, ...]
</answer>

## Task instructions
- Action must be one valid JSON array of calls to the listed builtin tools, preserving their argument schemas and JSON types. Request execution through this array only, without native tool-call syntax.
- Calls execute in array order after your response ends. Tool call results will be provided as observations in the next turn.
- Wait for those actual observations before choosing dependent actions. Never write, simulate, or assume an Observation, a tool return value, a later conversation turn, or successful execution. Never invent space/device IDs, function names, query answers, or state changes to continue the task.
- Invoke discovered device functions through `device_execute_action`. They are not additional builtin tools. Follow each tool's documented preconditions and argument formats.
- One task might contain several atom tasks.
    - For tasks related to control, you can take actions one by one or simultaneously.
    - For tasks related to queries, you should answer them in order through `session_submit_answer`, with one tool call per query.
    - For infeasible tasks, you should submit a report for each affected atom task through `session_submit_report`, with one tool call per atom task. Continue independent executable atom tasks.
- Use builtin tools with the prefix `memory_` for tasks related to memory.
- Use the observation's simulation time and `session_sleep_time` for timed actions. Device settings change through controls, while space properties may evolve gradually.
- Use `session_finish` when you want to end the interaction. A response with an empty action list will also finish the interaction immediately. However, the simulator will continue evolving until the fixed duration has elapsed or the world's state becomes stable.
- Include exactly one Thought section and one Action section within the same and only <answer> block, with no Markdown fences, extra sections, or text after </answer>.

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

## Available tools
{tool_list}
"""

USER_PROMPT = """The task information is provided below:

Domain: {domain}
User: {current_user}
Instruction: {instruction}

Current turn: {turn_index}
Current time: {simulation_time}
"""

USER_PROMPT_RUNTIME = """## Observation:
### Parser output:
{parser_output}
### Tool output:
{tool_results}

Current turn: {turn_index}
Current time: {simulation_time}
"""

PARSER_PASS = "Pass"
EMPTY_TOOL_OUTPUT = "No tool results."
PARSER_FEEDBACK_MESSAGES = {
    "extra_answer_blocks": "Multiple <answer> blocks were detected. Only the first block is considered for parsing. {count} additional block(s) were discarded; their actions were not executed.",
    "outside_text": "Text outside the accepted <answer> block was discarded; it did not request execution.",
    "missing_close": "The closing </answer> tag was missing. The parsed Thought and Action were accepted.",
    "missing_wrapper": "The <answer> wrapper was missing. The parsed Thought and Action were accepted.",
    "parse_error": "The previous response could not be parsed: {error}. No actions were executed; this was not an explicit empty Action list.",
}


def parse_actions(content):
    thought, calls, _ = _parse_response(content)
    return thought, calls


def _parse_response(content, *, issues=None):
    if not isinstance(content, str):
        raise AgentProtocolError("ReAct response contains no assistant text")
    content = content.strip()
    if issues is None:
        issues = []
    extra_blocks = content.count("<answer>") - 1
    if extra_blocks > 0:
        issues.append({"code": "extra_answer_blocks", "count": extra_blocks})
    prefix, opening, body = content.partition("<answer>")
    if opening:
        content, closing, suffix = body.partition("</answer>")
        if prefix.strip():
            issues.append({"code": "outside_text"})
        if not closing:
            issues.append({"code": "missing_close"})
        elif suffix.strip() and not suffix.count("<answer>"):
            issues.append({"code": "outside_text"})
    else:
        issues.append({"code": "missing_wrapper"})
    thought_text, separator, action_text = content.partition("Action:")
    
    match = re.fullmatch(r"\s*Thought:\s*(.+?)\s*", thought_text, flags=re.DOTALL)
    if (not separator or match is None or not match[1].strip()
            or re.fullmatch(r"\s*(.+?)\s*", action_text) is None):
        raise AgentProtocolError("ReAct requires Thought followed by Action JSON")
    try:
        calls = json.loads(action_text)
    except json.JSONDecodeError as error:
        raise AgentProtocolError(f"invalid ReAct Action JSON: {error}") from error
    
    if not isinstance(calls, list):
        raise AgentProtocolError("ReAct Action must be a tool call list")
    return match[1].strip(), calls, issues




class ReActAgent:
    agent_strategy = "react"
    
    def __init__(self, **model_options):
        self.io = ModelIO(**model_options)
    
    @property
    def audit_records(self):
        return self.io.audit_records
    
    def reset(self, context: TaskContext) -> None:
        self.io.audit_records.clear()
        self.pending = []
        self.pending_feedback = []
        self.tools = deepcopy(context.tools)
        tool_list = json.dumps(self.tools, ensure_ascii=False)
        self.task_fields = {
            "instruction": context.instruction,
            "domain": context.domain,
            "current_user": json.dumps(context.current_user, ensure_ascii=False),
        }
        self.history = [{
            "role": "system",
            "content": SYSTEM_PROMPT.format(tool_list=tool_list)
        }]
    
    def act(self, observation: Observation) -> list[ToolInvocation]:
        tool_results = [deepcopy(result) for _, result in zip(self.pending, observation.tool_results, strict=True)]
        parser_output = "\n".join(
            PARSER_FEEDBACK_MESSAGES[item["code"]].format(**item) for item in self.pending_feedback
        ) or PARSER_PASS
        prompt = USER_PROMPT if len(self.history) == 1 else USER_PROMPT_RUNTIME
        self.history.append({
            "role": "user",
            "content": prompt.format(
                **self.task_fields,
                parser_output=parser_output,
                tool_results=json.dumps(tool_results, ensure_ascii=False) if tool_results else EMPTY_TOOL_OUTPUT,
                turn_index=observation.turn_index,
                simulation_time=json.dumps(observation.simulation_time, ensure_ascii=False),
            )
        })
        request = {"instructions": self.history[0]["content"], "input": deepcopy(self.history[1:])} if self.io.responses_api else {"messages": deepcopy(self.history)}
        response, audit = self.io.call(request, turn_index=observation.turn_index, strategy=self.agent_strategy, tool_count=len(self.tools))
        content = response["text"]
        audit["assistant_text"] = content
        self.history.append({"role": "assistant", "content": content or ""})
        issues = []
        try:
            thought, calls, issues = _parse_response(content, issues=issues)
            audit["thought"] = thought
            audit["format_issues"] = deepcopy(issues)
            self.pending_feedback = issues
            calls = ActionBatch(calls)
        except AgentProtocolError as error:
            audit["format_issues"] = deepcopy(issues)
            audit["protocol_error"] = str(error)
            self.pending_feedback = [item for item in issues if item["code"] == "extra_answer_blocks"]
            self.pending_feedback.append({"code": "parse_error", "error": str(error)})
            calls = ActionBatch(parse_error=str(error))
        self.pending = deepcopy(list(calls))
        audit["tool_calls"] = deepcopy(list(calls))
        return calls
