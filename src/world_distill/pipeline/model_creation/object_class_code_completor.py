"""
Implement functions in Object Class Template (Python Class)
"""

import argparse
import ast
from copy import deepcopy
import json
import re
from pathlib import Path

from src.utils import (
    load_file,
    print_run_config,
    print_run_summary,
    print_status,
    save_file,
)
from .validator import validate_event_effect_shapes
from .sandbox import scan_generated_source
from . import prompt
from .specification import supports_deferred_power, resolve_specification


def assemble_specification_methods(template_code: str, candidate_code: str) -> str:
    """Insert generated method bodies into the unchanged template declarations."""
    template = ast.parse(template_code)
    owner = next(node for node in template.body if isinstance(node, ast.ClassDef))
    candidate = ast.parse(candidate_code)
    if len(candidate.body) != 1 or not isinstance(candidate.body[0], ast.ClassDef):
        raise ValueError("Method-only completion must contain exactly one class")
    generated = candidate.body[0]
    targets = {node.name: node for node in owner.body if isinstance(node, ast.FunctionDef)
               and any(marker in ast.unparse(node) for marker in
                       ("[NOT_IMPLEMENTED_FUNCTION]", "[NOT_IMPLEMENTED_EVENT]"))}
    methods = {node.name: node for node in generated.body if isinstance(node, ast.FunctionDef)}
    if generated.name != owner.name or set(methods) != set(targets) or len(generated.body) != len(methods):
        raise ValueError("Generated methods must match all and only the template completion targets")
    for name, target in targets.items():
        method = methods[name]
        same_return = ast.dump(method.returns or ast.Constant(None)) == ast.dump(target.returns or ast.Constant(None))
        if ast.dump(method.args) != ast.dump(target.args) or not same_return or method.decorator_list:
            raise ValueError(f"Generated method signature changed: {name}")
        body = method.body[1:] if ast.get_docstring(method, clean=False) is not None else method.body
        if not body:
            raise ValueError(f"Generated method has no body: {name}")
        docstring = target.body[:1] if ast.get_docstring(target, clean=False) is not None else []
        target.body = docstring + deepcopy(body)
    return ast.unparse(template) + "\n"
from src.utils.llm import call_llm_api, extract_python_code_from_answer
from src.utils.rag import get_vectordb, prepend_fixed_references


def check_python_code(
    file_path: str,
    *,
    enforce_security: bool = True,
) -> tuple[str, list[str]]:
    """Check syntax, compilation, effect structure, and generated-code safety."""
    source = Path(file_path).read_text(encoding="utf-8")
    errors: list[str] = []
    try:
        ast.parse(source)
    except SyntaxError as error:
        errors.append(f"SyntaxError at line {error.lineno}: {error.msg}")
    if not errors:
        errors.extend(validate_event_effect_shapes(source, label=file_path))
    try:
        compile(source, file_path, "exec")
    except SyntaxError as error:
        errors.append(f"Compilation error: {error}")
    if enforce_security and not errors:
        security = scan_generated_source(file_path)
        errors.extend(
            f"{item['code']} line {item['line']}: {item['message']}"
            for item in security["errors"]
        )
    return "[PYTHON_CODE_CHECK_FAILED]" if errors else "[PASS]", errors


def apply_template_declarations(template_code: str, candidate_code: str) -> tuple[str, list[str]]:
    """Assemble immutable capability data from the template, outside LLM control."""
    template = ast.parse(template_code)
    candidate = ast.parse(candidate_code)
    owner = next(node for node in template.body if isinstance(node, ast.ClassDef))
    implementation = next(node for node in candidate.body if isinstance(node, ast.ClassDef) and node.name == owner.name)
    names = {"PROCESS"}
    def declaration_name(node):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            return node.targets[0].id
        return None
    expected = {declaration_name(node): node for node in owner.body if declaration_name(node) in names}
    actual = {declaration_name(node): node for node in implementation.body if declaration_name(node) in names}
    changed = [name for name in sorted(set(expected) | set(actual)) if name not in expected or name not in actual or ast.dump(expected[name]) != ast.dump(actual[name])]
    if not changed:
        return candidate_code, []
    implementation.body = [node for node in implementation.body if declaration_name(node) not in names]
    offset = int(bool(implementation.body) and isinstance(implementation.body[0], ast.Expr) and isinstance(implementation.body[0].value, ast.Constant) and isinstance(implementation.body[0].value.value, str))
    implementation.body[offset:offset] = [deepcopy(node) for node in expected.values()]
    return ast.unparse(candidate) + "\n", changed


