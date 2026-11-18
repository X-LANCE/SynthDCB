"""
Build environment_metas.json from environment object class source files.

Usage:
python -m src.world_distill.pipeline.model_creation.environment_loader \
  --environment_path simulator/devices/Home \
  --output simulator/devices/Home/environment_metas.json
"""

import argparse
import ast
import re
from pathlib import Path
from typing import Any

from src.utils import DEVICES_DIR, print_run_config, print_run_summary, write_json


def parse_docstring(docstring: str | None) -> dict[str, Any]:
    """Return the docstring."""
    if not docstring:
        return {"description": "", "args": {}, "returns": {}, "error_codes": {}}

    result: dict[str, Any] = {
        "description": "",
        "args": {},
        "returns": {},
        "error_codes": {},
    }
    lines = docstring.strip().split("\n")
    current_section = "description"
    current_arg = None
    description_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("Args:"):
            current_section = "args"
            current_arg = None
            continue
        if stripped.startswith("Returns:"):
            current_section = "returns"
            current_arg = None
            continue
        if stripped.startswith("Error Codes:"):
            current_section = "error_codes"
            current_arg = None
            continue

        if current_section == "description":
            if stripped:
                description_lines.append(stripped)
        elif current_section == "args":
            arg_match = re.match(r"^-\s*(\w+):\s*(.+)$", stripped)
            if arg_match:
                arg_name = arg_match.group(1)
                result["args"][arg_name] = {"description": arg_match.group(2)}
                current_arg = arg_name
            elif current_arg and stripped and not stripped.startswith("(no arguments"):
                result["args"][current_arg]["description"] += " " + stripped
        elif current_section == "returns":
            ret_match = re.match(r"^-\s*(.+?):\s*(.+)$", stripped)
            if ret_match:
                result["returns"][ret_match.group(1)] = ret_match.group(2)
        elif current_section == "error_codes":
            err_match = re.match(r"^-\s*(\w+):\s*(.+)$", stripped)
            if err_match:
                result["error_codes"][err_match.group(1)] = err_match.group(2)

    result["description"] = " ".join(description_lines)
    return result


def extract_event_description(node: ast.FunctionDef) -> str:
    """Return the event description."""
    docstring = ast.get_docstring(node) or ""
    first_paragraph = docstring.strip().split("\n\n", 1)[0]
    return " ".join(line.strip() for line in first_paragraph.splitlines() if line.strip())


def extract_property_info(node: ast.Assign | ast.AnnAssign) -> dict[str, Any] | None:
    """Return the property info."""
    if not isinstance(node, ast.Assign) or not node.targets:
        return None

    target = node.targets[0]
    value = node.value
    if not isinstance(target, ast.Attribute):
        return None
    if not isinstance(target.value, ast.Name) or target.value.id != "self":
        return None
    if not isinstance(value, ast.Call):
        return None

    func = value.func
    if isinstance(func, ast.Name):
        property_type = func.id
    elif isinstance(func, ast.Attribute):
        property_type = func.attr
    else:
        return None
    if not property_type.endswith("Property"):
        return None

    prop_info: dict[str, Any] = {
        "name": target.attr,
        "property_class": property_type,
        "kwargs": {},
    }
    for keyword in value.keywords:
        if keyword.arg:
            try:
                prop_info["kwargs"][keyword.arg] = ast.literal_eval(keyword.value)
            except (ValueError, TypeError):
                prop_info["kwargs"][keyword.arg] = ast.unparse(keyword.value)
    return prop_info


