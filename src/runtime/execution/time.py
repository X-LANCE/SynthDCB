from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from .audit import AuditTrail, state_diff
from src.contracts import ContractPackage
from .effects import EffectReducer
from src.contracts.errors import EnvironmentContractError
from .errors import RuntimeExecutionError
from src.object_model import MutableWorldState


class TimeRuntime:
    def __init__(
        self,
        state: MutableWorldState,
        world_spec: dict[str, Any],
        contract: ContractPackage,
        reducer: EffectReducer,
        audit: AuditTrail,
        snapshot: Callable[[], dict[str, Any]],
        hook_context: Callable[[str, dict[str, Any], int | None], dict[str, Any]],
        terminate: Callable[[str], dict[str, Any]],
        notify_dependencies: Callable[[dict[str, Any]], list[dict[str, Any]]],
    ) -> None:
        """Initialize the TimeRuntime."""
        self.state = state
        self.world_spec = world_spec
        self.contract = contract
        self.reducer = reducer
        self.audit = audit
        self.snapshot = snapshot
        self.hook_context = hook_context
        self.terminate = terminate
        self.notify_dependencies = notify_dependencies
        self.evaluation_end_minute: int | None = None

    @property
    def max_elapsed_minutes(self) -> int | None:
        limits = [value for value in (
            self.state.time_policy.get("max_elapsed_minutes"), self.evaluation_end_minute,
        ) if value is not None]
        return min(limits) if limits else None

    def advance(
        self,
        minutes: int,
        *,
        cause: str,
        action_record_id: str | None = None,
        turn_id: str | None = None,
        enforce_agent_limit: bool = True,
    ) -> dict[str, Any]:
        """Return the advance."""
        if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes < 0:
            raise RuntimeExecutionError(
                "[VALIDATION_ERROR]",
                "invalid_parameters",
                "minutes must be a non-negative integer",
                "$.parameters.minutes",
            )
        requested_minutes = minutes
        max_elapsed = self.max_elapsed_minutes if enforce_agent_limit else None
        remaining = (
            None
            if max_elapsed is None
            else max_elapsed - self.state.time_state["elapsed_minutes"]
        )
        applied_minutes = (
            requested_minutes
            if remaining is None
            else min(requested_minutes, max(remaining, 0))
        )
        limit_reached = (
            max_elapsed is not None
            and self.state.time_state["elapsed_minutes"] + applied_minutes
            == max_elapsed
        )
        state_checkpoint = self.state.checkpoint()
        reducer_checkpoint = self.reducer.checkpoint()
        audit_checkpoint = self.audit.checkpoint()
        tick_sequences: list[int] = []
        try:
            for _ in range(applied_minutes):
                tick_sequences.append(self._one_minute_tick()["sequence"])
        except Exception:
            self.state.restore(state_checkpoint)
            self.reducer.restore(reducer_checkpoint)
            self.audit.restore(audit_checkpoint)
            raise

        time_advance: dict[str, Any] = {
            "cause": cause,
            "requested_minutes": requested_minutes,
            "minutes": applied_minutes,
            "limit_reached": limit_reached,
            "tick_sequences": tick_sequences,
        }
        if action_record_id is not None:
            time_advance["action_record_id"] = action_record_id
        if turn_id is not None:
            time_advance["turn_id"] = turn_id
        self.audit.append(
            {
                "record_type": "time_advance",
                "simulation_time": deepcopy(self.state.time_state),
                "status": "committed",
                "events": [],
                "effects": [],
                "state_diff": [],
                "time_advance": time_advance,
            }
        )
        if limit_reached:
            self.terminate("elapsed_time_limit")
        return {
            "requested_minutes": requested_minutes,
            "applied_minutes": applied_minutes,
            "tick_count": len(tick_sequences),
            "limit_reached": limit_reached,
            "time_state": deepcopy(self.state.time_state),
        }

    def _one_minute_tick(self) -> dict[str, Any]:
        """Return the one minute tick."""
        before = self.snapshot()
        self.state.advance_clock_one_minute()
        pre_tick = self.snapshot()
        effects: list[dict[str, Any]] = []
        events: list[dict[str, Any]] = []
        for device_id in sorted(self.state.devices):
            device = self.state.devices[device_id]
            hook = getattr(device.instance, "_on_tick", None)
            if not callable(hook):
                continue
            dependencies = set(device.effect_properties)
            if not dependencies.issubset(device.property_names):
                continue
            code, emitted = hook(self.hook_context(device_id, pre_tick, 1))
            if code != "[PASS]":
                raise RuntimeExecutionError("[EFFECT_ERROR]", "effect_validation", code)
            for effect in emitted:
                if effect.get("trigger") != "tick" or effect.get("source") != device_id:
                    raise RuntimeExecutionError(
                        "[EFFECT_ERROR]",
                        "effect_validation",
                        "tick effect trigger/source does not match its hook",
                    )
                effects.append(deepcopy(effect))
            events.append(
                {
                    "trigger": "tick",
                    "source": device_id,
                    "hook": "_on_tick",
                    "status": "dispatched",
                    "changed_properties": [],
                }
            )
        try:
            applications = self.reducer.apply(effects)
        except EnvironmentContractError as exc:
            code = "[CONFLICT]" if exc.code == "EFFECT_CONFLICT" else "[EFFECT_ERROR]"
            kind = "effect_conflict" if code == "[CONFLICT]" else "effect_validation"
            raise RuntimeExecutionError(code, kind, exc.message, exc.path) from exc
        events.extend(self.notify_dependencies(before))
        after = self.snapshot()
        differences = state_diff(before, after)
        for event in events:
            event["changed_properties"] = sorted(
                item["property"] for item in differences
                if item["scope"] == "object" and item["target_id"] == event["source"]
            )
        return self.audit.append(
            {
                "record_type": "tick",
                "simulation_time": deepcopy(self.state.time_state),
                "status": "committed",
                "events": events,
                "effects": applications,
                "state_diff": differences,
            }
        )

    def submit_turn_boundary(
        self,
        turn_id: str,
        *,
        apply_after_turn: bool,
        terminated: bool,
    ) -> dict[str, Any]:
        """Record the boundary of an agent turn."""
        boundary = {
            "turn_id": turn_id,
            "apply_after_turn": apply_after_turn,
        }
        self.contract.validate_schema(boundary, "urn:dcb:v2:schema:turn-boundary")
        if terminated:
            raise RuntimeExecutionError(
                "[SESSION_FINISHED]",
                "session_finished",
                "turn boundaries are not accepted after termination",
            )
        record = self.audit.append(
            {
                "record_type": "turn_boundary",
                "simulation_time": deepcopy(self.state.time_state),
                "status": "observed",
                "links": {"turn_id": turn_id},
                "events": [],
                "effects": [],
                "state_diff": [],
            }
        )
        if apply_after_turn:
            minutes = self.state.time_policy["after_turn_default_minutes"]
            if minutes:
                self.advance(minutes, cause="after_turn", turn_id=turn_id)
        return record
