"""
Verify Object Class Implementation (Python Class) by generating and running test cases.
"""

import argparse
import ast
import os
from pathlib import Path

from src.utils import (
    config,
    format_json,
    load_file,
    load_json,
    now_iso,
    print_run_config,
    print_run_summary,
    print_status,
    save_file,
)
from . import prompt
from src.utils.llm import call_llm_api, extract_python_code_from_answer
from src.utils.rag import prepend_fixed_references
from src.world_distill.pipeline.model_creation.sandbox import run_generated_code
from src.world_distill.pipeline.model_creation.specification import (
    resolve_specification,
)
from .validator import validate_effects, validate_model_artifacts


def convert_python_path_to_module(file_path: str) -> str:
    """
    Converts a python file path to a module path.

    Args:
        file_path: Path to the python file.

    Returns:
        module_path: Dotted module path.
    """

    path_obj = Path(file_path)
    if path_obj.is_absolute():
        rel_path = str(path_obj.relative_to(config.PROJECT_ROOT))
    else:
        rel_path = str(path_obj)

    module_path = rel_path.replace(os.sep, '.').replace('.py', '')
    return module_path


def _get_examples(template_content: str = None,
                  name: str = None,
                  domain: str = "Home",
                  use_rag: bool = True,
                  generated_sources: dict[Path, str] | None = None) -> str:
    """
    Get reference examples from vector database using semantic search.
    """
    example_parts = []
    results = []
    
    if use_rag:
        from src.utils.rag import get_vectordb
        query_parts = []
        if name:
            query_parts.append(name)
        if template_content:
            try:
                tree = ast.parse(template_content)
            except SyntaxError:
                tree = None
            if tree is not None:
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        query_parts.append(node.name)
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        query_parts.append(node.name)
                        docstring = ast.get_docstring(node)
                        if docstring:
                            query_parts.append(docstring[:240])
        
        query_parts.append("python test")
        query = " ".join(query_parts)
        
        vectordb = get_vectordb(domain=domain, stage="test", generated_sources=generated_sources)
        results = vectordb.search(
            query, top_k=3, kinds={"document"}, max_chars=12_000,
            min_score=0.25,
        ) + vectordb.search(
            query, top_k=6, kinds={"test"}, max_chars=12_000,
            min_score=0.25,
        )
        
        for result in results:
            content = str(result["content"])
            language = "text" if result["type"] == "document" else "python"
            similarity = result["similarity"]
            example_parts.append(
                prompt.CODE_RETRIEVED_EXAMPLE_PROMPT.format(
                    name=result["name"], similarity=similarity, path=result["path"],
                    language=language, content=content,
                )
            )
    if not example_parts:
        return prompt.VERIFIER_NO_EXAMPLES_TEXT
    return "\n\n---\n\n".join(example_parts)


def analyze_error(class_code,
                  test_code,
                  console_output,
                  model_scenario: str = "judge",
                  model: str | None = None,
                  *,
                  return_record: bool = False,
                  specification: str | None = None,
                  cache_prefix: str = ""):
    """Analyze the error."""
    user_prompt = prompt.OBJECT_CLASS_VERIFIER_ANALYZER_USER_PROMPT.format(class_code=class_code,
                                                                            test_code=test_code,
                                                                            console_output=console_output)
    if specification is not None:
        user_prompt = prompt.VERIFIER_ANALYZER_SPECIFICATION_PROMPT.format(specification=specification) + user_prompt
    if cache_prefix:
        user_prompt = cache_prefix + "\n\n" + user_prompt
    
    status, response_dict = call_llm_api(system_prompt=prompt.OBJECT_CLASS_VERIFIER_ANALYZER_SYSTEM_PROMPT,
                                         user_prompt=user_prompt,
                                         model_scenario=model_scenario,
                                         model=model,
                                         cache_prefix=cache_prefix)
    
    record = {
        "role": "verify_failure_analysis",
        "llm_input": {
            "system_prompt": prompt.OBJECT_CLASS_VERIFIER_ANALYZER_SYSTEM_PROMPT,
            "user_prompt": user_prompt,
            "cache_prefix_chars": len(cache_prefix),
        },
        "llm_output": response_dict,
        "code": status,
    }
    if status != "[PASS]":
        print_status(f"Error calling LLM for analysis: {status}", "error")
        result = status
        return (result, record) if return_record else result
    
    answer = response_dict.get("answer", "")
    
    # Extract tag
    if "[TEST_PYTHON_ERROR]" in answer:
        result = "[TEST_PYTHON_ERROR]"
    elif "[IMPLEMENT_PYTHON_ERROR]" in answer:
        result = "[IMPLEMENT_PYTHON_ERROR]"
    elif "[PASS]" in answer:
        result = "[PASS]"
    else:
        result = answer
    return (result, record) if return_record else result


