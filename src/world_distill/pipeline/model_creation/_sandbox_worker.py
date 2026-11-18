"""Private worker used by :mod:`model_creation.sandbox`.

This file is invoked with ``python -I -B``.  It is not a public CLI.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
from pathlib import Path
import sys
import types
import unittest
from typing import Any


RESULT_PREFIX = "DCB_SANDBOX_RESULT="
WINDOWS_TRUSTED_SYSTEM_LIBRARIES = frozenset(
    {
        "kernel32",
        "kernel32.dll",
    }
)


class OutputLimitExceeded(RuntimeError):
    """Generated process output exceeded its configured byte limit."""


class CappedTextIO(io.StringIO):
    def __init__(self, limit: int) -> None:
        """Initialize the CappedTextIO."""
        super().__init__()
        self.limit = limit
        self.used = 0

    def write(self, text: str) -> int:
        """Write text while enforcing the output-byte limit."""
        encoded_size = len(str(text).encode("utf-8"))
        if self.used + encoded_size > self.limit:
            raise OutputLimitExceeded("generated process output exceeded limit")
        self.used += encoded_size
        return super().write(text)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--mode", choices=("unittest",), required=True)
    parser.add_argument("--candidate_root", type=Path, required=True)
    parser.add_argument("--project_root", type=Path, required=True)
    parser.add_argument("--test_path", type=Path, required=True)
    parser.add_argument("--output_bytes", type=int, required=True)
    parser.add_argument("--process_count", type=int, required=True)
    return parser.parse_args()


def _is_within(path: Path, roots: tuple[Path, ...]) -> bool:
    """Return whether the path is inside an allowed root."""
    resolved = path.resolve(strict=False)
    return any(resolved == root or root in resolved.parents for root in roots)


def _native_library_allowed(
    raw_library: object,
    roots: tuple[Path, ...],
    *,
    platform_name: str | None = None,
) -> bool:
    """Allow interpreter libraries and the minimal Windows loader dependency."""

    if raw_library is None:
        return True
    try:
        raw_path = os.fspath(raw_library)
    except TypeError:
        return False
    platform_name = platform_name or os.name
    if (
        platform_name == "nt"
        and isinstance(raw_path, str)
        and Path(raw_path).name.casefold()
        in WINDOWS_TRUSTED_SYSTEM_LIBRARIES
        and len(Path(raw_path).parts) == 1
    ):
        # CPython and its standard library may resolve Windows primitives via
        # ``ctypes.windll.kernel32`` after the audit hook is installed.  The
        # generated source still cannot import/access ctypes because the
        # parent static gate rejects that API surface.
        return True
    return _is_within(Path(raw_path), roots)


def install_guards(candidate_root: Path, project_root: Path) -> None:
    """Install the guards."""
    system_roots = {
        Path(sys.base_prefix).resolve(),
        Path(sys.prefix).resolve(),
        Path(__file__).resolve().parent,
    }
    readable_roots = (
        candidate_root.resolve(),
        project_root.resolve(),
        *sorted(system_roots, key=str),
    )

    def audit(event: str, args: tuple[Any, ...]) -> None:
        """Reject prohibited runtime audit events."""
        if event.startswith("socket."):
            raise PermissionError("network access is disabled")
        if event in {
            "subprocess.Popen",
            "os.system",
            "os.posix_spawn",
            "os.spawn",
        }:
            raise PermissionError(f"process/native access is disabled: {event}")
        if event == "ctypes.dlopen":
            raw_library = args[0] if args else None
            allowed_native_roots = tuple(sorted(system_roots, key=str))
            if _native_library_allowed(
                raw_library,
                allowed_native_roots,
            ):
                return
            raise PermissionError(
                f"native library outside interpreter roots: {raw_library}"
            )
        if event != "open" or not args:
            return
        raw_path = args[0]
        if isinstance(raw_path, int):
            return
        try:
            path = Path(os.fspath(raw_path))
        except TypeError:
            raise PermissionError("unsupported file target")
        mode = args[1] if len(args) > 1 else "r"
        flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
        writing = (
            isinstance(mode, str) and any(flag in mode for flag in "wax+")
        ) or bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
        if writing:
            raise PermissionError(f"filesystem writes are disabled: {path}")
        if not _is_within(path, readable_roots):
            raise PermissionError(f"filesystem read outside allowlist: {path}")

    sys.addaudithook(audit)


def clear_environment() -> None:
    """Clear the environment."""
    keep = {
        name: os.environ[name]
        for name in (
            "DCB_GENERATED_CODE_SANDBOX",
            "LANG",
            "LC_ALL",
            "PYTHONDONTWRITEBYTECODE",
            "PYTHONHASHSEED",
            "SYSTEMROOT",
            "WINDIR",
        )
        if name in os.environ
    }
    os.environ.clear()
    os.environ.update(keep)


def apply_candidate_process_limit(process_count: int) -> None:
    """Apply the candidate process limit."""
    if os.name != "posix":
        return
    import resource

    if hasattr(resource, "RLIMIT_NPROC"):
        resource.setrlimit(resource.RLIMIT_NPROC, (process_count, process_count))


def _load_test_module(path: Path, candidate_root: Path) -> types.ModuleType:
    """Return the test module."""
    from src.runtime.loading.modules import load_module_from_tree

    return load_module_from_tree(
        path,
        tree_root=candidate_root,
        namespace="dcb_generated_candidate",
    )


def run_unittest(
    test_path: Path,
    candidate_root: Path,
    output_bytes: int,
) -> dict[str, Any]:
    """Run the unittest."""
    module = _load_test_module(test_path, candidate_root)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    count = suite.countTestCases()
    stream = CappedTextIO(output_bytes)
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    passed = count > 0 and result.wasSuccessful()
    return {
        "code": "[PASS]" if passed else "[GENERATED_TEST_FAILED]",
        "test_count": count,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "output": stream.getvalue(),
    }


def main() -> int:
    """Run the command-line entry point."""
    args = parse_args()
    candidate_root = args.candidate_root.resolve()
    project_root = args.project_root.resolve()
    if not candidate_root.is_dir():
        raise FileNotFoundError(candidate_root)
    sys.path.insert(0, str(project_root))
    from src.utils import format_json
    clear_environment()
    apply_candidate_process_limit(args.process_count)
    install_guards(candidate_root, project_root)

    captured = CappedTextIO(args.output_bytes)
    try:
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            result = run_unittest(
                args.test_path.resolve(), candidate_root, args.output_bytes,
            )
        result["captured_output"] = captured.getvalue()
    except BaseException as error:
        result = {
            "code": (
                "[SANDBOX_OUTPUT_LIMIT]"
                if isinstance(error, OutputLimitExceeded)
                else "[SANDBOX_EXECUTION_FAILED]"
            ),
            "error_type": type(error).__name__,
            "error": str(error),
            "captured_output": captured.getvalue(),
        }
    print(RESULT_PREFIX + format_json(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["code"] == "[PASS]" else 1


if __name__ == "__main__":
    raise SystemExit(main())
