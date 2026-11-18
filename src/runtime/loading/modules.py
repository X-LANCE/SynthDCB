"""Load file-backed Domain modules inside deterministic namespace packages."""

from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
from pathlib import Path
import sys
import types


def _package(name: str, path: Path) -> types.ModuleType:
    """Return the package."""
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    module = types.ModuleType(name)
    module.__package__ = name
    module.__path__ = [str(path)]
    module.__spec__ = importlib.machinery.ModuleSpec(
        name,
        loader=None,
        is_package=True,
    )
    sys.modules[name] = module
    return module


def load_module_from_tree(
    path: str | Path,
    *,
    tree_root: str | Path,
    namespace: str,
) -> types.ModuleType:
    """Load one module while preserving its relative-import package tree."""

    source = Path(path).resolve()
    root = Path(tree_root).resolve()
    try:
        relative = source.relative_to(root)
    except ValueError as error:
        raise ValueError(f"module {source} is outside tree root {root}") from error
    if source.suffix != ".py" or not relative.parts:
        raise ValueError(f"module path must be a Python file: {source}")

    digest = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:12]
    prefix = f"{namespace}_{digest}"
    _package(prefix, root)
    current_name = prefix
    current_path = root
    for part in relative.parts[:-1]:
        current_name = f"{current_name}.{part}"
        current_path = current_path / part
        _package(current_name, current_path)

    module_name = f"{current_name}.{source.stem}"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(module_name, source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    return module
