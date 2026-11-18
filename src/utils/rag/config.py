"""Retrieval and optional embedding configuration."""

from __future__ import annotations

import os


EMBEDDING_BASE_URL = os.getenv(
    "DCB_EMBEDDING_BASE_URL",
    os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/embeddings",
)
EMBEDDING_MODEL = os.getenv(
    "DCB_EMBEDDING_MODEL",
    "text-embedding-3-small",
)
EMBEDDING_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_TIMEOUT = 60
EMBEDDING_MAX_RETRY = 3
DEFAULT_CACHE_DIR = "knowledge/vectordb"
DEFAULT_EMBEDDING_DIM = 1536
RAG_INDEX_VERSION = "dcb-rag-v3"


def _env_flag(name: str, default: bool = False) -> bool:
    """Read a boolean feature flag from the environment."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# Retrieval is useful without a remote embedding service.  Keep semantic
# embeddings opt-in so an empty local cache cannot unexpectedly fan out into
# third-party API calls during generation or deterministic validation.
RAG_USE_EMBEDDINGS = _env_flag("DCB_RAG_EMBEDDINGS", False)


def get_embedding_config() -> dict:
    """Return the embedding config."""
    return {
        "base_url": EMBEDDING_BASE_URL,
        "model": EMBEDDING_MODEL,
        "api_key": EMBEDDING_API_KEY,
        "timeout": EMBEDDING_TIMEOUT,
        "max_retry": EMBEDDING_MAX_RETRY,
    }


def get_rag_config(domain: str) -> dict:
    """Return the non-secret retrieval configuration for evidence snapshots."""
    from src.utils.config import PROJECT_ROOT
    from .sources import source_config_path

    source_path = source_config_path(PROJECT_ROOT, domain)
    if source_path.is_relative_to(PROJECT_ROOT):
        source_path = source_path.relative_to(PROJECT_ROOT)

    return {
        "index_version": RAG_INDEX_VERSION,
        "use_embeddings": RAG_USE_EMBEDDINGS,
        "embedding_model": EMBEDDING_MODEL if RAG_USE_EMBEDDINGS else None,
        "cache_dir": DEFAULT_CACHE_DIR,
        "source_config": source_path.as_posix(),
    }
