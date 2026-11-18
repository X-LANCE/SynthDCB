"""Small file, JSON, formatting, and console helpers."""

from __future__ import annotations

import datetime
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

import colorama
from tqdm import tqdm


colorama.init(autoreset=True)


CONSOLE_WIDTH = 72
STATUS_COLORS = {
    "error": "red",
    "info": "cyan",
    "success": "green",
    "warning": "yellow",
}


parse_json = json.loads
format_json = json.dumps


def parse_json_object(text: str, **kwargs: Any) -> dict[str, Any]:
    """Decode JSON text and require an object at the top level."""
    payload = parse_json(text, **kwargs)
    if not isinstance(payload, dict):
        raise ValueError("JSON value must be an object")
    return payload


def load_json(path: str | Path, **kwargs: Any) -> Any:
    """Load and decode a UTF-8 JSON file."""
    return parse_json(Path(path).read_text(encoding="utf-8"), **kwargs)


def load_jsonl(path: str | Path, **kwargs: Any) -> list[Any]:
    """Read nonblank UTF-8 JSONL rows."""
    with Path(path).open("r", encoding="utf-8") as stream:
        return [parse_json(line, **kwargs) for line in stream if line.strip()]


def json_payload(value: Any) -> str:
    """Serialize prompt contracts without Python repr ambiguity."""
    return format_json(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def load_file(path: str | Path) -> str:
    """Read a UTF-8 text file."""
    return Path(path).read_text(encoding="utf-8")


def save_file(path: str | Path, obj: str) -> None:
    """Write a UTF-8 text file."""
    Path(path).write_text(obj, encoding="utf-8")


def _print_colored(
    content: object,
    front_color: str = "reset",
    back_color: str = "reset",
    style: str = "normal",
    pad: int = 0,
) -> None:
    """Print text using explicit colorama style names."""
    text = str(content)
    if len(text) + 4 <= pad:
        text = f"{' ' + text + ' ':=^{pad}}"
    rendered = (
        getattr(colorama.Fore, front_color.upper())
        + getattr(colorama.Back, back_color.upper())
        + getattr(colorama.Style, style.upper())
        + text
    )
    print(rendered)


def print_status(message: object, status: str = "info") -> None:
    """Print one consistently prefixed status message."""
    color = STATUS_COLORS[status]
    _print_colored(f"[{status.upper()}] {message}", color)


def _print_run_panel(
    kind: str,
    title: str,
    fields: Iterable[tuple[str, object]],
) -> None:
    """Render one configuration or summary panel."""
    rows = tuple(fields)
    label_width = max((len(label) for label, _ in rows), default=0)
    border = "=" * CONSOLE_WIDTH
    _print_colored(f"\n{border}", "magenta")
    _print_colored(f"[{kind}] {title}", "magenta")
    _print_colored(border, "magenta")
    for label, value in rows:
        _print_colored(f"  {label:<{label_width}} : {value}", "cyan")
    _print_colored(border, "magenta")


def print_run_config(
    title: str,
    fields: Iterable[tuple[str, object]],
) -> None:
    """Print the effective configuration before a command starts."""
    _print_run_panel("CONFIG", title, fields)


def print_run_summary(
    title: str,
    status: str,
    fields: Iterable[tuple[str, object]] = (),
) -> None:
    """Print the final status and selected command results."""
    _print_run_panel("SUMMARY", title, (("Status", status), *tuple(fields)))


def progress_bar(
    *,
    total: int,
    description: str,
    unit: str,
    initial: int = 0,
    enabled: bool = True,
) -> tqdm:
    """Create a progress bar with the project-wide terminal style."""
    return tqdm(
        total=total,
        initial=initial,
        desc=description,
        unit=unit,
        disable=not enabled,
        dynamic_ncols=True,
    )


def indent(text: str, n: int = 4) -> str:
    """Indent every nonempty line by the requested width."""
    pad = " " * n
    return "\n".join(pad + line if line else line for line in text.splitlines())


def safe_json(value: Any) -> str:
    """Return Python-source literal text for a JSON-compatible value."""
    return repr(value)


def now_iso() -> str:
    """Return the local time in second-precision ISO 8601 format."""
    return datetime.datetime.now().isoformat(timespec="seconds", sep=" ")


SECRET_KEY = re.compile(
    r"(?:api[_-]?key|authorization|access[_-]?token|refresh[_-]?token|password|secret)",
    re.IGNORECASE,
)
BEARER_VALUE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")


def sorted_json_bytes(value: Any) -> bytes:
    """Serialize the value as sorted JSON bytes."""
    return format_json(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    """Return the SHA-256 digest of sorted JSON data."""
    return hashlib.sha256(sorted_json_bytes(value)).hexdigest()


def redact(value: Any, *, key: str = "") -> Any:
    """Remove credentials while preserving prompts, responses, and usage."""

    if SECRET_KEY.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {
            str(item_key): redact(item, key=str(item_key))
            for item_key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return BEARER_VALUE.sub("Bearer [REDACTED]", value)
    return value


def write_json(path: str | Path, payload: Any) -> Path:
    """Atomically write a UTF-8 JSON file, creating its parent directory."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        format_json(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination


def write_jsonl(path: str | Path, records: Iterable[dict[str, Any]]) -> Path:
    """Atomically replace a UTF-8 JSONL file."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        "".join(
            format_json(record, ensure_ascii=False, sort_keys=True) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination


def append_jsonl(path: str | Path, records: Iterable[dict[str, Any]]) -> Path:
    """Append and flush JSONL rows; callers own locking and recovery."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("a", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(format_json(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        stream.flush()
    return destination
