"""Multi-sample benchmark runner with empirical pass@k aggregation."""

from __future__ import annotations

import csv
import re
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from functools import cached_property
from os import scandir
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Iterator, Sequence, TypeVar

from src.utils import DEVICES_DIR, RESULTS_DIR, write_json, write_jsonl
from src.contracts import ContractPackage, load_json
from src.contracts.errors import EnvironmentContractError
from src.runtime import DomainRuntimeCache, World, WorldBlueprint
from src.utils.llm import get_llm_config

from ..loading import TaskBundle, TaskLoader
from src.utils.llm.context_caller import create_openai_client, is_context_length_error
from ..agent_factory import agent_system_prompt, create_agent
from ..interfaces import (
    BaseAgent,
    AgentModelMismatchError,
    AgentProtocolError,
    AgentTransportError,
)
from ..validation import (
    MemoryJudgeError,
    apply_memory_judge,
    evaluate_world,
    judge_memory_content,
    memory_content_checks,
)
from ..validation.workflow import complete_background_simulation
from ..validation.memory_judger import memory_driver_context
from ..validation.report_judger import (
    ReportJudgeError, apply_report_judge, judge_reports, report_judge_context,
)
from .runner import AgentRun, AgentRunner
from .trajectory import TrajectoryExecutor


# Temporarily disabled for resuming existing runs after configuration changes.
CHECK_RESUME_CONFIG = False

INSTRUCTION_SOURCES = ("template", "llm")
EVALUATION_STYLES = (
    "template", "direct", "concise", "polite", "conversational",
    "distracting", "folk", "implicit",
)

_Item = TypeVar("_Item")


def _preparation_steps(
    items: Sequence[_Item],
    description: str,
    callback: Callable[[dict[str, Any]], None] | None,
) -> Iterator[_Item]:
    """Expose preparation progress without coupling the runner to a terminal."""
    if callback is not None:
        callback({"event": "preparation_start", "description": description, "total": len(items)})
    for index, item in enumerate(items, 1):
        yield item
        if callback is not None:
            callback({"event": "preparation_progress", "finished": index})
    if callback is not None:
        callback({"event": "preparation_complete"})


@dataclass(frozen=True)
class BatchCase:
    """One scenario and its optional private reference trajectory."""

    case_id: str
    world_dir: Path
    task_root: Path | None = None
    reference_trajectory: dict[str, Any] | None = None


@dataclass(frozen=True)
class BatchAttempt:
    """One sampled agent run with public grouping metadata."""

    case_id: str
    sample_index: int
    task_family: str
    task_subtype: str
    run: AgentRun


@dataclass(frozen=True)
class BatchRun:
    """Aggregate benchmark report and every underlying attempt."""

    benchmark_report: dict[str, Any]
    attempts: tuple[BatchAttempt, ...]

    def write(self, output_dir: str | Path) -> None:
        """Write aggregate, trajectory, and per-attempt reports as JSON."""
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        write_json(root / "benchmark_report.json", self.benchmark_report)
        attempts_dir = root / "attempts"
        attempts_dir.mkdir(exist_ok=True)
        for attempt in self.attempts:
            stem = f"{attempt.case_id}_sample_{attempt.sample_index}"
            write_json(attempts_dir / f"{stem}.trajectory.json", attempt.run.trajectory)
            write_json(attempts_dir / f"{stem}.evaluation.json", attempt.run.report)


ProviderFactory = Callable[[BatchCase, int], BaseAgent]


def evaluate_reference_case(
    world_root: str | Path,
    task_root: str | Path,
    *,
    domain_path: str | Path | None = None,
    contract_root: str | Path | None = None,
) -> dict[str, Any]:
    """Replay optional stored reference evidence and evaluate one case."""
    world = World(
        world_root,
        domain_path,
        domain=load_json(Path(world_root) / "world_init.json")["domain"]["type"],
        contract_root=contract_root,
    )
    bundle = TaskLoader(contract=world.contract).load(task_root, world)
    observed = None
    reference_snapshot = None
    if bundle.reference_trajectory is not None:
        observed = TrajectoryExecutor(
            world,
            task_id=bundle.task_id,
        ).replay(bundle.reference_trajectory)
        complete_background_simulation(world, bundle)
        reference_snapshot = world.get_state()
    report = evaluate_world(
        world,
        bundle,
        replay_reference_snapshot=reference_snapshot,
    )
    return {
        "world_id": world.get_state()["world_id"],
        "task_id": bundle.task_id,
        "reference_trajectory": observed,
        "evaluation_report": report,
    }


class BatchRunner:
    """Run k fresh providers per case and aggregate outcome-based metrics."""

    def __init__(
        self,
        cases: Sequence[BatchCase],
        provider_factory: ProviderFactory,
        *,
        samples_per_case: int,
        max_turns: int,
        domain_path: str | Path | None = None,
        contract_root: str | Path | None = None,
        require_device_tool_discovery: bool = True,
    ) -> None:
        """Freeze cases, provider factory, and per-sample runtime limits."""
        if not cases:
            raise ValueError("cases must not be empty")
        if samples_per_case < 1:
            raise ValueError("samples_per_case must be positive")
        if max_turns < 1:
            raise ValueError("max_turns must be positive")
        self.cases = tuple(cases)
        self.provider_factory = provider_factory
        self.samples_per_case = samples_per_case
        self.max_turns = max_turns
        self.domain_path = domain_path
        self.contract_root = contract_root
        self.require_device_tool_discovery = require_device_tool_discovery
        self.contract = ContractPackage(contract_root)

    def run(self, *, run_id: str) -> BatchRun:
        """Execute all attempts and return a validated benchmark report."""
        attempts: list[BatchAttempt] = []
        for case in self.cases:
            reference_snapshot = self._reference_snapshot(case)
            for sample_index in range(1, self.samples_per_case + 1):
                runner = AgentRunner(
                    case.world_dir,
                    self.provider_factory(case, sample_index),
                    task_root=case.task_root,
                    domain_path=self.domain_path,
                    contract_root=self.contract_root,
                    max_turns=self.max_turns,
                    require_device_tool_discovery=(
                        self.require_device_tool_discovery
                    ),
                )
                run = runner.run(
                    trajectory_id=(
                        f"{case.case_id}_sample_{sample_index}"
                    ),
                    replay_reference_snapshot=reference_snapshot,
                )
                attempts.append(
                    BatchAttempt(
                        case_id=case.case_id,
                        sample_index=sample_index,
                        task_family=runner.task_bundle.task["meta"]["task_family"],
                        task_subtype=runner.task_bundle.task["meta"]["task_subtype"],
                        run=run,
                    )
                )

        report = self._aggregate(run_id, attempts)
        self.contract.validate_schema(
            report,
            "urn:dcb:v2:schema:benchmark-report",
        )
        return BatchRun(
            benchmark_report=report,
            attempts=tuple(attempts),
        )

    def _reference_snapshot(
        self,
        case: BatchCase,
    ) -> dict[str, Any] | None:
        """Replay private reference evidence through the executor."""
        world = World(
            case.world_dir,
            self.domain_path,
            domain=load_json(Path(case.world_dir) / "world_init.json")["domain"]["type"],
            contract_root=self.contract_root,
        )
        bundle = TaskLoader(contract=world.contract).load(
            case.task_root or case.world_dir,
            world,
        )
        trajectory = (
            case.reference_trajectory
            if case.reference_trajectory is not None
            else bundle.reference_trajectory
        )
        if trajectory is None:
            return None
        TrajectoryExecutor(
            world,
            task_id=bundle.task_id,
        ).replay(trajectory)
        complete_background_simulation(world, bundle)
        return world.get_state()

    def _aggregate(
        self,
        run_id: str,
        attempts: list[BatchAttempt],
    ) -> dict[str, Any]:
        """Aggregate raw attempts, pass@k, and public task breakdowns."""
        reports = [attempt.run.report for attempt in attempts]
        assertion_accuracies = [
            (
                sum(item["passed"] for item in report["assertions"])
                / len(report["assertions"])
                if report["assertions"]
                else 1.0
            )
            for report in reports
        ]
        answer_accuracies = [
            report["metrics"]["answer_accuracy"]
            for report in reports
            if report["metrics"]["answer_accuracy"] is not None
        ]
        list_recalls = [report["metrics"]["list_answer_recall"] for report in reports if report["metrics"].get("list_answer_recall") is not None]
        report_accuracies = [
            report["metrics"]["report_accuracy"]
            for report in reports
            if report["metrics"]["report_accuracy"] is not None
        ]
        report_counts = [report["metrics"]["report_count_accuracy"] for report in reports if report["metrics"]["report_count_accuracy"] is not None]
        report_semantics = [report["metrics"]["report_semantic_accuracy"] for report in reports if report["metrics"]["report_semantic_accuracy"] is not None]
        return {
            "run_id": run_id,
            "sample_count": len(attempts),
            "metrics": {
                "scenario_pass_rate": self._mean(
                    [report["task_success"] for report in reports]
                ),
                "pass_at_n": self._pass_at_n(attempts),
                "avg_property_accuracy": self._mean(
                    assertion_accuracies
                ),
                "avg_action_success_rate": self._mean(
                    [
                        report["metrics"]["action_success_rate"]
                        for report in reports
                    ]
                ),
                "avg_turns": self._mean(
                    [
                        report["trajectory_summary"]["turns"]
                        for report in reports
                    ]
                ),
                "avg_total_actions": self._mean(
                    [
                        report["trajectory_summary"]["total_tool_calls"]
                        for report in reports
                    ]
                ),
                "avg_answer_accuracy": (
                    self._mean(answer_accuracies)
                    if answer_accuracies
                    else None
                ),
                "avg_list_answer_recall": self._mean(list_recalls) if list_recalls else None,
                "avg_report_accuracy": (
                    self._mean(report_accuracies)
                    if report_accuracies
                    else None
                ),
                "avg_report_count_accuracy": self._mean(report_counts) if report_counts else None,
                "avg_report_semantic_accuracy": self._mean(report_semantics) if report_semantics else None,
            },
            "breakdowns": {
                "task_family": self._breakdown(
                    attempts,
                    lambda attempt: attempt.task_family,
                ),
                "task_subtype": self._breakdown(
                    attempts,
                    lambda attempt: attempt.task_subtype,
                ),
                "task_category": self._breakdown(
                    attempts,
                    lambda attempt: (
                        f"{attempt.task_family}.{attempt.task_subtype}"
                    ),
                ),
                "termination_reason": self._breakdown(
                    attempts,
                    lambda attempt: attempt.run.report["termination"][
                        "reason"
                    ],
                ),
            },
        }

    def _pass_at_n(
        self,
        attempts: list[BatchAttempt],
    ) -> dict[str, float]:
        """Compute empirical task pass@1 through pass@k from ordered samples."""
        by_case = {
            case.case_id: sorted(
                (
                    attempt
                    for attempt in attempts
                    if attempt.case_id == case.case_id
                ),
                key=lambda attempt: attempt.sample_index,
            )
            for case in self.cases
        }
        return {
            str(n): self._mean(
                [
                    any(
                        attempt.run.report["task_success"]
                        for attempt in case_attempts[:n]
                    )
                    for case_attempts in by_case.values()
                ]
            )
            for n in range(1, self.samples_per_case + 1)
        }

    @staticmethod
    def _breakdown(
        attempts: list[BatchAttempt],
        key: Callable[[BatchAttempt], str],
    ) -> dict[str, dict[str, Any]]:
        """Group attempt count and pass rate by one public metadata field."""
        groups: dict[str, list[BatchAttempt]] = {}
        for attempt in attempts:
            groups.setdefault(key(attempt), []).append(attempt)
        return {
            name: {
                "attempt_count": len(group),
                "pass_rate": BatchRunner._mean(
                    [
                        attempt.run.report["task_success"]
                        for attempt in group
                    ]
                ),
            }
            for name, group in sorted(groups.items())
        }

    @staticmethod
    def _mean(values: Sequence[int | float | bool]) -> float:
        """Return the arithmetic mean for a non-empty metric sequence."""
        return sum(values) / len(values)