def check_generated_unittest_source(test_code: str) -> list[str]:
    """Check the generated unittest source."""
    errors = []
    try:
        tree = ast.parse(test_code)
    except SyntaxError as exc:
        return [f"SyntaxError at line {exc.lineno}: {exc.msg}"]

    test_case_classes = []
    test_methods = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        inherits_test_case = any(
            (
                isinstance(base, ast.Attribute)
                and base.attr == "TestCase"
            )
            or (
                isinstance(base, ast.Name)
                and base.id == "TestCase"
            )
            for base in node.bases
        )
        if inherits_test_case:
            test_case_classes.append(node.name)
            test_methods.extend(
                item.name for item in node.body
                if isinstance(item, ast.FunctionDef) and item.name.startswith("test_")
            )

    if not test_case_classes:
        errors.append("No unittest.TestCase subclass found.")
    if not test_methods:
        errors.append("No test_* methods found in unittest.TestCase classes.")
    return errors


def classify_execution_failure(console_output: str,
                               class_file_name: str,
                               test_file_name: str) -> str | None:
    """Classify the execution failure."""
    if "NO TESTS RAN" in console_output or "Ran 0 tests" in console_output:
        return "[TEST_PYTHON_ERROR]"
    if "[NOT_IMPLEMENTED_FUNCTION]" in console_output or "[NOT_IMPLEMENTED_EVENT]" in console_output:
        return "[IMPLEMENT_PYTHON_ERROR]"
    if "Traceback" in console_output and class_file_name in console_output:
        return "[IMPLEMENT_PYTHON_ERROR]"
    if "AssertionError" in console_output:
        return None
    if "Traceback" in console_output and test_file_name in console_output and class_file_name not in console_output:
        return "[TEST_PYTHON_ERROR]"
    return None


