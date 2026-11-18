"""Thin production CLI for one task sampled from an existing world."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.contracts import load_json
from src.utils import print_run_config, print_run_summary
from src.world_distill.pipeline import (
    generate_task,
    TaskAuthoringError,
    TaskAuthoringInput,
)


def parse_args() -> argparse.Namespace:
    """Parse single-task authoring arguments."""
    parser = argparse.ArgumentParser(
        description="Generate and validate one offline template task candidate"
    )
    parser.add_argument("--authoring_run_id", required=True)
    parser.add_argument("--scenario_id", required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--domain_path", type=Path, required=True)
    parser.add_argument("--source_world_root", type=Path, required=True)
    parser.add_argument("--task_output_root", type=Path, required=True)
    parser.add_argument("--run_output_root", type=Path, required=True)
    parser.add_argument("--task_constraints", type=Path, required=True)
    parser.add_argument("--random_seed", type=int, required=True)
    parser.add_argument("--initial_tweak_count", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    """Author and validate one task sampled from an existing world."""
    args = parse_args()
    print_run_config(
        "Task authoring",
        (
            ("Run ID", args.authoring_run_id),
            ("Scenario", args.scenario_id),
            ("Domain", args.domain),
            ("Source world", args.source_world_root.resolve()),
            ("Constraints", args.task_constraints.resolve()),
            ("Instruction source", "rule template"),
            ("Seed", args.random_seed),
        ),
    )
    request = TaskAuthoringInput(
        authoring_run_id=args.authoring_run_id,
        scenario_id=args.scenario_id,
        domain=args.domain,
        domain_path=args.domain_path,
        source_world_root=args.source_world_root,
        task_output_root=args.task_output_root,
        run_output_root=args.run_output_root,
        task_constraints=load_json(args.task_constraints),
        random_seed=args.random_seed,
        initial_tweak_count=args.initial_tweak_count,
    )
    try:
        output = generate_task(request)
    except TaskAuthoringError as error:
        print_run_summary(
            "Task authoring",
            "FAIL",
            (("Failure record", error.failure_path),),
        )
        return 1
    print_run_summary(
        "Task authoring",
        "PASS",
        (
            ("Scenario", output.scenario_id),
            ("World root", output.world_root),
            ("Task root", output.task_root),
            ("Validation", output.validation_metadata_path),
            ("Resumed", output.resumed),
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
