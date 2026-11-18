"""Rewrite selected template task instructions in place."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from concurrent.futures import as_completed, ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from src.contracts import ContractPackage, load_json
from src.runtime.loading.templates import apply_init_operations
from src.utils import (
    json_payload,
    print_run_config,
    print_run_summary,
    progress_bar,
    write_json,
)
from src.utils.llm import call_llm_api, extract_json_from_answer, get_llm_config
from src.world_distill.pipeline.scenario_creation import prompt
from src.world_distill.pipeline.scenario_creation.generation_records import (
    GenerationRecords,
)
from src.world_distill.pipeline.scenario_creation.task_instruction import (
    build_instruction_variants,
    Completion,
    INSTRUCTION_STYLES,
)
from src.world_distill.pipeline.scenario_creation.validator import (
    instruction_literal_anchors,
    validate_instruction_alignment,
    validate_public_assets,
)


DEFAULT_STYLES = INSTRUCTION_STYLES
EMBEDDED_WORLD_DIRECTORY = "test_world"


class TaskRewriteTransportError(RuntimeError):
    """The external rewrite service exhausted its transport retries."""





def _write_lines(path: Path, values: Iterable[str]) -> None:
    """Write one identifier per line atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.candidate")
    items = list(values)
    temporary.write_text(
        "".join(f"{value}\n" for value in items),
        encoding="utf-8",
    )
    temporary.replace(path)


def _usage(response: dict[str, Any]) -> dict[str, int]:
    """Return non-negative integer usage fields."""
    raw = response.get("usage", {})
    return {
        str(key): int(value)
        for key, value in raw.items()
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0
    } if isinstance(raw, dict) else {}


def _completion_record(
    *,
    task_id: str,
    style: str,
    audit_records: GenerationRecords,
    task_path: Path,
) -> dict[str, Any]:
    """Return the completion record for one rewritten task."""
    usage: Counter[str] = Counter()
    response_models: set[str] = set()
    for record in audit_records.records:
        usage.update(record["usage"])
        response_model = record["model"].get("response_model")
        if response_model:
            response_models.add(response_model)
    return {
        "task_id": task_id,
        "style": style,
        "model_calls": len(audit_records.records),
        "usage": dict(usage),
        "response_models": sorted(response_models),
        "audit_record_path": str(audit_records.path),
        "task_path": str(task_path.resolve()),
    }


