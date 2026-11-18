"""CLI for list creation followed by deterministic model creation."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from src.contracts import load_json
from src.utils import (
    DEVICES_DIR,
    DOMAIN_CONFIG_DIR,
    PROJECT_ROOT,
    RUN_DIR,
    print_run_config,
    print_run_summary,
    progress_bar,
    redact,
    write_json,
    write_jsonl,
)
from src.world_distill.pipeline import (
    ListCreationInput,
    ModelCreationInput,
    PipelineRequest,
    run_pipeline,
)
from src.world_distill.pipeline.models import as_jsonable
from src.utils.rag import source_config_path


def parse_args() -> argparse.Namespace:
    """Parse environment-generation command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate or validate one DCB Domain environment"
    )
    parser.add_argument("--domain", required=True)
    parser.add_argument("--stage", choices=("list", "all"), default="all")
    parser.add_argument("--description", default="")
    parser.add_argument("--type_list", type=Path, required=True)
    parser.add_argument("--type_list_output", type=Path)
    parser.add_argument("--generation_run_id", default="default")
    parser.add_argument(
        "--output_root", type=Path,
        help="Model assets; defaults to simulator/devices/<domain>-<generation-run-id>.",
    )
    parser.add_argument(
        "--run_root", type=Path,
        help="Generation logs; defaults to run/<domain>-<generation-run-id>.",
    )
    parser.add_argument("--checkpoint_root", type=Path)
    parser.add_argument("--property_catalog", type=Path)
    parser.add_argument("--required_contracts", type=Path, help="Per-class minimum properties, functions and behavior for model generation and validation.")
    parser.add_argument("--coverage_class", action="append", default=[])
    parser.add_argument("--expand_list", action="store_true")
    parser.add_argument(
        "--list_max_iterations",
        type=int,
        default=3,
        help="Maximum expansion rounds; stop early when a round adds nothing.",
    )
    parser.add_argument(
        "--list_max_attempts",
        type=int,
        default=3,
        help="Maximum validation/repair attempts within each expansion round.",
    )
    parser.add_argument(
        "--review_list",
        action="store_true",
        help=(
            "Attach five LLM-as-a-Judge samples per base/derived class; "
            "scores never filter the list."
        ),
    )
    parser.add_argument(
        "--list_review_max_attempts_per_sample",
        type=int,
        default=3,
    )
    parser.add_argument("--list_review_max_workers", type=int, default=1)
    parser.add_argument("--generate_models", action="store_true")
    parser.add_argument("--skip_tests", action="store_true")
    parser.add_argument("--no_rag", action="store_true", help="Disable source retrieval in list/meta/code/test generation.")
    parser.add_argument("--max_workers", type=int, default=4)
    parser.add_argument("--model")
    return parser.parse_args()