def _get_examples(is_base: bool, name: str = None, template_content: str = None, domain: str = "Home",
                  desc: str = None, use_rag: bool = True,
                  generated_sources: dict[Path, str] | None = None) -> str:
    """Return the examples."""
    del is_base
    example_parts: list[str] = []
    function_names: list[str] = []
    try:
        tree = ast.parse(template_content or "")
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            source = ast.get_source_segment(template_content or "", node) or ""
            if (
                "[NOT_IMPLEMENTED_FUNCTION]" in source
                or "[NOT_IMPLEMENTED_EVENT]" in source
            ):
                function_names.append(node.name)
    except SyntaxError:
        function_names = re.findall(
            r"^\s*def\s+(\w+)\(",
            template_content or "",
            re.MULTILINE,
        )

    if use_rag:
        vectordb = get_vectordb(domain=domain, stage="code", generated_sources=generated_sources)
        query = " ".join(
            part
            for part in (
                name or "",
                desc or "",
                " ".join(function_names),
                "device method event property wrapper implementation",
            )
            if part
        )
        diverse_examples = vectordb.search(
            query, top_k=3, kinds={"document"}, max_chars=12_000,
            min_score=0.20,
        ) + vectordb.search(
            query, top_k=6, kinds={"implementation"}, max_chars=24_000,
            min_score=0.20,
        )
        for example in diverse_examples:
            content = str(example["content"])
            language = "text" if example["type"] == "document" else "python"
            example_parts.append(
                prompt.CODE_RETRIEVED_EXAMPLE_PROMPT.format(
                    name=example["name"], similarity=example["similarity"], path=example["path"],
                    language=language, content=content,
                )
            )
    if not example_parts:
        return prompt.CODE_NO_EXAMPLES_TEXT
    return "\n\n---\n\n".join(example_parts)


def _reserved_power_errors(template_code: str, candidate_code: str) -> list[str]:
    """Reject changes to template property declarations and power scaffolding."""
    try:
        template_tree = ast.parse(template_code)
        candidate_tree = ast.parse(candidate_code)
    except SyntaxError:
        # The normal Python validator reports syntax failures with the useful
        # line/column details; this guard only handles reserved-method drift.
        return []

    def class_methods(tree: ast.Module) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
        """Return methods from the one generated class."""
        class_node = next(
            (item for item in tree.body if isinstance(item, ast.ClassDef)),
            None,
        )
        if class_node is None:
            return {}
        return {
            item.name: item
            for item in class_node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    expected = class_methods(template_tree)
    actual = class_methods(candidate_tree)
    errors: list[str] = []
    def property_declarations(method):
        if method is None:
            return {}
        return {node.targets[0].attr: node for node in ast.walk(method)
                if isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Attribute)
                and isinstance(node.targets[0].value, ast.Name) and node.targets[0].value.id == "self"
                and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
                and node.value.func.id.endswith("Property")}
    expected_properties = property_declarations(expected.get("__init__"))
    actual_properties = property_declarations(actual.get("__init__"))
    for name, declaration in expected_properties.items():
        if name not in actual_properties or ast.dump(declaration, include_attributes=False) != ast.dump(actual_properties[name], include_attributes=False):
            errors.append(f"template property declaration {name} was modified or removed")
    if not supports_deferred_power(template_code):
        return errors
    for name in ("__init__", "get_power", "set_power"):
        template_method = expected.get(name)
        if template_method is None:
            if name in actual:
                errors.append(f"reserved power method {name} must not be added")
            continue
        candidate_method = actual.get(name)
        if candidate_method is None:
            errors.append(f"reserved power method {name} is missing")
        elif ast.dump(template_method, include_attributes=False) != ast.dump(
            candidate_method,
            include_attributes=False,
        ):
            errors.append(f"reserved power method {name} was modified")
    for required in ("_power_managed_properties", "handle_power_switch"):
        if required in template_code and required not in candidate_code:
            errors.append(f"reserved power scaffold {required} was removed")
    return errors


