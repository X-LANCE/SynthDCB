"""CLI for adding placement constraints to one existing type list."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.utils import RUN_DIR, print_run_config, print_run_summary
from src.world_distill.pipeline.list_creation.object_class_placement import (
    PLACEMENT_MODEL,
    create_placement_type_list,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse placement-generation arguments."""
    parser = argparse.ArgumentParser(
        description="Add Domain placement constraints to an existing type list"
    )
    parser.add_argument("--type_list", type=Path, required=True)
    parser.add_argument("--layout_catalog", type=Path, required=True)
    parser.add_argument("--output_root", type=Path, required=True)
    parser.add_argument(
        "--run_root", type=Path,
        help="Request and attempt logs; defaults to run/<output-root name>/placement.",
    )
    parser.add_argument("--model", default=PLACEMENT_MODEL)
    parser.add_argument(
        "--max_generation_attempts",
        type=int,
        choices=(1, 2),
        default=2,
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Generate, validate, and persist the enriched type list."""
    args = parse_args(argv)
    run_root = (
        args.run_root or RUN_DIR / args.output_root.resolve().name / "placement"
    ).resolve()
    print_run_config(
        "Type-list placement",
        (
            ("Type list", args.type_list.resolve()),
            ("Layout catalog", args.layout_catalog.resolve()),
            ("Output root", args.output_root.resolve()),
            ("Run root", run_root),
            ("Model", args.model),
            ("Generation attempts per batch", args.max_generation_attempts),
            ("Transport attempts per call", 1),
        ),
    )
    output = create_placement_type_list(
        args.type_list,
        args.layout_catalog,
        args.output_root,
        run_root=run_root,
        model=args.model,
        max_generation_attempts=args.max_generation_attempts,
    )
    print_run_summary("Type-list placement", "PASS", (("Output", output),))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