@dataclass(frozen=True)
class DatasetCase:
    """Paths for one task; task and world payloads are loaded on demand."""

    task_id: str
    task_root: Path
    world_root: Path
    domain_path: Path

    def _task_artifact_path(self, filename: str) -> Path:
        """Return a flat artifact with legacy-private fallback."""
        path = self.task_root / filename
        return (
            path
            if path.is_file()
            else self.task_root / "private" / filename
        )

    @cached_property
    def _task(self) -> dict[str, Any]:
        """Return the task."""
        task = load_json(self.task_root / "task.json")
        if task["task_id"] != self.task_id:
            raise ValueError(
                f"task id mismatch: directory={self.task_id}, "
                f"file={task['task_id']}"
            )
        return task

    @cached_property
    def _world(self) -> dict[str, Any]:
        """Return the world."""
        return load_json(self.world_root / "world_init.json")

    @cached_property
    def _target(self) -> dict[str, Any]:
        """Return the target."""
        return load_json(self._task_artifact_path("target.json"))

    @cached_property
    def _validation(self) -> dict[str, Any]:
        """Return the validation."""
        return load_json(self._task_artifact_path("validation_metadata.json"))

    @property
    def domain(self) -> str:
        """Return the domain."""
        return str(self._world["domain"]["type"])

    @property
    def task_family(self) -> str:
        """Return the task family."""
        return str(self._task["meta"]["task_family"])

    @property
    def task_subtype(self) -> str:
        """Return the task subtype."""
        return str(self._task["meta"]["task_subtype"])

    @property
    def task_category(self) -> str:
        """Return the task category."""
        return f"{self.task_family}.{self.task_subtype}"

    @property
    def has_object_target(self) -> bool:
        """Return whether the case targets an object."""
        return bool(self._target["objects"])

    @property
    def has_space_target(self) -> bool:
        """Return whether the case targets a space."""
        return bool(self._target["spaces"])

    @property
    def has_answers(self) -> bool:
        """Return whether the case expects submitted answers."""
        return bool(self._target["expected_answers"])

    @property
    def has_reports(self) -> bool:
        """Return whether the case expects submitted reports."""
        return bool(self._target["expected_reports"])

    @property
    def uses_memory(self) -> bool:
        """Return whether the case reads or writes memory."""
        return bool(
            self._target["required_memory_ids"]
            or self._target.get("expected_memory_mutations", [])
        )

    @property
    def has_time_constraint(self) -> bool:
        """Return whether the case has a time constraint."""
        return self._target["time_constraint"] is not None


@dataclass(frozen=True)
class DatasetAttemptPlan:
    """One task attempt bound to an optional instruction variant."""

    case: DatasetCase
    sample_index: int
    instruction_source: str | None = None
    instruction_style: str | None = None
    instruction: str | None = None
    instruction_index: int | None = None
    instruction_variant_index: int | None = None
    instruction_repeat_index: int | None = None


def _select_instruction_variants(
    task: dict[str, Any],
    source: str,
    count: int | None,
    style: str | None = None,
) -> tuple[tuple[int, str, str], ...]:
    """Select matching variants in stored order, cycling when count is larger."""
    if source not in INSTRUCTION_SOURCES:
        raise ValueError(f"unknown instruction source {source!r}")
    if count is not None and (
        not isinstance(count, int) or isinstance(count, bool) or count < 1
    ):
        raise ValueError("instruction_count must be a positive integer")
    available_list: list[tuple[int, str, str]] = []
    for variant in task.get("instruction_variants", []):
        if (
            isinstance(variant, list)
            and len(variant) == 3
            and variant[0] == source
        ):
            available_list.append(
                (len(available_list) + 1, str(variant[1]), str(variant[2]))
            )
    available = tuple(
        item for item in available_list
        if style in (None, "template") or item[1] == style
    )
    if not available:
        raise ValueError(
            f"task {task.get('task_id')} has no {source} instruction variants"
            + (f" for style {style!r}" if style is not None else "")
        )
    selected_count = len(available) if count is None else count
    return tuple(available[index % len(available)] for index in range(selected_count))


