"""CLI for the production world-pool -> task-pool generation pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.utils import print_run_config, print_run_summary
from src.world_distill.pipeline import generate_scenarios
from src.world_distill.pipeline.scenario_creation.scenario_plan import (
    load_scenario_plan,
)
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse world/task scenario-generation arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate reusable random worlds and then validated task bundles"
        )
    )
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument(
        "--stage",
        choices=("all", "worlds", "tasks"),
        default="all",
    )
    parser.add_argument("--max_workers", type=int)
    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
) -> int:
    """Run the selected scenario-generation stages."""
    args = parse_args(argv)
    print_run_config(
        "Scenario generation",
        (
            ("Plan", args.plan.resolve()),
            ("Stage", args.stage),
            ("Workers", args.max_workers or "plan default"),
        ),
    )
    request = load_scenario_plan(
        args.plan,
        stage=args.stage,
        max_workers=args.max_workers,
    )
    output = generate_scenarios(
        request,
        show_progress=True,
    )
    fields: list[tuple[str, object]] = [("Plan", args.plan.resolve())]
    for name, stage in output.report["stages"].items():
        if stage is not None:
            fields.extend(
                (
                    (f"{name} count", stage["count"]),
                    (
                        f"{name} output",
                        stage[
                            "world_list"
                            if name == "world_generation"
                            else "task_list"
                        ],
                    ),
                    (f"{name} resumed", stage["resumed"]),
                )
            )
    print_run_summary(
        "Scenario generation",
        output.report["status"],
        fields,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
