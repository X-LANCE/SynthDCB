"""Embedding client and per-text cache."""

from __future__ import annotations

import hashlib
import pickle
from pathlib import Path
import threading
from typing import Callable

import requests

from src.utils import format_json
from src.utils.llm.config import format_authorization_header

from .config import DEFAULT_EMBEDDING_DIM, get_embedding_config


class EmbeddingClient:
    def __init__(
        self,
        cache_dir: str | Path,
        *,
        config_provider: Callable[[], dict] = get_embedding_config,
    ):
        """Initialize the embedding client and its cache directory."""
        self.cache_dir = Path(cache_dir)
        self.config_provider = config_provider
        self.embedding_dim = DEFAULT_EMBEDDING_DIM
        self._cache_lock = threading.Lock()

    def get(self, text: str) -> list[float]:
        """Return the cached or remote embedding for one text."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        config = self.config_provider()
        identity = format_json(
            {
                "base_url": config.get("base_url"),
                "model": config.get("model"),
                "text": text,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        cache_path = self.cache_dir / f"embedding-{digest}.pkl"
        if cache_path.exists():
            with self._cache_lock:
                with cache_path.open("rb") as handle:
                    cached = pickle.load(handle)
            if (
                not isinstance(cached, list)
                or not cached
                or not all(type(value) in (int, float) for value in cached)
            ):
                raise ValueError(f"Invalid embedding cache: {cache_path}")
            return cached

        response = requests.post(
            config["base_url"],
            headers={
                "Content-Type": "application/json",
                "Authorization": format_authorization_header(
                    config.get("api_key")
                ),
            },
            json={"model": config["model"], "input": text},
            timeout=config["timeout"],
        )
        response.raise_for_status()
        data = response.json()["data"]
        if not data:
            raise ValueError("Embedding API returned no data")
        embedding = data[0]["embedding"]
        if (
            not isinstance(embedding, list)
            or not embedding
            or not all(type(value) in (int, float) for value in embedding)
        ):
            raise ValueError("Embedding API returned an invalid vector")
        self.embedding_dim = len(embedding)
        with self._cache_lock:
            with cache_path.open("wb") as handle:
                pickle.dump(embedding, handle)
        return embedding
