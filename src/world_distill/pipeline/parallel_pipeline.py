"""
This module provides a simple interface to run a pre-existing task plan in parallel.
"""

import argparse
import sys
import time
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from src.utils import (
    config,
    load_json,
    print_run_config,
    print_run_summary,
    print_status,
    write_json,
)
from src.world_distill.pipeline.model_creation.object_class_code_completor import main as complete_code_main
from src.world_distill.pipeline.model_creation.object_class_meta_creator import main as create_meta_main
from src.world_distill.pipeline.model_creation.object_class_template_creator import main as create_template_main
from src.world_distill.pipeline.model_creation.object_class_code_verifier import main as verify_code_main

class Task:
    """Represents a single task in the pipeline."""
    
    def __init__(self,
                 task_id: str,
                 name: str,
                 params: Dict[str, Any],
                 dependencies: List[str],
                 max_retries: int = 3):
        """Initialize the Task."""
        self.task_id = task_id
        self.name = name
        self.params = params
        self.dependencies = dependencies
        self.status = "pending"  # pending, running, completed, failed
        self.result: Optional[Dict[str, Any]] = None
        self.retries = 0
        self.max_retries = max_retries
        self.repair_rounds = 0
        self.log_data: List[Dict[str, Any]] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializes the task to a dictionary."""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "params": self.params,
            "dependencies": self.dependencies,
            "status": self.status,
            "result": self.result,
            "retries": self.retries,
            "max_retries": self.max_retries,
            "repair_rounds": self.repair_rounds,
            "log_data": self.log_data,
        }
    
    @classmethod
    def from_dict(cls,
                  data: Dict[str, Any]) -> "Task":
        """Deserializes a task from a dictionary."""
        task = cls(
            task_id=data["task_id"],
            name=data["name"],
            params=data["params"],
            dependencies=data.get("dependencies", []),
            max_retries=data.get("max_retries", 3),
        )
        task.status = data.get("status", "pending")
        task.result = data.get("result")
        task.retries = data.get("retries", 0)
        task.repair_rounds = data.get("repair_rounds", 0)
        task.log_data = data.get("log_data", [])
        return task


class TaskManager:
    """Manages the execution of a set of tasks with dependencies."""
    
    def __init__(self,
                 tasks_file: Path,
                 no_resume: bool = False,
                 on_failure: str = 'retry_parent',
                 report_file: Path | None = None,
                 max_parent_reruns: int = config.DEFAULT_MAX_REVIEW_ROUNDS):
        """Initialize the TaskManager."""
        if on_failure not in {"fail", "retry_parent"}:
            raise ValueError(
                "on_failure must be 'fail' or 'retry_parent'"
            )
        if max_parent_reruns < 0:
            raise ValueError("max_parent_reruns must be non-negative")
        self.tasks_file = tasks_file
        if not self.tasks_file.is_file():
            raise FileNotFoundError(f"task plan not found: {self.tasks_file}")
        self.tasks_file_checkpoint = tasks_file.with_suffix('.checkpoint.json')
        self.report_file = report_file or tasks_file.with_suffix('.report.json')
        self.no_resume = no_resume
        self.plan_input = load_json(self.tasks_file)
        self.tasks: Dict[str, Task] = self._load_tasks()
        self.project_path = config.PROJECT_ROOT
        self.on_failure = on_failure
        self.max_parent_reruns = max_parent_reruns
        self._save_lock = Lock()

    def _load_tasks(self) -> Dict[str, Task]:
        """Loads tasks from the JSON file."""
        tasks_data = None
        if not self.no_resume and self.tasks_file_checkpoint.exists():
            checkpoint = load_json(self.tasks_file_checkpoint)
            if (
                isinstance(checkpoint, dict)
                and checkpoint.get("stage") == "model_creation_tasks"
                and checkpoint.get("plan_input") == self.plan_input
                and isinstance(checkpoint.get("tasks"), dict)
            ):
                tasks_data = checkpoint["tasks"]
        if tasks_data is None:
            tasks_data = deepcopy(self.plan_input)
        
        if not tasks_data:
            raise ValueError(f"task plan contains no tasks: {self.tasks_file}")
        tasks = {
            task_id: Task.from_dict(data)
            for task_id, data in tasks_data.items()
        }
        if not self.no_resume:
            for task in tasks.values():
                if task.status != "completed":
                    task.status = "pending"
            invalid = {
                task.task_id
                for task in tasks.values()
                if task.status == "completed"
                and not self._completed_artifact_exists(task)
            }
            if invalid:
                changed = True
                while changed:
                    changed = False
                    for task in tasks.values():
                        if task.task_id in invalid:
                            continue
                        if any(parent in invalid for parent in task.dependencies):
                            invalid.add(task.task_id)
                            changed = True
                for task_id in sorted(invalid):
                    task = tasks[task_id]
                    task.status = "pending"
                    task.result = None
                    task.retries = 0
                    task.repair_rounds = 0
                    task.log_data.append(
                        {
                            "code": "[ARTIFACT_MISSING]",
                            "validation": {
                                "error": "completed artifact or a dependency artifact is missing"
                            },
                        }
                    )
        return tasks

    @staticmethod
    def _completed_artifact_exists(task: Task) -> bool:
        """Return whether a completed task still has its output artifact."""
        if not isinstance(task.result, dict):
            return False
        output_file = task.result.get("output_file")
        return isinstance(output_file, str) and Path(output_file).is_file()
    
    def save_tasks(self):
        """Saves the current state of all tasks to the JSON file."""
        with self._save_lock:
            self.tasks_file_checkpoint.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "stage": "model_creation_tasks",
                "plan_input": self.plan_input,
                "tasks": {
                    task_id: task.to_dict()
                    for task_id, task in self.tasks.items()
                },
            }
            write_json(self.tasks_file_checkpoint, payload)

    def request_final_gate_repairs(
        self,
        repairs: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Reset bounded per-class DAG branches with independent-gate feedback.

        ``repairs`` maps a generated class name to a target LLM stage
        (``create_meta`` or ``complete_code``) and structured errors.  The
        target plus every transitive descendant is invalidated.  A class that
        already consumed the configured parent-repair budget is reported as
        exhausted instead of being silently regenerated again.
        """

        descendants: Dict[str, set[str]] = {
            task_id: set() for task_id in self.tasks
        }
        for task in self.tasks.values():
            for parent_id in task.dependencies:
                descendants.setdefault(parent_id, set()).add(task.task_id)

        requested: list[Dict[str, Any]] = []
        exhausted: list[Dict[str, Any]] = []
        unmatched: list[Dict[str, Any]] = []
        llm_stages = {"create_meta", "complete_code", "verify_code"}

        for class_name, repair in sorted(repairs.items()):
            target_stage = str(repair.get("target_stage") or "complete_code")
            class_tasks = [
                task
                for task in self.tasks.values()
                if task.params.get("name") == class_name
            ]
            target = next(
                (
                    task
                    for task in class_tasks
                    if task.name == target_stage
                ),
                None,
            )
            if target is None:
                unmatched.append(
                    {
                        "class_name": class_name,
                        "target_stage": target_stage,
                    }
                )
                continue
            consumed = max(
                (task.repair_rounds for task in class_tasks),
                default=0,
            )
            if consumed >= self.max_parent_reruns:
                exhausted.append(
                    {
                        "class_name": class_name,
                        "target_stage": target_stage,
                        "repair_rounds": consumed,
                        "limit": self.max_parent_reruns,
                    }
                )
                continue

            affected: set[str] = {target.task_id}
            frontier = [target.task_id]
            while frontier:
                current = frontier.pop()
                for child_id in descendants.get(current, set()):
                    if child_id not in affected:
                        affected.add(child_id)
                        frontier.append(child_id)

            feedback = {
                "code": "[INDEPENDENT_FINAL_GATE_REPAIR_REQUEST]",
                "source": "independent_final_gate",
                "validation": {
                    "errors": list(repair.get("errors") or []),
                    "round": consumed + 1,
                },
            }
            target.repair_rounds = consumed + 1
            for task_id in affected:
                task = self.tasks[task_id]
                task.status = "pending"
                task.retries = 0
                task.result = None
                if task.name in llm_stages:
                    task.log_data.append(feedback)

            requested.append(
                {
                    "class_name": class_name,
                    "target_stage": target_stage,
                    "repair_round": consumed + 1,
                    "affected_task_ids": sorted(affected),
                    "errors": list(repair.get("errors") or []),
                }
            )

        self.save_tasks()
        self.save_report()
        return {
            "requested": requested,
            "exhausted": exhausted,
            "unmatched": unmatched,
        }

    @staticmethod
    def _collect_llm_usages(obj: Any) -> list[dict[str, Any]]:
        """Return the LLM usages."""
        records: list[dict[str, Any]] = []
        if isinstance(obj, dict):
            usage = obj.get("usage")
            if isinstance(usage, dict):
                records.append({
                    "response_model": obj.get("model") or "unknown",
                    "requested_model": obj.get("requested_model") or obj.get("model") or "unknown",
                    "model_scenario": obj.get("model_scenario") or "unknown",
                    "usage": usage,
                })
            for value in obj.values():
                records.extend(TaskManager._collect_llm_usages(value))
        elif isinstance(obj, list):
            for value in obj:
                records.extend(TaskManager._collect_llm_usages(value))
        return records

    def build_report(self) -> dict[str, Any]:
        """Return the report."""
        usage_by_model: dict[str, dict[str, int]] = {}
        usage_by_requested_model: dict[str, dict[str, int]] = {}
        usage_by_model_scenario: dict[str, dict[str, int]] = {}
        usage_by_stage: dict[str, dict[str, int]] = {}
        calls: list[dict[str, Any]] = []

        def add_usage(bucket: dict[str, dict[str, int]], key: str, usage: dict[str, Any]) -> None:
            """Add the usage."""
            stats = bucket.setdefault(key, {
                "calls": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            })
            stats["calls"] += 1
            for field in ["prompt_tokens", "completion_tokens", "total_tokens"]:
                value = usage.get(field, 0)
                if isinstance(value, int):
                    stats[field] += value

        for task in self.tasks.values():
            for index, log_data in enumerate(task.log_data):
                for record in self._collect_llm_usages(log_data):
                    usage = record["usage"]
                    response_model = record["response_model"]
                    requested_model = record["requested_model"]
                    model_scenario = record["model_scenario"]
                    add_usage(usage_by_model, response_model, usage)
                    add_usage(usage_by_requested_model, requested_model, usage)
                    add_usage(usage_by_model_scenario, model_scenario, usage)
                    add_usage(usage_by_stage, task.name, usage)
                    calls.append({
                        "task_id": task.task_id,
                        "task_name": task.name,
                        "attempt_index": index,
                        "model": response_model,
                        "response_model": response_model,
                        "requested_model": requested_model,
                        "model_scenario": model_scenario,
                        "usage": usage,
                    })

        return {
            "task_file": str(self.tasks_file),
            "checkpoint_file": str(self.tasks_file_checkpoint),
            "summary": {
                "task_count": len(self.tasks),
                "completed": sum(1 for task in self.tasks.values() if task.status == "completed"),
                "failed": sum(1 for task in self.tasks.values() if task.status == "failed"),
                "pending": sum(1 for task in self.tasks.values() if task.status == "pending"),
                "running": sum(1 for task in self.tasks.values() if task.status == "running"),
            },
            "usage_by_model": usage_by_model,
            "usage_by_requested_model": usage_by_requested_model,
            "usage_by_model_scenario": usage_by_model_scenario,
            "usage_by_stage": usage_by_stage,
            "llm_calls": calls,
            "tasks": [task.to_dict() for task in self.tasks.values()],
        }

    def save_report(self) -> None:
        """Save the report."""
        with self._save_lock:
            self.report_file.parent.mkdir(parents=True, exist_ok=True)
            write_json(self.report_file, self.build_report())
    
    def add_task(self,
                 name: str,
                 params: Dict[str, Any],
                 dependencies: List[str]) -> str:
        """Adds a new task."""
        task_id = str(uuid.uuid4())
        task = Task(task_id, name, params, dependencies)
        self.tasks[task_id] = task
        self.save_tasks()
        return task_id
    
    def execute_tasks(self,
                      max_workers: int = 4,
                      task_num: Optional[int] = None):
        """Executes tasks in parallel, respecting dependencies."""
        if max_workers < 1:
            raise ValueError("max_workers must be positive")
        if task_num is not None and task_num < 1:
            raise ValueError("task_num must be positive")
        start_time = time.time()
        last_status_time = start_time
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = set()
            while True:
                completed_count = sum(1 for t in self.tasks.values() if t.status == "completed")
                
                # Check if we should stop submitting new tasks
                stop_submitting = task_num is not None and completed_count >= task_num
                
                if not stop_submitting:
                    ready_tasks = self._get_ready_tasks()
                    
                    # Filter out tasks that are already in flight
                    running_task_ids = {t.task_id for t in self.tasks.values() if t.status == "running"}
                    tasks_to_submit = [t for t in ready_tasks if t.task_id not in running_task_ids][
                        :max_workers - len(futures)
                    ]
                    
                    for task in tasks_to_submit:
                        # Reserve the task before submit so the next scheduler
                        # pass cannot enqueue the same pending task twice.
                        task.status = "running"
                        future = executor.submit(self._execute_single_task, task)
                        futures.add(future)
                    if tasks_to_submit:
                        self.save_tasks()
                
                # If no more tasks to submit and no tasks are running, we are done.
                if not futures:
                    if stop_submitting:
                        print_status(f"Reached task limit of {task_num}. All running tasks have completed.", "info")
                    break
                
                # Process completed futures
                done, futures = wait(futures, timeout=1.0, return_when=FIRST_COMPLETED)
                for future in done:
                    future.result()
                
                self.save_tasks()
                
                # Periodic status update
                current_time = time.time()
                if current_time - last_status_time > 10:  # Update every 10 seconds
                    elapsed_time = current_time - start_time
                    running_count = sum(1 for t in self.tasks.values() if t.status == "running")
                    pending_count = sum(1 for t in self.tasks.values() if t.status == "pending")
                    failed_count = sum(1 for t in self.tasks.values() if t.status == "failed")
                    print_status(f"Status: {elapsed_time:.2f}s elapsed. Completed: {completed_count}, Running: {running_count}, Pending: {pending_count}, Failed: {failed_count}", "info")
                    last_status_time = current_time
        
        elapsed_time = time.time() - start_time
        num_completed = sum(1 for t in self.tasks.values() if t.status == "completed")
        num_failed = sum(1 for t in self.tasks.values() if t.status == "failed")
        self.save_report()
        print_status(f"Execution finished in {elapsed_time:.2f} seconds. Completed: {num_completed}, Failed: {num_failed}", "info")
    
    def _get_ready_tasks(self) -> List[Task]:
        """Gets a list of tasks that are ready to be executed."""
        ready_tasks = []
        for task in self.tasks.values():
            if (
                task.status in {"pending", "failed"}
                and task.retries < task.max_retries
            ):
                if all(self.tasks[dep_id].status == "completed" for dep_id in task.dependencies):
                    ready_tasks.append(task)
        return ready_tasks
    
    def _execute_single_task(self,
                             task: Task):
        """Executes a single task."""
        print_status(f"Executing task: {task.name} ({task.task_id})", "info")
        task.retries += 1
        started_at = datetime.now(timezone.utc)
        started_monotonic = time.monotonic()
        log_data: dict[str, Any] = {}
        logged = False
        
        try:
            result_output, log_data = self._dispatch_task(task)
            if not isinstance(log_data, dict):
                raise TypeError("pipeline task log must be a dictionary")
            log_data["attempt"] = {
                "attempt_index": task.retries,
                "started_at": started_at.isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": round(
                    time.monotonic() - started_monotonic,
                    6,
                ),
            }
            task.log_data.append(log_data)
            logged = True
            if not result_output:
                if task.name == "verify_code" and log_data["code"] == "[IMPLEMENT_PYTHON_ERROR]":
                    task.retries = task.max_retries
                raise RuntimeError(log_data["code"])
            code = log_data["code"]
            if code != "[PASS]":
                if task.name == "verify_code" and code == "[IMPLEMENT_PYTHON_ERROR]":
                    task.retries = task.max_retries
                raise RuntimeError(code)
            task.result = {
                "output_file": str(result_output),
                "details": code,
            }
            task.status = "completed"
            print_status(f"Task {task.name} ({task.task_id}) completed.", "success")
        except RuntimeError as e:
            if not logged:
                task.log_data.append(
                    {
                        "code": "[TASK_RUNTIME_ERROR]",
                        "error": str(e),
                        "attempt": {
                            "attempt_index": task.retries,
                            "started_at": started_at.isoformat(),
                            "finished_at": datetime.now(timezone.utc).isoformat(),
                            "elapsed_seconds": round(
                                time.monotonic() - started_monotonic,
                                6,
                            ),
                        },
                    }
                )
            task.status = "failed"
            task.result = {
                "error": str(e)
            }
            print_status(f"Task {task.name} ({task.task_id}) failed. Retry {task.retries}/{task.max_retries}. Error: {e}", "error")
            if task.retries >= task.max_retries:
                print_status(f"Task {task.name} ({task.task_id}) has failed permanently.", "error")
                self._handle_permanent_failure(task)
        
        self.save_tasks()
        self.save_report()
    
    def _accepted_rag_sources(self, domain: str) -> dict[Path, str]:
        """Expose only accepted classes in this plan with completed dependencies."""
        def completed_before(task: Task, verified_at: str) -> bool:
            return (
                task.status == "completed"
                and task.log_data[-1]["attempt"]["finished_at"] <= verified_at
                and all(completed_before(self.tasks[parent], verified_at)
                        for parent in task.dependencies)
            )

        sources = {}
        for task in self.tasks.values():
            if (task.name != "verify_code" or task.params.get("domain") != domain
                    or task.status != "completed" or not task.log_data):
                continue
            acceptance = task.log_data[-1].get("validation", {}).get("reference_acceptance", {})
            if acceptance.get("code") != "[PASS]":
                continue
            verified_at = task.log_data[-1]["attempt"]["started_at"]
            if not all(completed_before(self.tasks[parent], verified_at) for parent in task.dependencies):
                continue
            paths = {
                Path(task.params["specification"]).resolve(): "object_spec",
                Path(task.params["py"]).resolve(): "implementation",
                Path(task.params["output"]).resolve(): "test",
            }
            if all(path.is_file() for path in paths):
                sources.update(paths)
        return sources

    def _dispatch_task(self,
                       task: Task):
        """Dispatches a task to its corresponding function."""
        params = task.params.copy()
        if task.log_data:
            params['log_data'] = task.log_data
        sources = {}
        if task.name != "create_template" and params.get("use_rag", True):
            sources = self._accepted_rag_sources(params.get("domain", "Home"))
            params["generated_sources"] = sources
        
        if task.name == 'create_meta':
            args = argparse.Namespace(**params)
            result = create_meta_main(args)
        elif task.name == 'create_template':
            args = argparse.Namespace(**params)
            result = create_template_main(args)
        elif task.name == 'complete_code':
            args = argparse.Namespace(**params)
            result = complete_code_main(args)
        elif task.name == 'verify_code':
            args = argparse.Namespace(**params)
            result = verify_code_main(args)
        else:
            raise ValueError(f"Unknown task name: {task.name}")
        result[1]["rag_generated_sources"] = {str(path): kind for path, kind in sources.items()}
        return result
    
    def _handle_permanent_failure(self,
                                  failed_task: Task):
        """Handles the permanent failure of a task based on the on_failure policy."""
        print_status(f"Handling permanent failure for task {failed_task.name} ({failed_task.task_id}).", "info")
        
        if self.on_failure == 'fail':
            print_status("Failure policy halted the pipeline.", "error")
            return

        if failed_task.log_data[-1].get("code") == "[MAX_TRY_REACHED]":
            print_status("Model service attempts exhausted; preserving completed dependencies.", "error")
            return

        if failed_task.repair_rounds >= self.max_parent_reruns:
            print_status(
                f"Task {failed_task.name} exhausted "
                f"{self.max_parent_reruns} parent repair rounds.",
                "error",
            )
            return

        print_status(f"Repairing current class for {failed_task.name}.", "info")
        failed_task.repair_rounds += 1
        failed_task.status = "pending"
        failed_task.retries = 0

        failure_log = failed_task.log_data[-1]
        for dep_id in failed_task.dependencies:
            parent_task = self.tasks[dep_id]
            # A base class is an authoritative dependency. Child feedback must
            # not rewrite its metadata behind already generated implementations.
            if parent_task.params.get("name") != failed_task.params.get("name"):
                continue
            print_status(
                f"Resetting parent task {parent_task.name} "
                f"({parent_task.task_id}) to pending.",
                "info",
            )
            parent_task.status = "pending"
            parent_task.retries = 0
            parent_task.log_data.append(
                {
                    "code": "[PARENT_REPAIR_REQUEST]",
                    "source_task": failed_task.task_id,
                    "validation": failure_log.get("validation", {}),
                }
            )

        print_status(f"Re-triggering parents and task {failed_task.name}.", "info")
        self.save_tasks()


