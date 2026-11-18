"""
Create Object Class Meta (JSON Specification) with LLM.
Either from scratch or based on Object Base Class Meta.
"""

import argparse
import json
import time
from pathlib import Path

from . import prompt
from src.utils import (
    config,
    format_json,
    load_file,
    load_json,
    parse_json,
    print_run_config,
    print_run_summary,
    print_status,
    write_json,
)
from src.contracts.capabilities import validate_capability_spec
from src.contracts.schema import DEVICE_SPEC_SCHEMA
from src.world_distill.pipeline.model_creation.validator import (
    validate_json_schema,
    validate_required_contract,
)
from src.world_distill.pipeline.model_creation.specification import (
    normalize_power_contract,
    resolve_specification,
    resolve_specification_delta,
)
from src.utils.llm import call_llm_api, extract_json_from_answer
from src.utils.rag import get_vectordb, prepend_fixed_references


def _generation_json_reference(content: object) -> str:
    """Serialize the supplied JSON reference without changing its declarations."""

    if isinstance(content, dict):
        payload = content
    elif isinstance(content, str):
        try:
            payload = parse_json(content)
        except json.JSONDecodeError:
            return prompt.META_INVALID_REFERENCE_TEXT
    else:
        return prompt.META_INVALID_REFERENCE_TEXT
    return format_json(
        payload,
        ensure_ascii=False,
        indent=2,
    )


def _generation_candidate_reference(content: object) -> str:
    """Keep the supplied candidate as repair context."""

    if isinstance(content, str):
        code, payload = extract_json_from_answer(content)
        if code == "[PASS]":
            return _generation_json_reference(payload)
        return content
    return _generation_json_reference(content)


def _property_catalog_context(
    domain: str,
    property_catalog: str | Path | None,
) -> str:
    """Return the property catalog context."""
    path = (
        Path(property_catalog)
        if property_catalog
        else (
            config.DOMAIN_CONFIG_DIR
            / domain
            / f"{domain.lower()}.property-specs.json"
        )
    )
    if not path.is_file():
        return prompt.META_NO_PROPERTY_CATALOG_TEXT
    payload = load_json(path)
    compact = {
        "domain_type": payload.get("domain_type"),
        "space_types": payload.get("space_types", {}),
        "space_properties": payload.get("space_properties", {}),
    }
    return prompt.META_PROPERTY_CATALOG_CONTENT_PROMPT.format(
        catalog=format_json(compact, ensure_ascii=False, indent=2)
    )


def _get_examples(
    is_base: bool,
    name: str,
    domain: str,
    desc: str,
    use_rag: bool = True,
    property_catalog: str | Path | None = None,
    generated_sources: dict[Path, str] | None = None,
) -> str:
    """
    Retrieve relevant examples and format the prompt for JSON generation.
    """
    del is_base
    knowledge_parts = []
    schema_content = format_json(DEVICE_SPEC_SCHEMA, ensure_ascii=False, indent=2)
    knowledge_parts.append(
        prompt.META_SCHEMA_REFERENCE_PROMPT.format(schema=schema_content)
    )
    knowledge_parts.append(
        prompt.META_PROPERTY_CATALOG_REFERENCE_PROMPT.format(
            catalog=_property_catalog_context(domain, property_catalog)
        )
    )
    # Build query for semantic search
    query_parts = [name] if name else []
    if desc:
        query_parts.append(desc)
    query_parts.append("JSON specification")
    query = " ".join(query_parts)

    results = []
    if use_rag:
        vectordb = get_vectordb(domain=domain, stage="meta", generated_sources=generated_sources)
        results = vectordb.search(
            query, top_k=3, kinds={"document"}, max_chars=12_000,
            min_score=0.20,
        ) + vectordb.search(
            query, top_k=3, kinds={"object_spec"}, max_chars=60_000,
            min_score=0.20,
        )

    print_status(f"Found {len(results)} bounded ObjectClass references via RAG", "info")

    for result in results:
        content = (_generation_json_reference(result["content"])
                   if result["type"] == "object_spec" else result["content"])
        language = "json" if result["type"] == "object_spec" else "text"
        similarity = result["similarity"]
        knowledge_parts.append(
            prompt.META_RETRIEVED_EXAMPLE_PROMPT.format(
                name=result["name"], similarity=similarity, path=result["path"],
                language=language, content=content,
            )
        )

    if use_rag and not results:
        knowledge_parts.append(
            prompt.META_NO_EXAMPLES_TEXT
        )
    return "\n\n---\n\n".join(knowledge_parts)