def _read_task_ids(path: str | Path) -> tuple[str, ...]:
    """Return the unique non-empty IDs from a one-ID-per-line file."""
    identifiers = tuple(
        line.strip()
        for line in Path(path).resolve().read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    if not identifiers or len(identifiers) != len(set(identifiers)):
        raise ValueError("task ID list must contain unique non-empty IDs")
    return identifiers


def _artifact_path(task_root: Path, filename: str) -> Path:
    """Return a flat artifact or its private-directory equivalent."""
    direct = task_root / filename
    private = task_root / "private" / filename
    path = direct if direct.is_file() else private
    if not path.is_file():
        raise ValueError(f"task artifact is missing: {path}")
    return path


def _templates(task: dict[str, Any], seed: dict[str, Any]) -> list[str]:
    """Return the task's template instruction variants."""
    values = [
        variant[2]
        for variant in task.get("instruction_variants", [])
        if variant[0] == "template"
    ]
    values.extend(seed.get("derived", {}).get("instruction_variants", []))
    return list(dict.fromkeys(values)) or [task["instruction"]]


def _world_layout(task_root: Path) -> dict[str, Any]:
    """Read a self-contained task world's layout without answer or state values."""
    embedded = task_root / EMBEDDED_WORLD_DIRECTORY
    root = embedded if (embedded / "world_init.json").is_file() else task_root
    world_init = load_json(_artifact_path(root, "world_init.json"))
    if world_init.get("template") is not None:
        raise ValueError("instruction rewriting requires a resolved world layout (template=null)")
    world = apply_init_operations(world_init["config"], world_init.get("init", []))
    return {
        "spaces": {
            identifier: {
                "type": spec["type"],
                "name": spec.get("metadata", {}).get("name"),
                "properties": list(spec.get("properties", {})),
            }
            for identifier, spec in world["spaces"].items()
        },
        "devices": {
            identifier: {
                "class": spec["class"],
                "space_id": spec.get("space_id"),
                "name": spec.get("metadata", {}).get("name"),
                "properties": list(spec.get("properties", {})),
            }
            for identifier, spec in world["objects"].items()
        },
        "connections": world.get("domain_metadata", {}).get("connections", []),
    }


def _protected_literal_anchors(
    seed: dict[str, Any], *, allow_property_paraphrases: bool = False,
) -> list[str]:
    """Return non-entity public anchors that rewrites must preserve verbatim."""
    derived = seed.get("derived", {})
    anchors = instruction_literal_anchors(seed)
    if allow_property_paraphrases:
        anchors.difference_update(
            str(atom.get("spec", {}).get("property", "")).casefold()
            for atom in seed.get("atoms", [])
        )
    return sorted(
        {
            str(value)
            for value in derived.get("public_anchors", [])
            if str(value).strip() and str(value).casefold() in anchors
        },
        key=str.casefold,
    )


def _rewrite_candidate(
    *,
    task: dict[str, Any],
    templates: list[str],
    seed: dict[str, Any],
    style: str,
    instruction: str,
    contract: ContractPackage,
) -> dict[str, Any]:
    """Build and validate one rewritten task candidate."""
    instruction = instruction.strip()
    if not instruction:
        raise ValueError("task rewrite instruction is empty")
    if instruction in templates:
        raise ValueError("task rewrite did not change the wording")
    variant = ["llm", style, instruction]
    if variant in task.get("instruction_variants", []):
        raise ValueError("task rewrite duplicates an existing variant of this style")
    candidate = deepcopy(task)
    candidate.setdefault("instruction_variants", build_instruction_variants(templates)).append(variant)
    contract.validate_task(candidate)
    infeasible = any("reason_code" in atom["spec"] for atom in seed.get("atoms", []))
    validate_instruction_alignment(
        templates,
        instruction,
        seed,
        allow_entity_aliases=True,
        allow_property_paraphrases=style != "direct" and not infeasible,
        allow_intent_shift=style == "implicit" and not infeasible,
    )
    validate_public_assets(task=candidate)
    return candidate


def _audited_completion(
    *,
    audit_records: GenerationRecords,
    run_id: str,
    task_id: str,
    stage: str,
    model_scenario: str,
    model: str | None,
    max_transport_attempts: int,
    completion: Completion | None,
) -> Completion:
    """Return a completion that records every request and response."""
    contract_version = ContractPackage().contract_version

    def caller(system: str, user: str) -> tuple[str, dict[str, Any]]:
        number = len(audit_records.records) + 1
        try:
            code, response = (
                completion(system, user)
                if completion is not None
                else call_llm_api(
                    system,
                    user,
                    model_scenario=model_scenario,
                    model=model,
                    max_transport_attempts=max_transport_attempts,
                )
            )
        except Exception as error:
            code = "[EXCEPTION]"
            response = {
                "error": {
                    "kind": type(error).__name__,
                    "message": str(error) or type(error).__name__,
                }
            }
        audit_records.append(
            {
                "record_id": f"call_{number:04d}",
                "authoring_run_id": run_id,
                "scenario_id": task_id,
                "contract_version": contract_version,
                "stage": stage,
                "attempt": number,
                "model": {
                    "model_scenario": model_scenario,
                    "requested_model": model,
                    "response_model": response.get("model"),
                },
                "usage": _usage(response),
                "evidence": {
                    "system": system,
                    "user": user,
                    "response_code": code,
                    "response": deepcopy(response),
                },
            }
        )
        return code, response

    return caller


def _rewrite_one(
    *,
    task_root: Path,
    task_id: str,
    style: str,
    run_id: str,
    output_root: Path,
    contract: ContractPackage,
    model_scenario: str,
    model: str | None,
    max_transport_attempts: int,
    max_generation_attempts: int,
    completion: Completion | None,
) -> dict[str, Any]:
    """Rewrite and atomically update one selected task.json."""
    root = task_root / task_id
    task_path = root / "task.json"
    task = load_json(task_path)
    if task["task_id"] != task_id:
        raise ValueError(f"task ID differs from directory name: {task_id}")
    validation = load_json(_artifact_path(root, "validation_metadata.json"))
    seed = validation["meta"]
    templates = _templates(task, seed)
    world_layout = _world_layout(root)
    audit_records = GenerationRecords(
        output_root / "audits" / task_id / "model_audit.jsonl",
        id_field="record_id",
        contract=contract,
        schema_id="urn:dcb:v2:schema:task-authoring-record",
    )
    caller = _audited_completion(
        audit_records=audit_records,
        run_id=run_id,
        task_id=task_id,
        stage="instruction_rewrite",
        model_scenario=model_scenario,
        model=model,
        max_transport_attempts=max_transport_attempts,
        completion=completion,
    )
    error: Exception | None = None
    candidate: dict[str, Any] | None = None
    for _ in range(max_generation_attempts):
        try:
            style_prompt = prompt.INSTRUCTION_STYLE_EXAMPLES[style]
            system = prompt.TASK_REWRITE_SYSTEM_PROMPT.format(
                instruction_style=style,
                instruction_style_description=style_prompt["description"].strip(),
                instruction_style_examples="\n\n".join(
                    f"Example {index}:\nInput: {example['input']}\n"
                    + (f"Layout: {example['layout']}\n" if "layout" in example else "")
                    + f"Rewrite: {example['rewrite']}"
                    for index, example in enumerate(style_prompt["examples"], 1)
                ),
            )
            user = prompt.TASK_REWRITE_USER_PROMPT.format(
                task_id=task_id,
                task_family=task["meta"]["task_family"],
                task_subtype=task["meta"]["task_subtype"],
                world_layout=json_payload(world_layout),
                instruction_template=json_payload(templates),
            )
            failures = [atom["spec"] for atom in seed.get("atoms", []) if "reason_code" in atom["spec"]]
            user += "\nCurrent user (use their space only for an unqualified unique device): " + json_payload(task.get('current_user'))
            user += "\nUnambiguous device references for this user: " + json_payload(seed['derived'].get('public_entity_aliases', {}))
            if failures:
                user += "\nFixed infeasible request details (preserve the request, do not expose this diagnosis): " + json_payload(failures)
            if any(atom["spec"].get("reason_code") == "BLOCKED_BY_DEPENDENCY" for atom in seed.get("atoms", [])):
                user += "\nPrivate dependency graph (preserve dependencies and independent requests; never expose IDs): " + json_payload(seed["atoms"])
            user += f"\nRequested instruction style: {style}\n"
            if style != "implicit" or failures:
                user += (
                    ("\nProtected non-entity literals (preserve each verbatim): " if style == "direct" or failures else "\nRequired values and constraints (numbers may use exact word equivalents): ")
                    + json_payload(_protected_literal_anchors(
                        seed, allow_property_paraphrases=style != "direct" and not failures,
                    ))
                )
            existing = [v[2] for v in task.get("instruction_variants", [])
                        if v[0] == "llm" and v[1] == style]
            if existing:
                user += "\nExisting rewrites (use different wording): " + json_payload(existing)
            if error is not None:
                user += (
                    f"\nPrevious rewrite failed validation: {error}. "
                    "Correct this issue while preserving the requested style. "
                    "Use wording different from every supplied template.\n"
                )
            code, response = caller(
                system,
                user,
            )
            if code != "[PASS]":
                error_type = (
                    TaskRewriteTransportError
                    if code in {"[EXCEPTION]", "[MAX_TRY_REACHED]"}
                    else RuntimeError
                )
                raise error_type(f"task rewrite failed: {code}")
            code, payload = extract_json_from_answer(response.get("answer", ""))
            if code != "[PASS]" or not isinstance(payload, dict):
                raise ValueError("task rewrite response is not a JSON object")
            instruction = payload.get("instruction")
            if not isinstance(instruction, str):
                raise ValueError("task rewrite instruction is empty")
            candidate = _rewrite_candidate(
                task=task,
                templates=templates,
                seed=seed,
                style=style,
                instruction=instruction,
                contract=contract,
            )
            error = None
            break
        except TaskRewriteTransportError:
            raise
        except (KeyError, RuntimeError, TypeError, ValueError) as caught:
            error = caught
    if candidate is None or error is not None:
        raise RuntimeError(str(error) if error is not None else "rewrite failed")
    write_json(task_path, candidate)
    return _completion_record(
        task_id=task_id,
        style=style,
        audit_records=audit_records,
        task_path=task_path,
    )


def _recover_completion(
    *,
    task_root: Path,
    task_id: str,
    style: str,
    run_id: str,
    output_root: Path,
    contract: ContractPackage,
) -> dict[str, Any] | None:
    """Recover a task write or replay a still-valid audited response."""
    root = task_root / task_id
    task_path = root / "task.json"
    task = load_json(task_path)
    audit_path = output_root / "audits" / task_id / "model_audit.jsonl"
    if not audit_path.is_file():
        return None
    audit_records = GenerationRecords(
        audit_path,
        id_field="record_id",
        contract=contract,
        schema_id="urn:dcb:v2:schema:task-authoring-record",
    )
    audited_instructions = []
    style_marker = f"Requested instruction style: {style}\n"
    for record in reversed(audit_records.records):
        if record["authoring_run_id"] != run_id:
            continue
        if record["evidence"]["response_code"] != "[PASS]":
            continue
        if style_marker not in record["evidence"]["user"]:
            continue
        code, payload = extract_json_from_answer(
            record["evidence"]["response"].get("answer", "")
        )
        if code == "[PASS]" and isinstance(payload, dict):
            value = payload.get("instruction")
            if isinstance(value, str):
                audited_instructions.append(value.strip())
    validation = load_json(_artifact_path(root, "validation_metadata.json"))
    seed = validation["meta"]
    templates = _templates(task, seed)
    for instruction in audited_instructions:
        try:
            candidate = _rewrite_candidate(
                task=task, templates=templates, seed=seed, style=style,
                instruction=instruction, contract=contract,
            )
            break
        except (KeyError, TypeError, ValueError):
            continue
    else:
        return None
    write_json(task_path, candidate)
    return _completion_record(
        task_id=task_id,
        style=style,
        audit_records=audit_records,
        task_path=task_path,
    )


def _style_counts(task_path: Path) -> Counter[str]:
    return Counter(v[1] for v in load_json(task_path).get("instruction_variants", [])
                   if v[0] == "llm")


def _fill_task_styles(*, styles, num_per_style, progress, **options):
    # One worker owns each task so style updates cannot overwrite each other.
    task_path = options["task_root"] / options["task_id"] / "task.json"
    counts = _style_counts(task_path)
    recovery_options = {key: options[key] for key in (
        "task_root", "task_id", "run_id", "output_root", "contract",
    )}
    for style in styles:
        for _ in range(max(0, num_per_style - counts[style])):
            if _recover_completion(style=style, **recovery_options) is None:
                _rewrite_one(style=style, **options)
        if counts[style] < num_per_style:
            with progress.get_lock():
                progress.update(1)


def run_instruction_rewrite(
    *,
    run_id: str,
    task_root: str | Path,
    task_ids: str | Path,
    output_root: str | Path,
    styles: tuple[str, ...] = DEFAULT_STYLES,
    num_per_style: int = 1,
    model_scenario: str = "generate",
    model: str | None = None,
    max_workers: int = 16,
    max_transport_attempts: int = 3,
    max_generation_attempts: int = 3,
    completion: Completion | None = None,
    show_progress: bool = True,
) -> dict[str, Any]:
    """Rewrite only listed task.json files in place."""
    root = Path(task_root).resolve()
    id_path = Path(task_ids).resolve()
    destination = Path(output_root).resolve()
    identifiers = _read_task_ids(id_path)
    if max_workers < 1 or max_transport_attempts < 1 or max_generation_attempts < 1:
        raise ValueError("worker and retry limits must be positive")
    if not styles or len(styles) != len(set(styles)):
        raise ValueError("styles must be non-empty and unique")
    if any(style not in INSTRUCTION_STYLES for style in styles):
        raise ValueError("styles contains an unknown instruction style")
    if isinstance(num_per_style, bool) or not isinstance(num_per_style, int) or num_per_style < 1:
        raise ValueError("num_per_style must be a positive integer")
    counts = {task_id: _style_counts(root / task_id / "task.json") for task_id in identifiers}
    pending = [task_id for task_id in identifiers
               if any(counts[task_id][style] < num_per_style for style in styles)]
    contract = ContractPackage()
    configured = get_llm_config(model_scenario)
    write_json(
        destination / "run_config.json",
        {
            "version": 1,
            "run_id": run_id,
            "task_root": str(root),
            "task_ids": str(id_path),
            "styles": list(styles),
            "num_per_style": num_per_style,
            "resume_style_policy": "fill_missing_variants_in_place",
            "model_scenario": model_scenario,
            "requested_model": model,
            "resolved_model": model or configured["model"],
            "base_url": configured["base_url"],
        },
    )
    failures = GenerationRecords(destination / "failures.jsonl", id_field="failure_id")
    with progress_bar(
        total=len(identifiers) * len(styles),
        initial=sum(counts[task_id][style] >= num_per_style
                    for task_id in identifiers for style in styles),
        description=f"LLM instruction rewrite ({max_workers} workers)",
        unit="task-style",
        enabled=show_progress,
    ) as progress, ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _fill_task_styles,
                task_root=root,
                task_id=task_id,
                styles=styles,
                num_per_style=num_per_style,
                progress=progress,
                run_id=run_id,
                output_root=destination,
                contract=contract,
                model_scenario=model_scenario,
                model=model,
                max_transport_attempts=max_transport_attempts,
                max_generation_attempts=max_generation_attempts,
                completion=completion,
            ): task_id
            for task_id in pending
        }
        for future in as_completed(futures):
            task_id = futures[future]
            try:
                future.result()
            except Exception as error:
                failures.append(
                    {
                        "failure_id": f"failure_{len(failures.records) + 1:08d}",
                        "task_id": task_id,
                        "kind": type(error).__name__,
                        "message": str(error) or type(error).__name__,
                    }
                )
                if isinstance(error, TaskRewriteTransportError):
                    for pending_future in futures:
                        pending_future.cancel()
                    break
    counts = {task_id: _style_counts(root / task_id / "task.json") for task_id in identifiers}
    done = {task_id for task_id in identifiers
            if all(counts[task_id][style] >= num_per_style for style in styles)}
    _write_lines(destination / "completed.jsonl", (
        json.dumps({"task_id": task_id, "style_counts": dict(counts[task_id])})
        for task_id in sorted(done)
    ))
    _write_lines(destination / "completed_task_ids.txt", sorted(done))
    report = {
        "status": "PASS" if done == set(identifiers) else "FAIL",
        "run_id": run_id,
        "selected_task_count": len(identifiers),
        "styles": list(styles),
        "num_per_style": num_per_style,
        "expected_variant_count": len(identifiers) * len(styles) * num_per_style,
        "completed_task_count": len(done),
        "pending_task_count": len(set(identifiers) - done),
        "task_root": str(root),
        "completed_task_ids": str(destination / "completed_task_ids.txt"),
        "failure_list": str(failures.path),
        "audit_root": str(destination / "audits"),
    }
    write_json(destination / "report.json", report)
    return report


