"""OpenAI-compatible completion transport, retry, and usage handling."""

from __future__ import annotations

from .prompt import (
    GENERAL_SYSTEM_PROMPT,
)

import time
from typing import Tuple

import requests

from src.utils.utils import print_status, safe_json

from . import config
from .response import parse_response




def _format_error_response(response: requests.Response) -> str:
    """Decode JSON escapes for logs while preserving non-JSON bodies."""
    try:
        return safe_json(response.json())
    except requests.exceptions.JSONDecodeError:
        return response.text


def compose_system_prompt(system_prompt: str) -> str:
    """Prepend the shared DCB project context to a stage prompt."""
    stage_prompt = system_prompt.strip()
    return (
        f"{GENERAL_SYSTEM_PROMPT}\n\n{stage_prompt}"
        if stage_prompt
        else GENERAL_SYSTEM_PROMPT
    )


def call_llm_api(
    system_prompt: str,
    user_prompt: str,
    model_scenario: str = "default",
    *,
    model: str | None = None,
    max_transport_attempts: int | None = None,
    cache_prefix: str = "",
) -> Tuple[str, dict]:
    """Call one configured OpenAI-compatible endpoint with bounded retries."""
    model_config = config.get_llm_config(model_scenario)
    if not model_config.get("api_key"):
        raise ValueError(f"Set OPENAI_API_KEY for model calls ({model_scenario})")
    requested_model = model or model_config["model"]
    max_tokens = model_config["max_response_tokens"]
    base_url = model_config["base_url"]
    responses_api = "responses" in base_url
    user_text = user_prompt.strip()
    prefix = cache_prefix.strip()
    if prefix and not user_text.startswith(prefix):
        raise ValueError("cache_prefix must be an exact prefix of user_prompt")
    request_json = {
        "model": requested_model,
        "temperature": model_config["temperature"],
        "top_p": model_config["top_p"],
    }
    service_tier = model_config.get("service_tier")
    if service_tier:
        request_json["service_tier"] = service_tier
    if responses_api:
        request_json.update(
            instructions=compose_system_prompt(system_prompt),
            input=user_text,
        )
        if prefix:
            fixed_block = {"type": "input_text", "text": prefix}
            if requested_model == "gpt-5.6" or requested_model.startswith("gpt-5.6-"):
                fixed_block["prompt_cache_breakpoint"] = {"mode": "explicit"}
                request_json["prompt_cache_options"] = {"mode": "explicit"}
            content = [fixed_block]
            remainder = user_text[len(prefix):]
            if remainder:
                content.append({"type": "input_text", "text": remainder})
            request_json["input"] = [{"role": "user", "content": content}]
    else:
        request_json["messages"] = [
            {
                "role": "system",
                "content": compose_system_prompt(system_prompt),
            },
            {"role": "user", "content": user_text},
        ]
    if max_tokens is not None and int(max_tokens) > 0:
        request_json[
            "max_output_tokens" if responses_api else "max_tokens"
        ] = int(max_tokens)
    if not responses_api:
        for key, caster in (
            ("top_k", int),
            ("min_p", float),
            ("presence_penalty", float),
        ):
            value = model_config.get(key)
            if value is not None:
                request_json[key] = caster(value)

    headers = {
        "Content-Type": "application/json",
        "Authorization": config.format_authorization_header(
            model_config.get("api_key")
        ),
    }
    max_retry = (
        int(max_transport_attempts)
        if max_transport_attempts is not None
        else int(model_config["max_retry"])
    )
    if max_retry < 1:
        raise ValueError("max_transport_attempts must be positive")
    retry_delay_seconds = float(model_config.get("retry_delay_seconds", 0))
    if retry_delay_seconds < 0:
        raise ValueError("retry_delay_seconds must be non-negative")
    timeout = model_config["timeout"]
    errors: list[Exception] = []
    response = None
    for attempt in range(1, max_retry + 1):
        try:
            response = requests.post(
                base_url,
                json=request_json,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            parsed = parse_response(response.json())
            parsed["requested_model"] = requested_model
            parsed["model_scenario"] = model_scenario
            return "[PASS]", parsed
        except (
            IndexError,
            KeyError,
            TypeError,
            ValueError,
            requests.RequestException,
        ) as error:
            errors.append(error)
            if response is not None and response.text:
                print_status(
                    f"LLM API error response: {_format_error_response(response)}",
                    "warning",
                )
            print_status(
                f"LLM call failed (attempt {attempt}/{max_retry}): {error}",
                "warning",
            )
            if attempt < max_retry:
                time.sleep(retry_delay_seconds)

    last_error = errors[-1]
    print_status(
        f"LLM call failed after {max_retry} attempts: {last_error}",
        "error",
    )
    error_response: dict = {}
    if response is not None:
        try:
            error_response = response.json()
        except requests.exceptions.JSONDecodeError:
            error_response = {"text": response.text}
    return "[MAX_TRY_REACHED]", {
        "error_response": error_response,
        "error": str(last_error),
        "requested_model": requested_model,
        "model_scenario": model_scenario,
    }
