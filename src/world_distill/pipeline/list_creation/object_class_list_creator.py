"""
Create Object Class List with LLM.
"""

import argparse
from pathlib import Path
from src.utils import (
    config,
    format_json,
    json_payload,
    load_json,
    print_run_config,
    print_run_summary,
    print_status,
    write_json,
)
from src.utils.llm import call_llm_api, extract_json_from_answer
from src.utils.rag import get_vectordb, prepend_fixed_references
from . import prompt
from src.contracts.schema import type_list_change_schema
from .object_class_list_validator import split_type_list_changes, validate_type_list_change_schema


def create_object_class_list(
    existing_types: dict,
    *,
    domain: str = "Home",
    domain_description: str = "",
    model_scenario: str = "generate",
    model: str | None = None,
    max_object_types: int = 3,
    external_knowledge: str = "",
    use_rag: bool = True,
    validation_feedback: str = "No preceding validation failure.",
) -> tuple[dict, dict]:
    """
    Call LLM to create a list of object classes.
    """
    print_status("Calling LLM to enumerate new device types...", "info")
    
    references = []
    if use_rag:
        vectordb = get_vectordb(domain=domain, stage="type_list")
        query = f"{domain} {domain_description} device categories capabilities 智能设备品类 功能"
        references = vectordb.search(
            query, top_k=3, kinds={"document"}, max_chars=12_000,
            min_score=0.05,
        ) + vectordb.search(
            query, top_k=3, kinds={"object_spec"}, max_chars=60_000,
            min_score=0.05,
        )
    knowledge = [external_knowledge] if external_knowledge else []
    knowledge.extend(
        f"Retrieved reference (not a required capability contract): {item['name']}\n"
        f"Source: {item['path']} (score: {item['similarity']:.3f})\n{item['content']}"
        for item in references
    )

    system_prompt = prompt.OBJECT_LIST_CREATOR_SYSTEM_PROMPT.format(
        domain=domain,
        domain_description=domain_description,
        json_schema=json_payload(type_list_change_schema(domain)),
    )
    user_prompt = prompt.OBJECT_LIST_CREATOR_USER_PROMPT.format(
        max_object_types=max_object_types,
        external_knowledge=(
            "\n\n---\n\n".join(knowledge)
            or "No external knowledge documents are configured for this domain."
        ),
        validation_feedback=validation_feedback,
        existing_classes=format_json(
            existing_types,
            ensure_ascii=False,
            indent=2,
        )
    )
    
    user_prompt, cache_prefix = prepend_fixed_references(
        user_prompt, domain=domain, stage="type_list", use_rag=use_rag,
    )
    code, response = call_llm_api(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model_scenario=model_scenario,
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
        "code": ""
    }
    
    if code != "[PASS]" or not isinstance(response.get("answer"), str):
        print_status("Failed to get a response from LLM.", "error")
        log_data["code"] = code
        return {}, log_data
    
    code, json_content = extract_json_from_answer(response["answer"])
    
    if code != "[PASS]" or not isinstance(json_content, dict):
        print_status("Failed to extract JSON from LLM response.", "error")
        print_status(f"LLM response: {response}", "warning")
        log_data["code"] = code
        return {}, log_data
    
    log_data["code"] = "[PASS]"
    return json_content, log_data


def main(args) -> str | None:
    """Run the object-class list creator."""
    domain = "Home"
    input_path = Path(args.input)
    output_path = Path(args.output)
    if not input_path.is_file():
        raise FileNotFoundError(f"object-class list not found: {input_path}")
    if args.iterations < 1:
        raise ValueError("iterations must be positive")

    print_run_config(
        "Object class list",
        (
            ("Input", input_path),
            ("Iterations", args.iterations),
            ("Output", output_path),
        ),
    )
    all_device_types = load_json(input_path)
    print_status(f"Loaded {len(all_device_types)} existing device types.", "info")

    for i in range(args.iterations):
        print_status(f"Iteration {i + 1}/{args.iterations}", "info")
        new_types, log_data = create_object_class_list(
            all_device_types,
            domain=domain,
        )
        if log_data["code"] != "[PASS]":
            print_run_summary(
                "Object class list",
                log_data["code"],
                (("Output", "-"),),
            )
            return None
        validate_type_list_change_schema(new_types, domain=domain)
        updates, deletions = split_type_list_changes(
            new_types,
            existing_types=all_device_types,
        )
        if not updates and not deletions:
            print_status("LLM returned no new device types; iteration stopped.", "info")
            break

        print_status(
            f"LLM returned {len(updates)} class entries and "
            f"{len(deletions)} deletions.",
            "info",
        )
        for key in deletions:
            del all_device_types[key]
        for key, value in updates.items():
            all_device_types[key] = value
        print_status(f"Total device types is now {len(all_device_types)}.", "info")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(output_path, all_device_types)
    print_run_summary(
        "Object class list",
        "PASS",
        (
            ("Device types", len(all_device_types)),
            ("Output", output_path),
        ),
    )
    return str(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Use LLM to enumerate new device types and expand the type list.")
    parser.add_argument("--input", type=str, default=str(config.DEVICES_DIR / "type_list_seed" / "home_type_list_seed.json"), help="Path to the existing type list JSON file.")
    parser.add_argument("--output", type=str, default=str(config.DEVICES_DIR / "Home-default" / "type_list.json"), help="Path to save the updated type list JSON file.")
    parser.add_argument("--iterations", "-n", type=int, default=5, help="Number of iterations to run.")
    
    args = parser.parse_args()
    output = main(args)
    raise SystemExit(0 if output else 1)