def extract_function_info(node: ast.FunctionDef) -> dict[str, Any]:
    """Return the function info."""
    parsed_doc = parse_docstring(ast.get_docstring(node))
    args_info = {}
    defaults_offset = len(node.args.args) - len(node.args.defaults)

    for index, arg in enumerate(node.args.args):
        if arg.arg == "self":
            continue

        arg_info: dict[str, Any] = {"name": arg.arg}
        if arg.annotation:
            arg_info["type"] = ast.unparse(arg.annotation)

        default_index = index - defaults_offset
        if 0 <= default_index < len(node.args.defaults):
            try:
                arg_info["default"] = ast.literal_eval(node.args.defaults[default_index])
            except (ValueError, TypeError):
                arg_info["default"] = ast.unparse(node.args.defaults[default_index])

        if arg.arg in parsed_doc["args"]:
            arg_info["description"] = parsed_doc["args"][arg.arg].get("description", "")
        args_info[arg.arg] = arg_info

    return {
        "name": node.name,
        "description": parsed_doc["description"],
        "arguments": args_info,
        "returns": {
            "type": ast.unparse(node.returns) if node.returns else None,
            "details": parsed_doc["returns"],
        },
        "error_codes": parsed_doc["error_codes"],
    }


def extract_class_meta_from_docstring(docstring: str | None) -> dict[str, Any]:
    """Return the class meta from docstring."""
    meta = {"name": "", "description": "", "version": "", "base": ""}
    if not docstring:
        return meta

    lines = docstring.strip().split("\n")
    if lines:
        meta["name"] = lines[0].strip()

    for line in lines[1:]:
        stripped = line.strip()
        if stripped.startswith("Description:"):
            meta["description"] = stripped[len("Description:") :].strip()
        elif stripped.startswith("Version:"):
            meta["version"] = stripped[len("Version:") :].strip()
        elif stripped.startswith("Base:"):
            base_value = stripped[len("Base:") :].strip()
            if base_value != "-":
                meta["base"] = base_value
    return meta


def parse_object_class(file_path: Path, source_code: str) -> list[dict[str, Any]]:
    """Return the object class."""
    tree = ast.parse(source_code, filename=str(file_path))

    classes = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        class_info: dict[str, Any] = {
            "class_name": node.name,
            "file_path": str(file_path),
            "meta": extract_class_meta_from_docstring(ast.get_docstring(node)),
            "properties": {},
            "functions": {},
            "events": {},
        }
        if not class_info["meta"]["name"]:
            class_info["meta"]["name"] = node.name
        from .specification import active_section, resolve_specification
        specification, _ = resolve_specification(file_path.with_suffix(".json"))
        event_specs = active_section(specification, "events")

        base_classes = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_classes.append(ast.unparse(base))
        if base_classes and base_classes != ["object"]:
            class_info["meta"]["base"] = base_classes

        for item in node.body:
            if not isinstance(item, ast.FunctionDef):
                continue
            if item.name == "__init__":
                for stmt in item.body:
                    if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
                        prop_info = extract_property_info(stmt)
                        if prop_info:
                            class_info["properties"][prop_info["name"]] = prop_info
            elif item.name.startswith("_on_"):
                class_info["events"][item.name[4:]] = {
                    "description": extract_event_description(item),
                    "effect_properties": event_specs.get(item.name[4:], {}).get("effect_properties", []),
                }
            elif not item.name.startswith("_"):
                class_info["functions"][item.name] = extract_function_info(item)

        classes.append(class_info)

    return classes


def scan_directory(directory: Path) -> list[Path]:
    """Return the directory."""
    python_files = []
    support_files = {"DomainRuntime.py", "EventRuntime.py"}
    for path in directory.rglob("*.py"):
        if "__pycache__" in str(path):
            continue
        if path.name in support_files:
            continue
        if "_test" in path.name or "test_" in path.name:
            continue
        if ".template" in path.name:
            continue
        python_files.append(path)
    return python_files


def get_qualified_class_key(file_path: Path, env_root: Path, class_name: str | None = None) -> str:
    """Return the qualified class key."""
    try:
        rel = file_path.relative_to(env_root)
    except ValueError:
        rel = file_path
    key_parts = list(rel.parent.parts)
    if class_name and (not key_parts or key_parts[-1] != class_name):
        key_parts.append(class_name)
    elif not key_parts:
        key_parts.append(class_name or rel.stem)
    return ".".join(key_parts)


