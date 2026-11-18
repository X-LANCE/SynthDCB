"""Static and process-isolated execution for untrusted generated models.

The sandbox is deliberately narrow: generated Home models may use the Python
standard-library modules needed by the object contract and may import
``src.object_model``.  They may not perform I/O, inspect process state, open a
network connection, or create another process.  Dynamic checks run in a fresh
interpreter with a minimal environment and POSIX resource limits when those
limits are available.
"""

from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
from functools import lru_cache
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
from src.utils import parse_json


SANDBOX_RESULT_PREFIX = "DCB_SANDBOX_RESULT="


@dataclass(frozen=True, slots=True)
class SandboxLimits:
    """Frozen resource envelope for one generated-code process."""

    wall_time_seconds: int = 20
    cpu_seconds: int = 10
    memory_mb: int = 512
    process_count: int = 1
    open_files: int = 64
    output_bytes: int = 262_144

    def validate(self) -> None:
        """Validate that every sandbox resource limit is positive."""
        for name, value in asdict(self).items():
            if not isinstance(value, int) or value <= 0:
                raise ValueError(f"sandbox limit {name} must be a positive integer")


ALLOWED_IMPORT_ROOTS = frozenset(
    {
        "__future__",
        "collections",
        "dataclasses",
        "enum",
        "functools",
        "math",
        "re",
        "src",
        "typing",
        "unittest",
    }
)

FORBIDDEN_NAMES = frozenset(
    {
        "__builtins__",
        "__import__",
        "breakpoint",
        "compile",
        "delattr",
        "eval",
        "exec",
        "getattr",
        "globals",
        "hasattr",
        "input",
        "locals",
        "open",
        "setattr",
        "vars",
    }
)

FORBIDDEN_ATTRIBUTE_ROOTS = frozenset(
    {
        "asyncio",
        "builtins",
        "ctypes",
        "http",
        "importlib",
        "io",
        "multiprocessing",
        "os",
        "pathlib",
        "requests",
        "shutil",
        "socket",
        "subprocess",
        "sys",
        "urllib",
    }
)


def _attribute_root(node: ast.AST) -> str | None:
    """Return the attribute root."""
    current = node
    while isinstance(current, ast.Attribute):
        current = current.value
    return current.id if isinstance(current, ast.Name) else None


def _is_super_init(node: ast.Attribute) -> bool:
    """Allow only the template-owned ``super().__init__`` inheritance call."""

    value = node.value
    return (
        node.attr == "__init__"
        and isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id == "super"
        and not value.args
        and not value.keywords
    )


def _parameter_reads(tree: ast.AST) -> set[ast.Name]:
    """Find parameter references that cannot resolve to a forbidden builtin.

    Nested scopes, defaults and decorators are deliberately excluded. Calling
    a forbidden name remains rejected even when it is a parameter.
    """
    reads = set()
    for function in ast.walk(tree):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        parameters = {arg.arg for arg in (
            *function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs,
        )} & FORBIDDEN_NAMES
        pending = list(function.body)
        while pending and parameters:
            node = pending.pop()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                continue
            if isinstance(node, ast.Name) and node.id in parameters:
                reads.add(node)
            pending.extend(ast.iter_child_nodes(node))
    return reads


