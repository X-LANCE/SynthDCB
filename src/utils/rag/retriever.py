"""Offline-first lexical retrieval with optional semantic reranking."""

from __future__ import annotations

from collections import Counter
import hashlib
import math
import os
import re
from pathlib import Path
import threading
from typing import Iterable, Sequence

from src.utils.config import PROJECT_ROOT

from .config import (
    DEFAULT_CACHE_DIR,
    EMBEDDING_MODEL,
    RAG_INDEX_VERSION,
    RAG_USE_EMBEDDINGS,
)
from .corpus import (
    CORPUS_KINDS,
    build_corpus_entries,
    corpus_fingerprint,
    identifier_tokens,
)
from .embeddings import EmbeddingClient
from .vectordb import VectorDB
from .sources import STAGE_KINDS, resolve_sources, source_config_path


_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "class",
        "device",
        "for",
        "from",
        "function",
        "home",
        "implementation",
        "in",
        "of",
        "object",
        "python",
        "specification",
        "test",
        "the",
        "to",
    }
)
_TYPE_ALIASES = {
    "document": {"document"},
    "json": {"object_spec"},
    "object_spec": {"object_spec"},
    "python": {"implementation"},
    "python_function": {"implementation"},
    "implementation": {"implementation"},
    "test": {"test"},
}


