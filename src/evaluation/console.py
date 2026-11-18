"""Colored terminal presentation for dataset benchmark runs."""

from __future__ import annotations

from argparse import Namespace
import sys
from typing import Any

from src.utils import (
    load_json,
    print_run_config,
    print_run_summary,
    print_status,
    progress_bar,
)


class RunConsole:
    """Render v1-style deployment messages, progress, and final metrics."""

    def __init__(self) -> None:
        """Initialize the console without an active progress bar."""
        self._bar: Any | None = None

    def handle(self, event: dict[str, Any]) -> None:
        """Render one benchmark progress event."""
        name = event["event"]
        if name == "preparation_start":
            self.close()
            self._bar = progress_bar(
                total=event["total"],
                description=event["description"],
                unit=event.get("unit", "task"),
            )
        elif name == "preparation_progress" and self._bar is not None:
            self._bar.update(event["finished"] - self._bar.n)
        elif name == "preparation_complete":
            self.close()
        elif name == "deployment_start":
            print_status(
                f"Deploying and validating {event['task_count']} tasks...",
            )
        elif name == "deployment_complete":
            print_status(
                f"Deployment ready: {event['task_count']} tasks.",
                "success",
            )
        elif name == "attempt_start":
            cached = event["cached_attempts"]
            total = event["jobs_total"]
            if cached:
                print_status(
                    f"Loaded {cached} cached attempts; {total} remain.",
                )
            if total:
                self._bar = progress_bar(
                    total=total,
                    description="Dataset evaluation",
                    unit="sample",
                )
                self._refresh(event)
            else:
                print_status(
                    "No pending attempts. Loaded cached results.",
                    "success",
                )
        elif name == "attempt_progress" and self._bar is not None:
            self._bar.update(event["jobs_finished"] - self._bar.n)
            self._refresh(event)

    def close(self) -> None:
        """Close and discard the active progress bar."""
        if self._bar is not None:
            self._bar.close()
            self._bar = None

    def _refresh(self, event: dict[str, Any]) -> None:
        """Refresh benchmark counters on the active progress bar."""
        todo = max(
            event["expected_attempts"] - event["attempts_finished"],
            0,
        )
        self._bar.set_postfix_str(
            " ".join(
                (
                    f"tokens={event['total_tokens']:,}",
                    f"input={event['input_tokens']:,}",
                    f"output={event['output_tokens']:,}",
                    f"turns={event['turns']:,}",
                    f"pass={event['passed']}",
                    f"fail={event['failed']}",
                    f"retry={event['retryable']}",
                    f"invalid={event['invalid']}",
                    f"todo={todo}",
                )
            ),
            refresh=True,
        )

    @staticmethod
    def print_configuration(args: Namespace, task_count: int | None = None) -> None:
        """Print the effective dataset-evaluation configuration."""
        variant_mode = args.style is not None
        samples = args.samples_per_instruction if variant_mode else args.samples_per_task
        attempts = task_count * samples if task_count is not None else "pending"
        print_run_config(
            "Dataset evaluation",
            (
                ("Model", args.model),
                ("Agent strategy", getattr(args, "agent_strategy", "react")),
                ("Tasks", task_count if task_count is not None else "pending"),
                (
                    "Instruction style",
                    args.style or "default instruction",
                ),
                (
                    "Samples per task",
                    samples,
                ),
                ("Total attempts", attempts),
                ("Max turns", args.max_turns),
                ("Workers", args.num_workers),
                (
                    "Tool parse recovery",
                    "yes" if args.recover_tool_call_errors else "no",
                ),
                ("Resume", "no" if args.no_resume else "yes"),
                ("Output", args.result_path or f"auto under {args.result_dir or 'results'}"),
            ),
        )
        sys.stdout.flush()

    @staticmethod
    def print_dataset_ready(args: Namespace, task_count: int) -> None:
        """Report exact counts and the output path after input discovery."""
        samples = args.samples_per_instruction if args.style else args.samples_per_task
        print_status(
            f"Dataset ready: Tasks={task_count}, Total attempts={task_count * samples}, "
            f"Output={args.result_path}"
        )
        sys.stdout.flush()

    @staticmethod
    def print_summary(result: dict[str, Any]) -> None:
        """Print the final dataset-evaluation metrics."""
        status = result["status"]
        fields: list[tuple[str, object]] = [
            ("Model", result["model"]),
            ("Tasks", result["task_count"]),
        ]

        if status == "PASS":
            report = load_json(result["model_report"])
            overall = report["overall"]
            averages = overall["averages"]
            counts = overall["applicable_counts"]
            task_count = overall["task_count"]
            attempt_count = overall["attempt_count"]
            pass_at_n = ", ".join(
                f"Pass@{key}={round(value * task_count)}/{task_count} "
                f"({value:.2%})"
                for key, value in overall["pass_at_n"].items()
            )
            fields.extend(
                (
                    (
                        "Samples",
                        f"{attempt_count} "
                        f"({report['samples_per_task']} per task)",
                    ),
                    ("Pass@n", pass_at_n),
                )
            )

            for label, key in (
                ("Sample success", "sample_success_rate"),
                ("State success", "state_success_rate"),
                ("Property accuracy", "property_accuracy"),
                ("Object property", "object_property_accuracy"),
                ("Space property", "space_property_accuracy"),
                ("Action success", "action_success_rate"),
                ("Answer accuracy", "answer_accuracy"),
                ("Report accuracy", "report_accuracy"),
                ("Report count accuracy", "report_count_accuracy"),
                ("Report semantic accuracy", "report_semantic_accuracy"),
                ("Memory success", "memory_success_rate"),
                ("Time constraint", "time_constraint_success_rate"),
                ("Effect replay", "effect_replay_rate"),
                ("Time-plan valid", "time_plan_valid_rate"),
                ("False complete", "false_complete_rate"),
            ):
                value = averages[key]
                if value is not None:
                    fields.append(
                        (label, f"{value:.2%} (n={counts[key]})")
                    )

            for label, key, suffix in (
                ("Avg side effects", "unexpected_side_effect_count", ""),
                ("Avg turns", "turns", ""),
                ("Avg tool calls", "tool_calls", ""),
                ("Avg failed calls", "failed_calls", ""),
                ("Avg model calls", "model_calls", ""),
                ("Avg API requests", "api_requests", ""),
                ("Avg latency", "latency_seconds", "s"),
            ):
                value = averages[key]
                if value is not None:
                    fields.append((label, f"{value:.2f}{suffix}"))
            usage = overall["usage_totals"]
            fields.extend(
                (
                    ("API requests", f"{usage['api_requests']:,}"),
                    (
                        "Total tokens",
                        f"{usage['total_tokens']:,} "
                        f"(input={usage['input_tokens']:,}, "
                        f"output={usage['output_tokens']:,}, "
                        f"cached={usage.get('cached_tokens', 0):,}, "
                        f"reasoning={usage.get('reasoning_tokens', 0):,})",
                    ),
                )
            )
        elif status == "INCOMPLETE":
            progress = result["progress"]
            fields.append(
                (
                    "Progress",
                    f"completed={progress['completed']}, "
                    f"retryable={progress['retryable']}, "
                    f"invalid={progress['invalid']}, "
                    f"pending={progress['pending']}",
                )
            )
        else:
            fields.extend(
                (
                    ("Planned attempts", result["attempt_count"]),
                    ("Maximum calls", result["maximum_model_calls"]),
                )
            )
        fields.append(("Output", result["result_path"]))
        print_run_summary("Dataset evaluation", status, fields)