def complete_object_class(args) -> tuple[str | None, dict]:
    """Complete the object class."""
    generation_desc = getattr(args, "desc", "")
    template_path = Path(args.template)
    print_status(f"Loading template file: {template_path.name}", "info")
    template_code = load_file(template_path)
    is_base = bool(
        getattr(args, "is_base", not getattr(args, "base_code", None))
    )
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    implementation_markers = (
        "[NOT_IMPLEMENTED_FUNCTION]",
        "[NOT_IMPLEMENTED_EVENT]",
    )
    if (
        (not is_base or supports_deferred_power(template_code))
        and not any(marker in template_code for marker in implementation_markers)
    ):
        validation_path = output_path if getattr(args, "fix_code", False) and output_path.is_file() else template_path
        reserved_errors: list[str] = []
        if validation_path != template_path:
            reserved_errors = _reserved_power_errors(
                template_code,
                load_file(validation_path),
            )
        if reserved_errors:
            code, errors = "[POWER_TEMPLATE_MUTATION]", reserved_errors
        else:
            code, errors = check_python_code(str(validation_path))
        log_data = {
            "llm_input": None,
            "llm_output": None,
            "validation": {
                "is_valid": code == "[PASS]",
                "errors": errors,
            },
            "deterministic_completion": "no child-local implementation bodies",
            "code": code,
        }
        if code == "[PASS]":
            if validation_path == template_path:
                save_file(output_path, template_code)
            print_status("No child-local bodies require completion.", "success")
            return str(validation_path if validation_path != template_path else output_path), log_data
        return None, log_data
    if getattr(args, "fix_code", False):
        if not output_path.is_file():
            raise FileNotFoundError(
                f"Cannot repair missing implementation: {output_path}"
            )
        current_code = load_file(output_path)
    
    system_prompt = (
        prompt.CODE_REPAIR_SYSTEM_PROMPT
        if getattr(args, "fix_code", False)
        else prompt.CODE_COMPLETION_SYSTEM_PROMPT
    )
    
    examples = _get_examples(
        is_base=is_base,
        name=getattr(args, "name", None),
        template_content=template_code,
        domain=getattr(args, "domain", None) or "Home",
        desc=generation_desc,
        use_rag=getattr(args, "use_rag", True),
        generated_sources=getattr(args, "generated_sources", None),
    )
    
    if getattr(args, "fix_code", False):
        print_status(f"Fixing existing code at: {output_path}", "info")
        previous = getattr(args, "log_data", None)
        if isinstance(previous, list):
            previous = previous[-1] if previous else {}
        if not isinstance(previous, dict):
            previous = {}
        validation = previous.get("validation", {})
        errors = (
            (
                validation.get("errors")
                or validation.get("error_output")
                or validation.get("analysis")
            )
            if isinstance(validation, dict)
            else None
        ) or prompt.CODE_NO_ERROR_TEXT
    
    if not is_base:
        base_path = Path(getattr(args, "base_code"))
        print_status(f"Loading base code file: {base_path.name}", "info")
        base_code = load_file(base_path)
    
    if is_base:
        if getattr(args, "fix_code", False):
            user_prompt = prompt.CODE_FIX_BASE_USER_PROMPT.format(name=args.name,
                                                                   domain=args.domain,
                                                                   desc=generation_desc,
                                                                   current_code=current_code,
                                                                   errors=errors,
                                                                   template_code=template_code,
                                                                   reference_knowledge=examples)
        else:
            user_prompt = prompt.CODE_COMPLETION_BASE_USER_PROMPT.format(name=args.name,
                                                                          domain=args.domain,
                                                                          desc=generation_desc,
                                                                          template_code=template_code,
                                                                          reference_knowledge=examples)
    else:
        if getattr(args, "fix_code", False):
            user_prompt = prompt.CODE_FIX_INHERIT_USER_PROMPT.format(name=args.name,
                                                                      domain=args.domain,
                                                                      desc=generation_desc,
                                                                      base_code=base_code,
                                                                      current_code=current_code,
                                                                      errors=errors,
                                                                      template_code=template_code,
                                                                      reference_knowledge=examples)
        else:
            user_prompt = prompt.CODE_COMPLETION_INHERIT_USER_PROMPT.format(name=args.name,
                                                                             domain=args.domain,
                                                                             desc=generation_desc,
                                                                             base_code=base_code,
                                                                             template_code=template_code,
                                                                             reference_knowledge=examples)
    
    specification_only = getattr(args, "implementation_from_specification_only", False)
    if specification_only:
        specification, _ = resolve_specification(template_path.parent / f"{args.name}.json")
        owner = next(node for node in ast.parse(template_code).body if isinstance(node, ast.ClassDef))
        signatures = [ast.unparse(node).splitlines()[0] for node in owner.body
                      if isinstance(node, ast.FunctionDef)
                      and any(marker in ast.unparse(node) for marker in implementation_markers)]
        previous_logs = getattr(args, "log_data", None) or []
        user_prompt = prompt.CODE_SPECIFICATION_METHODS_USER_PROMPT.format(
            name=args.name, specification=json.dumps(specification, ensure_ascii=False, indent=2),
            signatures="\n".join(signatures),
            feedback=json.dumps(previous_logs[-1].get("validation", {}) if previous_logs else {}, ensure_ascii=False),
        )
        system_prompt = prompt.CODE_SPECIFICATION_METHODS_SYSTEM_PROMPT

    user_prompt, cache_prefix = prepend_fixed_references(
        user_prompt, domain=args.domain, stage="code",
        use_rag=getattr(args, "use_rag", True),
    )
    code, response = call_llm_api(
        system_prompt,
        user_prompt,
        model_scenario=getattr(args, "model_scenario", "code"),
        model=getattr(args, "model", None),
        cache_prefix=cache_prefix,
    )
    
    log_data = {
        "llm_input": {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "cache_prefix_chars": len(cache_prefix),
        },
        "llm_output": response,
        "validation": {},
        "code": ""
    }
    
    if code != "[PASS]":
        print_status("Failed to get a response from LLM.", "error")
        log_data["code"] = code
        return None, log_data
    
    code, python_content = extract_python_code_from_answer(response["answer"])
    
    if code != "[PASS]":
        print_status("Failed to extract Python code from LLM response.", "error")
        print_status(f"LLM response: {response['answer']}", "warning")
        log_data["code"] = code
        return None, log_data

    try:
        if specification_only:
            python_content = assemble_specification_methods(template_code, python_content)
            log_data["completion_assembly"] = "specification_methods_into_original_template"
        python_content, assembled = apply_template_declarations(template_code, python_content)
    except (SyntaxError, StopIteration, ValueError) as exc:
        log_data["code"] = "[PYTHON_CODE_INVALID]"
        log_data["validation"] = {"is_valid": False, "errors": [f"candidate class cannot be assembled: {exc}"]}
        return None, log_data
    log_data["template_declarations_assembled"] = assembled
    
    candidate_path = output_path.with_name(
        f".{output_path.name}.candidate"
    )
    save_file(candidate_path, python_content)
    code = "[PYTHON_CODE_INVALID]"
    errors = ["validation did not complete"]
    try:
        reserved_errors = _reserved_power_errors(template_code, python_content)
        if reserved_errors:
            code, errors = "[POWER_TEMPLATE_MUTATION]", reserved_errors
        else:
            code, errors = check_python_code(str(candidate_path))
    finally:
        if code != "[PASS]" and candidate_path.exists():
            if getattr(args, "fix_code", False):
                candidate_path.unlink()
            else:
                # The next bounded attempt is a repair, so retain the rejected
                # first-pass implementation together with its exact validator
                # errors. A failed repair still leaves the previous candidate
                # untouched until a replacement passes validation.
                candidate_path.replace(output_path)
    is_valid = (code == "[PASS]")
    log_data["validation"] = {
        "is_valid": is_valid,
        "errors": errors
    }
    
    if is_valid:
        candidate_path.replace(output_path)
        print_status("Python code validation passed!", "success")
        log_data["code"] = code
        return str(output_path), log_data
    else:
        print_status(f"Python code validation failed: {errors}", "error")
        log_data["code"] = code
        return None, log_data