def review_meta(specification: dict, *, model: str | None, domain_context: str = "", cache_prefix: str = "") -> dict:
    class_name = specification.get("meta", {}).get("name")
    user = format_json({class_name: specification} if class_name else specification, ensure_ascii=False, indent=2)
    if domain_context:
        user += prompt.META_REVIEW_DOMAIN_CONTEXT_PROMPT.format(domain_context=domain_context)
    if cache_prefix:
        user = cache_prefix + "\n\n" + user
    start = time.perf_counter()
    code, response = call_llm_api(
        system_prompt=prompt.META_REVIEW_PROMPT, user_prompt=user,
        model_scenario="judge", model=model, cache_prefix=cache_prefix,
    )
    record = {
        "role": "meta_semantic_review",
        "llm_input": {"system_prompt": prompt.META_REVIEW_PROMPT, "user_prompt": user,
                      "cache_prefix_chars": len(cache_prefix)},
        "llm_output": response, "code": code,
        "elapsed_seconds": time.perf_counter() - start,
    }
    if code != "[PASS]":
        record["errors"] = [f"meta review request failed: {code}"]
        return record
    code, verdict = extract_json_from_answer(response["answer"])
    valid = (
        code == "[PASS]" and isinstance(verdict, dict)
        and set(verdict) == {"approved", "issues"}
        and type(verdict["approved"]) is bool
        and isinstance(verdict["issues"], list)
        and all(isinstance(issue, str) and issue.strip() for issue in verdict["issues"])
        and verdict["approved"] == (not verdict["issues"])
    )
    if not valid:
        record["code"] = "[META_REVIEW_INVALID]"
        record["errors"] = ["meta review returned an invalid verdict"]
        if code == "[PASS]" and isinstance(verdict, dict) and verdict.get("issues"):
            record["errors"].append(
                "Unvalidated reviewer feedback (verdict still rejected): "
                + format_json(verdict["issues"], ensure_ascii=False)
            )
        return record
    record["verdict"] = verdict
    record["errors"] = verdict["issues"]
    record["code"] = "[PASS]" if verdict["approved"] else "[META_REVIEW_REJECTED]"
    return record


