"""OpenAI-compatible LLM configuration and calls."""

from .config import (
    ACTIVE_LLM_SERVER,
    LLM_CONFIGS,
    LLM_SERVER_CONFIGS,
    format_authorization_header,
    get_llm_config,
    print_llm_config,
)
from .context_caller import ContextCaller, CallResult, create_openai_client
from .llm_caller import (
    GENERAL_SYSTEM_PROMPT,
    call_llm_api,
    compose_system_prompt,
)
from .response import (
    extract_answer_from_string,
    extract_json_from_answer,
    extract_python_code_from_answer,
    extract_python_code_from_string,
    extract_think_from_string,
    parse_response,
    parse_agent_response,
)

__all__ = [
    "ContextCaller", "CallResult", "create_openai_client", "parse_agent_response",
    "ACTIVE_LLM_SERVER",
    "GENERAL_SYSTEM_PROMPT",
    "LLM_CONFIGS",
    "LLM_SERVER_CONFIGS",
    "call_llm_api",
    "compose_system_prompt",
    "extract_answer_from_string",
    "extract_json_from_answer",
    "extract_python_code_from_answer",
    "extract_python_code_from_string",
    "extract_think_from_string",
    "format_authorization_header",
    "get_llm_config",
    "parse_response",
    "print_llm_config",
]
