"""Single-task execution loop, world interaction, and evaluation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.runtime import DomainRuntimeCache, World, WorldBlueprint

from ..loading import TaskBundle, TaskLoader
from ..interfaces import BaseAgent
from ..validation import evaluate_world
from ..validation.workflow import complete_background_simulation, evaluation_end
from .environment import EvaluationEnvironment


@dataclass(frozen=True)
class AgentRun:
    """Completed agent trajectory and its private evaluation report."""
    
    trajectory: dict[str, Any]
    report: dict[str, Any]
    provider_audit: tuple[dict[str, Any], ...] = ()


class AgentRunner:
    """Run one agent without exposing private target evidence."""
    
    def __init__(
            self,
            world_dir: str | Path,
            agent: BaseAgent,
            *,
            task_root: str | Path | None = None,
            domain_path: str | Path | None = None,
            domain: str | None = None,
            contract_root: str | Path | None = None,
            runtime_cache: DomainRuntimeCache | None = None,
            blueprint: WorldBlueprint | None = None,
            task_bundle: TaskBundle | None = None,
            max_turns: int,
            require_device_tool_discovery: bool = True,
    ) -> None:
        """Initialize the AgentRunner."""
        from src.contracts import load_json
        
        self.world = World(
            world_dir,
            domain_path,
            domain=domain or (
                runtime_cache.domain if runtime_cache else load_json(Path(world_dir) / "world_init.json")["domain"][
                    "type"]),
            contract_root=contract_root,
            runtime_cache=runtime_cache,
            blueprint=blueprint,
            require_device_tool_discovery=require_device_tool_discovery,
        )
        if task_bundle is None:
            self.task_bundle = TaskLoader(
                contract=self.world.contract
            ).load(task_root or world_dir, self.world)
        else:
            self.task_bundle = task_bundle
            self.world.bind_memory(task_bundle.memory)
            self.world.bind_evaluation_horizon(evaluation_end(task_bundle.target))
        self.agent = agent
        self.environment = EvaluationEnvironment(self.world, self.task_bundle, max_turns=max_turns)
        self.records = self.environment.records
    
    def run(
            self,
            *,
            trajectory_id: str,
            replay_reference_snapshot: dict[str, Any] | None = None,
    ) -> AgentRun:
        try:
            return self._run(trajectory_id=trajectory_id, replay_reference_snapshot=replay_reference_snapshot)
        finally:
            complete_background_simulation(self.world, self.task_bundle)
    
    def _run(
            self,
            *,
            trajectory_id: str,
            replay_reference_snapshot: dict[str, Any] | None = None,
    ) -> AgentRun:
        """Run the agent loop for one trajectory."""
        self.agent.reset(self.environment.get_task_context())
        observation = self.environment.observe()
        while not self.environment.terminated:
            tool_calls = self.agent.act(observation)
            self.environment.step(tool_calls)
            observation = self.environment.observe()
        
        trajectory = {
            "trajectory_id": trajectory_id,
            "world_id": self.world.get_state()["world_id"],
            "task_id": self.task_bundle.task_id,
            "source": "agent",
            "records": self.records,
        }
        self.world.contract.validate_trajectory(trajectory)
        report = evaluate_world(
            self.world,
            self.task_bundle,
            replay_reference_snapshot=replay_reference_snapshot,
        )
        return AgentRun(
            trajectory=trajectory,
            report=report,
            provider_audit=tuple(
                deepcopy(getattr(self.agent, "audit_records", ()))
            ),
        )
