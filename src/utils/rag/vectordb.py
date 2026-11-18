"""Persistent retrieval entries and optional vectors."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Iterator

from .config import (
    DEFAULT_CACHE_DIR,
    DEFAULT_EMBEDDING_DIM,
    RAG_INDEX_VERSION,
)


class VectorDB:
    def __init__(self, cache_dir: str | Path = DEFAULT_CACHE_DIR):
        """Initialize a vector store and load its persisted state."""
        self.cache_dir = Path(cache_dir)
        self.db_file = self.cache_dir / "vectordb.pkl"
        self.embeddings_cache: dict[str, list[float]] = {}
        self.metadata_cache: dict[str, dict] = {}
        self.embeddings_dim = DEFAULT_EMBEDDING_DIM
        self.corpus_fingerprint: str | None = None
        self.index_version = RAG_INDEX_VERSION
        self._load()

    def _load(self) -> None:
        """Load the exact current vector-store format when it exists."""
        if not self.db_file.exists():
            return
        with self.db_file.open("rb") as handle:
            data = pickle.load(handle)
        if data["index_version"] != RAG_INDEX_VERSION:
            raise ValueError(
                f"Vector database uses {data['index_version']!r}; "
                f"expected {RAG_INDEX_VERSION!r}"
            )
        self.embeddings_cache = data["embeddings_cache"]
        self.metadata_cache = data["metadata_cache"]
        self.embeddings_dim = data["embeddings_dim"]
        self.corpus_fingerprint = data["corpus_fingerprint"]

    def save(self) -> None:
        """Persist the vector store atomically."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "embeddings_cache": self.embeddings_cache,
            "metadata_cache": self.metadata_cache,
            "embeddings_dim": self.embeddings_dim,
            "corpus_fingerprint": self.corpus_fingerprint,
            "index_version": self.index_version,
        }
        temporary = self.db_file.with_suffix(".pkl.tmp")
        with temporary.open("wb") as handle:
            pickle.dump(data, handle)
        temporary.replace(self.db_file)

    def upsert(
        self,
        key: str,
        embedding: list[float],
        metadata: dict,
    ) -> None:
        """Insert or replace one vector and its metadata."""
        self.embeddings_cache[key] = embedding
        self.metadata_cache[key] = metadata
        if embedding:
            self.embeddings_dim = len(embedding)

    def clear(self) -> None:
        """Discard all entries before rebuilding a changed corpus."""

        self.embeddings_cache.clear()
        self.metadata_cache.clear()
        self.corpus_fingerprint = None

    def items(self) -> Iterator[tuple[str, list[float], dict]]:
        """Yield stored entries in deterministic key order."""
        for key in sorted(self.metadata_cache):
            yield (
                key,
                self.embeddings_cache[key],
                self.metadata_cache[key],
            )