def _plan_dataset_attempts(
    cases: Sequence[DatasetCase],
    *,
    samples_per_task: int,
    instruction_source: str | None,
    samples_per_instruction: int | None,
    instruction_count: int | None,
    instruction_style: str | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[DatasetAttemptPlan, ...]:
    """Return deterministic attempt plans for default or selected instructions."""
    if instruction_style is not None:
        if instruction_style not in EVALUATION_STYLES:
            raise ValueError(f"unknown instruction style {instruction_style!r}")
        source = "template" if instruction_style == "template" else "llm"
        if instruction_source not in (None, source):
            raise ValueError("instruction_source conflicts with instruction_style")
        if instruction_count is not None:
            raise ValueError("instruction_count cannot be combined with instruction_style")
        instruction_source = source
    if instruction_source is None:
        if samples_per_instruction is not None or instruction_count is not None:
            raise ValueError(
                "instruction_source is required with instruction variant options"
            )
        return tuple(
            DatasetAttemptPlan(case=case, sample_index=sample_index)
            for case in cases
            for sample_index in range(1, samples_per_task + 1)
        )
    if type(samples_per_instruction) is not int or samples_per_instruction < 1:
        raise ValueError("samples_per_instruction must be positive")
    plans: list[DatasetAttemptPlan] = []
    for case in _preparation_steps(cases, "Planning instructions", progress_callback):
        sample_index = 0
        variants = _select_instruction_variants(
            case._task,
            instruction_source,
            samples_per_instruction if instruction_style is not None else instruction_count,
            style=instruction_style,
        )
        repeats = 1 if instruction_style is not None else samples_per_instruction
        for instruction_index, (variant_index, style, instruction) in enumerate(
            variants,
            start=1,
        ):
            for repeat_index in range(1, repeats + 1):
                sample_index += 1
                plans.append(
                    DatasetAttemptPlan(
                        case=case,
                        sample_index=sample_index,
                        instruction_source=instruction_source,
                        instruction_style=style,
                        instruction=instruction,
                        instruction_index=instruction_index,
                        instruction_variant_index=variant_index,
                        instruction_repeat_index=repeat_index,
                    )
                )
    return tuple(plans)


def resolve_dataset_input(
    task_path: str | Path,
    *,
    domain_path: str | Path | None = None,
    max_tasks: int | None = None,
    max_tasks_per_category: int | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[DatasetCase, ...]:
    """Resolve task directories and apply deterministic uniform sampling."""
    source = Path(task_path).resolve()
    resolved_domain_root = (
        Path(domain_path).resolve() if domain_path is not None else None
    )
    for name, value in (
        ("max_tasks", max_tasks),
        ("max_tasks_per_category", max_tasks_per_category),
    ):
        if value is not None and value < 1:
            raise ValueError(f"{name} must be positive")
    if max_tasks is not None and max_tasks_per_category is not None:
        raise ValueError(
            "max_tasks and max_tasks_per_category are mutually exclusive"
        )

    if source.is_file():
        if source.suffix.lower() not in {".txt", ".list"}:
            raise ValueError("task_path file must use .txt or .list")
        task_dirs = []
        for line in _preparation_steps(
            source.read_text(encoding="utf-8").splitlines(),
            "Reading task list",
            progress_callback,
        ):
            value = line.strip()
            if not value:
                continue
            path = Path(value)
            task_dirs.append(
                (path if path.is_absolute() else source.parent / path).resolve()
            )
    elif source.is_dir():
        task_dirs = sorted(
            (Path(entry.path) for entry in scandir(source) if entry.is_dir()),
            key=lambda path: path.name,
        )
    else:
        raise FileNotFoundError(source)

    if not task_dirs:
        raise ValueError("task_path contains no task directories")
    for task_dir in _preparation_steps(task_dirs, "Checking task directories", progress_callback):
        if not task_dir.is_dir():
            raise FileNotFoundError(task_dir)
    task_dirs = sorted(task_dirs, key=lambda path: path.name)
    task_ids = [path.name for path in task_dirs]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("dataset contains duplicate task ids")

    cases: list[DatasetCase] = []
    for case_task_root in _preparation_steps(task_dirs, "Loading dataset", progress_callback):
        task_id = case_task_root.name
        dataset_root = case_task_root.parent.parent
        embedded_world_root = (
            case_task_root
            if (case_task_root / "world_init.json").is_file()
            else dataset_root / "task_worlds" / task_id
        )
        model_root = resolved_domain_root
        if model_root is None:
            domain = load_json(embedded_world_root / "world_init.json")["domain"]["type"]
            local_models = dataset_root / "environment" / domain
            model_root = local_models if local_models.is_dir() else DEVICES_DIR / domain
        cases.append(
            DatasetCase(
                task_id=task_id,
                task_root=case_task_root,
                world_root=embedded_world_root,
                domain_path=model_root,
            )
        )
    if max_tasks_per_category is not None:
        groups: dict[str, list[DatasetCase]] = {}
        for case in _preparation_steps(cases, "Sampling task categories", progress_callback):
            groups.setdefault(case.task_category, []).append(case)
        cases = sorted(
            (
                case
                for group in groups.values()
                for case in _uniform_sample(group, max_tasks_per_category)
            ),
            key=lambda case: case.task_id,
        )
    elif max_tasks is not None:
        cases = _uniform_sample(cases, max_tasks)
    return tuple(cases)


def _uniform_sample(items: Sequence[Any], limit: int) -> list[Any]:
    """Return the uniform sample."""
    if limit >= len(items):
        return list(items)
    return [items[index * len(items) // limit] for index in range(limit)]


def initialize_result_path(
    *,
    result_path: str | Path | None,
    result_dir: str | Path | None,
    model: str,
    force_overwrite: bool,
    domain: str | None = None,
) -> Path:
    """Create a result path or reuse an existing directory for resume."""
    if result_path is not None and result_dir is not None:
        raise ValueError("result_path and result_dir are mutually exclusive")
    if result_path is None:
        if not domain:
            raise ValueError("domain is required for an automatic result path")
        base = Path(result_dir or RESULTS_DIR)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result = base / f"{_model_slug(domain)}_{_model_slug(model)}_{stamp}"
    else:
        result = Path(result_path)
    result = result.resolve()
    if result.exists():
        if force_overwrite:
            if result.is_dir():
                shutil.rmtree(result)
            else:
                result.unlink()
        elif not result.is_dir():
            raise FileExistsError(
                f"result path is not a directory; use --force_overwrite: {result}"
            )
        else:
            return result
    result.mkdir(parents=True)
    return result


def run_dataset_benchmark(
    cases: Sequence[DatasetCase],
    *,
    model: str,
    samples_per_task: int,
    max_turns: int,
    num_workers: int,
    max_transport_attempts: int,
    result_path: str | Path,
    client: Any | None = None,
    memory_judge_client: Any | None = None,
    report_judge_completion: Callable | None = None,
    dry_run: bool = False,
    no_resume: bool = False,
    device_tool_discovery: str = "required",
    recover_tool_call_errors: bool = False,
    instruction_source: str | None = None,
    samples_per_instruction: int | None = None,
    instruction_count: int | None = None,
    instruction_style: str | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    record_requests: bool = False,
    agent_strategy: str = "react",
) -> dict[str, Any]:
    """Run or resume one model over a deployed dataset."""
    if not cases:
        raise ValueError("cases must not be empty")
    if agent_strategy not in {"react", "toolcall"}:
        raise ValueError("unknown agent_strategy")
    provider_config = get_llm_config("eval")
    for name, value in (
        ("samples_per_task", samples_per_task),
        ("max_turns", max_turns),
        ("num_workers", num_workers),
        ("max_transport_attempts", max_transport_attempts),
    ):
        if value < 1:
            raise ValueError(f"{name} must be positive")
    if not model:
        raise ValueError("model must not be empty")
    if device_tool_discovery not in {"required", "optional"}:
        raise ValueError("device_tool_discovery must be required or optional")
    plans = _plan_dataset_attempts(
        cases,
        samples_per_task=samples_per_task,
        instruction_source=instruction_source,
        samples_per_instruction=samples_per_instruction,
        instruction_count=instruction_count,
        instruction_style=instruction_style,
        progress_callback=progress_callback,
    )
    if instruction_style is not None:
        instruction_source = "template" if instruction_style == "template" else "llm"
    attempts_by_task: dict[str, int] = {}
    for plan in plans:
        attempts_by_task[plan.case.task_id] = (
            attempts_by_task.get(plan.case.task_id, 0) + 1
        )
    max_samples_per_task = max(attempts_by_task.values())
    memory_judge_calls = sum(
        bool(plan.case._target.get("expected_memory_mutations", []))
        for plan in _preparation_steps(plans, "Reading evaluation targets", progress_callback)
    )
    memory_judge_config = get_llm_config("memory_judge")
    report_judge_calls = sum(bool(plan.case._target["expected_reports"]) for plan in plans)
    report_judge_config = get_llm_config("report_judge")
    report_judge_run_config = {
        "enabled": bool(report_judge_calls),
        "model": report_judge_config["model"], "endpoint": report_judge_config["base_url"],
        "requests_per_report_attempt": 1,
        "payload": "task, expected failure requests, relevant World inventory/state/property schemas/tools, submitted codes and descriptions",
        "audit_output": "attempts/<task_id>/sample_*.json::report_judge_audit",
    }

    output = Path(result_path).resolve()
    judge_audit_root = output / "models" / _model_slug(model)
    if instruction_source is not None:
        judge_audit_root /= f"instruction_sources/{instruction_source}"
    memory_judge_run_config = {
        "enabled": bool(memory_judge_calls),
        "model": memory_judge_config["model"],
        "endpoint": memory_judge_config["base_url"],
        "temperature": 0,
        "requests_per_write_attempt": 1,
        "payload": (
            "task instruction, expected memory facts, and candidate content"
        ),
        "audit_output": (
            "attempts/<task_id>/sample_*.json::memory_judge_audit"
        ),
    }
    if progress_callback is not None:
        progress_callback(
            {
                "event": "deployment_start",
                "task_count": len(cases),
                "result_path": str(output),
            }
        )
    deployment = _prepare_dataset(cases, output, progress_callback=progress_callback)
    if progress_callback is not None:
        progress_callback(
            {
                "event": "deployment_complete",
                "task_count": len(cases),
            }
        )
    estimate = {
        "model": model,
        "task_count": len(cases),
        "samples_per_task": max_samples_per_task,
        "attempt_count": len(plans),
        "maximum_model_calls": len(plans) * max_turns + memory_judge_calls + report_judge_calls,
        "maximum_agent_model_calls": len(plans) * max_turns,
        "maximum_memory_judge_calls": memory_judge_calls,
        "maximum_report_judge_calls": report_judge_calls,
        "report_judge": deepcopy(report_judge_run_config),
        "memory_judge": {
            **deepcopy(memory_judge_run_config),
            "audit_output": str(
                judge_audit_root
                / "attempts"
                / "<task_id>"
                / "sample_*.json::memory_judge_audit"
            ),
        },
        "result_path": str(output),
        "dataset_manifest": str(output / "dataset_manifest.json"),
        "recover_tool_call_errors": recover_tool_call_errors,
        "instruction_source": instruction_source,
        "instruction_style": instruction_style,
        "samples_per_instruction": samples_per_instruction,
        "instruction_count": instruction_count,
        "agent_strategy": agent_strategy,
    }
    if dry_run:
        return {"status": "DRY_RUN", **estimate}

    model_root = output / "models" / _model_slug(model)
    run_root = (
        model_root
        if instruction_source is None
        else model_root / "instruction_sources" / instruction_source
    )
    root_config_path = model_root / "config.json"
    if (
        instruction_source is not None
        and root_config_path.is_file()
        and "instruction_parts" not in load_json(root_config_path)
    ):
        raise ValueError(
            f"cannot combine instruction runs with a legacy model run: {model_root}"
        )
    if instruction_style is not None:
        for source in INSTRUCTION_SOURCES:
            other_config = model_root / "instruction_sources" / source / "config.json"
            if source != instruction_source and other_config.is_file():
                raise ValueError(
                    "instruction style config differs from existing checkpoint; "
                    "use a separate result_path for each style"
                )
    if no_resume and run_root.exists():
        shutil.rmtree(run_root)
    config = {
        "model": model,
        "samples_per_task": max_samples_per_task,
        "max_turns": max_turns,
        "interaction_contract": "builtin-tool-list-v2",
        "max_transport_attempts": max_transport_attempts,
        "device_tool_discovery": device_tool_discovery,
        "recover_tool_call_errors": recover_tool_call_errors,
        "task_ids": [case.task_id for case in cases],
        "dataset_manifest": str(output / "dataset_manifest.json"),
        "agent": {
            "protocol": agent_strategy,
            "agent_strategy": agent_strategy,
            "system_prompt": agent_system_prompt(agent_strategy),
            "endpoint": provider_config["base_url"],
            "temperature": provider_config.get("temperature", 0.0),
            "top_p": provider_config.get("top_p", 1.0),
            "max_response_tokens": provider_config.get(
                "max_response_tokens"
            ),
            "require_model_identity": False,
        },
        "memory_judge": deepcopy(memory_judge_run_config),
        "report_judge": deepcopy(report_judge_run_config),
    }
    if record_requests:
        config["agent"]["record_requests"] = True
    if instruction_source is not None:
        config.update(
            {
                "instruction_source": instruction_source,
                "samples_per_instruction": samples_per_instruction,
                "instruction_count": instruction_count,
                "attempt_count": len(plans),
            }
        )
    if instruction_style is not None:
        config["instruction_style"] = instruction_style
    config_path = run_root / "config.json"
    if config_path.is_file():
        stored_config = load_json(config_path)
        stored_config["agent"].setdefault("agent_strategy", "toolcall")
        if stored_config["agent"]["agent_strategy"] == "tool-calling":
            stored_config["agent"]["agent_strategy"] = "toolcall"
        if stored_config["agent"]["agent_strategy"] != agent_strategy:
            raise ValueError(
                f"agent strategy differs from existing checkpoint: {config_path}; "
                "use a separate result_path for each strategy"
            )
        if stored_config.get("interaction_contract") != config["interaction_contract"]:
            raise ValueError(
                "agent/environment interface differs from existing checkpoint; use a new result_path"
            )
        stored_config.setdefault("recover_tool_call_errors", False)
        stored_config["dataset_manifest"] = _path_identity(
            stored_config.get("dataset_manifest")
        )
        comparable_config = {
            **config,
            "dataset_manifest": _path_identity(config["dataset_manifest"]),
        }
        # Provider endpoints are transport settings, not benchmark identity.
        for section in ("agent", "memory_judge", "report_judge"):
            for candidate in (stored_config, comparable_config):
                if section in candidate:
                    candidate[section] = dict(candidate[section])
                    candidate[section].pop("endpoint", None)
        # Task membership may change; cached attempts remain keyed by task ID.
        for candidate in (stored_config, comparable_config):
            candidate.pop("task_ids", None)
            candidate.pop("attempt_count", None)
            for section in ("memory_judge", "report_judge"):
                candidate[section].pop("enabled", None)
                candidate[section].pop("prompt_version", None)
        # Older checkpoints enforced response model names; aliases are now accepted.
        for candidate in (stored_config, comparable_config):
            candidate["agent"].pop("require_model_identity", None)
        # Style/default plans have stable sample indices when their count changes.
        # Legacy multi-instruction repeat plans do not, so keep their strict guard.
        if instruction_style is not None or instruction_source is None:
            for candidate in (stored_config, comparable_config):
                for key in ("samples_per_task", "samples_per_instruction", "attempt_count"):
                    candidate.pop(key, None)
        if CHECK_RESUME_CONFIG and stored_config != comparable_config:
            raise ValueError(
                f"run config differs from existing checkpoint: {config_path}"
            )
    write_json(config_path, config)

    shared_client = client or create_openai_client("eval")
    shared_memory_judge_client = (
        memory_judge_client
        if memory_judge_client is not None
        else (
            create_openai_client("memory_judge")
            if memory_judge_calls
            else None
        )
    )
    jobs: list[tuple[DatasetAttemptPlan, Path]] = []
    cached_records: list[dict[str, Any]] = []
    for plan in _preparation_steps(plans, "Loading checkpoints", progress_callback):
        path = _attempt_path(run_root, plan.case.task_id, plan.sample_index)
        if path.is_file():
            saved = load_json(path)
            if saved["status"] not in {"retryable_error", "invalid"}:
                cached_records.append(saved)
                continue
        jobs.append((plan, path))

    live_metrics = _live_attempt_metrics(cached_records)
    if progress_callback is not None:
        progress_callback(
            {
                "event": "attempt_start",
                "jobs_total": len(jobs),
                "cached_attempts": len(cached_records),
                "expected_attempts": len(plans),
                **live_metrics,
            }
        )

    def execute(job: tuple[DatasetAttemptPlan, Path]) -> dict[str, Any]:
        """Execute a dataset benchmark job and return its report."""
        plan, path = job
        case = plan.case
        try:
            runtime_cache, blueprint, task_bundle, reference_snapshot = deployment.prepare_case(case)
        except (EnvironmentContractError, ValueError, OSError) as error:
            write_json(path.with_suffix(".initialization_error.json"), {"task_id": case.task_id, "stage": "world_initialization_or_reference", "exception_type": type(error).__name__, "error": str(error), "post_simulation": None})
            record = {
                "task_id": case.task_id,
                "sample_index": plan.sample_index,
                "requested_model": model,
                "status": "retryable_error",
                "task_success": False,
                "failure_kind": "initialization",
                "error": {"type": type(error).__name__, "message": str(error)},
            }
            write_json(path, record)
            return record
        if plan.instruction is not None:
            task_bundle = replace(
                task_bundle,
                task={**task_bundle.task, "instruction": plan.instruction},
            )
        record = _run_dataset_attempt(
            plan,
            model=model,
            max_turns=max_turns,
            max_transport_attempts=max_transport_attempts,
            reference_snapshot=reference_snapshot,
            runtime_cache=runtime_cache,
            blueprint=blueprint,
            task_bundle=task_bundle,
            client=shared_client,
            memory_judge_client=shared_memory_judge_client,
            report_judge_completion=report_judge_completion,
            require_device_tool_discovery=(
                device_tool_discovery == "required"
            ),
            recover_tool_call_errors=recover_tool_call_errors,
            record_requests=record_requests,
            agent_strategy=agent_strategy,
        )
        write_json(path, record)
        if record.get("post_simulation") is not None:
            for name, payload in record["post_simulation"].items():
                write_json(path.parent / f"{path.stem}_simulation" / f"{name}.json", payload)
        return record

    if jobs:
        status_counts: dict[str, int] = {}
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {executor.submit(execute, job): job for job in jobs}
            for finished_count, future in enumerate(
                as_completed(futures),
                start=1,
            ):
                record = future.result()
                status = str(record["status"])
                status_counts[status] = status_counts.get(status, 0) + 1
                for key, value in _live_attempt_metrics((record,)).items():
                    live_metrics[key] += value
                if progress_callback is not None:
                    progress_callback(
                        {
                            "event": "attempt_progress",
                            "jobs_finished": finished_count,
                            "jobs_total": len(jobs),
                            "expected_attempts": (
                                len(plans)
                            ),
                            "status_counts": dict(status_counts),
                            **live_metrics,
                        }
                    )

    records = _load_attempt_records(
        run_root,
        plans,
    )
    progress = _progress(records, len(plans))
    write_json(run_root / "progress.json", progress)
    if progress["pending"] or progress["retryable"] or progress["invalid"]:
        return {"status": "INCOMPLETE", **estimate, "progress": progress}

    reports = _write_model_reports(
        output,
        run_root,
        model=model,
        records=records,
        samples_per_task=max_samples_per_task,
    )
    if instruction_source is not None:
        reports = _write_combined_instruction_reports(
            output,
            model_root,
            model=model,
        )
    return {
        "status": "PASS",
        **estimate,
        "progress": progress,
        "benchmark_report": reports["benchmark_report"],
        "model_report": reports["model_report"],
    }


def _collect_instruction_part_records(
    model_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load completed instruction-source parts and assign combined indices."""
    configs: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    shared: dict[str, Any] | None = None
    for source in INSTRUCTION_SOURCES:
        part_root = model_root / "instruction_sources" / source
        config_path = part_root / "config.json"
        progress_path = part_root / "progress.json"
        if not config_path.is_file() or not progress_path.is_file():
            continue
        progress = load_json(progress_path)
        if any(progress[key] for key in ("pending", "retryable", "invalid")):
            continue
        config = load_json(config_path)
        if config.get("instruction_source") != source:
            raise ValueError(f"instruction source mismatch: {part_root}")
        current_shared = {
            key: config[key]
            for key in (
                "model",
                "task_ids",
                "max_turns",
                "max_transport_attempts",
                "device_tool_discovery",
                "recover_tool_call_errors",
                "agent",
                "memory_judge",
            )
        }
        current_shared["dataset_manifest"] = _path_identity(
            config["dataset_manifest"]
        )
        if shared is None:
            shared = current_shared
        elif current_shared != shared:
            raise ValueError(
                f"instruction-source runs use different settings: {part_root}"
            )
        if config.get("instruction_style") is not None:
            # Retain extra cached attempts on disk, but report only this run's prefix.
            part_records = [
                load_json(_attempt_path(part_root, task_id, sample_index))
                for task_id in config["task_ids"]
                for sample_index in range(1, config["samples_per_instruction"] + 1)
            ]
        else:
            part_records = [
                load_json(path)
                for task_id in config["task_ids"]
                for path in (part_root / "attempts" / task_id).glob("sample_*.json")
                if path.stem.removeprefix("sample_").isdigit()
            ]
        if len(part_records) != int(config["attempt_count"]):
            raise ValueError(f"instruction-source attempt count mismatch: {part_root}")
        configs.append(config)
        records.extend(part_records)
    if not configs:
        raise ValueError(f"no completed instruction-source runs under {model_root}")

    source_order = {
        source: index for index, source in enumerate(INSTRUCTION_SOURCES)
    }
    ordered = sorted(
        records,
        key=lambda record: (
            record["task_id"],
            source_order[record["instruction_source"]],
            record["instruction_index"],
            record["instruction_repeat_index"],
        ),
    )
    combined: list[dict[str, Any]] = []
    sample_indices: dict[str, int] = {}
    for record in ordered:
        task_id = str(record["task_id"])
        sample_indices[task_id] = sample_indices.get(task_id, 0) + 1
        combined.append(
            {
                **record,
                "source_sample_index": record["sample_index"],
                "sample_index": sample_indices[task_id],
            }
        )
    return configs, combined


def _write_combined_instruction_reports(
    output: Path,
    model_root: Path,
    *,
    model: str,
) -> dict[str, Any]:
    """Merge completed template/LLM parts and write one Pass@n report."""
    configs, records = _collect_instruction_part_records(model_root)
    if any(config["model"] != model for config in configs):
        raise ValueError("instruction-source runs use different models")
    samples_by_task: dict[str, int] = {}
    for record in records:
        task_id = str(record["task_id"])
        samples_by_task[task_id] = samples_by_task.get(task_id, 0) + 1
    samples_per_task = max(samples_by_task.values())
    shared = configs[0]
    combined_config = {
        key: shared[key]
        for key in (
            "model",
            "max_turns",
            "max_transport_attempts",
            "device_tool_discovery",
            "recover_tool_call_errors",
            "task_ids",
            "dataset_manifest",
            "agent",
            "memory_judge",
        )
    }
    combined_config.update(
        {
            "samples_per_task": samples_per_task,
            "attempt_count": len(records),
            "instruction_parts": [
                {
                    "instruction_source": config["instruction_source"],
                    **({"instruction_style": config["instruction_style"]}
                       if "instruction_style" in config else {}),
                    "samples_per_instruction": config["samples_per_instruction"],
                    "instruction_count": config["instruction_count"],
                }
                for config in configs
            ],
        }
    )
    root_config_path = model_root / "config.json"
    if root_config_path.is_file() and "instruction_parts" not in load_json(
        root_config_path
    ):
        raise ValueError(
            f"cannot combine instruction runs with a legacy model run: {model_root}"
        )
    write_json(root_config_path, combined_config)
    write_json(
        model_root / "progress.json",
        {
            "completed": len(records),
            "retryable": 0,
            "invalid": 0,
            "pending": 0,
            "expected": len(records),
        },
    )
    return _write_model_reports(
        output,
        model_root,
        model=model,
        records=records,
        samples_per_task=samples_per_task,
    )


def analyze_benchmark_root(result_path: str | Path) -> dict[str, Any]:
    """Compare completed model runs at or below one result path."""
    output = Path(result_path).resolve()
    model_roots = sorted(output.glob("models/*/config.json"))
    if not model_roots:
        model_roots = sorted(output.glob("*/models/*/config.json"))
    if not model_roots:
        raise ValueError(f"no model runs found under {output}")

    model_reports: dict[str, dict[str, Any]] = {}
    model_records: dict[str, list[dict[str, Any]]] = {}
    comparison_config: dict[str, Any] | None = None
    for config_path in model_roots:
        model_root = config_path.parent
        config = load_json(config_path)
        config.setdefault("recover_tool_call_errors", False)
        current_config = {
            key: config[key]
            for key in (
                "task_ids",
                "samples_per_task",
                "max_turns",
                "max_transport_attempts",
                "device_tool_discovery",
                "recover_tool_call_errors",
                "agent",
                "memory_judge",
            )
        }
        current_config["instruction_parts"] = config.get("instruction_parts")
        if comparison_config is None:
            comparison_config = current_config
        elif current_config != comparison_config:
            raise ValueError(
                "model runs use different task/sample/turn settings: "
                f"{model_root}"
            )
        progress = load_json(model_root / "progress.json")
        if any(progress[key] for key in ("pending", "retryable", "invalid")):
            raise ValueError(f"model run is incomplete: {model_root}")
        records = (
            _collect_instruction_part_records(model_root)[1]
            if config.get("instruction_parts")
            else sorted(
                (
                    load_json(_attempt_path(model_root, task_id, sample_index))
                    for task_id in config["task_ids"]
                    for sample_index in range(1, int(config["samples_per_task"]) + 1)
                ),
                key=lambda item: (item["task_id"], item["sample_index"]),
            )
        )
        reports = _write_model_reports(
            output,
            model_root,
            model=config["model"],
            records=records,
            samples_per_task=int(config["samples_per_task"]),
        )
        if config["model"] in model_reports:
            raise ValueError(
                f"duplicate model run under result path: {config['model']}"
            )
        model_reports[config["model"]] = load_json(reports["model_report"])
        model_records[config["model"]] = records

    comparison = {
        "status": "PASS",
        "generated_at": _now(),
        "models": model_reports,
        "pairwise": _pairwise_comparison(model_records),
    }
    analysis_root = output / "analysis"
    write_json(analysis_root / "comparison.json", comparison)
    _write_metrics_csv(analysis_root / "metrics.csv", model_reports)
    _write_attempts_csv(analysis_root / "attempts.csv", model_records)
    _write_failures(analysis_root / "failures.jsonl", model_records)
    (analysis_root / "report.md").write_text(
        _comparison_markdown(comparison),
        encoding="utf-8",
    )
    return {
        "status": "PASS",
        "model_count": len(model_reports),
        "models": sorted(model_reports),
        "analysis_root": str(analysis_root),
    }


def _model_slug(model: str) -> str:
    """Return the model slug."""
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", model).strip("_")
    if not slug:
        raise ValueError("model does not contain a filesystem-safe character")
    return slug


def _case_manifest_record(case: DatasetCase) -> dict[str, Any]:
    """Return the case manifest record."""
    return {
        "task_id": case.task_id,
        "task_root": str(case.task_root),
        "world_root": str(case.world_root),
        "domain_path": str(case.domain_path),
    }


def _path_identity(value: Any) -> str:
    """Return the path identity."""
    text = str(value)
    return (
        text.casefold()
        if re.match(r"^/mnt/[A-Za-z]/", text)
        else text
    )


def _deployment_manifest_identity(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the deployment manifest identity."""
    path_keys = ("task_root", "world_root", "domain_path")
    return {
        "task_count": payload.get("task_count"),
        "cases": [
            {
                "task_id": record.get("task_id"),
                **{
                    key: _path_identity(record.get(key))
                    for key in path_keys
                },
            }
            for record in payload.get("cases", [])
        ],
    }


def _case_record(
    case: DatasetCase,
    task_bundle: TaskBundle,
    blueprint: WorldBlueprint,
) -> dict[str, Any]:
    """Return the case record."""
    target = task_bundle.target
    metadata = task_bundle.validation_metadata
    if metadata is None:
        raise ValueError(
            f"task {case.task_id} has no validation metadata"
        )
    return {
        **_case_manifest_record(case),
        "domain": blueprint.domain,
        "task_family": str(task_bundle.task["meta"]["task_family"]),
        "task_subtype": str(task_bundle.task["meta"]["task_subtype"]),
        "task_category": (
            f"{task_bundle.task['meta']['task_family']}."
            f"{task_bundle.task['meta']['task_subtype']}"
        ),
        "applicability": {
            "object": bool(target["objects"]),
            "space": bool(target["spaces"]),
            "answer": bool(target["expected_answers"]),
            "list_answer": any(isinstance(item["value"], list) for item in target["expected_answers"]),
            "report": bool(target["expected_reports"]),
            "memory": bool(
                target["required_memory_ids"]
                or target.get("expected_memory_mutations", [])
            ),
            "time": target["time_constraint"] is not None,
        },
    }


@dataclass
class DatasetDeployment:
    """Lazily prepare and cache each task when its first attempt starts."""

    domain: str
    domain_path: Path
    snapshot_root: Path
    runtime_lock: Any
    runtime_cache: DomainRuntimeCache | None
    case_locks: dict[str, Any]
    prepared_cases: dict[
        str,
        tuple[WorldBlueprint, TaskBundle, dict[str, Any] | None],
    ]

    def prepare_case(
        self,
        case: DatasetCase,
    ) -> tuple[
        DomainRuntimeCache,
        WorldBlueprint,
        TaskBundle,
        dict[str, Any] | None,
    ]:
        """Load one task once, including its blueprint and reference state."""
        with self.case_locks[case.task_id]:
            prepared = self.prepared_cases.get(case.task_id)
            if prepared is not None:
                return self._get_runtime_cache(), *prepared

            runtime_cache = self._get_runtime_cache()
            blueprint = runtime_cache.load_world_blueprint(
                case.world_root
            )
            world = World(
                case.world_root,
                case.domain_path,
                runtime_cache=runtime_cache,
                blueprint=blueprint,
            )
            task_bundle = TaskLoader(contract=world.contract).load(
                case.task_root,
                world,
            )
            if task_bundle.task_id != case.task_id:
                raise ValueError(
                    f"task id mismatch: directory={case.task_id}, "
                    f"file={task_bundle.task_id}"
                )
            path = self.snapshot_root / f"{case.task_id}.json"
            if path.is_file():
                snapshot = load_json(path)["snapshot"]
            else:
                snapshot = None
                if task_bundle.reference_trajectory is not None:
                    TrajectoryExecutor(
                        world,
                        task_id=case.task_id,
                    ).replay(task_bundle.reference_trajectory)
                    complete_background_simulation(world, task_bundle)
                    snapshot = world.get_state()
                write_json(
                    path,
                    {"task_id": case.task_id, "snapshot": snapshot},
                )
            prepared = (blueprint, task_bundle, snapshot)
            self.prepared_cases[case.task_id] = prepared
            return runtime_cache, *prepared

    def _get_runtime_cache(self) -> DomainRuntimeCache:
        """Return the runtime cache."""
        with self.runtime_lock:
            if self.runtime_cache is None:
                self.runtime_cache = DomainRuntimeCache(
                    self.domain,
                    self.domain_path,
                )
            return self.runtime_cache


def _prepare_dataset(
    cases: Sequence[DatasetCase],
    output: Path,
    *,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> DatasetDeployment:
    """Return the dataset."""
    manifest = {
        "task_count": len(cases),
        "cases": [_case_manifest_record(case) for case in cases],
    }
    manifest_path = output / "dataset_manifest.json"
    if manifest_path.is_file():
        stored = load_json(manifest_path)
        previous = {
            record["task_id"]: record
            for record in _deployment_manifest_identity(stored)["cases"]
        }
        current = _deployment_manifest_identity(manifest)["cases"]
        previous_domains = {record["domain_path"] for record in previous.values()}
        for record in current:
            if (
                record["task_id"] in previous
                and record != previous[record["task_id"]]
            ) or (previous_domains and record["domain_path"] not in previous_domains):
                raise ValueError(
                    f"dataset differs from existing deployment: {manifest_path}"
                )
        # Keep deployment identities for removed tasks so re-adding them is safe.
        known = {record["task_id"]: record for record in stored["cases"]}
        known.update({record["task_id"]: record for record in manifest["cases"]})
        manifest = {"task_count": len(known), "cases": list(known.values())}

    domain_roots = {case.domain_path for case in cases}
    if len(domain_roots) != 1:
        raise ValueError("one benchmark run must use exactly one Domain root")
    domain_path = next(iter(domain_roots))
    domains = {
        load_json(case.world_root / "world_init.json")["domain"]["type"]
        for case in _preparation_steps(cases, "Checking dataset domains", progress_callback)
    }
    if len(domains) != 1:
        raise ValueError("one benchmark run must use exactly one Domain")
    domain = next(iter(domains))
    write_json(manifest_path, manifest)
    return DatasetDeployment(
        domain=domain,
        domain_path=domain_path,
        snapshot_root=output / "deployment" / "reference_snapshots",
        runtime_lock=Lock(),
        runtime_cache=None,
        case_locks={case.task_id: Lock() for case in cases},
        prepared_cases={},
    )


def _attempt_path(model_root: Path, task_id: str, sample_index: int) -> Path:
    """Return the attempt path."""
    return model_root / "attempts" / task_id / f"sample_{sample_index:04d}.json"


def _run_dataset_attempt(
    plan: DatasetAttemptPlan,
    *,
    model: str,
    max_turns: int,
    max_transport_attempts: int,
    reference_snapshot: dict[str, Any] | None,
    runtime_cache: DomainRuntimeCache,
    blueprint: WorldBlueprint,
    task_bundle: TaskBundle,
    client: Any,
    memory_judge_client: Any | None,
    report_judge_completion: Callable | None = None,
    require_device_tool_discovery: bool,
    recover_tool_call_errors: bool,
    record_requests: bool = False,
    agent_strategy: str = "react",
) -> dict[str, Any]:
    """Run the dataset attempt."""
    case = plan.case
    base = {
        **_case_record(case, task_bundle, blueprint),
        "sample_index": plan.sample_index,
        "requested_model": model,
        "started_at": _now(),
        "agent_strategy": agent_strategy,
    }
    if plan.instruction_source is not None:
        base.update(
            {
                "instruction_source": plan.instruction_source,
                "instruction_style": plan.instruction_style,
                "instruction": plan.instruction,
                "instruction_index": plan.instruction_index,
                "instruction_variant_index": plan.instruction_variant_index,
                "instruction_repeat_index": plan.instruction_repeat_index,
            }
        )
    agent = create_agent(
        client=client,
        model=model,
        max_transport_attempts=max_transport_attempts,
        require_model_identity=False,
        recover_tool_call_errors=recover_tool_call_errors,
        agent_strategy=agent_strategy,
        record_requests=record_requests,
    )
    started = datetime.now(timezone.utc)
    runner = None
    try:
        runner = AgentRunner(
            case.world_root,
            agent,
            task_root=case.task_root,
            domain_path=case.domain_path,
            runtime_cache=runtime_cache,
            blueprint=blueprint,
            task_bundle=task_bundle,
            max_turns=max_turns,
            require_device_tool_discovery=require_device_tool_discovery,
        )
        run = runner.run(
            trajectory_id=(
                f"{case.task_id}_"
                f"{plan.instruction_source or 'default'}_"
                f"sample_{plan.sample_index}"
            ),
            replay_reference_snapshot=reference_snapshot,
        )
        expected_mutations = task_bundle.target.get(
            "expected_memory_mutations",
            [],
        )
        checks = memory_content_checks(
            expected_mutations,
            runner.world.get_initial_memory(),
            runner.world.get_memory(),
        )
        if (
            expected_mutations
            and run.report["memory_success"]
            and len(checks) == len(expected_mutations)
        ):
            if memory_judge_client is None:
                raise RuntimeError("memory Judge client is required")
            try:
                judgement = judge_memory_content(
                    memory_judge_client,
                    task_bundle.instruction,
                    checks,
                    current_user=task_bundle.task.get("current_user"),
                    driver_context=memory_driver_context(runner.world.get_state()),
                )
            except MemoryJudgeError as error:
                report = apply_memory_judge(run.report, checks, error.audit)
                runner.world.contract.validate_schema(
                    report,
                    "urn:dcb:v2:schema:evaluation-report",
                )
                return {
                    **base,
                    "status": "retryable_error",
                    "task_success": False,
                    "failure_kind": "memory_judge",
                    "elapsed_seconds": (
                        datetime.now(timezone.utc) - started
                    ).total_seconds(),
                    "finished_at": _now(),
                    "provider_audit": list(run.provider_audit),
                    "memory_judge_audit": error.audit,
                    "trajectory": run.trajectory,
                    "evaluation_report": report,
                    "post_simulation": runner.world.post_simulation,
                    "error": {
                        "type": type(error).__name__,
                        "message": str(error),
                    },
                }
            apply_memory_judge(run.report, checks, judgement)
            runner.world.contract.validate_schema(
                run.report,
                "urn:dcb:v2:schema:evaluation-report",
            )
        if task_bundle.target["expected_reports"] and runner.world.submitted_reports:
            try:
                judgement = judge_reports(report_judge_context(runner.world, task_bundle), completion=report_judge_completion)
            except ReportJudgeError as error:
                apply_report_judge(run.report, error.audit)
                return {**base, "status": "retryable_error", "task_success": False, "failure_kind": "report_judge",
                        "elapsed_seconds": (datetime.now(timezone.utc) - started).total_seconds(), "finished_at": _now(),
                        "provider_audit": list(run.provider_audit), "memory_judge_audit": run.report["memory_judge"],
                        "report_judge_audit": error.audit, "trajectory": run.trajectory, "evaluation_report": run.report,
                        "post_simulation": runner.world.post_simulation,
                        "error": {"type": type(error).__name__, "message": str(error)}}
            apply_report_judge(run.report, judgement)
            runner.world.contract.validate_schema(run.report, "urn:dcb:v2:schema:evaluation-report")
        return {
            **base,
            "status": "completed",
            "task_success": bool(run.report["task_success"]),
            "failure_kind": None,
            "elapsed_seconds": (
                datetime.now(timezone.utc) - started
            ).total_seconds(),
            "finished_at": _now(),
            "provider_audit": list(run.provider_audit),
            "memory_judge_audit": run.report["memory_judge"],
            "report_judge_audit": run.report["report_judge"],
            "trajectory": run.trajectory,
            "evaluation_report": run.report,
            "post_simulation": runner.world.post_simulation,
            "error": None,
        }
    except AgentTransportError as error:
        context_exceeded = is_context_length_error(error)
        status = "completed" if context_exceeded else "retryable_error"
        failure_kind = "context_length_exceeded" if context_exceeded else "transport"
        error_payload = {
            "type": type(error).__name__,
            "message": str(error),
        }
    except AgentModelMismatchError as error:
        status = "invalid"
        failure_kind = "model_identity"
        error_payload = {
            "type": type(error).__name__,
            "message": str(error),
        }
    except AgentProtocolError as error:
        status = "completed"
        failure_kind = "protocol"
        error_payload = {
            "type": type(error).__name__,
            "message": str(error),
        }
    return {
        **base,
        "status": status,
        "task_success": False,
        "failure_kind": failure_kind,
        "elapsed_seconds": (
            datetime.now(timezone.utc) - started
        ).total_seconds(),
        "finished_at": _now(),
        "provider_audit": deepcopy(agent.audit_records),
        "memory_judge_audit": None,
        "trajectory": None,
        "evaluation_report": None,
        "partial_records": deepcopy(runner.records) if runner is not None else [],
        "post_simulation": runner.world.post_simulation if runner is not None else None,
        "error": error_payload,
    }


def _load_attempt_records(
    run_root: Path,
    plans: Sequence[DatasetAttemptPlan],
) -> list[dict[str, Any]]:
    """Return the attempt records."""
    records: list[dict[str, Any]] = []
    for plan in plans:
        path = _attempt_path(run_root, plan.case.task_id, plan.sample_index)
        if path.is_file():
            records.append(load_json(path))
    return records


def _progress(records: Sequence[dict[str, Any]], expected: int) -> dict[str, int]:
    """Return the progress."""
    counts = {"completed": 0, "retryable": 0, "invalid": 0}
    for record in records:
        status = record["status"]
        if status == "completed":
            counts["completed"] += 1
        elif status == "retryable_error":
            counts["retryable"] += 1
        else:
            counts["invalid"] += 1
    return {**counts, "pending": expected - len(records), "expected": expected}


def _live_attempt_metrics(
    records: Sequence[dict[str, Any]],
) -> dict[str, int]:
    """Return the live attempt metrics."""
    metrics = {
        "attempts_finished": len(records),
        "passed": 0,
        "failed": 0,
        "retryable": 0,
        "invalid": 0,
        "turns": 0,
        **_sum_usage_from_records(records),
    }
    for record in records:
        status = record["status"]
        if status == "completed":
            outcome = "passed" if record["task_success"] else "failed"
            metrics[outcome] += 1
        elif status == "retryable_error":
            metrics["retryable"] += 1
        else:
            metrics["invalid"] += 1
        report = record.get("evaluation_report") or {}
        metrics["turns"] += int(
            report.get("trajectory_summary", {}).get("turns", 0)
        )
    return metrics


def _write_model_reports(
    output: Path,
    model_root: Path,
    *,
    model: str,
    records: Sequence[dict[str, Any]],
    samples_per_task: int,
) -> dict[str, Any]:
    """Write the model reports."""
    model_report = {
        "model": model,
        "generated_at": _now(),
        "samples_per_task": samples_per_task,
        "overall": _aggregate_records(records, samples_per_task),
        "by_task_family": _group_records(
            records,
            samples_per_task,
            lambda record: record["task_family"],
        ),
        "by_task_subtype": _group_records(
            records,
            samples_per_task,
            lambda record: record["task_subtype"],
        ),
        "by_task_category": _group_records(
            records,
            samples_per_task,
            lambda record: record["task_category"],
        ),
    }
    benchmark_report = _benchmark_report(
        output,
        model,
        records,
        model_report,
    )
    ContractPackage().validate_schema(
        benchmark_report,
        "urn:dcb:v2:schema:benchmark-report",
    )
    write_json(model_root / "benchmark_report.json", benchmark_report)
    write_json(model_root / "model_report.json", model_report)
    return {
        "benchmark_report": str(model_root / "benchmark_report.json"),
        "model_report": str(model_root / "model_report.json"),
    }


def _aggregate_records(
    records: Sequence[dict[str, Any]],
    samples_per_task: int,
) -> dict[str, Any]:
    """Aggregate the records."""
    ordered = sorted(records, key=lambda item: (item["task_id"], item["sample_index"]))
    task_ids = sorted({record["task_id"] for record in ordered})
    averages: dict[str, float | None] = {}
    counts: dict[str, int] = {}

    values: dict[str, list[float]] = {
        "sample_success_rate": [],
        "state_success_rate": [],
        "property_accuracy": [],
        "object_property_accuracy": [],
        "space_property_accuracy": [],
        "action_success_rate": [],
        "answer_accuracy": [],
        "list_answer_recall": [],
        "report_accuracy": [],
        "report_count_accuracy": [],
        "report_semantic_accuracy": [],
        "semantic_success_rate": [],
        "memory_success_rate": [],
        "memory_rouge_l_f1": [],
        "time_constraint_success_rate": [],
        "effect_replay_rate": [],
        "time_plan_valid_rate": [],
        "false_complete_rate": [],
        "unexpected_side_effect_count": [],
        "turns": [],
        "tool_calls": [],
        "failed_calls": [],
        "model_calls": [],
        "api_requests": [],
        "input_tokens": [],
        "output_tokens": [],
        "total_tokens": [],
        "cached_tokens": [],
        "reasoning_tokens": [],
        "latency_seconds": [],
    }
    termination: dict[str, int] = {}
    failures: dict[str, int] = {}
    for record in ordered:
        report = record.get("evaluation_report")
        applicability = record["applicability"]
        values["semantic_success_rate"].append(float(bool(record["task_success"]) and (
            not applicability["report"] or bool(report and report["report_semantic_success"]))))
        values["sample_success_rate"].append(float(record["task_success"]))
        values["state_success_rate"].append(
            float(report["state_success"]) if report else 0.0
        )
        assertions = report["assertions"] if report else []
        values["property_accuracy"].append(
            sum(float(item["passed"]) for item in assertions) / len(assertions)
            if assertions
            else (0.0 if applicability["object"] or applicability["space"] else 1.0)
        )
        metrics = report["metrics"] if report else {}
        if applicability["object"]:
            values["object_property_accuracy"].append(
                float(metrics.get("object_property_accuracy", 0.0))
            )
        if applicability["space"]:
            values["space_property_accuracy"].append(
                float(metrics.get("space_property_accuracy") or 0.0)
            )
        values["action_success_rate"].append(
            float(metrics.get("action_success_rate", 0.0))
        )
        for key, applicable, source in (
            ("answer_accuracy", applicability["answer"], "answer_accuracy"),
            ("list_answer_recall", applicability.get("list_answer", False), "list_answer_recall"),
            ("report_accuracy", applicability["report"], "report_accuracy"),
            ("report_count_accuracy", applicability["report"], "report_count_accuracy"),
            ("report_semantic_accuracy", applicability["report"], "report_semantic_accuracy"),
            ("memory_success_rate", applicability["memory"], None),
            ("time_constraint_success_rate", applicability["time"], None),
        ):
            if applicable:
                if source is not None:
                    values[key].append(float(metrics.get(source) or 0.0))
                else:
                    field = (
                        "memory_success"
                        if key == "memory_success_rate"
                        else "time_constraint_success"
                    )
                    values[key].append(float(report[field]) if report else 0.0)
        for key, source in (
            ("effect_replay_rate", "effect_replay_pass"),
            ("time_plan_valid_rate", "time_plan_valid"),
        ):
            value = metrics.get(source)
            if value is not None:
                values[key].append(float(value))
        memory_rouge = metrics.get("memory_rouge_l_f1")
        if memory_rouge is not None:
            values["memory_rouge_l_f1"].append(float(memory_rouge))
        values["false_complete_rate"].append(
            float(metrics.get("false_complete", False))
        )
        side_effects = metrics.get("unexpected_side_effect_count")
        if side_effects is not None:
            values["unexpected_side_effect_count"].append(float(side_effects))
        summary = report["trajectory_summary"] if report else {}
        values["turns"].append(float(summary.get("turns", 0)))
        values["tool_calls"].append(float(summary.get("total_tool_calls", 0)))
        values["failed_calls"].append(float(summary.get("failed_calls", 0)))
        reason = summary.get("termination_reason") or record.get("failure_kind") or "unknown"
        termination[reason] = termination.get(reason, 0) + 1
        if record.get("failure_kind"):
            kind = str(record["failure_kind"])
            failures[kind] = failures.get(kind, 0) + 1

        audit = record.get("provider_audit", [])
        values["model_calls"].append(float(len(audit)))
        values["api_requests"].append(
            float(
                sum(
                    int(item.get("transport_attempt_count", 1))
                    for item in audit
                )
            )
        )
        usage = _sum_usage(audit)
        for key in (
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "cached_tokens",
            "reasoning_tokens",
        ):
            values[key].append(float(usage[key]))
        values["latency_seconds"].append(
            sum(float(item.get("latency_seconds", 0.0)) for item in audit)
        )

    for key, items in values.items():
        counts[key] = len(items)
        averages[key] = sum(items) / len(items) if items else None
    by_task = {
        task_id: sorted(
            (record for record in ordered if record["task_id"] == task_id),
            key=lambda item: item["sample_index"],
        )
        for task_id in task_ids
    }
    pass_at_n = {
        str(index): (
            sum(
                any(record["task_success"] for record in task_records[:index])
                for task_records in by_task.values()
            )
            / len(by_task)
            if by_task
            else 0.0
        )
        for index in range(1, samples_per_task + 1)
    }
    return {
        "task_count": len(task_ids),
        "attempt_count": len(ordered),
        "pass_at_n": pass_at_n,
        "averages": averages,
        "applicable_counts": counts,
        "termination_reasons": dict(sorted(termination.items())),
        "failure_kinds": dict(sorted(failures.items())),
        "usage_totals": _sum_usage_from_records(ordered),
    }


def _group_records(
    records: Sequence[dict[str, Any]],
    samples_per_task: int,
    key: Callable[[dict[str, Any]], str],
) -> dict[str, dict[str, Any]]:
    """Return the records."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        groups.setdefault(key(record), []).append(record)
    return {
        name: _aggregate_records(group, samples_per_task)
        for name, group in sorted(groups.items())
    }


def _benchmark_report(
    _output: Path,
    model: str,
    records: Sequence[dict[str, Any]],
    model_report: dict[str, Any],
) -> dict[str, Any]:
    """Return the benchmark report."""
    overall = model_report["overall"]
    averages = overall["averages"]
    def breakdown(name: str) -> dict[str, dict[str, int | float]]:
        """Return the breakdown."""
        return {
            group_name: {
                "attempt_count": group["attempt_count"],
                "pass_rate": float(
                    group["averages"]["sample_success_rate"] or 0.0
                ),
            }
            for group_name, group in model_report[name].items()
        }
    termination: dict[str, dict[str, Any]] = {}
    for reason, count in overall["termination_reasons"].items():
        matching = [
            record
            for record in records
            if (
                (record.get("evaluation_report") or {})
                .get("trajectory_summary", {})
                .get("termination_reason")
                or record.get("failure_kind")
                or "unknown"
            )
            == reason
        ]
        termination[reason] = {
            "attempt_count": count,
            "pass_rate": sum(bool(item["task_success"]) for item in matching) / count,
        }
    run_id = f"benchmark_{_model_slug(model)}"[:64]
    return {
        "run_id": run_id,
        "sample_count": len(records),
        "metrics": {
            "scenario_pass_rate": float(averages["sample_success_rate"] or 0.0),
            "pass_at_n": overall["pass_at_n"],
            "avg_property_accuracy": float(averages["property_accuracy"] or 0.0),
            "avg_action_success_rate": float(averages["action_success_rate"] or 0.0),
            "avg_turns": float(averages["turns"] or 0.0),
            "avg_total_actions": float(averages["tool_calls"] or 0.0),
            "avg_answer_accuracy": averages["answer_accuracy"],
            "avg_list_answer_recall": averages["list_answer_recall"],
            "avg_report_accuracy": averages["report_accuracy"],
            "avg_report_count_accuracy": averages["report_count_accuracy"],
            "avg_report_semantic_accuracy": averages["report_semantic_accuracy"],
            "semantic_scenario_pass_rate": averages["semantic_success_rate"],
            "token_usage": {
                "input_tokens": overall["usage_totals"]["input_tokens"],
                "output_tokens": overall["usage_totals"]["output_tokens"],
            },
        },
        "breakdowns": {
            "task_family": breakdown("by_task_family"),
            "task_subtype": breakdown("by_task_subtype"),
            "task_category": breakdown("by_task_category"),
            "termination_reason": termination,
        },
    }


def _sum_usage(audit: Sequence[dict[str, Any]]) -> dict[str, int]:
    """Return the sum usage."""
    totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cached_tokens": 0,
        "reasoning_tokens": 0,
    }
    for item in audit:
        usage = item.get("usage", {})
        input_value = usage.get("prompt_tokens")
        if input_value is None:
            input_value = usage.get("input_tokens", 0)
        output_value = usage.get("completion_tokens")
        if output_value is None:
            output_value = usage.get("output_tokens", 0)
        input_tokens = int(input_value or 0)
        output_tokens = int(output_value or 0)
        totals["input_tokens"] += input_tokens
        totals["output_tokens"] += output_tokens
        totals["total_tokens"] += int(
            usage.get("total_tokens", input_tokens + output_tokens) or 0
        )
        prompt_details = (
            usage.get("prompt_tokens_details")
            or usage.get("input_tokens_details")
            or {}
        )
        completion_details = (
            usage.get("completion_tokens_details")
            or usage.get("output_tokens_details")
            or {}
        )
        totals["cached_tokens"] += int(
            prompt_details.get("cached_tokens", 0) or 0
        )
        totals["reasoning_tokens"] += int(
            completion_details.get("reasoning_tokens", 0) or 0
        )
    return totals


def _sum_usage_from_records(records: Sequence[dict[str, Any]]) -> dict[str, int]:
    """Return the sum usage from records."""
    totals = {
        "model_calls": 0,
        "api_requests": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cached_tokens": 0,
        "reasoning_tokens": 0,
    }
    for record in records:
        audit = record.get("provider_audit", [])
        totals["model_calls"] += len(audit)
        totals["api_requests"] += sum(
            int(item.get("transport_attempt_count", 1)) for item in audit
        )
        usage = _sum_usage(audit)
        for key in (
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "cached_tokens",
            "reasoning_tokens",
        ):
            totals[key] += usage[key]
    return totals


def _pairwise_comparison(
    model_records: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, int]]:
    """Return the pairwise comparison."""
    models = sorted(model_records)
    pass_counts = {
        model: {
            task_id: sum(
                bool(record["task_success"])
                for record in records
                if record["task_id"] == task_id
            )
            for task_id in {record["task_id"] for record in records}
        }
        for model, records in model_records.items()
    }
    result: dict[str, dict[str, int]] = {}
    for left_index, left in enumerate(models):
        for right in models[left_index + 1 :]:
            shared = sorted(set(pass_counts[left]) & set(pass_counts[right]))
            result[f"{left}::{right}"] = {
                "left_wins": sum(pass_counts[left][key] > pass_counts[right][key] for key in shared),
                "ties": sum(pass_counts[left][key] == pass_counts[right][key] for key in shared),
                "right_wins": sum(pass_counts[left][key] < pass_counts[right][key] for key in shared),
            }
    return result


def _write_metrics_csv(
    path: Path,
    reports: dict[str, dict[str, Any]],
) -> None:
    """Write the metrics CSV."""
    rows: list[dict[str, Any]] = []
    for model, report in sorted(reports.items()):
        groups = [
            ("overall", "overall", report["overall"]),
            *(
                ("task_family", name, metrics)
                for name, metrics in report["by_task_family"].items()
            ),
            *(
                ("task_subtype", name, metrics)
                for name, metrics in report["by_task_subtype"].items()
            ),
            *(
                ("task_category", name, metrics)
                for name, metrics in report["by_task_category"].items()
            ),
        ]
        for dimension, group, metrics in groups:
            row = {
                "model": model,
                "group_dimension": dimension,
                "group": group,
                "task_count": metrics["task_count"],
                "attempt_count": metrics["attempt_count"],
                **{f"pass_at_{key}": value for key, value in metrics["pass_at_n"].items()},
                **{
                    f"avg_{key}": value
                    for key, value in metrics["averages"].items()
                },
                **{
                    (
                        "total_tokens"
                        if key == "total_tokens"
                        else f"total_{key}"
                    ): value
                    for key, value in metrics["usage_totals"].items()
                },
            }
            rows.append(row)
    _write_csv(path, rows)


def _write_attempts_csv(
    path: Path,
    model_records: dict[str, list[dict[str, Any]]],
) -> None:
    """Write the attempts CSV."""
    rows: list[dict[str, Any]] = []
    for model, records in sorted(model_records.items()):
        for record in records:
            report = record.get("evaluation_report") or {}
            metrics = report.get("metrics", {})
            summary = report.get("trajectory_summary", {})
            usage = _sum_usage(record.get("provider_audit", []))
            rows.append(
                {
                    "model": model,
                    "task_id": record["task_id"],
                    "task_family": record["task_family"],
                    "task_subtype": record["task_subtype"],
                    "task_category": record["task_category"],
                    "sample_index": record["sample_index"],
                    "instruction_source": record.get("instruction_source"),
                    "instruction_style": record.get("instruction_style"),
                    "instruction_index": record.get("instruction_index"),
                    "instruction_variant_index": record.get(
                        "instruction_variant_index"
                    ),
                    "instruction_repeat_index": record.get(
                        "instruction_repeat_index"
                    ),
                    "task_success": record["task_success"],
                    "failure_kind": record.get("failure_kind"),
                    "state_success": report.get("state_success"),
                    "answer_success": report.get("answer_success"),
                    "report_success": report.get("report_success"),
                    "memory_success": report.get("memory_success"),
                    "memory_judge_status": (
                        report.get("memory_judge") or {}
                    ).get("status"),
                    "memory_rouge_l_f1": metrics.get(
                        "memory_rouge_l_f1"
                    ),
                    "time_constraint_success": report.get("time_constraint_success"),
                    "object_property_accuracy": metrics.get("object_property_accuracy"),
                    "space_property_accuracy": metrics.get("space_property_accuracy"),
                    "action_success_rate": metrics.get("action_success_rate"),
                    "false_complete": metrics.get("false_complete"),
                    "turns": summary.get("turns", 0),
                    "tool_calls": summary.get("total_tool_calls", 0),
                    "failed_calls": summary.get("failed_calls", 0),
                    "termination_reason": summary.get("termination_reason"),
                    "model_calls": len(record.get("provider_audit", [])),
                    **usage,
                }
            )
    _write_csv(path, rows)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write the CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_failures(
    path: Path,
    model_records: dict[str, list[dict[str, Any]]],
) -> None:
    """Write failed attempts as JSONL records."""
    write_jsonl(path, (
        {
            "model": model,
            "task_id": record["task_id"],
            "task_family": record["task_family"],
            "task_subtype": record["task_subtype"],
            "task_category": record["task_category"],
            "sample_index": record["sample_index"],
            "instruction_source": record.get("instruction_source"),
            "instruction_index": record.get("instruction_index"),
            "instruction_repeat_index": record.get("instruction_repeat_index"),
            "failure_kind": record.get("failure_kind"),
            "error": record.get("error"),
            "evaluation_errors": (record.get("evaluation_report") or {}).get("errors", []),
        }
        for model, records in sorted(model_records.items())
        for record in records
        if not record["task_success"]
    ))


def _comparison_markdown(comparison: dict[str, Any]) -> str:
    """Return the comparison markdown."""
    lines = [
        "# SynthDCB agent benchmark",
        "",
        "| Model | Tasks | Attempts | Pass@1 | Pass@N | Sample pass | Avg turns | Avg tool calls |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for model, report in sorted(comparison["models"].items()):
        overall = report["overall"]
        passes = overall["pass_at_n"]
        averages = overall["averages"]
        last_pass = passes[str(max(int(key) for key in passes))]
        lines.append(
            f"| {model} | {overall['task_count']} | {overall['attempt_count']} | "
            f"{passes['1']:.4f} | {last_pass:.4f} | "
            f"{averages['sample_success_rate']:.4f} | "
            f"{averages['turns']:.2f} | {averages['tool_calls']:.2f} |"
        )
    lines.extend(["", "## Pairwise wins by per-task pass count", ""])
    for pair, values in comparison["pairwise"].items():
        lines.append(
            f"- `{pair}`: {values['left_wins']} / {values['ties']} / {values['right_wins']}"
        )
    lines.extend(
        [
            "",
            "## Metrics by task category",
            "",
            "| Model | Task category | Tasks | Attempts | Pass@1 | Pass@N | Sample pass | State pass | Property accuracy |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for model, report in sorted(comparison["models"].items()):
        for task_category, metrics in report["by_task_category"].items():
            passes = metrics["pass_at_n"]
            averages = metrics["averages"]
            last_pass = passes[str(max(int(key) for key in passes))]
            lines.append(
                f"| {model} | {task_category} | {metrics['task_count']} | "
                f"{metrics['attempt_count']} | {passes['1']:.4f} | "
                f"{last_pass:.4f} | "
                f"{averages['sample_success_rate']:.4f} | "
                f"{averages['state_success_rate']:.4f} | "
                f"{averages['property_accuracy']:.4f} |"
            )
    lines.append("")
    return "\n".join(lines)





def _now() -> str:
    """Return the now."""
    return datetime.now(timezone.utc).isoformat()