def environment_loader(environment_path: Path, output_path: Path) -> tuple[str, dict[str, Any]]:
    """Load and validate an environment package."""
    log_data: dict[str, Any] = {
        "code": "",
        "scanned_files": [],
        "extracted_classes": [],
        "errors": [],
    }

    environment_path = Path(environment_path)
    output_path = Path(output_path)
    if not environment_path.is_dir():
        raise NotADirectoryError(f"environment path is not a directory: {environment_path}")

    python_files = scan_directory(environment_path)
    log_data["scanned_files"] = [str(path) for path in python_files]
    metas = {}

    for py_file in python_files:
        source_code = py_file.read_text(encoding="utf-8")
        for class_info in parse_object_class(py_file, source_code):
            qualified_key = get_qualified_class_key(
                py_file,
                environment_path,
                class_info["class_name"],
            )
            class_info["file_path"] = py_file.relative_to(environment_path).as_posix()
            metas[qualified_key] = class_info
            log_data["extracted_classes"].append(qualified_key)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(output_path, metas)
    log_data["code"] = "[PASS]"
    return str(output_path), log_data


def write_model_summary(domain: str, domain_path: Path, contract=None) -> Path:
    """Write descriptive counts from all implementations, including effective inheritance."""
    from datetime import datetime, timezone
    from uuid import uuid4
    from src.contracts import ContractPackage
    from src.object_model import BaseProperty
    from src.runtime.execution import ToolCatalogBuilder
    from src.runtime.loading.domains import discover_model_files
    from src.runtime.loading.modules import load_module_from_tree
    from .specification import resolve_specification

    root = Path(domain_path).resolve()
    files = discover_model_files(root, domain)
    types = {}
    property_count = tool_count = 0
    builder = ToolCatalogBuilder(contract or ContractPackage())
    namespace = f"model_summary_{uuid4().hex}"
    for class_id, path in files.items():
        module = load_module_from_tree(path, tree_root=root, namespace=namespace)
        model = getattr(module, path.stem)
        if not isinstance(model, type) or model.__module__ != module.__name__:
            raise ValueError(f"model class missing from {path}")
        instance = model()
        types[class_id] = model
        disabled = set(getattr(instance, "_disabled", {}).get("properties", []))
        property_count += sum(
            isinstance(value, BaseProperty) and name not in disabled
            for name, value in vars(instance).items()
        )
        specification, _ = resolve_specification(path.with_suffix(".json"))
        tool_count += len(builder.describe_device(instance, specification))
    model_types = set(types.values())
    derived = sum(
        any(parent in model_types for parent in model.__mro__[1:])
        for model in model_types
    )
    payload = {
        "create_date": datetime.now(timezone.utc).isoformat(),
        "domain": domain,
        "base_class_count": len(types) - derived,
        "derived_class_count": derived,
        "property_count": property_count,
        "tool_count": tool_count,
        "classes": {key: str(path.relative_to(root)) for key, path in files.items()},
    }
    output = root / "meta.json"
    write_json(output, payload)
    return output


def main(args: argparse.Namespace) -> tuple[str, dict[str, Any]]:
    """Run the command-line entry point."""
    print_run_config(
        "Environment metadata",
        (
            ("Environment", args.environment_path),
            ("Output", args.output),
        ),
    )
    output_path, log_data = environment_loader(args.environment_path, args.output)
    print_run_summary(
        "Environment metadata",
        "PASS",
        (
            ("Scanned files", len(log_data["scanned_files"])),
            ("Extracted classes", len(log_data["extracted_classes"])),
            ("Output", output_path),
        ),
    )
    return output_path, log_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Environment metadata builder for object classes")
    parser.add_argument("--environment_path", type=str, help="Root environment directory")
    parser.add_argument("--output", type=str, help="Output environment_metas.json path")
    parsed_args = parser.parse_args()
    parsed_args.environment_path = (
        Path(parsed_args.environment_path)
        if parsed_args.environment_path
        else DEVICES_DIR / "Home"
    )
    parsed_args.output = Path(parsed_args.output) if parsed_args.output else parsed_args.environment_path / "environment_metas.json"
    main(parsed_args)
