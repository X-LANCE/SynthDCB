from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.contracts import ContractPackage, is_number
from src.object_model import MutableWorldState


def _normalize_value(value: float, spec: dict[str, Any]) -> int | float:
    """Clamp, round, and cast a value according to its property specification."""
    minimum = spec["minimum"]
    maximum = spec["maximum"]
    if minimum is not None:
        value = max(value, float(minimum))
    if maximum is not None:
        value = min(value, float(maximum))
    rounded = round(value, int(spec["precision"]))
    return int(rounded) if spec["type"] == "integer" else float(rounded)


class EffectReducer:
    def __init__(
        self,
        state: MutableWorldState,
        world_spec: dict[str, Any],
        contract: ContractPackage,
    ) -> None:
        """Initialize the EffectReducer."""
        self.state = state
        self.world_spec = world_spec
        self.contract = contract
        self.catalog = contract.catalogs[world_spec["domain"]["type"]]
        self._baselines: dict[tuple[str, str], float] = {}
        self._contributions: dict[tuple[str, str], dict[str, float]] = {}
        for space_id, space in state.spaces.items():
            for prop, value in space.properties.items():
                spec = self.catalog["space_properties"].get(prop)
                if spec and spec["allowed_effect_functions"] and is_number(value):
                    self._baselines[(space_id, prop)] = float(value)

    def checkpoint(self) -> dict[str, Any]:
        """Return the checkpoint."""
        return {
            "baselines": deepcopy(self._baselines),
            "contributions": deepcopy(self._contributions),
        }

    def restore(self, checkpoint: dict[str, Any]) -> None:
        """Restore a previously captured effect-reducer checkpoint."""
        self._baselines = deepcopy(checkpoint["baselines"])
        self._contributions = deepcopy(checkpoint["contributions"])

    def apply(self, effects: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply effects and return their audit records."""
        self.contract.validate_effect_batch(effects, self.world_spec)
        next_baselines = deepcopy(self._baselines)
        next_contributions = deepcopy(self._contributions)
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for effect in effects:
            key = (effect["target"], effect["parameters"]["property"])
            grouped.setdefault(key, []).append(effect)

        commits: dict[tuple[str, str], dict[str, Any]] = {}
        for key in sorted(grouped):
            target, prop = key
            spec = self.catalog["space_properties"][prop]
            before = deepcopy(self.state.spaces[target].properties[prop])
            baseline = next_baselines[key]
            contributions = next_contributions.setdefault(key, {})
            delta = 0.0
            approaches: list[dict[str, Any]] = []
            for effect in grouped[key]:
                function = effect["function"]
                parameters = effect["parameters"]
                if function == "set_contribution":
                    contributions[effect["source"]] = float(parameters["value"])
                elif function == "delta":
                    delta += float(parameters["value"])
                else:
                    approaches.append(parameters)

            if not approaches:
                baseline += delta
            else:
                change = 0.0
                for approach in approaches:
                    target_value = float(approach["value"])
                    rate = abs(float(approach["rate_per_minute"]))
                    distance = target_value - baseline
                    change += max(-rate, min(rate, distance))
                baseline += change
            next_baselines[key] = baseline
            raw_value = baseline + sum(contributions.values())
            normalized = _normalize_value(raw_value, spec)
            commits[key] = {
                "before": before,
                "raw_value": raw_value,
                "normalized_value": normalized,
                "after": normalized,
            }

        for (target, prop), commit in commits.items():
            self.state.spaces[target].properties[prop] = commit["after"]
        self._baselines = next_baselines
        self._contributions = next_contributions

        applications: list[dict[str, Any]] = []
        for effect in effects:
            key = (effect["target"], effect["parameters"]["property"])
            commit = commits[key]
            applications.append(
                {
                    "effect": deepcopy(effect),
                    "before": deepcopy(commit["before"]),
                    "raw_value": commit["raw_value"],
                    "clamped_value": float(commit["normalized_value"]),
                    "normalized_value": commit["normalized_value"],
                    "after": deepcopy(commit["after"]),
                    "status": "applied",
                }
            )
        return applications
