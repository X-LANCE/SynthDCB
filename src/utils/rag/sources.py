"""Resolve only the source ranges explicitly configured for a domain and stage."""

import os
from pathlib import Path
from typing import Any

from src.contracts.jsonio import load_json
from src.utils.config import PROJECT_ROOT

SOURCE_CONFIG_ROOT = Path("simulator/domains")
SOURCE_CONFIG_NAME = "rag_sources.json"
STAGE_KINDS = {
    "type_list": {"document", "object_spec"},
    "meta": {"document", "object_spec"},
    "code": {"document", "implementation"},
    "test": {"document", "test"},
}
EXTENSIONS = {
    "document": {".md", ".txt"},
    "object_spec": {".json"},
    "implementation": {".py"},
    "test": {".py"},
}


def source_config_path(
    project_root: Path, domain: str, source_config: str | Path | None = None,
) -> Path:
    source_config = source_config or os.getenv("DCB_RAG_SOURCE_CONFIG")
    path = Path(source_config) if source_config is not None else SOURCE_CONFIG_ROOT / domain / SOURCE_CONFIG_NAME
    return (path if path.is_absolute() else project_root / path).resolve()


def _patterns(values: Any) -> list[str]:
    if not isinstance(values, list) or any(
        not isinstance(value, str) or not value or Path(value).is_absolute()
        or ".." in Path(value).parts for value in values
    ):
        raise ValueError("source patterns must be repository-relative glob strings")
    return values


def resolve_sources(
    project_root: Path,
    domain: str | None,
    stage: str | None,
    *,
    source_config: str | Path | None = None,
    fixed: bool | None = None,
) -> dict[Path, str]:
    """Resolve all, fixed, or retrieved sources; fixed files retain configuration order."""
    root = Path(project_root).resolve()
    source_config = source_config or os.getenv("DCB_RAG_SOURCE_CONFIG")
    if domain is None and source_config is None:
        config_paths = sorted((root / SOURCE_CONFIG_ROOT).glob(f"*/{SOURCE_CONFIG_NAME}"))
        if not config_paths:
            raise FileNotFoundError(f"No RAG source configurations under {root / SOURCE_CONFIG_ROOT}")
    else:
        config_paths = [source_config_path(root, domain, source_config)]
    selected_stages = [stage] if stage is not None else list(STAGE_KINDS)
    files = {}
    fixed_files = {}
    for config_path in config_paths:
        selected_domain = domain or config_path.parent.name
        scopes = load_json(config_path)
        if not isinstance(scopes, dict) or set(scopes) != set(STAGE_KINDS):
            raise ValueError(f"{selected_domain} requires the four RAG stage scopes")
        for selected_stage in selected_stages:
            if selected_stage not in STAGE_KINDS:
                raise ValueError(f"unknown RAG stage: {selected_stage}")
            entries = scopes[selected_stage]
            if not isinstance(entries, list):
                raise ValueError(f"{selected_domain}.{selected_stage} must be an array")
            for entry in entries:
                if (
                    not isinstance(entry, dict)
                    or set(entry) - {"kind", "include", "exclude", "fixed"}
                    or not {"kind", "include"}.issubset(entry)
                ):
                    raise ValueError("source entries require kind/include and optional exclude/fixed")
                is_fixed = entry.get("fixed", False)
                if type(is_fixed) is not bool:
                    raise ValueError("source fixed must be a boolean")
                kind = entry["kind"]
                if not isinstance(kind, str) or kind not in STAGE_KINDS[selected_stage]:
                    raise ValueError(f"unsupported {selected_stage} source kind: {kind}")
                includes = _patterns(entry["include"])
                excludes = _patterns(entry.get("exclude", []))
                if not includes:
                    raise ValueError("source include cannot be empty; use [] for a disabled stage")
                excluded = {path.resolve() for pattern in excludes for path in root.glob(pattern)}
                for pattern in includes:
                    matches = [
                        path for path in sorted(root.glob(pattern))
                        if path.is_file() and path.resolve() not in excluded
                    ]
                    if not matches:
                        raise FileNotFoundError(f"RAG source matched no files: {pattern}")
                    for path in matches:
                        path = path.resolve()
                        if not path.is_relative_to(root) or path.suffix not in EXTENSIONS[kind]:
                            raise ValueError(f"invalid {kind} source: {path}")
                        if path in files and files[path] != kind:
                            raise ValueError(f"conflicting source kinds for {path}")
                        files[path] = kind
                        if is_fixed:
                            fixed_files[path] = kind
    if fixed is True:
        return fixed_files
    if fixed is False:
        files = {path: kind for path, kind in files.items() if path not in fixed_files}
    return dict(sorted(files.items(), key=lambda item: str(item[0])))


def prepend_fixed_references(
    user_prompt: str, *, domain: str, stage: str, use_rag: bool = True,
    project_root: Path = PROJECT_ROOT, source_config: str | Path | None = None,
) -> tuple[str, str]:
    """Put complete fixed documents and examples before request-dependent content."""
    if not use_rag:
        return user_prompt, ""
    root = Path(project_root).resolve()
    sources = resolve_sources(root, domain, stage, source_config=source_config, fixed=True)
    if not sources:
        return user_prompt, ""
    parts = []
    for documents, heading in ((True, "Fixed domain documents"), (False, "Fixed representative examples")):
        entries = []
        for path, kind in sources.items():
            if (kind == "document") != documents:
                continue
            language = {"document": "text", "object_spec": "json"}.get(kind, "python")
            content = path.read_text(encoding="utf-8-sig").rstrip()
            fence = "```"
            while fence in content:
                fence += "`"
            entries.append(
                f"### Source: {path.relative_to(root).as_posix()}\n\n"
                f"{fence}{language}\n{content}\n{fence}"
            )
        if entries:
            parts.append(f"## {heading}\n\n" + "\n\n".join(entries))
    prefix = "\n\n".join(parts)
    return prefix + "\n\n" + user_prompt.lstrip(), prefix