def scan_generated_source(path: str | Path) -> dict[str, Any]:
    """Return deterministic security findings for one generated Python file."""

    source_path = Path(path).resolve()
    source = source_path.read_text(encoding="utf-8")
    errors: list[dict[str, Any]] = []
    try:
        tree = ast.parse(source, filename=str(source_path))
    except SyntaxError as error:
        return {
            "path": str(source_path),
            "passed": False,
            "errors": [
                {
                    "code": "SYNTAX_ERROR",
                    "line": error.lineno,
                    "message": error.msg,
                }
            ],
        }

    def add(node: ast.AST, code: str, message: str) -> None:
        """Add a generated-source security finding."""
        errors.append(
            {
                "code": code,
                "line": getattr(node, "lineno", None),
                "message": message,
            }
        )

    parameter_reads = _parameter_reads(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root not in ALLOWED_IMPORT_ROOTS:
                    add(node, "FORBIDDEN_IMPORT", alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            module = node.module or ""
            root = module.split(".", 1)[0]
            if root not in ALLOWED_IMPORT_ROOTS:
                add(node, "FORBIDDEN_IMPORT", module)
            elif root == "src" and not (
                module == "src.object_model"
                or module.startswith("src.object_model.")
            ):
                add(node, "FORBIDDEN_PROJECT_IMPORT", module)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id in FORBIDDEN_NAMES and node not in parameter_reads:
                add(node, "FORBIDDEN_NAME", node.id)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_NAMES:
                add(node.func, "FORBIDDEN_NAME", node.func.id)
        elif isinstance(node, ast.Attribute):
            root = _attribute_root(node)
            if root in FORBIDDEN_ATTRIBUTE_ROOTS:
                add(node, "FORBIDDEN_ATTRIBUTE", ast.unparse(node))
            if (
                node.attr.startswith("__")
                and node.attr.endswith("__")
                and not _is_super_init(node)
            ):
                add(node, "DUNDER_ACCESS", ast.unparse(node))

    unique: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for error in errors:
        key = (error["code"], error["line"], error["message"])
        if key not in seen:
            seen.add(key)
            unique.append(error)
    return {
        "path": str(source_path),
        "passed": not unique,
        "errors": unique,
    }


def scan_generated_sources(paths: Iterable[str | Path]) -> dict[str, Any]:
    """Scan a candidate bundle and aggregate its static security result."""

    files = [scan_generated_source(path) for path in paths]
    return {
        "code": (
            "[PASS]"
            if files and all(item["passed"] for item in files)
            else "[SANDBOX_STATIC_REJECTED]"
        ),
        "files": files,
        "errors": [
            {
                "path": item["path"],
                **error,
            }
            for item in files
            for error in item["errors"]
        ],
    }


def _limit_process(
    limits: SandboxLimits,
    *,
    set_process_limit: bool = True,
):
    """Limit the process."""
    if os.name != "posix":
        return None

    def apply_limits() -> None:
        """Apply the limits."""
        import resource

        memory_bytes = limits.memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_CPU, (limits.cpu_seconds, limits.cpu_seconds))
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        resource.setrlimit(resource.RLIMIT_FSIZE, (limits.output_bytes, limits.output_bytes))
        resource.setrlimit(resource.RLIMIT_NOFILE, (limits.open_files, limits.open_files))
        if set_process_limit and hasattr(resource, "RLIMIT_NPROC"):
            resource.setrlimit(
                resource.RLIMIT_NPROC,
                (limits.process_count, limits.process_count),
            )

    return apply_limits


@lru_cache(maxsize=1)
def _os_sandbox_tools() -> tuple[str, str] | None:
    """Return a verified unshare+bwrap backend when the host permits it."""

    if os.name != "posix":
        return None
    unshare = shutil.which("unshare")
    bwrap = shutil.which("bwrap")
    if unshare is None or bwrap is None:
        return None
    probe = [
        unshare,
        "--user",
        "--map-root-user",
        "--net",
        "--pid",
        "--fork",
        bwrap,
        "--die-with-parent",
        "--new-session",
        "--unshare-all",
        "--share-net",
        "--ro-bind",
        "/",
        "/",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--clearenv",
        "/usr/bin/true",
    ]
    try:
        completed = subprocess.run(
            probe,
            env={},
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return (unshare, bwrap) if completed.returncode == 0 else None


def _os_sandbox_prefix(
    root: Path,
    environment: dict[str, str],
) -> tuple[list[str], str]:
    """Return the OS sandbox prefix."""
    tools = _os_sandbox_tools()
    if tools is None:
        raise RuntimeError(
            "Linux namespace sandbox requires working unshare and bwrap binaries"
        )
    unshare, bwrap = tools
    command = [
        unshare,
        "--user",
        "--map-root-user",
        "--net",
        "--pid",
        "--fork",
        bwrap,
        "--die-with-parent",
        "--new-session",
        "--unshare-all",
        "--share-net",
        "--ro-bind",
        "/",
        "/",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--clearenv",
    ]
    for name, value in sorted(environment.items()):
        command.extend(["--setenv", name, value])
    command.extend(["--chdir", str(root), "--"])
    return command, "linux-user-net-pid-mount-namespace+bwrap-ro-root"


def _minimal_environment() -> dict[str, str]:
    """Return the minimal environment."""
    environment = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "DCB_GENERATED_CODE_SANDBOX": "1",
    }
    for name in ("LANG", "LC_ALL", "SYSTEMROOT", "WINDIR"):
        value = os.environ.get(name)
        if value:
            environment[name] = value
    return environment


def _result_from_output(output: str) -> dict[str, Any] | None:
    """Return the result from output."""
    for line in reversed(output.splitlines()):
        if not line.startswith(SANDBOX_RESULT_PREFIX):
            continue
        try:
            payload = parse_json(line.removeprefix(SANDBOX_RESULT_PREFIX))
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None
    return None


def run_generated_code(
    *,
    candidate_root: str | Path,
    source_paths: Iterable[str | Path],
    mode: str,
    test_path: str | Path | None = None,
    limits: SandboxLimits | None = None,
) -> dict[str, Any]:
    """Run a generated unittest in the isolated worker."""

    if mode != "unittest":
        raise ValueError(f"unsupported sandbox mode: {mode}")
    policy = limits or SandboxLimits()
    policy.validate()
    root = Path(candidate_root).resolve()
    paths = tuple(Path(path).resolve() for path in source_paths)
    static_report = scan_generated_sources(paths)
    if static_report["code"] != "[PASS]":
        return {
            "code": "[SANDBOX_STATIC_REJECTED]",
            "mode": mode,
            "limits": asdict(policy),
            "environment_policy": "minimal-no-secrets-no-proxies",
            "static": static_report,
            "dynamic": None,
        }

    worker = Path(__file__).with_name("_sandbox_worker.py")
    project_root = Path(__file__).resolve().parents[4]
    worker_command = [
        sys.executable,
        "-I",
        "-B",
        str(worker),
        "--mode",
        mode,
        "--candidate_root",
        str(root),
        "--project_root",
        str(project_root),
        "--output_bytes",
        str(policy.output_bytes),
        "--process_count",
        str(policy.process_count),
    ]
    if test_path is not None:
        worker_command.extend(["--test_path", str(Path(test_path).resolve())])

    environment = _minimal_environment()
    prefix, backend = _os_sandbox_prefix(root, environment)
    command = prefix + worker_command

    try:
        completed = subprocess.run(
            command,
            cwd=root,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=policy.wall_time_seconds,
            preexec_fn=_limit_process(
                policy,
                set_process_limit=not bool(prefix),
            ),
        )
    except subprocess.TimeoutExpired as error:
        captured = "\n".join(
            part
            for part in (
                error.stdout if isinstance(error.stdout, str) else "",
                error.stderr if isinstance(error.stderr, str) else "",
            )
            if part
        )
        return {
            "code": "[SANDBOX_TIMEOUT]",
            "mode": mode,
            "limits": asdict(policy),
            "environment_policy": "minimal-no-secrets-no-proxies",
            "backend": backend,
            "static": static_report,
            "dynamic": {
                "returncode": None,
                "output": captured[-policy.output_bytes :],
            },
        }

    output = "\n".join(
        part for part in (completed.stdout, completed.stderr) if part
    )
    truncated = len(output.encode("utf-8")) > policy.output_bytes
    if truncated:
        encoded = output.encode("utf-8")[-policy.output_bytes :]
        output = encoded.decode("utf-8", errors="replace")
    worker_result = _result_from_output(output)
    if worker_result is None:
        code = (
            "[SANDBOX_OUTPUT_LIMIT]"
            if truncated
            else "[SANDBOX_PROCESS_FAILED]"
        )
    else:
        code = str(worker_result.get("code", "[SANDBOX_PROCESS_FAILED]"))
        if completed.returncode != 0 and code == "[PASS]":
            code = "[SANDBOX_PROCESS_FAILED]"
    return {
        "code": code,
        "mode": mode,
        "limits": asdict(policy),
        "environment_policy": "minimal-no-secrets-no-proxies",
        "backend": backend,
        "static": static_report,
        "dynamic": {
            "returncode": completed.returncode,
            "output": output,
            "output_truncated": truncated,
            "result": worker_result,
        },
    }