def main() -> int:
    """Run the selected Domain-generation stages and report final status."""
    args = parse_args()
    if args.stage == "list" and args.generate_models:
        raise ValueError("--generate_models requires --stage all")
    source_config = source_config_path(PROJECT_ROOT, args.domain)
    use_rag = not args.no_rag and (
        bool(os.getenv("DCB_RAG_SOURCE_CONFIG")) or source_config.is_file()
    )

    batch_name = f"{args.domain}-{args.generation_run_id}"
    output_root = (args.output_root or DEVICES_DIR / batch_name).resolve()
    run_root = (args.run_root or RUN_DIR / batch_name).resolve()
    property_catalog = (
        args.property_catalog
        or DOMAIN_CONFIG_DIR / args.domain / f"{args.domain.lower()}.property-specs.json"
    ).resolve()
    checkpoint_root = (
        args.checkpoint_root.resolve()
        if args.checkpoint_root is not None
        else run_root / "checkpoints"
    )
    type_list_output = (
        args.type_list_output.resolve()
        if args.type_list_output is not None
        else output_root / "type_list.json"
    )
    attempts_path = run_root / "list_attempts.jsonl"
    request_path = run_root / "request.json"
    title = (
        "Type-list generation"
        if args.stage == "list"
        else "Environment generation"
    )
    write_json(
        request_path,
        {
            "stage": args.stage,
            "domain": args.domain,
            "generation_run_id": args.generation_run_id,
            "output_root": str(output_root),
            "run_root": str(run_root),
            "property_catalog": str(property_catalog),
            "required_contracts": load_json(args.required_contracts) if args.required_contracts else {},
            "type_list_input": {
                "path": str(args.type_list.resolve()),
            },
            "type_list_output": str(type_list_output),
            "checkpoint_root": str(checkpoint_root),
            "use_rag": use_rag,
            "rag_source_config": str(source_config) if use_rag else None,
            "expand_with_llm": args.expand_list,
            "model_scenario": "generate" if args.expand_list else None,
            "requested_model": args.model,
            "max_iterations": args.list_max_iterations,
            "max_generation_attempts": args.list_max_attempts,
            "review_with_llm": args.review_list,
            "attempt_records": str(attempts_path),
        },
    )
    print_run_config(
        title,
        (
            ("Domain", args.domain),
            ("Stage", args.stage),
            ("Type list", args.type_list.resolve()),
            ("Type-list output", type_list_output),
            ("Output root", output_root),
            ("Run root", run_root),
            ("Property catalog", property_catalog),
            ("Checkpoint root", checkpoint_root),
            (
                "RAG source configuration",
                source_config if use_rag else "disabled",
            ),
            ("Expand list", args.expand_list),
            ("List iterations", args.list_max_iterations),
            ("Attempts/iteration", args.list_max_attempts),
            ("Review list", args.review_list),
            ("Generate models", args.stage == "all" and args.generate_models),
            ("Run model tests", args.stage == "all" and not args.skip_tests),
            ("Workers", args.max_workers),
            ("Model", args.model or "configured default"),
        ),
    )
    list_input = ListCreationInput(
        domain=args.domain,
        description=args.description,
        existing_types=load_json(args.type_list),
        use_rag=use_rag,
        coverage_requirements=tuple(args.coverage_class),
        expand_with_llm=args.expand_list,
        model=args.model,
        max_generation_attempts=args.list_max_attempts,
        max_iterations=args.list_max_iterations,
        review_with_llm=args.review_list,
        review_model_scenario="judge",
        review_model=args.model,
        review_max_attempts_per_sample=(
            args.list_review_max_attempts_per_sample
        ),
        review_max_workers=args.list_review_max_workers,
    )
    list_attempts: list[dict[str, object]] = []

    def record_list_attempt(log: dict[str, object]) -> None:
        list_attempts.append(redact(log))
        write_jsonl(attempts_path, list_attempts)

    iteration_progress = progress_bar(
        total=args.list_max_iterations,
        description="Type-list iterations",
        unit="round",
        enabled=args.expand_list,
    )

    def record_list_iteration(report: dict[str, object]) -> None:
        iteration_progress.set_postfix(
            new=report["new_class_count"],
            deleted=report["deleted_class_count"],
            total=report["total_class_count"],
            refresh=False,
        )
        iteration_progress.update(1)

    model_creation_factory = None
    if args.stage == "all":
        model_creation_factory = lambda output: ModelCreationInput(
            domain=args.domain,
            object_types=output.object_types,
            output_root=output_root,
            run_root=run_root / "model_creation",
            generation_run_id=args.generation_run_id,
            property_catalog=property_catalog,
            required_contracts=load_json(args.required_contracts) if args.required_contracts else {},
            generate_with_llm=args.generate_models,
            use_rag=use_rag,
            run_tests=not args.skip_tests,
            max_workers=args.max_workers,
            model=args.model,
        )

    try:
        result = run_pipeline(
            PipelineRequest(
                list_creation=list_input,
                model_creation_factory=model_creation_factory,
                checkpoint_root=checkpoint_root,
            ),
            list_attempt_sink=record_list_attempt,
            list_review_attempt_sink=record_list_attempt,
            list_iteration_sink=record_list_iteration,
        )
    finally:
        iteration_progress.close()
    if result.list_creation is None:
        raise RuntimeError("list creation produced no output")
    write_json(type_list_output, result.list_creation.object_types)
    write_json(
        run_root / "list_creation.output.json",
        as_jsonable(result.list_creation),
    )
    if not attempts_path.exists():
        write_jsonl(attempts_path, ())
    print_run_summary(
        title,
        result.report["status"],
        (
            ("Domain", args.domain),
            ("Completed stages", ", ".join(result.report["completed_stages"])),
            ("Type-list output", type_list_output),
            ("Request", request_path),
            ("Attempt records", attempts_path),
            ("Checkpoint root", checkpoint_root),
        ),
    )
    return 0 if result.report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
