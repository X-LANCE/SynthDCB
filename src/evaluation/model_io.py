"""Shared model transport and audit, without agent prompts."""
from copy import deepcopy

from src.utils.llm import get_llm_config
from src.utils.llm.context_caller import ContextCaller
from .interfaces import AgentTransportError, AgentModelMismatchError


class ModelIO:
    def __init__(self, *, client, model=None, model_scenario="eval", max_transport_attempts=3,
                 require_model_identity=False, record_requests=False):
        self.config = get_llm_config(model_scenario)
        self.model = model or self.config["model"]
        self.caller = ContextCaller(client=client, config=self.config, model=self.model,
                                    max_transport_attempts=max_transport_attempts,
                                    record_requests=record_requests)
        self.require_model_identity = require_model_identity
        self.audit_records = []

    @property
    def responses_api(self):
        return self.caller.responses_api

    def call(self, request, *, turn_index, strategy, tool_count):
        result = self.caller.call(request)
        response = result.response
        audit = {
            "turn_index": turn_index,
            "requested_model": self.model,
            "response_model": response["model"] if response is not None else "",
            "latency_seconds": result.latency_seconds,
            "usage": response["usage"] if response is not None else {},
            "finish_reason": response["finish_reason"] if response is not None else "transport_error",
            "tool_count": tool_count,
            "transport_attempt_count": result.attempts,
            "transport_errors": result.errors,
            "tool_calls": [],
            "agent_strategy": strategy,
        }
        if self.caller.record_requests:
            audit["wire"] = result.wire
        self.audit_records.append(audit)
        if response is None:
            raise AgentTransportError(result.errors[-1])
        audit.update(reasoning=deepcopy(response["reasoning"]), think=response["think"])
        if self.require_model_identity and response["model"] != self.model:
            raise AgentModelMismatchError(f"requested {self.model!r}, received {response['model']!r}")
        return response, audit
