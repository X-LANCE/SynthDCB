"""OpenAI-compatible service and model settings for generation and evaluation."""

import os
from pathlib import Path

from dotenv import load_dotenv

from src.utils.utils import print_run_config


load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)

ACTIVE_LLM_SERVER = "openai"
LLM_SERVER_CONFIGS = {
    ACTIVE_LLM_SERVER: {
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "api_key": os.getenv("OPENAI_API_KEY"),
        "api_protocol": os.getenv("DCB_API_PROTOCOL", "chat"),
        "timeout": 1200,
        "max_retry": 3,
        "retry_delay_seconds": 5,
        "max_response_tokens": 32768,
        "temperature": 0.0,
        "top_p": 1.0,
    },
}

_model = os.getenv("OPENAI_MODEL", "gpt-6-luna")
_judge_model = os.getenv("DCB_JUDGE_MODEL", _model)
LLM_CONFIGS = {
    stage: {"server": ACTIVE_LLM_SERVER, "model": _model}
    for stage in ("default", "generate", "code", "tool", "eval")
}
LLM_CONFIGS.update({
    stage: {"server": ACTIVE_LLM_SERVER, "model": _judge_model}
    for stage in ("judge", "memory_judge", "report_judge")
})


def format_authorization_header(api_key: str | None) -> str:
    """Format an optional API key as an HTTP authorization value."""
    if not api_key:
        return ""
    if api_key.lower().startswith("bearer "):
        return api_key
    return f"Bearer {api_key}"


def get_llm_config(scenario: str = "default") -> dict:
    """Resolve a stage and normalize the endpoint used by its API protocol."""
    stage = LLM_CONFIGS[scenario]
    config = {**LLM_SERVER_CONFIGS[stage["server"]], **stage}
    protocol = config["api_protocol"]
    if protocol not in {"responses", "chat"}:
        raise ValueError(f"unsupported api_protocol: {protocol!r}")
    base_url = str(config["base_url"]).rstrip("/")
    for suffix in ("/chat/completions", "/responses"):
        if base_url.endswith(suffix):
            base_url = base_url[:-len(suffix)]
            break
    endpoint = "responses" if protocol == "responses" else "chat/completions"
    config["base_url"] = f"{base_url}/{endpoint}"
    return config


def print_llm_config(scenario: str) -> None:
    """Print the service settings without including credentials."""
    config = get_llm_config(scenario)
    print_run_config("LLM", (
        ("Scenario", scenario),
        ("Model", config["model"]),
        ("Base URL", config["base_url"]),
        ("API key", "configured" if config.get("api_key") else "missing"),
        ("Timeout", config["timeout"]),
        ("Max response tokens", config["max_response_tokens"]),
    ))
