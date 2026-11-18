"""Send fully constructed agent contexts; no conversation or environment logic."""
from copy import deepcopy
import time
from dataclasses import dataclass
from typing import Any

from src.utils import print_status
from .config import get_llm_config
from .response import response_to_dict, parse_agent_response


def is_context_length_error(error) -> bool:
    """Recognize explicit token/context limit errors, including wrapped vLLM errors."""
    message = str(error).lower()
    return any(marker in message for marker in (
        "context_length_exceeded", "maximum context length",
        "maximum input length", "model's context length is only",
    ))


def create_openai_client(model_scenario: str = "eval") -> Any:
    """Create one SDK client from the existing repository LLM config."""
    from openai import OpenAI

    config = get_llm_config(model_scenario)
    api_key = config.get("api_key")
    if not api_key:
        raise ValueError(f"Set OPENAI_API_KEY for model calls ({model_scenario})")
    base_url = str(config["base_url"])
    for suffix in ("/chat/completions", "/responses"):
        if base_url.endswith(suffix):
            base_url = base_url[: -len(suffix)]
            break
    return OpenAI(
        api_key=str(api_key).removeprefix("Bearer ").removeprefix("bearer "),
        base_url=base_url,
        timeout=float(config["timeout"]),
        max_retries=0,
    )


@dataclass
class CallResult:
    response: dict | None
    latency_seconds: float
    attempts: int
    errors: list[str]
    wire: list[dict]


class ContextCaller:
    """API transport, model parameters, retry policy, and wire audit."""

    def __init__(self, *, client, config, model, max_transport_attempts=3, record_requests=False):
        if max_transport_attempts < 1:
            raise ValueError("max_transport_attempts must be positive")
        self.client = client
        self.config = config
        self.model = model
        self.responses_api = config["api_protocol"] == "responses"
        self.max_transport_attempts = max_transport_attempts
        self.record_requests = record_requests
        self.retry_delay_seconds = float(config.get("retry_delay_seconds", 0))
        if self.retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds must be non-negative")

    def call(self, context: dict) -> CallResult:
        request = {"model": self.model, **deepcopy(context)}
        service_tier = self.config.get("service_tier")
        if service_tier:
            request["service_tier"] = service_tier
        if self.model != "kimi-k3":
            request.update(temperature=self.config.get("temperature", 0.0),
                           top_p=self.config.get("top_p", 1.0))
        max_tokens = self.config.get("max_response_tokens")
        if max_tokens is not None and self.model != "kimi-k3":
            request[
                "max_output_tokens" if self.responses_api else "max_tokens"
            ] = int(max_tokens)

        wire = []
        transport_errors: list[str] = []
        started = time.monotonic()
        response = None
        transport_attempt_count = 0
        for transport_attempt_count in range(
            1, self.max_transport_attempts + 1
        ):
            attempt = {"request": deepcopy(request)} if self.record_requests else None
            if attempt is not None:
                wire.append(attempt)
            try:
                if self.responses_api:
                    response = self.client.responses.create(**request)
                else:
                    response = self.client.chat.completions.create(**request)
                if attempt is not None:
                    attempt["response"] = response_to_dict(response)
                break
            except KeyboardInterrupt:
                raise
            except Exception as error:
                if attempt is not None:
                    attempt["error_type"] = type(error).__name__
                transport_errors.append(str(error))
                print_status(
                    f"LLM API call failed (model {self.model}, "
                    f"attempt {transport_attempt_count}/{self.max_transport_attempts}): {error}",
                    "warning",
                )
                status = getattr(error, "status_code", None)
                if is_context_length_error(error) or (
                    isinstance(status, int) and 400 <= status < 500 and status not in {408, 409, 429}
                ):
                    break  # Retrying an unchanged invalid request cannot fix it.
                if transport_attempt_count < self.max_transport_attempts:
                    time.sleep(self.retry_delay_seconds)
        latency = time.monotonic() - started
        return CallResult(
            parse_agent_response(response_to_dict(response), responses_api=self.responses_api)
            if response is not None else None,
            latency, transport_attempt_count, transport_errors, wire,
        )
