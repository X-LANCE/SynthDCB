"""Deterministic discovery and AST-aware chunking for the model corpus."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import re
from typing import Any, Iterable

from .config import RAG_INDEX_VERSION
from .sources import resolve_sources
from src.utils import format_json, parse_json


CORPUS_KINDS = frozenset({"document", "object_spec", "implementation", "test"})
_IDENTIFIER_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_WORD = re.compile(r"[\W_]+", re.UNICODE)


def identifier_tokens(value: str) -> list[str]:
    """Split CamelCase, snake_case, and prose into stable lowercase terms."""

    expanded = _IDENTIFIER_BOUNDARY.sub(" ", value or "").lower()
    return [token for token in _NON_WORD.split(expanded) if token]


def _domain_for_path(file_path: Path) -> str | None:
    """Return the domain for path."""
    parts = file_path.parts
    for marker in ("domains", "devices"):
        if marker in parts:
            index = parts.index(marker)
            if index + 1 < len(parts):
                return parts[index + 1]
    return None


def _source_class(file_path: Path) -> str:
    """Return the source class."""
    stem = file_path.stem
    return stem[:-5] if stem.endswith("_test") else stem


def infer_asset_kind(file_path: Path) -> str | None:
    """Return the asset kind."""
    if file_path.suffix in {".md", ".txt"}:
        return "document"
    if file_path.suffix == ".json":
        return "object_spec"
    if file_path.suffix != ".py":
        return None
    return "test" if file_path.stem.endswith("_test") else "implementation"


def extract_json_info(json_content: str) -> str:
    """Build a semantic query document from one ObjectClass specification."""

    data = parse_json(json_content)
    if not isinstance(data, dict) or len(data) != 1:
        raise ValueError("ObjectClass specification must contain exactly one class")

    class_name, raw_spec = next(iter(data.items()))
    if not isinstance(raw_spec, dict):
        raise ValueError("ObjectClass specification body must be an object")
    meta = raw_spec.get("meta") if isinstance(raw_spec.get("meta"), dict) else {}
    parts = [
        f"Object class {class_name}",
        " ".join(identifier_tokens(str(class_name))),
        str(meta.get("description") or ""),
    ]
    for section, label in (
        ("properties", "Properties"),
        ("functions", "Functions"),
        ("events", "Events"),
    ):
        raw_section = raw_spec.get(section)
        update = (
            raw_section.get("update")
            if isinstance(raw_section, dict)
            else None
        )
        if not isinstance(update, dict):
            continue
        section_parts: list[str] = []
        for name, detail in update.items():
            tokens = " ".join(identifier_tokens(str(name)))
            description = (
                str(detail.get("description") or "")
                if isinstance(detail, dict)
                else ""
            )
            type_name = (
                str(detail.get("type") or "")
                if isinstance(detail, dict)
                else ""
            )
            section_parts.append(
                " ".join(part for part in (str(name), tokens, type_name, description) if part)
            )
        if section_parts:
            parts.append(f"{label}: " + "; ".join(section_parts))
    return "\n".join(part for part in parts if part)


def _function_entry(
    *,
    content: str,
    file_path: Path,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    class_name: str | None,
    kind: str,
) -> dict[str, Any] | None:
    """Return the function entry."""
    if kind == "implementation" and node.name.startswith("__"):
        return None
    function_code = ast.get_source_segment(content, node)
    if not function_code:
        return None
    source_class = _source_class(file_path)
    display_name = f"{class_name}.{node.name}" if class_name else f"{source_class}.{node.name}"
    docstring = ast.get_docstring(node) or ""
    arguments = [
        argument.arg
        for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
        if argument.arg not in {"self", "cls"}
    ]
    query_parts = [
        f"{kind} for {source_class}",
        f"class {class_name}" if class_name else "",
        f"function {node.name}",
        " ".join(identifier_tokens(node.name)),
        f"arguments {' '.join(arguments)}" if arguments else "",
        docstring[:800],
    ]
    return {
        "id": f"{file_path.as_posix()}#{display_name}",
        "display_name": display_name,
        "type": kind,
        "content": function_code,
        "query_text": "\n".join(part for part in query_parts if part),
        "metadata": {
            "file": file_path.as_posix(),
            "class": class_name,
            "source_class": source_class,
            "function": node.name,
            "docstring": docstring[:800],
            "domain": _domain_for_path(file_path),
        },
    }


def extract_function_chunks(
    content: str,
    file_path: Path,
    *,
    kind: str | None = None,
) -> list[dict[str, Any]]:
    """Return direct module/class functions without recursively duplicating nests."""

    resolved_kind = kind or infer_asset_kind(file_path)
    if resolved_kind not in {"implementation", "test"}:
        return []
    tree = ast.parse(content)
    chunks: list[dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            entry = _function_entry(
                content=content,
                file_path=file_path,
                node=node,
                class_name=None,
                kind=resolved_kind,
            )
            if entry:
                chunks.append(entry)
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                entry = _function_entry(
                    content=content,
                    file_path=file_path,
                    node=item,
                    class_name=node.name,
                    kind=resolved_kind,
                )
                if entry:
                    chunks.append(entry)
    return chunks


def get_all_model_files(
    project_root: Path, domain: str | None = None, *, stage: str | None = None,
    source_config: str | Path | None = None,
) -> list[Path]:
    """Return the configured source files, with no implicit reference directories."""
    return list(resolve_sources(project_root, domain, stage, source_config=source_config))


def build_corpus_entries(
    file_paths: Iterable[Path], *, asset_kinds: dict[Path, str] | None = None,
    domain: str | None = None,
) -> list[dict[str, Any]]:
    """Return the corpus entries."""
    entries: list[dict[str, Any]] = []
    for file_path in sorted({Path(path).resolve() for path in file_paths}, key=str):
        kind = (asset_kinds or {}).get(file_path) or infer_asset_kind(file_path)
        if kind not in CORPUS_KINDS:
            continue
        content = file_path.read_text(encoding="utf-8-sig")
        if kind == "document":
            for offset in range(0, len(content), 4000):
                chunk = content[offset:offset + 4000]
                title = f"{file_path.stem} [{offset // 4000 + 1}]"
                entries.append({
                    "id": f"{file_path.as_posix()}#document-{offset}",
                    "display_name": title, "type": kind, "content": chunk,
                    "query_text": f"{file_path.stem}\n{chunk}",
                    "metadata": {"file": str(file_path), "source_class": None, "domain": domain},
                })
        elif kind == "object_spec":
            parsed = parse_json(content)
            if not isinstance(parsed, dict) or len(parsed) != 1:
                raise ValueError(
                    f"ObjectClass specification must contain one class: {file_path}"
                )
            source_class = str(next(iter(parsed)))
            entries.append(
                {
                    "id": file_path.as_posix(),
                    "display_name": source_class,
                    "type": kind,
                    "content": content,
                    "query_text": extract_json_info(content),
                    "metadata": {
                        "file": file_path.as_posix(),
                        "source_class": source_class,
                        "domain": _domain_for_path(file_path),
                    },
                }
            )
        else:
            entries.extend(
                extract_function_chunks(content, file_path, kind=kind)
            )
    if domain is not None:
        for entry in entries:
            entry["metadata"]["domain"] = domain
    return entries


def corpus_fingerprint(file_paths: Iterable[Path], *, asset_kinds: dict[Path, str] | None = None) -> str:
    """Hash index format, relative identities, and exact source bytes."""

    records = []
    for path in sorted({Path(item).resolve() for item in file_paths}, key=str):
        portable_path = path.as_posix()
        for marker in ("domains", "src"):
            if marker in path.parts:
                portable_path = "/".join(path.parts[path.parts.index(marker):])
                break
        records.append(
            {
                "path": portable_path,
                "kind": (asset_kinds or {}).get(path) or infer_asset_kind(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    payload = format_json(
        {
            "index_version": RAG_INDEX_VERSION,
            "chunker_sha256": hashlib.sha256(
                Path(__file__).read_bytes()
            ).hexdigest(),
            "files": records,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def corpus_snapshot(
    project_root: Path, domain: str | None = None, *,
    stage: str | None = None, source_config: str | Path | None = None,
) -> dict[str, Any]:
    """Return the corpus snapshot."""
    root = project_root.resolve()
    sources = resolve_sources(root, domain, stage, source_config=source_config)
    files = list(sources)
    entries = build_corpus_entries(files, asset_kinds=sources, domain=domain)
    by_kind = {
        kind: sum(entry["type"] == kind for entry in entries)
        for kind in sorted(CORPUS_KINDS)
    }
    return {
        "index_version": RAG_INDEX_VERSION,
        "domain": domain,
        "fingerprint": corpus_fingerprint(files, asset_kinds=sources),
        "stage": stage,
        "files": [path.relative_to(root).as_posix() for path in files],
        "file_count": len(files),
        "entry_count": len(entries),
        "entries_by_kind": by_kind,
    }