def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Return the cosine similarity."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(left * right for left, right in zip(a, b))
    norm_a = math.sqrt(sum(value * value for value in a))
    norm_b = math.sqrt(sum(value * value for value in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _tokens(value: str) -> list[str]:
    """Return the tokens."""
    tokens = [
        token for token in identifier_tokens(value)
        if len(token) > 1 and token not in _STOP_WORDS
    ]
    # Chinese prose has no word separators; overlapping pairs allow lexical matching.
    for phrase in re.findall(r"[\u4e00-\u9fff]+", value):
        tokens.extend(phrase[index:index + 2] for index in range(len(phrase) - 1))
    return tokens


def _lexical_scores(query: str, entries: list[dict]) -> dict[str, float]:
    """Return the lexical scores."""
    query_counts = Counter(_tokens(query))
    if not query_counts:
        return {str(entry["key"]): 0.0 for entry in entries}
    document_tokens = [set(_tokens(str(entry["metadata"].get("query_text", "")))) for entry in entries]
    document_frequency = Counter(
        token
        for tokens in document_tokens
        for token in tokens
    )
    total_documents = max(1, len(entries))
    query_weight = {
        token: (1.0 + math.log1p(count))
        * (1.0 + math.log((total_documents + 1) / (document_frequency[token] + 1)))
        for token, count in query_counts.items()
    }
    denominator = sum(query_weight.values()) or 1.0
    scores: dict[str, float] = {}
    for entry, tokens in zip(entries, document_tokens):
        overlap = sum(weight for token, weight in query_weight.items() if token in tokens)
        metadata = entry["metadata"]
        name_tokens = set(_tokens(str(metadata.get("name", ""))))
        source_tokens = set(
            _tokens(str((metadata.get("metadata") or {}).get("source_class", "")))
        )
        name_boost = 0.08 * len(set(query_counts) & (name_tokens | source_tokens))
        scores[str(entry["key"])] = min(1.0, overlap / denominator + name_boost)
    return scores


def _normalized_class(value: object) -> str:
    """Return the normalized class."""
    return "".join(identifier_tokens(str(value))).lower()


class Retriever:
    def __init__(
        self,
        store: VectorDB | None = None,
        embedding_client: EmbeddingClient | None = None,
        *,
        use_embeddings: bool | None = None,
    ):
        """Initialize the Retriever."""
        self.store = store or VectorDB()
        self.use_embeddings = (
            RAG_USE_EMBEDDINGS if use_embeddings is None else use_embeddings
        )
        self.embedding_client = embedding_client or EmbeddingClient(
            self.store.cache_dir
        )

    def index_files(
        self, file_paths: Iterable[Path], *,
        asset_kinds: dict[Path, str] | None = None,
        domain: str | None = None,
    ) -> None:
        """Replace stale entries with a deterministic snapshot of the corpus."""

        paths = sorted({Path(path).resolve() for path in file_paths}, key=str)
        fingerprint = corpus_fingerprint(paths, asset_kinds=asset_kinds)
        has_required_embeddings = (
            not self.use_embeddings
            or all(
                self.store.embeddings_cache.get(key)
                for key in self.store.metadata_cache
            )
        )
        if (
            self.store.corpus_fingerprint == fingerprint
            and has_required_embeddings
        ):
            return
        entries = build_corpus_entries(paths, asset_kinds=asset_kinds, domain=domain)
        self.store.clear()
        for entry in entries:
            query_text = str(entry["query_text"])
            embedding = (
                self.embedding_client.get(query_text[:4000])
                if self.use_embeddings
                else []
            )
            metadata = entry["metadata"]
            self.store.upsert(
                str(entry["id"]),
                embedding,
                {
                    "path": metadata["file"],
                    "name": entry["display_name"],
                    "type": entry["type"],
                    "content": entry["content"],
                    "query_text": query_text,
                    "metadata": metadata,
                },
            )
        self.store.corpus_fingerprint = fingerprint
        self.store.save()

    @staticmethod
    def _resolved_kinds(
        *,
        kinds: Iterable[str] | None,
        file_type: str | None,
    ) -> set[str] | None:
        """Return the resolved kinds."""
        requested = set(kinds or ())
        if file_type:
            requested.add(file_type)
        if not requested:
            return None
        resolved: set[str] = set()
        for value in requested:
            resolved.update(_TYPE_ALIASES.get(value, {value}))
        unknown = resolved - CORPUS_KINDS
        if unknown:
            raise ValueError(f"unknown corpus kinds: {sorted(unknown)}")
        return resolved

    def _rank(
        self,
        query: str,
        *,
        kinds: set[str] | None,
        exclude_class: str | None,
    ) -> list[dict]:
        """Rank corpus entries against the query."""
        excluded = _normalized_class(exclude_class) if exclude_class else ""
        candidates: list[dict] = []
        for key, embedding, metadata in self.store.items():
            if kinds is not None and metadata.get("type") not in kinds:
                continue
            source_class = (metadata.get("metadata") or {}).get("source_class")
            if excluded and _normalized_class(source_class) == excluded:
                continue
            candidates.append(
                {
                    "key": key,
                    "embedding": embedding,
                    "metadata": metadata,
                }
            )
        lexical = _lexical_scores(query, candidates)
        query_embedding = (
            self.embedding_client.get(query)
            if self.use_embeddings and any(item["embedding"] for item in candidates)
            else []
        )
        for item in candidates:
            semantic = _cosine_similarity(query_embedding, item["embedding"])
            lexical_score = lexical.get(str(item["key"]), 0.0)
            item["lexical"] = lexical_score
            item["semantic"] = semantic
            item["score"] = (
                0.75 * lexical_score + 0.25 * max(0.0, semantic)
                if query_embedding and item["embedding"]
                else lexical_score
            )
        ranked = sorted(
            candidates,
            key=lambda item: (
                -item["score"],
                str(item["metadata"].get("path", "")),
                str(item["metadata"].get("name", "")),
            ),
        )
        return [item for item in ranked if item["score"] > 0]

    @staticmethod
    def _select_diverse(
        ranked: list[dict],
        *,
        top_k: int,
        max_chars: int | None,
    ) -> list[dict]:
        """Return the diverse."""
        selected: list[dict] = []
        used_sources: set[str] = set()
        remaining = list(ranked)
        while remaining and len(selected) < top_k:
            best_score = float(remaining[0]["score"])
            preferred_index = next(
                (
                    index
                    for index, item in enumerate(remaining)
                    if str(
                        (item["metadata"].get("metadata") or {}).get("source_class")
                        or item["metadata"].get("path")
                    )
                    not in used_sources
                    and float(item["score"]) >= max(0.0, best_score - 0.08)
                ),
                0,
            )
            item = remaining.pop(preferred_index)
            content_length = len(str(item["metadata"].get("content", "")))
            consumed = sum(
                len(str(chosen["metadata"].get("content", "")))
                for chosen in selected
            )
            if max_chars is not None and consumed + content_length > max_chars:
                continue
            selected.append(item)
            used_sources.add(
                str(
                    (item["metadata"].get("metadata") or {}).get("source_class")
                    or item["metadata"].get("path")
                )
            )
        return selected

    def search(
        self,
        query: str,
        top_k: int = 3,
        file_type: str | None = None,
        *,
        kinds: Iterable[str] | None = None,
        exclude_class: str | None = None,
        max_chars: int | None = None,
        min_score: float = 0.0,
    ) -> list[dict]:
        """Search the corpus for matching entries."""
        if top_k <= 0:
            return []
        if not 0.0 <= min_score <= 1.0:
            raise ValueError("min_score must be between 0 and 1")
        resolved_kinds = self._resolved_kinds(kinds=kinds, file_type=file_type)
        ranked = self._rank(
            query,
            kinds=resolved_kinds,
            exclude_class=exclude_class,
        )
        ranked = [
            item for item in ranked if float(item["score"]) >= min_score
        ]
        selected = self._select_diverse(
            ranked,
            top_k=top_k,
            max_chars=max_chars,
        )
        return [
            {
                "path": item["metadata"]["path"],
                "name": item["metadata"]["name"],
                "type": item["metadata"]["type"],
                "content": item["metadata"]["content"],
                "similarity": item["score"],
                "score_components": {
                    "lexical": item["lexical"],
                    "semantic": item["semantic"],
                },
                "metadata": item["metadata"].get("metadata", {}),
            }
            for item in selected
        ]

    def search_functions(
        self,
        query: str,
        target_function_hint: str | None = None,
        num_samples: int = 3,
        diversity_weight: float = 0.7,
        *,
        exclude_class: str | None = None,
        max_chars: int | None = None,
        min_score: float = 0.0,
    ) -> list[dict]:
        """Return the search functions."""
        del diversity_weight  # Diversity is source-aware and deterministic in v2.
        enhanced_query = (
            f"{target_function_hint} {query}"
            if target_function_hint
            else query
        )
        return self.search(
            enhanced_query,
            top_k=num_samples,
            kinds={"implementation"},
            exclude_class=exclude_class,
            max_chars=max_chars,
            min_score=min_score,
        )


_retrievers: dict[tuple, Retriever] = {}
_retriever_lock = threading.Lock()


def _cache_directory(
    project_root: Path,
    domain: str | None,
    use_embeddings: bool,
    stage: str | None = None,
    source_config: Path | None = None,
) -> Path:
    """Keep domain/mode indexes independent and rooted in the project."""

    domain_name = "".join(identifier_tokens(domain or "all")) or "all"
    if use_embeddings:
        model_hash = hashlib.sha256(
            EMBEDDING_MODEL.encode("utf-8")
        ).hexdigest()[:12]
        mode = f"semantic-{model_hash}"
    else:
        mode = "lexical"
    config_hash = hashlib.sha256(
        str(source_config_path(project_root, domain, source_config)
            if domain is not None or source_config is not None else project_root / "simulator/domains").encode()
    ).hexdigest()[:12]
    return (
        project_root
        / DEFAULT_CACHE_DIR
        / f"{RAG_INDEX_VERSION}-{domain_name}-{stage or 'all'}-{config_hash}-{mode}"
    )


def get_vectordb(
    *,
    domain: str | None = None,
    stage: str | None = None,
    source_config: str | Path | None = None,
    project_root: Path = PROJECT_ROOT,
    use_embeddings: bool | None = None,
    force_refresh: bool = False,
    generated_sources: dict[Path, str] | None = None,
) -> Retriever:
    """Return an indexed retriever without issuing remote calls by default."""

    enabled = RAG_USE_EMBEDDINGS if use_embeddings is None else use_embeddings
    root = Path(project_root).resolve()
    source_config = source_config or os.getenv("DCB_RAG_SOURCE_CONFIG")
    config_path = (source_config_path(root, domain, source_config)
                   if domain is not None or source_config is not None else None)
    accepted = {
        Path(path).resolve(): kind for path, kind in (generated_sources or {}).items()
        if stage is None or kind in STAGE_KINDS[stage]
    }
    source_identity = tuple(sorted((str(path), kind) for path, kind in accepted.items()))
    key = (str(root), domain, stage, enabled, str(config_path), source_identity)
    with _retriever_lock:
        sources = resolve_sources(root, domain, stage, source_config=config_path, fixed=False)
        sources.update(accepted)
        fixed = resolve_sources(root, domain, stage, source_config=config_path, fixed=True)
        sources = {path: kind for path, kind in sources.items() if path not in fixed}
        if force_refresh:
            _retrievers.pop(key, None)
        retriever = _retrievers.get(key)
        if retriever is None:
            cache_dir = _cache_directory(root, domain, enabled, stage, config_path)
            if accepted:
                cache_dir /= hashlib.sha256(repr(source_identity).encode()).hexdigest()[:12]
            retriever = Retriever(
                store=VectorDB(cache_dir),
                use_embeddings=enabled,
            )
            _retrievers[key] = retriever
        retriever.index_files(sources, asset_kinds=sources, domain=domain)
        return retriever


def reset_retrievers() -> None:
    """Clear process-local singleton state for deterministic tests."""

    with _retriever_lock:
        _retrievers.clear()