def create_object_class_meta(args) -> tuple[dict, dict]:
    """Return the object class meta."""
    generation_desc = getattr(args, "desc", "")
    is_base = not (hasattr(args, "base_json") and args.base_json)
    required_contract = getattr(args, "required_contract", None)
    previous_logs = getattr(args, "log_data", None)
    previous_candidate = ""
    previous_errors: object = ""
    if isinstance(previous_logs, list):
        for record in reversed(previous_logs):
            if not isinstance(record, dict):
                continue
            response = record.get("llm_output")
            if not previous_candidate and isinstance(response, dict):
                answer = response.get("answer")
                if isinstance(answer, str):
                    previous_candidate = answer
            validation = record.get("validation")
            if not previous_errors and isinstance(validation, dict):
                previous_errors = (
                    validation.get("errors")
                    or validation.get("error")
                    or validation.get("analysis")
                    or ""
                )
            if previous_candidate and previous_errors:
                break
    if is_base:
        reference_knowledge = _get_examples(
            is_base=True,
            name=args.name,
            domain=args.domain,
            desc=generation_desc,
            use_rag=getattr(args, "use_rag", True),
            property_catalog=getattr(args, "property_catalog", None),
            generated_sources=getattr(args, "generated_sources", None),
        )
        if isinstance(required_contract, dict) and required_contract:
            reference_knowledge += prompt.META_ACCEPTANCE_CONTRACT_PROMPT.format(
                contract=format_json(required_contract, ensure_ascii=False, indent=2)
            )
        
        system_prompt = prompt.BASE_SYSTEM_PROMPT
        if previous_candidate:
            user_prompt = prompt.META_REPAIR_USER_PROMPT.format(
                name=args.name,
                domain=args.domain,
                desc=generation_desc,
                current_candidate=_generation_candidate_reference(previous_candidate),
                errors=format_json(previous_errors, ensure_ascii=False)
                if previous_errors
                else prompt.META_NO_ERROR_TEXT,
                reference_knowledge=reference_knowledge,
            )
        else:
            user_prompt = prompt.BASE_USER_PROMPT.format(name=args.name, domain=args.domain, desc=generation_desc, reference_knowledge=reference_knowledge)
    else:
        reference_knowledge = _get_examples(
            is_base=False,
            name=args.name,
            domain=args.domain,
            desc=generation_desc,
            use_rag=getattr(args, "use_rag", True),
            property_catalog=getattr(args, "property_catalog", None),
            generated_sources=getattr(args, "generated_sources", None),
        )
        if isinstance(required_contract, dict) and required_contract:
            reference_knowledge += prompt.META_ACCEPTANCE_CONTRACT_PROMPT.format(
                contract=format_json(required_contract, ensure_ascii=False, indent=2)
            )
        
        system_prompt = prompt.BASE_SYSTEM_PROMPT
        base_json_content = load_file(args.base_json)
        if previous_candidate:
            inherited_reference = (
                reference_knowledge
                + prompt.META_BASE_REFERENCE_PROMPT.format(
                    specification=_generation_json_reference(base_json_content)
                )
            )
            user_prompt = prompt.META_REPAIR_USER_PROMPT.format(
                name=args.name,
                domain=args.domain,
                desc=generation_desc,
                current_candidate=_generation_candidate_reference(previous_candidate),
                errors=format_json(previous_errors, ensure_ascii=False)
                if previous_errors
                else prompt.META_NO_ERROR_TEXT,
                reference_knowledge=inherited_reference,
            )
        else:
            user_prompt = prompt.INHERIT_USER_PROMPT.format(name=args.name, domain=args.domain, desc=generation_desc, base_json=_generation_json_reference(base_json_content), reference_knowledge=reference_knowledge)
    
    user_prompt, cache_prefix = prepend_fixed_references(
        user_prompt, domain=args.domain, stage="meta",
        use_rag=getattr(args, "use_rag", True),
    )
    code, response = call_llm_api(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
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
        return {}, log_data
    
    code, json_content = extract_json_from_answer(response["answer"])
    
    if code != "[PASS]":
        print_status("Failed to extract JSON from LLM response.", "error")
        print_status(f"LLM response: {response['answer']}", "warning")
        log_data["code"] = code
        return {}, log_data
    
    if args.name not in json_content:
        json_content = {args.name: json_content}

    meta = json_content[args.name].get("meta", {})
    meta.pop("domain", None)
    meta.pop("schema_version", None)
    meta["name"] = args.name
    meta["description"] = generation_desc
    meta["version"] = "1.0.0"
    if not is_base:
        meta["from"] = f"../{Path(args.base_json).name}"
    else:
        # A base class has no parent.  This path is orchestration-owned rather
        # than model-authored; accepting an LLM value such as "Home" makes the
        # deterministic template stage resolve a nonexistent base file.
        meta["from"] = ""
    json_content[args.name]["meta"] = meta

    # Capability descriptions come from the model; the power API is owned by
    # the deterministic generator.  Normalize before any downstream gate so
    # meta, template, and validation all consume the same contract.
    parent_specification = None
    if not is_base:
        parent_specification, _ = resolve_specification(args.base_json)
        # Treat the resolved parent as the authoritative future-generation
        # contract before deciding whether a child must declare power methods.
        parent_specification = normalize_power_contract(
            parent_specification,
            is_base=True,
        )
    json_content[args.name] = normalize_power_contract(
        json_content[args.name],
        parent=parent_specification,
        is_base=is_base,
    )
    
    schema_code, schema_errors = validate_json_schema(
        json_content,
        DEVICE_SPEC_SCHEMA,
    )
    case_contract = None
    errors = list(schema_errors)
    code = schema_code
    effective_specification = json_content[args.name]
    if schema_code == "[PASS]":
        if not is_base:
            effective_specification = resolve_specification_delta(parent_specification, args.name, effective_specification)
        errors.extend(validate_capability_spec(effective_specification))
        if errors:
            code = "[CAPABILITY_DECLARATION_INVALID]"
    if schema_code == "[PASS]" and isinstance(required_contract, dict):
        effective_specification = json_content[args.name]
        if not is_base:
            effective_specification = resolve_specification_delta(
                parent_specification,
                args.name,
                json_content[args.name],
            )
        case_contract = validate_required_contract(
            json_content[args.name],
            required_contract,
            effective_specification=effective_specification,
        )
        if case_contract["code"] != "[PASS]":
            code = case_contract["code"]
            errors.extend(case_contract["errors"])
    log_data["candidate_json"] = json_content
    if code == "[PASS]":
        review = review_meta(
            effective_specification, model=getattr(args, "model", None),
            domain_context=_property_catalog_context(args.domain, getattr(args, "property_catalog", None)),
            cache_prefix=cache_prefix,
        )
        log_data["auxiliary_llm_calls"] = [review]
        code = review["code"]
        errors.extend(review["errors"])
    is_valid = (code == "[PASS]")
    log_data["validation"] = {
        "is_valid": is_valid,
        "schema": {
            "code": schema_code,
            "errors": schema_errors,
        },
        "case_contract": case_contract,
        "errors": errors,
    }
    
    if is_valid:
        print_status("JSON schema validation passed!", "success")
        log_data["code"] = code
        return json_content, log_data
    else:
        print_status(f"JSON specification validation failed: {errors}", "error")
        log_data["code"] = code
        return {}, log_data


def main(args):
    """Run the command-line entry point."""
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print_run_config(
        "Object class metadata",
        (
            ("Domain", args.domain),
            ("Class", args.name),
            ("Base", Path(args.base_json).resolve() if args.base_json else "-"),
            ("Model", args.model or "configured default"),
            ("Output", output_path),
        ),
    )
    json_content, log_data = create_object_class_meta(args)
    if not json_content:
        print_run_summary(
            "Object class metadata",
            log_data["code"],
            (("Output", "-"),),
        )
        return None, log_data

    write_json(output_path, json_content)
    print_run_summary(
        "Object class metadata",
        "PASS",
        (("Output", output_path),),
    )
    return str(output_path), log_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Object Class Meta (JSON Specification) with LLM.")
    parser.add_argument("--domain", type=str, default="Home", help="Domain this object belongs to.")
    parser.add_argument("--name", type=str, required=True, help="Name of this object.")
    parser.add_argument("--desc", type=str, default="", help="Description of type, function or feature of this object.")
    parser.add_argument("--base_json", type=str, default="", help="Path of the Object Base Class Meta that will inherit from. By default, create from scratch.")
    parser.add_argument("--output", type=Path, help="Output JSON path; defaults to simulator/devices/<domain>-default/<domain>/<name>/<name>.json, or a child of --base_json.")
    parser.add_argument("--no_rag", action="store_false", dest="use_rag", help="Disable RAG for example retrieval.")
    parser.add_argument("--property_catalog", default=None, help="Optional authoritative domain property catalog.")
    parser.add_argument("--model_scenario", default="code", help="LLM config scenario used for JSON generation.")
    parser.add_argument("--model", default=None, help="Optional model override; otherwise use the selected LLM config.")
    args = parser.parse_args()
    if args.base_json and not Path(args.base_json).is_file():
        raise FileNotFoundError(f"Base JSON file not found: {args.base_json}")
    if args.output is None:
        parent = (
            Path(args.base_json).resolve().parent
            if args.base_json
            else config.DEVICES_DIR / f"{args.domain}-default" / args.domain
        )
        args.output = parent / args.name / f"{args.name}.json"
    output, _ = main(args)
    raise SystemExit(0 if output else 1)
