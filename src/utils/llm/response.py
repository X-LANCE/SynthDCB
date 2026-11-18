"""Parsers for OpenAI-compatible text responses."""

from __future__ import annotations

import json
import re
from src.utils import parse_json


def parse_response(response_json: dict) -> dict:
    """Parse one OpenAI-compatible response into reasoning and answer text."""
    if "choices" in response_json:
        response_content = response_json["choices"][0]["message"]["content"]
    else:
        response_content = response_json.get("output_text") or "".join(
            content["text"]
            for output in response_json.get("output", [])
            for content in output.get("content", [])
            if content.get("type") == "output_text"
        )
        if not response_content:
            raise KeyError("response contains no output text")
    think_pattern = r"<think>\s*([\s\S]*?)\s*</think>"
    answer_pattern = r"<answer>\s*([\s\S]*?)\s*$"
    # Tags quoted inside JSON/code are content, not response wrappers.
    structured = response_content.lstrip().startswith(("{", "[", "```"))
    match_think = None if structured else re.search(think_pattern, response_content, re.DOTALL)
    match_answer = None if structured else re.search(answer_pattern, response_content, re.DOTALL)
    think = match_think.group(1).strip() if match_think else ""
    answer = (
        match_answer.group(1).strip().removesuffix("</answer>").strip()
        if match_answer
        else response_content
    )
    usage = dict(response_json.get("usage") or {})
    for legacy, modern in (
        ("prompt_tokens", "input_tokens"),
        ("completion_tokens", "output_tokens"),
        ("prompt_tokens_details", "input_tokens_details"),
        ("completion_tokens_details", "output_tokens_details"),
    ):
        value = usage.get(legacy) or usage.get(modern)
        if value is not None:
            usage[legacy] = value
            usage[modern] = value
    return {
        "think": think,
        "answer": answer,
        "usage": usage,
        "model": response_json.get("model", ""),
    }


def extract_json_from_answer(answer: str) -> tuple[str, dict]:
    """Extract and decode a JSON answer block."""
    if not isinstance(answer, str) or not answer:
        return "[NO_JSON_FOUND]", {}
    match = re.search(r"```json\s*([\s\S]*?)\s*```", answer)
    json_text = match.group(1).strip() if match else answer.strip()
    try:
        return "[PASS]", parse_json(json_text)
    except json.JSONDecodeError as error:
        return f"[JSON_DECODE_ERROR] {error}", {}


def extract_python_code_from_answer(response: str) -> tuple[str, str]:
    """Extract a fenced Python answer and return an explicit status."""
    match = re.search(r"```python\s*([\s\S]*?)\s*```", response)
    if match:
        return "[PASS]", match.group(1).strip()
    return "[NO_PYTHON_CODE_FOUND]", ""


def extract_answer_from_string(response: str) -> str:
    """Extract the trailing answer section from a model response."""
    match = re.search(r"<answer>\s*([\s\S]*?)\s*$", response, re.DOTALL)
    return (
        match.group(1).replace("</answer>", "").strip()
        if match
        else ""
    )


def extract_think_from_string(response: str) -> str:
    """Extract the reasoning section from a model response."""
    match = re.search(r"<think>\s*([\s\S]*?)\s*</think>", response, re.DOTALL)
    return match.group(1).strip() if match else ""


def extract_python_code_from_string(response: str) -> str:
    """Extract fenced Python source or return an empty string."""
    match = re.search(r"```python\s*([\s\S]*?)\s*```", response)
    return match.group(1).strip() if match else ""


def response_to_dict(value):
    """Serialize SDK responses and nested test objects without dropping fields."""
    from copy import deepcopy
    from types import SimpleNamespace
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump(exclude_none=True)
    if isinstance(value, SimpleNamespace):
        return {key: response_to_dict(item) if isinstance(item, (dict, list, SimpleNamespace)) or hasattr(item, "model_dump") else item
                for key, item in vars(value).items()}
    if isinstance(value, dict):
        return {key: response_to_dict(item) if isinstance(item, (dict, list, SimpleNamespace)) or hasattr(item, "model_dump") else item
                for key, item in value.items()}
    if isinstance(value, list):
        return [response_to_dict(item) if isinstance(item, (dict, list, SimpleNamespace)) or hasattr(item, "model_dump") else deepcopy(item) for item in value]
    return deepcopy(value)


def parse_agent_response(response: dict, *, responses_api: bool) -> dict:
    """Extract text, reasoning and calls; leave action validation to the agent."""
    from copy import deepcopy
    calls = []
    if responses_api:
        items = response.get("output") or []
        text = "".join(part.get("text", "") or ""
                       for item in items if item.get("type") == "message" and item.get("role", "assistant") == "assistant"
                       for part in item.get("content", []) if part.get("type") == "output_text")
        reasoning = [deepcopy(item) for item in items if item.get("type") == "reasoning"]
        for item in items:
            if item.get("type") == "function_call":
                calls.append({"name": item.get("name"), "arguments": item.get("arguments"), "id": item.get("call_id")})
        history = deepcopy(items)
        finish = response.get("status", "")
    else:
        items = response.get("choices") or []
        message = items[0].get("message") if items else None
        text = message.get("content") if message else None
        reasoning = {key: deepcopy(message[key]) for key in ("reasoning_content", "reasoning", "reasoning_details")
                     if message and message.get(key) is not None}
        history = []
        if message is not None:
            assistant = {"role": "assistant", "content": text}
            if message.get("tool_calls"):
                assistant["tool_calls"] = deepcopy(message["tool_calls"])
            assistant.update(reasoning)
            history.append(assistant)
            for call in message.get("tool_calls") or []:
                function = call.get("function", {})
                calls.append({"name": function.get("name"), "arguments": function.get("arguments"), "id": call.get("id")})
        finish = items[0].get("finish_reason", "") if items else ""
    return {"text": text, "think": extract_think_from_string(text or ""),
            "reasoning": reasoning, "tool_calls": calls, "history": history,
            "has_output": bool(items), "model": response.get("model") or "",
            "usage": deepcopy(response.get("usage") or {}), "finish_reason": finish}
