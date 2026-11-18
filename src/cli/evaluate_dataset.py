"""CLI for reference replay, real-agent batch runs, and result analysis."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.utils import RESULTS_DIR, print_run_config, print_run_summary, write_json
from src.evaluation import (
    analyze_benchmark_root,
    evaluate_reference_case,
    initialize_result_path,
    resolve_dataset_input,
    run_dataset_benchmark,
)
from src.evaluation.console import RunConsole
from src.evaluation.execution.batch import EVALUATION_STYLES
from src.utils.llm import LLM_CONFIGS, get_llm_config


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse dataset-evaluation subcommands and arguments."""
    parser = argparse.ArgumentParser(
        description="Evaluate DCB datasets",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True)

    reference = commands.add_parser(
        "reference",
        help="Replay and evaluate one stored reference trajectory",
    )
    reference.add_argument(
        "--world_path",
        type=Path,
        required=True,
        help="single world directory",
    )
    reference.add_argument(
        "--task_path",
        type=Path,
        required=True,
        help="corresponding task directory",
    )
    reference.add_argument(
        "--domain_path",
        type=Path,
        required=True,
        help="Domain environment root",
    )
    reference.add_argument("--run_id", required=True, help="replay run ID")
    reference.add_argument(
        "--result_dir",
        type=Path,
        default=RESULTS_DIR,
        help="directory under which the run ID is written (default: results)",
    )

    run = commands.add_parser(
        "run",
        help="Run one model over task directories listed by path",
    )
    run.add_argument(
        "--task_path",
        type=Path,
        required=True,
        help="task parent directory or .txt/.list of task directories",
    )
    run.add_argument(
        "--domain_path",
        type=Path,
        help=(
            "device directory containing models and type_list_with_placement.json; inferred from the "
            "task dataset or simulator/devices/<domain> when omitted"
        ),
    )
    run.add_argument(
        "--model",
        help="model ID; uses the eval config model when omitted",
    )
    run.add_argument("--api_protocol", choices=("responses", "chat"),
                     help="override the evaluated agent API protocol")
    run.add_argument("--api_key", help="override the evaluated agent API key")
    run.add_argument("--agent_strategy", choices=("react", "toolcall"), default="react",
                     help="react parses Thought/Action text; toolcall uses native API tools (default: react)")
    run.add_argument("--record_requests", action="store_true",
                     help="save model request/response bodies in provider_audit (no API credentials)")
    run.add_argument("--base_url", "--baseurl", dest="base_url",
                     help="override the evaluated agent API base URL (including /v1)")
    samples = run.add_mutually_exclusive_group()
    samples.add_argument(
        "--samples_per_task",
        type=int,
        default=5,
        help="sample count for the default instruction when --style is omitted",
    )
    run.add_argument(
        "--style",
        choices=EVALUATION_STYLES,
        help="select template or exactly one LLM style; omitted uses task.instruction",
    )
    samples.add_argument(
        "--samples_per_instruction",
        type=int,
        help="total attempts per task for --style; cycle matching instructions in stored order; "
             "resume adds missing attempts or reports only the first N when reduced",
    )
    limits = run.add_mutually_exclusive_group()
    limits.add_argument(
        "--max_tasks",
        type=int,
        help="uniformly sample at most N tasks globally (default: unlimited)",
    )
    limits.add_argument(
        "--max_tasks_per_category",
        type=int,
        help="uniformly sample at most N tasks per family.subtype category (default: unlimited)",
    )
    run.add_argument(
        "--max_turns",
        type=int,
        default=10,
        help="maximum environment turns per sample (not exposed to the agent) (default: 10)",
    )
    run.add_argument(
        "--num_workers",
        type=int,
        default=1,
        help="concurrent sample workers (default: 1)",
    )
    results = run.add_mutually_exclusive_group()
    results.add_argument(
        "--result_path",
        type=Path,
        help="exact output path; resumes when the directory already exists",
    )
    results.add_argument(
        "--result_dir",
        type=Path,
        help="parent for domain_model_YYYYMMDD_HHMMSS (default: results)",
    )
    run.add_argument(
        "--force_overwrite",
        action="store_true",
        help="replace an existing exact result path instead of resuming",
    )
    run.add_argument(
        "--no_resume",
        action="store_true",
        help="discard this model's checkpoints and rerun every sample",
    )
    run.add_argument(
        "--device_tool_discovery",
        choices=("required", "optional"),
        default="required",
        help="require device tools to be discovered in a preceding turn",
    )
    run.add_argument(
        "--recover_tool_call_errors",
        action="store_true",
        help=(
            "return malformed tool calls as non-mutating errors and continue "
            "the task"
        ),
    )
    run.add_argument(
        "--dry_run",
        action="store_true",
        help=(
            "validate and estimate without model calls or task execution "
            "(default: False)"
        ),
    )

    analyze = commands.add_parser(
        "analyze",
        help="Aggregate every completed model run under one output root",
    )
    analyze.add_argument(
        "--result_path",
        type=Path,
        required=True,
        help="one result path or a directory of auto-named result paths",
    )
    args = parser.parse_args(argv)
    if args.command == "run":
        if args.style is None and args.samples_per_instruction is not None:
            parser.error("--style is required with --samples_per_instruction")
        if args.style is not None and args.samples_per_instruction is None:
            parser.error("--samples_per_instruction is required with --style")
        for name in ("samples_per_task", "samples_per_instruction"):
            value = getattr(args, name)
            if value is not None and value < 1:
                parser.error(f"--{name} must be positive")
    return args