def run_all_style_rewrite(**options):
    """Compatibility entry point; rewrite the original tasks in place."""
    return run_instruction_rewrite(**options)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Rewrite selected template task instructions in place"
    )
    parser.add_argument("--run_id", required=True)
    parser.add_argument("--task_root", type=Path, required=True)
    parser.add_argument("--task_ids", type=Path, required=True)
    parser.add_argument("--output_root", type=Path, required=True)
    parser.add_argument(
        "--styles", nargs="+", choices=INSTRUCTION_STYLES, default=DEFAULT_STYLES
    )
    parser.add_argument("--all_styles", action="store_true", help="Compatibility flag; all seven styles are already the default")
    parser.add_argument("--num_per_style", type=int, default=1,
                        help="Target number of LLM variants per selected style (default: 1)")
    parser.add_argument("--model_scenario", default="generate")
    parser.add_argument("--model")
    parser.add_argument("--max_workers", type=int, default=16)
    parser.add_argument("--max_transport_attempts", type=int, default=3)
    parser.add_argument("--max_generation_attempts", type=int, default=3)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the selected-task rewrite CLI."""
    args = parse_args(argv)
    configured = get_llm_config(args.model_scenario)
    print_run_config(
        "Task instruction rewrite",
        (
            ("Task root", args.task_root.resolve()),
            ("Task IDs", args.task_ids.resolve()),
            ("Audit output", args.output_root.resolve()),
            ("Endpoint", configured["base_url"]),
            ("Model", args.model or configured["model"]),
        ),
    )
    report = run_instruction_rewrite(
        run_id=args.run_id,
        task_root=args.task_root,
        task_ids=args.task_ids,
        output_root=args.output_root,
        styles=tuple(args.styles),
        num_per_style=args.num_per_style,
        model_scenario=args.model_scenario,
        model=args.model,
        max_workers=args.max_workers,
        max_transport_attempts=args.max_transport_attempts,
        max_generation_attempts=args.max_generation_attempts,
    )
    print_run_summary(
        "Task instruction rewrite",
        report["status"],
        (
            ("Completed", report["completed_task_count"]),
            ("Pending", report["pending_task_count"]),
            ("Audit root", report["audit_root"]),
        ),
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