def main(args):
    """Run the command-line entry point."""
    args.fix_code = bool(
        getattr(args, "log_data", None)
        and Path(args.output).is_file()
    )
    base_code = getattr(args, "base_code", None)
    args.is_base = not base_code

    print_run_config(
        "Object class completion",
        (
            ("Mode", "repair" if args.fix_code else "complete"),
            ("Template", args.template),
            ("Base", base_code or "-"),
            ("Model", args.model or "configured default"),
            ("Output", args.output),
        ),
    )
    output_path, log_data = complete_object_class(args)
    if not output_path:
        print_run_summary(
            "Object class completion",
            log_data["code"],
            (("Output", "-"),),
        )
        return None, log_data

    print_run_summary(
        "Object class completion",
        "PASS",
        (("Output", output_path),),
    )
    return str(output_path), log_data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Object Class Completor")
    parser.add_argument("--template", type=str, required=True, help="Path to the object class template file")
    parser.add_argument("--output", type=str, required=True, help="Path to the output file")
    parser.add_argument("--base_code", type=str, help="Path to the base code file for inheritance")
    parser.add_argument("--name", type=str, help="Name of the object class")
    parser.add_argument("--domain", type=str, help="Domain of the object class")
    parser.add_argument("--desc", type=str, help="Description of the object class")
    parser.add_argument("--no_rag", action="store_false", dest="use_rag", help="Disable RAG for example retrieval.")
    parser.add_argument("--model_scenario", default="code", help="LLM config scenario used for code completion.")
    parser.add_argument("--model", default=None, help="Optional model override; otherwise use the selected LLM config.")
    
    args = parser.parse_args()
    output, _ = main(args)
    raise SystemExit(0 if output else 1)