def display_progress(task_manager: TaskManager):
    """Displays the progress of tasks as a static log."""
    tasks = list(task_manager.tasks.values())
    total_tasks = len(tasks)
    
    completed = sum(1 for t in tasks if t.status == "completed")
    running = sum(1 for t in tasks if t.status == "running")
    pending = sum(1 for t in tasks if t.status == "pending")
    failed = sum(1 for t in tasks if t.status == "failed")
    
    progress = completed / total_tasks
    
    # Print a summary line instead of a dynamic bar
    summary = f"Progress: {completed}/{total_tasks} ({progress:.2%}) | Running: {running}, Pending: {pending}, Failed: {failed}"
    print_status(summary, "info")
    
    # Optionally, list running and failed tasks for quick reference
    running_tasks = [f"{t.name} ({t.task_id[:8]})" for t in tasks if t.status == 'running']
    if running_tasks:
        print_status(f"  -> Running: {', '.join(running_tasks)}", "info")
    
    failed_tasks = [f"{t.name} ({t.task_id[:8]}, retries: {t.retries})" for t in tasks if t.status == 'failed']
    if failed_tasks:
        print_status(f"  -> Failed: {', '.join(failed_tasks)}", "error")


def main() -> int:
    """Run the device-model creation pipeline from a task file."""
    parser = argparse.ArgumentParser(description="Device Model Creation Pipeline from Task File")
    parser.add_argument("--task_file", type=Path, required=True, help="Path to pre-existing plans.json under run/<batch>/model_creation/.")
    parser.add_argument("--max_workers", type=int, default=10, help="Maximum number of parallel workers.")
    parser.add_argument("--poll_interval", type=int, default=10, help="Interval in seconds to poll for progress.")
    parser.add_argument("--task_num", type=int, default=None, help="Number of tasks to complete. If not specified, all tasks will be run.")
    parser.add_argument("--no_resume", action="store_true", help="Do not resume from existing checkpoint; reset tasks to pending.")
    parser.add_argument("--on_failure", type=str, default="fail", choices=["fail", "retry_parent"], help="Action to take on task failure: 'fail' to stop, or 'retry_parent' to re-run the parent task.")
    parser.add_argument("--report_file", default=None, help="Path to write pipeline usage/status report. Defaults to task file with .report.json suffix.")
    
    args = parser.parse_args()
    if args.poll_interval < 1:
        raise ValueError("poll_interval must be positive")
    
    task_file_path = args.task_file.resolve()

    report_file = Path(args.report_file).resolve() if args.report_file else None
    print_run_config(
        "Model creation pipeline",
        (
            ("Task plan", task_file_path),
            ("Workers", args.max_workers),
            ("Poll interval", args.poll_interval),
            ("Task limit", args.task_num or "all"),
            ("Resume", not args.no_resume),
            ("Failure policy", args.on_failure),
            ("Report", report_file or "task-plan default"),
        ),
    )
    task_manager = TaskManager(task_file_path, args.no_resume, on_failure=args.on_failure, report_file=report_file)

    from threading import Thread
    import signal
    
    execution_thread = Thread(target=task_manager.execute_tasks, args=(args.max_workers, args.task_num))
    
    def signal_handler(sig,frame):
        """Handle an interrupt signal."""
        print_status('\nCtrl+C detected! Shutting down gracefully...', "warning")
        task_manager.save_tasks()
        task_manager.save_report()
        sys.exit(130)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    execution_thread.start()
    
    while execution_thread.is_alive():
        display_progress(task_manager)
        time.sleep(args.poll_interval)

    display_progress(task_manager)
    tasks = tuple(task_manager.tasks.values())
    completed = sum(task.status == "completed" for task in tasks)
    failed = sum(task.status == "failed" for task in tasks)
    pending = sum(task.status == "pending" for task in tasks)
    target_reached = (
        completed == len(tasks)
        if args.task_num is None
        else completed >= min(args.task_num, len(tasks))
    )
    status = "PASS" if target_reached and failed == 0 else "FAIL"
    print_run_summary(
        "Model creation pipeline",
        status,
        (
            ("Completed", completed),
            ("Failed", failed),
            ("Pending", pending),
            ("Report", task_manager.report_file),
        ),
    )
    return 0 if status == "PASS" else 1


if __name__ == '__main__':
    raise SystemExit(main())
