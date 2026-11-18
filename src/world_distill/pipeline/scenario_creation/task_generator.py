"""Execute, validate, and publish one task from a reusable World."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import random
import time
from typing import Any, Sequence

from src.evaluation import ToolCall, TrajectoryExecutor
from src.evaluation.validation.workflow import evaluation_end, goal_evaluation_end
from src.runtime import DomainRuntimeCache, World
from src.runtime.execution import state_diff
from src.utils import write_json
from src.world_distill.pipeline.models import (
    GenerationProvenance,
    TaskAuthoringInput,
    TaskAuthoringOutput,
)

from .generation_records import GenerationRecords
from .task_builder import build_task_artifacts
from .task_common import PreparedTask
from .task_instruction import build_instruction_variants, expand_device_references
from .task_inventory import TaskInventory
from .target_references import current_user
from .validator import (
    validate_dataset_case,
    validate_instruction_alignment,
    validate_public_assets,
    validate_task,
)
from .world_initializer import derive_task_world_init


class TaskAuthoringError(RuntimeError):
    """One task candidate failed a production authoring gate."""

    def __init__(self, stage: str, message: str, failure_path: Path) -> None:
        """Initialize the TaskAuthoringError."""
        super().__init__(f"{stage}: {message}")
        self.stage = stage
        self.failure_path = failure_path


class _AuthoringRun:
    def __init__(
        self,
        request: TaskAuthoringInput,
        *,
        runtime_cache: DomainRuntimeCache,
        prepared: PreparedTask | None,
    ) -> None:
        """Initialize the AuthoringRun."""
        self.request = request
        self.runtime_cache = runtime_cache
        self.prepared = prepared
        self.runtime_cache.assert_domain(request.domain)
        self.contract = runtime_cache.contract
        self.rng = random.Random(request.random_seed)
        self.case_root = (
            request.run_output_root
            / request.authoring_run_id
            / "cases"
            / request.scenario_id
        ).resolve()
        self.request_path = self.case_root / "request.json"
        self.run_config_path = self.case_root / "run_config.json"
        self.merge_audit_path = self.case_root / "component_merge_audit.json"
        self.failure_path = self.case_root / "failures.jsonl"
        self.task_list_path = self.case_root / "task_list.jsonl"
        self._failure_records: GenerationRecords | None = None
        self.successes = GenerationRecords(
            self.task_list_path,
            id_field="task_id",
            contract=self.contract,
            schema_id="urn:dcb:v2:schema:task-list-record",
        )
        self.current_stage = "request_validation"
        self.normalized_request = self._request_payload()
        self.run_config = self._run_config_payload()

    @property
    def failures(self) -> GenerationRecords:
        """Return the failures."""
        if self._failure_records is None:
            self._failure_records = GenerationRecords(
                self.failure_path,
                id_field="failure_id",
            )
        return self._failure_records

    def _request_payload(self) -> dict[str, Any]:
        """Request the payload."""
        return {
            "authoring_run_id": self.request.authoring_run_id,
            "scenario_id": self.request.scenario_id,
            "domain": self.request.domain,
            "domain_path": str(self.request.domain_path.resolve()),
            "source_world_root": str(
                self.request.source_world_root.resolve()
            ),
            "task_output_root": str(
                self.request.task_output_root.resolve()
            ),
            "run_output_root": str(self.request.run_output_root.resolve()),
            "task_constraints": deepcopy(self.request.task_constraints),
            "random_seed": self.request.random_seed,
            "initial_tweak_count": self.request.initial_tweak_count,
        }

    def _run_config_payload(self) -> dict[str, Any]:
        """Run the config payload."""
        component_merge = (
            self.prepared is not None
            and self.prepared.artifacts.seed["task_family"] == "aggregate"
        )
        return {
            "contract_version": self.contract.contract_version,
            "transport": (
                "deterministic_component_merge"
                if component_merge
                else "deterministic_template"
            ),
            "model_scenario": None,
            "requested_model": None,
            "resolved_model": None,
            "base_url": None,
        }

    def _validate_request(self) -> None:
        """Validate the request."""
        self.contract.validate_schema(
            self.normalized_request,
            "urn:dcb:v2:schema:task-authoring-request",
        )
        if self.request.domain_path.resolve() != self.runtime_cache.domain_path:
            raise ValueError("domain_path differs from the runtime cache")
        if self.request.initial_tweak_count < 0:
            raise ValueError("initial_tweak_count cannot be negative")

    def _resume(self) -> TaskAuthoringOutput | None:
        """Resume task authoring from persisted records."""
        record = self.successes.get(self.request.scenario_id)
        if record is None:
            return None
        world_root = Path(record["effective_world_root"])
        task_root = Path(record["task_root"])
        metadata_path = Path(record["validation_metadata_path"])
        audit_record_path = Path(record["audit_record_path"])
        return TaskAuthoringOutput(
            authoring_run_id=record["authoring_run_id"],
            scenario_id=record["task_id"],
            world_root=world_root,
            task_root=task_root,
            validation_metadata_path=metadata_path,
            validation_report={
                "code": "[PASS]",
                "resumed_from_records": True,
            },
            task_list_path=self.task_list_path,
            success_record=deepcopy(record),
            provenance=GenerationProvenance(
                stage="task_authoring",
                artifact_paths=(self.task_list_path,),
                model_scenario=None,
                requested_model=None,
                attempts=0,
                validated=True,
                attempt_records_path=audit_record_path,
                failure_records_path=self.failure_path,
            ),
            resumed=True,
        )

    def _append_failure(
        self,
        *,
        kind: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> Path:
        """Append the failure."""
        failure_id = f"failure_{len(self.failures.records) + 1:04d}"
        self.failures.append(
            {
                "failure_id": failure_id,
                "authoring_run_id": self.request.authoring_run_id,
                "task_id": self.request.scenario_id,
                "stage": self.current_stage,
                "kind": kind,
                "message": message,
                "details": deepcopy(details or {}),
            }
        )
        return self.failure_path

    def _failure(self, error: Exception) -> TaskAuthoringError:
        """Create a task-authoring failure record."""
        path = self._append_failure(
            kind=type(error).__name__,
            message=str(error) or type(error).__name__,
            details=getattr(error, "details", None),
        )
        return TaskAuthoringError(self.current_stage, str(error), path)

    def run(self) -> TaskAuthoringOutput:
        """Run one task-authoring request."""
        try:
            self._validate_request()
            resumed = self._resume()
            if resumed is not None:
                return resumed
            started_monotonic = time.monotonic()
            write_json(self.request_path, self.normalized_request)
            write_json(self.run_config_path, self.run_config)

            source_blueprint = self.runtime_cache.load_world_blueprint(
                self.request.source_world_root
            )
            source_world = World(
                source_blueprint.root,
                runtime_cache=self.runtime_cache,
                blueprint=source_blueprint,
            )
            if source_blueprint.domain != self.request.domain:
                raise ValueError("source world Domain differs from task request")

            self.current_stage = "world_derivation"
            if self.prepared is None:
                world_init, tweaks = derive_task_world_init(
                    source_world,
                    task_id=self.request.scenario_id,
                    rng=self.rng,
                    tweak_count=self.request.initial_tweak_count,
                )
                effective_world_batch_id = self.request.scenario_id
                inventory_snapshot: dict[str, Any] = {}
            else:
                if (
                    self.prepared.source_world_id != source_blueprint.world_id
                    or self.prepared.source_world_root.resolve()
                    != source_blueprint.root
                ):
                    raise ValueError("prepared task source World differs from request")
                world_init = deepcopy(self.prepared.world_init)
                world_init["world_id"] = self.request.scenario_id
                tweaks = [deepcopy(item) for item in self.prepared.initial_tweaks]
                effective_world_batch_id = self.prepared.effective_world_batch_id
                inventory_snapshot = deepcopy(self.prepared.inventory_snapshot)
                if self.prepared.world_blueprint is None:
                    self.contract.validate_world_init(world_init)
            task_root = (
                self.request.task_output_root / self.request.scenario_id
            ).resolve()
            world_root = task_root
            blueprint = (
                self.runtime_cache.blueprint_from_world_init(
                    world_root,
                    world_init,
                )
                if self.prepared is None
                or self.prepared.world_blueprint is None
                else self.runtime_cache.rebind_world_blueprint(
                    self.prepared.world_blueprint,
                    world_root,
                    world_init,
                )
            )

            self.current_stage = "world_validation"
            world = World(
                world_root,
                runtime_cache=self.runtime_cache,
                blueprint=blueprint,
            )

            self.current_stage = "task_sampling"
            artifacts = (
                build_task_artifacts(
                    world,
                    task_id=self.request.scenario_id,
                    constraints=self.request.task_constraints,
                    rng=self.rng,
                )
                if self.prepared is None
                else self.prepared.artifacts
            )
            public_inventory = TaskInventory(world)
            user = current_user(public_inventory, self.request.task_constraints['requirements'].get('current_user'), self.rng)
            artifacts = expand_device_references(artifacts, public_inventory, current_user=user, rng=self.rng)
            metadata = artifacts.metadata
            metadata["derived"].update(
                {
                    "source_world_id": source_blueprint.world_id,
                    "effective_world_batch_id": effective_world_batch_id,
                    "batch_inventory": inventory_snapshot,
                    "initial_tweaks": deepcopy(tweaks),
                    "instruction_variants": deepcopy(
                        [artifacts.instruction_template]
                        if isinstance(artifacts.instruction_template, str)
                        else artifacts.instruction_template
                    ),
                    "instruction_style": "direct",
                    "current_user": deepcopy(user),
                    "random_seed": self.request.random_seed,
                    "public_entity_names": sorted(
                        {
                            *public_inventory.space_names.values(),
                            *public_inventory.device_names.values(),
                            *(name for names in public_inventory.device_name_variants.values() for name in names),
                        }
                    ),
                }
            )

            component_merge = (
                self.prepared is not None
                and artifacts.seed["task_family"] == "aggregate"
            )
            sampling = artifacts.seed["sampling"]
            if component_merge:
                metadata["derived"]["component_validation_reuse"] = {
                    "strategy": sampling["merge_strategy"],
                    "source_families": deepcopy(sampling["source_families"]),
                    "source_task_ids": deepcopy(sampling["source_task_ids"]),
                }
            else:
                metadata["derived"]["llm_authoring"] = {
                    "enabled": False,
                    "instruction_source": "rule_template",
                }
            templates = (
                [artifacts.instruction_template]
                if isinstance(artifacts.instruction_template, str)
                else artifacts.instruction_template
            )
            primary_instruction = (
                self.prepared.public_instruction
                if self.prepared is not None
                and self.prepared.public_instruction is not None
                else templates[0]
            )
            primary_instruction = artifacts.seed["derived"].get("target_reference_rewrites", {}).get(primary_instruction, primary_instruction)
            if primary_instruction not in templates:
                raise ValueError("primary instruction is not a template variant")
            self.current_stage = "instruction_template"
            task_meta = {
                "task_family": artifacts.seed["task_family"],
                "task_subtype": artifacts.seed["task_subtype"],
            }
            if component_merge:
                task_meta["source_task_ids"] = deepcopy(
                    sampling["source_task_ids"]
                )
            task = validate_task(
                {
                    "task_id": self.request.scenario_id,
                    "current_user": user,
                    "instruction": primary_instruction,
                    "instruction_variants": build_instruction_variants(
                        artifacts.instruction_template
                    ),
                    "meta": task_meta,
                },
                contract=self.contract,
            )

            self.current_stage = "instruction_validation"
            validate_instruction_alignment(
                artifacts.instruction_template,
                task["instruction"],
                artifacts.seed,
            )
            validate_public_assets(task=task, world_init=world_init)

            self.current_stage = "reference_replay"
            reference_world = world
            reference_world.bind_memory(artifacts.memory)
            reference_world.bind_evaluation_horizon(evaluation_end(artifacts.target))
            trajectory = create_reference_trajectory(
                reference_world,
                task_id=self.request.scenario_id,
                trajectory_id=f"{self.request.scenario_id}_reference",
                turns=artifacts.reference_plan["turns"],
                source="ground_truth",
                validate=False,
            )
            if any(atom["kind"] == "goal" for atom in artifacts.seed["atoms"]):
                start = world.get_initial_state()["runtime"]["time_state"]["elapsed_minutes"]
                end = goal_evaluation_end(start, reference_world.termination["elapsed_minutes"])
                artifacts.target["evaluation_end_minute"] = end
                reference_world = World(world_root, runtime_cache=self.runtime_cache, blueprint=blueprint)
                reference_world.bind_memory(artifacts.memory)
                reference_world.bind_evaluation_horizon(end)
                trajectory = create_reference_trajectory(
                    reference_world, task_id=self.request.scenario_id,
                    trajectory_id=f"{self.request.scenario_id}_reference",
                    turns=artifacts.reference_plan["turns"], source="ground_truth", validate=False,
                )

            self.current_stage = "candidate_finalization"
            gates = {
                "schema": "PASS",
                "privacy": "PASS",
                "atom_graph": "PASS",
                "instruction_alignment": "PASS",
                "target_semantics": "PASS",
                "reference_replay": "PASS",
                "evaluation": "PASS",
                "termination": "PASS",
            }
            gates[
                "component_validation_reuse"
                if component_merge
                else "instruction_template_reuse"
            ] = "PASS"
            validation_metadata = {
                "authoring_run_id": self.request.authoring_run_id,
                "scenario_id": self.request.scenario_id,
                "contract_version": self.contract.contract_version,
                "validated": True,
                "reference_source": "ground_truth",
                "reference_repairs": 0,
                "termination": trajectory["records"][-1]["termination"],
                "meta": metadata,
                "gates": gates,
            }
            destinations = {
                "world_init": world_root / "world_init.json",
                "task": task_root / "task.json",
                "target": task_root / "target.json",
                "reference_trajectory": task_root / "reference_trajectory.json",
                "validation_metadata": task_root / "validation_metadata.json",
            }
            payloads = {
                "world_init": world_init,
                "task": task,
                "target": artifacts.target,
                "reference_trajectory": trajectory,
                "validation_metadata": validation_metadata,
            }
            if artifacts.memory is not None:
                destinations["memory"] = task_root / "memory.json"
                payloads["memory"] = artifacts.memory
            else:
                stale_memory = task_root / "memory.json"
                if stale_memory.is_file():
                    stale_memory.unlink()
            for name, destination in destinations.items():
                write_json(destination, payloads[name])

            report = validate_dataset_case(
                world_root,
                task_root,
                domain_path=self.request.domain_path,
                runtime_cache=self.runtime_cache,
                world_blueprint=blueprint,
            )
            validation_metadata["meta"]["derived"]["validated_state_changes"] = state_diff(world.get_initial_state(), report["reference_snapshot"])
            used_tools = {f"{record['call']['command']['target']}_{record['call']['command']['function']}" for record in trajectory["records"] if record["kind"] == "tool_exchange" and record["call"]["command"]["target"] not in {"session", "memory"}}
            validation_metadata["meta"]["derived"]["referenced_capabilities"] = [
                {"target": tool["target"], "function": tool["function"], "reads": tool.get("reads", []), "writes": tool.get("writes", [])}
                for tool in world.get_tool_catalog()["tools"] if tool["tool_id"] in used_tools
            ]
            write_json(destinations["validation_metadata"], validation_metadata)
            if report["post_simulation"] is not None:
                evidence_root = task_root / "reference_simulation"
                for name, payload in report["post_simulation"].items():
                    write_json(evidence_root / f"{name}.json", payload)
            audit_record_path = self.run_config_path
            extra_artifacts: tuple[Path, ...] = (self.run_config_path,)
            if component_merge:
                write_json(
                    self.merge_audit_path,
                    {
                        "strategy": "validated_components",
                        "task_id": self.request.scenario_id,
                        "source_families": deepcopy(
                            artifacts.seed["sampling"]["source_families"]
                        ),
                        "source_task_ids": deepcopy(
                            artifacts.seed["sampling"]["source_task_ids"]
                        ),
                        "model_calls": 0,
                        "validation_gates": deepcopy(gates),
                    },
                )
                audit_record_path = self.merge_audit_path
                extra_artifacts = (self.merge_audit_path,)
            success_record = {
                "generation_run_id": self.request.authoring_run_id,
                "authoring_run_id": self.request.authoring_run_id,
                "task_id": self.request.scenario_id,
                "domain": self.request.domain,
                "task_family": artifacts.seed["task_family"],
                "task_subtype": artifacts.seed["task_subtype"],
                "sampling_profile_id": artifacts.seed["sampling"]["profile_id"],
                "sampling": deepcopy(artifacts.seed["sampling"]),
                "source_world_id": source_blueprint.world_id,
                "source_world_root": str(source_blueprint.root),
                "effective_world_root": str(world_root),
                "effective_world_batch_id": effective_world_batch_id,
                "task_root": str(task_root),
                "validation_metadata_path": str(
                    destinations["validation_metadata"]
                ),
                "instruction_style": "direct",
                "random_seed": self.request.random_seed,
                "initial_tweaks": deepcopy(tweaks),
                "elapsed_seconds": round(
                    time.monotonic() - started_monotonic,
                    6,
                ),
                "model_calls": 0,
                "usage": {},
                "response_models": [],
                "audit_record_path": str(audit_record_path),
            }
            self.successes.append(success_record)
            return TaskAuthoringOutput(
                authoring_run_id=self.request.authoring_run_id,
                scenario_id=self.request.scenario_id,
                world_root=world_root,
                task_root=task_root,
                validation_metadata_path=destinations[
                    "validation_metadata"
                ],
                validation_report=report,
                task_list_path=self.task_list_path,
                success_record=deepcopy(success_record),
                provenance=GenerationProvenance(
                    stage="task_authoring",
                    artifact_paths=tuple(destinations.values())
                    + extra_artifacts
                    + (self.task_list_path,),
                    model_scenario=None,
                    requested_model=None,
                    usage={},
                    attempts=0,
                    validated=True,
                    response_models=(),
                    attempt_records_path=audit_record_path,
                    failure_records_path=self.failure_path,
                ),
            )
        except TaskAuthoringError:
            raise
        except (KeyError, RuntimeError, TypeError, ValueError) as error:
            raise self._failure(error) from error


def generate_task(
    request: TaskAuthoringInput,
    *,
    runtime_cache: DomainRuntimeCache | None = None,
    prepared: PreparedTask | None = None,
) -> TaskAuthoringOutput:
    """Author one task through all gates and append its success last."""
    cache = runtime_cache or DomainRuntimeCache(
        request.domain,
        request.domain_path,
    )
    return _AuthoringRun(
        request,
        runtime_cache=cache,
        prepared=prepared,
    ).run()


def create_reference_trajectory(
    world: World,
    *,
    task_id: str,
    trajectory_id: str,
    turns: Sequence[Sequence[dict[str, Any]]],
    source: str = "ground_truth",
    validate: bool = True,
) -> dict[str, Any]:
    """Execute command turns and record exact tool results."""
    executor = TrajectoryExecutor(world, task_id=task_id)
    records: list[dict[str, Any]] = []
    call_index = 0
    for turn_index, commands in enumerate(turns, start=1):
        turn_id = f"turn_{turn_index}"
        executor.begin_turn(
            turn_id=turn_id,
            turn_index=turn_index,
            max_turns=len(turns),
        )
        for command in commands:
            call_index += 1
            call = ToolCall(
                call_id=f"call_{call_index}",
                turn_id=turn_id,
                command=deepcopy(command),
            )
            result = executor.execute_call(call)
            records.append(
                {
                    "kind": "tool_exchange",
                    "call": call.to_dict(),
                    "result": result.to_dict(),
                }
            )
        if not world.terminated:
            boundary = {
                "turn_id": turn_id,
                "apply_after_turn": True,
            }
            executor.submit_boundary(boundary)
            records.append(
                {"kind": "turn_boundary", "boundary": boundary}
            )
        if not world.terminated and turn_index == len(turns):
            world.terminate_max_turns(
                turn_id=turn_id,
                turn_index=turn_index,
                max_turns=len(turns),
            )
        if world.terminated:
            break
    termination = world.termination
    if termination is None:
        raise RuntimeError("reference creation ended without termination")
    records.append(
        {"kind": "termination", "termination": termination}
    )
    trajectory = {
        "trajectory_id": trajectory_id,
        "world_id": world.get_state()["world_id"],
        "task_id": task_id,
        "source": source,
        "records": records,
    }
    if validate:
        world.contract.validate_trajectory(trajectory)
    return trajectory