def verify_object_class(args) -> tuple[str | None, dict]:
    """Verify the object class."""
    py_file = Path(args.py).resolve()
    out_file = Path(args.output).resolve()
    
    if not py_file.is_file():
        raise FileNotFoundError(f"object class file not found: {py_file}")
    
    print_status(f"Loading target file: {py_file.name}", "info")
    code_content = load_file(py_file)
    
    module_name = py_file.stem
    
    # Simple extraction of class name
    class_name = module_name  # Default assumption
    for line in code_content.splitlines():
        if line.strip().startswith("class "):
            parts = line.strip().split()
            if len(parts) > 1:
                class_name = parts[1].split('(')[0].split(':')[0]
                break
    
    # Get examples
    domain = getattr(args, "domain", "Home") or "Home"
    examples = _get_examples(
        template_content=code_content,
        name=class_name,
        domain=domain,
        use_rag=getattr(args, "use_rag", True),
        generated_sources=getattr(args, "generated_sources", None),
    )
    specification_path_value = getattr(args, "specification", None)
    specification_path = (
        Path(specification_path_value).resolve()
        if specification_path_value
        else py_file.with_suffix(".json")
    )
    specification_chain = ()
    if specification_path.is_file():
        raw_specification = load_json(specification_path)
        resolved_specification, specification_chain = resolve_specification(specification_path)
        specification_name = str(next(iter(raw_specification)))
        specification = format_json(
            {specification_name: resolved_specification},
            ensure_ascii=False,
            indent=2,
        )
    else:
        specification = prompt.VERIFIER_NO_SPECIFICATION_TEXT
    
    specification_only = getattr(args, "test_from_specification_only", False)
    if specification_only and not specification_path.is_file():
        raise ValueError("Specification-only test generation requires a specification file")
    user_prompt = prompt.OBJECT_CLASS_VERIFIER_USER_PROMPT.format(
        specification=specification,
        code=prompt.VERIFIER_SPECIFICATION_ONLY_TEXT if specification_only else code_content,
        module_name=module_name,
        class_name=class_name,
        reference_knowledge=examples,
    )
    if len(specification_chain) > 1 and not specification_only:
        user_prompt += prompt.VERIFIER_PARENT_IMPLEMENTATIONS_PROMPT.format(
            code="\n\n".join(
                f"```python\n{path.with_suffix('.py').read_text(encoding='utf-8')}\n```"
                for path in specification_chain[:-1]
            )
        )
    previous_logs = getattr(args, "log_data", None)
    if previous_logs:
        previous = previous_logs[-1]
        user_prompt += prompt.VERIFIER_REPAIR_CONTEXT_PROMPT.format(
            validation=format_json(previous.get("validation", {}), ensure_ascii=False)
        )
    
    system_prompt = prompt.OBJECT_CLASS_VERIFIER_SYSTEM_PROMPT
    
    model = getattr(args, "model", None)
    user_prompt, cache_prefix = prepend_fixed_references(
        user_prompt, domain=domain, stage="test",
        use_rag=getattr(args, "use_rag", True),
    )
    code, response = call_llm_api(
        system_prompt,
        user_prompt,
        model_scenario=getattr(args, "model_scenario", "code"),
        model=model,
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
        print_status(f"LLM call failed: {code}", "error")
        log_data["code"] = code
        return None, log_data
    
    answer_content = response.get("answer", "")
    code, python_content = extract_python_code_from_answer(answer_content)
    
    if code != "[PASS]":
        print_status("Failed to generate test code.", "error")
        log_data["code"] = code
        return None, log_data
    
    # add prefix to python content
    python_content = f"""# This file is auto-generated.
# Test command
#     python -m {convert_python_path_to_module(str(out_file))}
# Generated at
#     {now_iso()}

{python_content}
"""
    structure_errors = check_generated_unittest_source(python_content)
    if structure_errors:
        print_status(f"Generated test structure is invalid: {structure_errors}", "error")
        log_data["code"] = "[TEST_PYTHON_ERROR]"
        log_data["validation"] = {
            "errors": structure_errors,
            "analysis": "[TEST_PYTHON_ERROR]"
        }
        return None, log_data
    
    # Ensure output directory exists
    out_file.parent.mkdir(parents=True, exist_ok=True)
    
    save_file(out_file, python_content)
    
    # Execute both generated artifacts only inside the candidate sandbox.
    sandbox_report = run_generated_code(
        candidate_root=getattr(args, "candidate_root", py_file.parent),
        source_paths=[py_file, out_file],
        mode="unittest",
        test_path=out_file,
    )
    code = sandbox_report["code"]
    dynamic = sandbox_report.get("dynamic") or {}
    worker_result = dynamic.get("result") or {}
    output = str(worker_result.get("output") or dynamic.get("output") or "")
    error = str(worker_result.get("error") or "")
    log_data["validation"]["sandbox"] = sandbox_report
    
    if code == "[PASS]":
        # The sandbox just ran the tests; reuse that result and check the
        # remaining per-class gates before publishing this class as a reference.
        candidate_root = Path(getattr(args, "candidate_root", py_file.parent))
        acceptance = validate_model_artifacts(
            candidate_root, {class_name: {}}, run_tests=False,
        )
        catalog = getattr(args, "property_catalog", None)
        if catalog:
            _, chain = resolve_specification(specification_path)
            effects = validate_effects(
                candidate_root, catalog,
                implementation_paths=[path.with_suffix(".py") for path in chain],
            )
            acceptance["effect_review"] = effects
            acceptance["errors"].extend(effects["errors"])
            if effects["code"] != "[PASS]":
                acceptance["code"] = effects["code"]
        log_data["validation"]["reference_acceptance"] = acceptance
        if acceptance["code"] != "[PASS]":
            log_data["code"] = "[IMPLEMENT_PYTHON_ERROR]"
            log_data["validation"]["errors"] = acceptance["errors"]
            return None, log_data
        print_status("Generated tests passed.", "success")
        log_data["code"] = "[PASS]"
        return str(out_file), log_data
    else:
        # Analyze error
        print_status("Test failed. Analyzing error...", "warning")
        static_errors = (sandbox_report.get("static") or {}).get("errors", [])
        implementation_static_error = any(
            Path(item.get("path", "")).resolve() == py_file
            for item in static_errors
        )
        if static_errors:
            analysis = (
                "[IMPLEMENT_PYTHON_ERROR]"
                if implementation_static_error
                else "[TEST_PYTHON_ERROR]"
            )
        else:
            analysis = classify_execution_failure(
                output or error,
                py_file.name,
                out_file.name,
            )
        if analysis is None:
            analysis, analysis_record = analyze_error(
                code_content,
                python_content,
                output or error,
                model_scenario=getattr(args, "judge_model_scenario", "judge"),
                model=model,
                return_record=True,
                specification=specification,
                cache_prefix=cache_prefix,
            )
            log_data["auxiliary_llm_calls"] = [analysis_record]
        if analysis == "[PASS]":
            analysis = "[TEST_PYTHON_ERROR]"
        print_status(f"Analysis Result: {analysis}", "info")
        log_data["code"] = analysis
        log_data["validation"] = {
            "error_output": output or error or format_json(static_errors),
            "analysis": analysis,
            "analysis_explanations": [
                record.get("llm_output", {}).get("answer", "")
                for record in log_data.get("auxiliary_llm_calls", [])
            ],
            "sandbox": sandbox_report,
        }
        return None, log_data


def main(args):
    """Run the command-line entry point."""
    print_run_config(
        "Object class verification",
        (
            ("Implementation", args.py),
            ("Domain", args.domain),
            ("Model", args.model or "configured default"),
            ("Output", args.output),
        ),
    )
    output_path, log_data = verify_object_class(args)
    if not output_path:
        print_run_summary(
            "Object class verification",
            log_data["code"],
            (("Output", "-"),),
        )
        return None, log_data

    print_run_summary(
        "Object class verification",
        "PASS",
        (("Output", output_path),),
    )
    return str(output_path), log_data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Verify Object Class implementation.")
    parser.add_argument("--py", required=True, help="Path to the object class python file.")
    parser.add_argument("--output", required=True, help="Path to the output test file.")
    parser.add_argument("--no_rag", action="store_false", dest="use_rag", help="Disable RAG for example retrieval.")
    parser.add_argument("--domain", default="Home", help="Domain used to select retrieval references.")
    parser.add_argument("--specification", default=None, help="Authoritative ObjectClass JSON specification.")
    parser.add_argument("--model_scenario", default="code", help="LLM config scenario used for test generation.")
    parser.add_argument("--judge_model_scenario", default="judge", help="LLM config scenario used for failure analysis.")
    parser.add_argument("--model", default=None, help="Optional model override for both verifier calls.")
    
    args = parser.parse_args()
    output, _ = main(args)
    raise SystemExit(0 if output else 1)
