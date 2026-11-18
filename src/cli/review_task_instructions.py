"""Review selected template tasks without modifying them."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import as_completed, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from src.contracts import ContractPackage, load_json
from src.utils import print_run_config, print_run_summary, progress_bar, write_json
from src.utils.llm import get_llm_config
from src.world_distill.pipeline.scenario_creation.generation_records import (
    GenerationRecords,
)
from src.world_distill.pipeline.scenario_creation.task_instruction import (
    Completion,
    review_task_reasonableness,
)

from .rewrite_task_instructions import (
    _artifact_path,
    _audited_completion,
    _read_task_ids,
    _templates,
    _write_lines,
)


def _world_summary(world_init: dict[str, Any]) -> dict[str, Any]:
    """Return the public world fields needed for intent review."""
    return {
        "world_id": world_init["world_id"],
        "template": world_init.get("template"),
        "config": world_init["config"],
        "init": world_init.get("init", []),
    }


def _review_one(
    *,
    task_root: Path,
    task_id: str,
    run_id: str,
    output_root: Path,
    contract: ContractPackage,
    model_scenario: str,
    model: str | None,
    max_transport_attempts: int,
    max_generation_attempts: int,
    completion: Completion | None,
) -> dict[str, Any]:
    """Review one selected task and return its judgment record."""
    root = task_root / task_id
    task = load_json(root / "task.json")
    contract.validate_task(task)
    if task["task_id"] != task_id:
        raise ValueError(f"task ID differs from directory name: {task_id}")
    validation = load_json(_artifact_path(root, "validation_metadata.json"))
    seed = validation["meta"]
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
        stage="reasonableness_review",
        model_scenario=model_scenario,
        model=model,
        max_transport_attempts=max_transport_attempts,
        completion=completion,
    )
    error: Exception | None = None
    review: dict[str, Any] | None = None
    for _ in range(max_generation_attempts):
        try:
            review, _ = review_task_reasonableness(
                task_id=task_id,
                task_family=task["meta"]["task_family"],
                task_subtype=task["meta"]["task_subtype"],
                instruction_template=_templates(task, seed),
                seed_summary=seed,
                world_summary=_world_summary(
                    load_json(_artifact_path(root, "world_init.json"))
                ),
                model_scenario=model_scenario,
                model=model,
                completion=caller,
            )
            error = None
            break
        except (KeyError, RuntimeError, TypeError, ValueError) as caught:
            error = caught
    if review is None or error is not None:
        raise RuntimeError(str(error) if error is not None else "review failed")
    usage: Counter[str] = Counter()
    response_models: set[str] = set()
    for record in audit_records.records:
        usage.update(record["usage"])
        response_model = record["model"].get("response_model")
        if response_model:
            response_models.add(response_model)
    return {
        "task_id": task_id,
        "judge": review["judge"],
        "explanation": review["explanation"],
        "model_calls": len(audit_records.records),
        "usage": dict(usage),
        "response_models": sorted(response_models),
        "audit_record_path": str(audit_records.path),
    }


def run_task_review(
    *,
    run_id: str,
    task_root: str | Path,
    task_ids: str | Path,
    output_root: str | Path,
    model_scenario: str = "judge",
    model: str | None = None,
    max_workers: int = 16,
    max_transport_attempts: int = 3,
    max_generation_attempts: int = 3,
    completion: Completion | None = None,
    show_progress: bool = True,
) -> dict[str, Any]:
    """Review only listed tasks and write approved/rejected ID lists."""
    root = Path(task_root).resolve()
    id_path = Path(task_ids).resolve()
    destination = Path(output_root).resolve()
    identifiers = _read_task_ids(id_path)
    if max_workers < 1 or max_transport_attempts < 1 or max_generation_attempts < 1:
        raise ValueError("worker and retry limits must be positive")
    configured = get_llm_config(model_scenario)
    write_json(
        destination / "run_config.json",
        {
            "version": 1,
            "run_id": run_id,
            "task_root": str(root),
            "task_ids": str(id_path),
            "model_scenario": model_scenario,
            "requested_model": model,
            "resolved_model": model or configured["model"],
            "base_url": configured["base_url"],
        },
    )
    contract = ContractPackage()
    completed = GenerationRecords(destination / "reviews.jsonl", id_field="task_id")
    failures = GenerationRecords(destination / "failures.jsonl", id_field="failure_id")
    pending = [task_id for task_id in identifiers if completed.get(task_id) is None]
    with progress_bar(
        total=len(identifiers),
        initial=len(identifiers) - len(pending),
        description=f"Task reasonableness review ({max_workers} workers)",
        unit="task",
        enabled=show_progress,
    ) as progress, ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _review_one,
                task_root=root,
                task_id=task_id,
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
                completed.append(future.result())
            except Exception as error:
                failures.append(
                    {
                        "failure_id": f"failure_{len(failures.records) + 1:08d}",
                        "task_id": task_id,
                        "kind": type(error).__name__,
                        "message": str(error) or type(error).__name__,
                    }
                )
            progress.update(1)
    reviews = completed.records
    reviewed_ids = {record["task_id"] for record in reviews}
    approved = sorted(
        record["task_id"] for record in reviews if record["judge"]
    )
    rejected = sorted(
        record["task_id"] for record in reviews if not record["judge"]
    )
    _write_lines(destination / "approved_task_ids.txt", approved)
    _write_lines(destination / "rejected_task_ids.txt", rejected)
    report = {
        "status": "PASS" if reviewed_ids == set(identifiers) else "FAIL",
        "run_id": run_id,
        "selected_task_count": len(identifiers),
        "reviewed_task_count": len(reviewed_ids),
        "approved_task_count": len(approved),
        "rejected_task_count": len(rejected),
        "pending_task_count": len(set(identifiers) - reviewed_ids),
        "task_root": str(root),
        "approved_task_ids": str(destination / "approved_task_ids.txt"),
        "rejected_task_ids": str(destination / "rejected_task_ids.txt"),
        "review_list": str(completed.path),
        "failure_list": str(failures.path),
        "audit_root": str(destination / "audits"),
    }
    write_json(destination / "report.json", report)
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Review selected template tasks without modifying them"
    )
    parser.add_argument("--run_id", required=True)
    parser.add_argument("--task_root", type=Path, required=True)
    parser.add_argument("--task_ids", type=Path, required=True)
    parser.add_argument("--output_root", type=Path, required=True)
    parser.add_argument("--model_scenario", default="judge")
    parser.add_argument("--model")
    parser.add_argument("--max_workers", type=int, default=16)
    parser.add_argument("--max_transport_attempts", type=int, default=3)
    parser.add_argument("--max_generation_attempts", type=int, default=3)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the selected-task review CLI."""
    args = parse_args(argv)
    configured = get_llm_config(args.model_scenario)
    print_run_config(
        "Task reasonableness review",
        (
            ("Task root", args.task_root.resolve()),
            ("Task IDs", args.task_ids.resolve()),
            ("Output root", args.output_root.resolve()),
            ("Endpoint", configured["base_url"]),
            ("Model", args.model or configured["model"]),
        ),
    )
    report = run_task_review(
        run_id=args.run_id,
        task_root=args.task_root,
        task_ids=args.task_ids,
        output_root=args.output_root,
        model_scenario=args.model_scenario,
        model=args.model,
        max_workers=args.max_workers,
        max_transport_attempts=args.max_transport_attempts,
        max_generation_attempts=args.max_generation_attempts,
    )
    print_run_summary(
        "Task reasonableness review",
        report["status"],
        (
            ("Approved", report["approved_task_count"]),
            ("Rejected", report["rejected_task_count"]),
            ("Approved IDs", report["approved_task_ids"]),
        ),
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