def main() -> int:
    """Run reference replay, model evaluation, or result analysis."""
    args = parse_args()
    if args.command != "run":
        return _run(args)
    original = LLM_CONFIGS["eval"]
    LLM_CONFIGS["eval"] = {
        **original,
        **{name: getattr(args, name) for name in ("api_protocol", "api_key", "base_url")
           if getattr(args, name) is not None},
    }
    try:
        return _run(args)
    finally:
        LLM_CONFIGS["eval"] = original


def _run(args: argparse.Namespace) -> int:
    if args.command == "run":
        model_config = get_llm_config("eval")
        args.model = args.model or str(model_config["model"])
        console = RunConsole()
        console.print_configuration(args)
        try:
            cases = resolve_dataset_input(
                args.task_path,
                domain_path=args.domain_path,
                max_tasks=args.max_tasks,
                max_tasks_per_category=args.max_tasks_per_category,
                progress_callback=console.handle,
            )
            args.result_path = initialize_result_path(
                result_path=args.result_path,
                result_dir=args.result_dir,
                model=args.model,
                force_overwrite=args.force_overwrite,
                domain=cases[0].domain if args.result_path is None else None,
            )
            console.print_dataset_ready(args, len(cases))
            result = run_dataset_benchmark(
                cases,
                model=args.model,
                samples_per_task=args.samples_per_task,
                max_turns=args.max_turns,
                num_workers=args.num_workers,
                max_transport_attempts=int(model_config["max_retry"]),
                result_path=args.result_path,
                dry_run=args.dry_run,
                no_resume=args.no_resume,
                device_tool_discovery=args.device_tool_discovery,
                recover_tool_call_errors=args.recover_tool_call_errors,
                instruction_style=args.style,
                samples_per_instruction=args.samples_per_instruction,
                progress_callback=console.handle,
                agent_strategy=args.agent_strategy,
                record_requests=args.record_requests,
            )
        finally:
            console.close()
        console.print_summary(result)
        return 0 if result["status"] in {"PASS", "DRY_RUN"} else 2

    if args.command == "analyze":
        print_run_config(
            "Benchmark analysis",
            (("Result path", args.result_path.resolve()),),
        )
        result = analyze_benchmark_root(args.result_path)
        print_run_summary(
            "Benchmark analysis",
            result["status"],
            (
                ("Models", ", ".join(result["models"])),
                ("Model count", result["model_count"]),
                ("Analysis root", result["analysis_root"]),
            ),
        )
        return 0

    print_run_config(
        "Reference replay",
        (
            ("Run ID", args.run_id),
            ("World", args.world_path.resolve()),
            ("Task", args.task_path.resolve()),
            ("Domain", args.domain_path.resolve()),
            ("Result directory", args.result_dir.resolve()),
        ),
    )
    result = evaluate_reference_case(
        args.world_path,
        args.task_path,
        domain_path=args.domain_path,
    )
    output = args.result_dir / args.run_id / "evaluation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, result)
    passed = result["evaluation_report"]["task_success"] is True
    print_run_summary(
        "Reference replay",
        "PASS" if passed else "FAIL",
        (
            ("Run ID", args.run_id),
            ("Output", output.resolve()),
        ),
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
