"""Task-seed, public-asset, instruction-alignment, and complete-bundle validation."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
from typing import Any

from src.contracts import ContractPackage, load_json
from src.evaluation import evaluate_world, TaskLoader, TrajectoryExecutor
from src.evaluation.validation.workflow import complete_background_simulation
from src.runtime import DomainRuntimeCache, World, WorldBlueprint

from .task_common import (
    graph_depth,
    InstructionAlignmentError,
    TaskArtifacts,
    TaskSeedError,
)
from .task_inventory import natural_key
from .task_sampler import AGGREGATE_COMPONENTS, TASK_SUBTYPES


# Task seed and built artifacts
# ------------------------------------------------------------------------


ATOM_KINDS = {"control", "query", "goal", "memory", "workflow"}


def validate_task_seed(seed: dict[str, Any]) -> None:
    """Validate the task seed."""
    family = seed.get("task_family")
    subtype = seed.get("task_subtype")
    if family not in TASK_SUBTYPES or subtype not in TASK_SUBTYPES[family]:
        raise TaskSeedError(f"unknown task type {family}.{subtype}")
    atoms = seed.get("atoms")
    if not isinstance(atoms, list) or not atoms:
        raise TaskSeedError("task seed requires atoms")
    identifiers = [atom.get("id") for atom in atoms]
    if len(identifiers) != len(set(identifiers)):
        raise TaskSeedError("atom IDs must be unique")
    known = set(identifiers)
    for atom in atoms:
        if atom.get("kind") not in ATOM_KINDS:
            raise TaskSeedError("unknown atom kind")
        dependencies = atom.get("depends_on")
        if not isinstance(dependencies, list) or not set(dependencies).issubset(known):
            raise TaskSeedError("atom dependency references an unknown atom")
        if atom["id"] in dependencies:
            raise TaskSeedError("an atom cannot depend on itself")
    graph_depth(atoms)
    feasibility = seed.get("expected_outcome", {}).get("feasibility")
    if feasibility not in {"feasible", "infeasible", "partial"}:
        raise TaskSeedError("expected_outcome.feasibility is invalid")
    outcomes = seed["expected_outcome"]["atoms"]
    if set(outcomes) != known or set(outcomes.values()) - {"success", "infeasible", "blocked"}:
        raise TaskSeedError("atom outcomes must cover every atom with a valid status")
    succeeded = sum(status == "success" for status in outcomes.values())
    if feasibility != ("feasible" if succeeded == len(atoms) else "partial" if succeeded else "infeasible"):
        raise TaskSeedError("partial infeasibility requires both executable and failed requests")
    by_id = {atom["id"]: atom for atom in atoms}
    for atom in atoms:
        if outcomes[atom["id"]] == "blocked":
            source = atom["spec"].get("target_from_query") or atom["spec"].get("value_from_query")
            if (source not in atom["depends_on"] or by_id[source]["kind"] != "query"
                    or outcomes[source] == "success" or atom["spec"].get("reason_code") != "BLOCKED_BY_DEPENDENCY"):
                raise TaskSeedError("blocked requests require a failed Query supplying their target or value")
    kinds = {atom["kind"] for atom in atoms}
    if feasibility == "feasible":
        if family == "query" and not (
            kinds == {"query"}
            or kinds == {"query", "memory"}
            and all(
                atom["depends_on"]
                for atom in atoms
                if atom["kind"] == "memory"
            )
        ):
            raise TaskSeedError(
                "Query tasks may append only dependent Memory atoms"
            )
        if family == "control" and "control" not in kinds:
            raise TaskSeedError("Control tasks require a Control atom")
        if family == "goal" and "goal" not in kinds:
            raise TaskSeedError("Goal tasks require a Goal atom")
        if family == "workflow" and "workflow" not in kinds:
            raise TaskSeedError("Workflow tasks require a Workflow atom")
        if family == "aggregate":
            required = set(AGGREGATE_COMPONENTS[subtype])
            if not required.issubset(kinds):
                raise TaskSeedError(
                    f"Aggregate {subtype} requires Atom kinds {sorted(required)}"
                )

    sampling = seed.get("sampling")
    if not isinstance(sampling, dict) or sampling.get("task_type") != f"{family}.{subtype}":
        raise TaskSeedError("sampling record does not match the task type")
    selection = sampling.get("target_selection")
    if isinstance(selection, dict) and "selected_ids" in selection:
        selected = selection["selected_ids"]
        ranked_query = family == "query" and subtype.startswith("target.comparison.")
        if not ranked_query and selected != sorted(selected, key=natural_key):
            raise TaskSeedError("selected target IDs must use natural order")

    if family == "control" and feasibility == "feasible":
        controls = [atom for atom in atoms if atom["kind"] == "control"]
        properties = {atom["spec"]["property"] for atom in controls}
        value_details = sampling.get("property_target_value", {})
        if value_details.get("method") == "query.property.device" and any(
            recipe.get("source_property") != recipe.get("property")
            for recipe in value_details.get("recipes", [])
        ):
            raise TaskSeedError(
                "query-derived Control values require the same source property"
            )
        if len(properties) > 1:
            power_off = any(
                atom["spec"]["property"] == "power"
                and atom["spec"]["assertion"].get("value") is False
                for atom in controls
            )
            if power_off and "operation_groups" not in sampling:
                raise TaskSeedError(
                    "a multi-property Control task cannot include power off"
                )
    if family == "control" and subtype == "single":
        post = [
            atom for atom in atoms
            if atom["kind"] == "query" and atom["spec"].get("role") == "post_control_answer"
        ]
        if post and not all(
            parent.startswith("c") for atom in post for parent in atom["depends_on"]
        ):
            raise TaskSeedError("post-Control Query must depend on Control")


def validate_task_artifacts(world: World, artifacts: TaskArtifacts) -> None:
    """Validate a built task's seed, target, memory bindings, and reference plan."""
    validate_task_seed(artifacts.seed)
    world.contract.validate_target(
        artifacts.target,
        world.get_world_spec(),
        world.get_initial_state(),
    )
    if artifacts.memory is not None:
        world.contract.validate_memory(artifacts.memory)
    available_memory_ids = {
        record["memory_id"]
        for record in (artifacts.memory or {"records": []})["records"]
    }
    if not set(artifacts.target["required_memory_ids"]).issubset(
        available_memory_ids
    ):
        raise TaskSeedError(
            "required memory IDs are missing from the task fixture"
        )
    world.contract.validate_schema(
        artifacts.reference_plan,
        "urn:dcb:v2:schema:reference-plan",
    )


# Public task payloads and privacy
# ------------------------------------------------------------------------


PRIVATE_KEYS = {
    "answer",
    "answers",
    "expected_answers",
    "expected_reports",
    "ground_truth",
    "memory",
    "required_memory_ids",
    "reference",
    "reference_trajectory",
    "required_tools",
    "target",
    "trajectory",
}


class PrivacyValidationError(ValueError):
    """Public authoring output contains private evaluation evidence."""


def _private_paths(value: Any, path: str) -> list[str]:
    """Return the private paths."""
    findings: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}"
            if key.lower() in PRIVATE_KEYS:
                findings.append(child)
            findings.extend(_private_paths(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(
                _private_paths(item, f"{path}[{index}]")
            )
    return findings


def validate_public_assets(
    *,
    task: dict[str, Any],
    world_init: dict[str, Any] | None = None,
    split_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Reject private-key leakage in every agent-visible asset."""
    findings = _private_paths(task, "$.task")
    if world_init is not None:
        findings.extend(_private_paths(world_init, "$.world_init"))
    if split_metadata is not None:
        findings.extend(
            _private_paths(split_metadata, "$.split_metadata")
        )
    if findings:
        raise PrivacyValidationError(
            "private evaluation data leaked into public assets: "
            + ", ".join(findings)
        )
    return {"code": "[PASS]", "private_paths": []}


def validate_task(
    payload: dict[str, Any],
    *,
    contract: ContractPackage,
) -> dict[str, Any]:
    """Return the task."""
    task = deepcopy(payload)
    contract.validate_task(task)
    validate_public_assets(task=task)
    return task


# Instruction alignment and protected literals
# ------------------------------------------------------------------------


def instruction_literal_anchors(seed: dict[str, Any]) -> set[str]:
    """Return non-entity public literals shared by rewrite prompts and validation."""
    public_anchors = {
        str(value).casefold()
        for value in seed["derived"].get("public_anchors", [])
        if str(value).strip()
    }
    anchors = set(public_anchors)
    entity_names = {
        str(value).casefold()
        for value in seed["derived"].get("public_entity_names", [])
    }
    if entity_names:
        anchors -= entity_names
    else:
        semantic: set[str] = set()
        for atom in seed.get("atoms", []):
            spec = atom.get("spec", {})
            prop = spec.get("property")
            if isinstance(prop, str):
                semantic.add(prop.casefold())
            if atom.get("kind") == "memory" or "memory_binding" in spec:
                continue
            assertion = spec.get("assertion", {})
            for value in (
                spec.get("requested_value"),
                assertion.get("value"),
                assertion.get("min"),
                assertion.get("max"),
            ):
                if value is not None and not isinstance(value, bool):
                    semantic.add(str(value).casefold())
        value_details = seed.get("sampling", {}).get(
            "property_target_value", {}
        )
        if value_details.get("method") != "memory":
            for record in value_details.get("records", []):
                semantic.add(str(record.get("property", "")).casefold())
                value = record.get("requested_value")
                if value is not None and not isinstance(value, bool):
                    semantic.add(str(value).casefold())
            for recipe in value_details.get("recipes", []):
                semantic.add(str(recipe.get("property", "")).casefold())
                for key in ("value", "amount", "selected_value"):
                    value = recipe.get(key)
                    if value is not None and not isinstance(value, bool):
                        semantic.add(str(value).casefold())
        selection = seed.get("sampling", {}).get("target_selection", {})
        for key in ("property", "k"):
            value = selection.get(key)
            if value is not None:
                semantic.add(str(value).casefold())
        anchors &= semantic
    return anchors


def validate_instruction_alignment(
    instruction_template: str | list[str],
    instruction: str,
    seed: dict[str, Any],
    *,
    allow_entity_aliases: bool = False,
    allow_property_paraphrases: bool = False,
    allow_intent_shift: bool = False,
) -> None:
    """Validate the instruction alignment."""
    lowered = instruction.casefold()
    public_anchors = {
        str(value).casefold()
        for value in seed["derived"].get("public_anchors", [])
        if str(value).strip()
    }
    anchors = instruction_literal_anchors(seed) if allow_entity_aliases else set(public_anchors)
    if allow_intent_shift:
        anchors.clear()
    if allow_property_paraphrases:
        anchors -= {
            str(atom.get("spec", {}).get("property", "")).casefold()
            for atom in seed.get("atoms", [])
        }
    # Short number words cover conversational counts; larger values retain digits.
    number_words = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split()
    entity_aliases = {key.casefold(): [name.casefold() for name in values]
                      for key, values in seed["derived"].get("public_entity_aliases", {}).items()}
    missing = sorted(
        anchor for anchor in anchors
        if not any(name in lowered for name in (anchor, *entity_aliases.get(anchor, []))) and not (
            allow_property_paraphrases
            and anchor.isdigit()
            and int(anchor) < len(number_words)
            and re.search(rf"\b{number_words[int(anchor)]}\b", lowered)
        )
    )
    if missing:
        raise InstructionAlignmentError(
            "instruction rewrite dropped protected public anchors: "
            + ", ".join(missing)
        )
    normalized_public_anchors = {
        re.sub(r"[_\s-]+", " ", anchor).strip()
        for anchor in public_anchors | {
            str(name).casefold()
            for name in seed["derived"].get("public_entity_names", [])
        }
    }
    leaked = []
    for identifier in seed["derived"].get("private_identifiers", []):
        token = str(identifier).casefold()
        normalized = re.sub(r"[_\s-]+", " ", token).strip()
        mentioned = re.search(
            rf"(?<![a-z0-9_]){re.escape(token)}(?![a-z0-9_])",
            lowered,
        )
        publicly_named = any(
            re.search(
                rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])",
                anchor,
            )
            for anchor in normalized_public_anchors
        )
        if mentioned and not publicly_named:
            leaked.append(identifier)
    if leaked:
        raise InstructionAlignmentError(
            "instruction rewrite exposed internal target IDs: "
            + ", ".join(sorted(leaked, key=natural_key))
        )
    memory_value_atoms = [
        atom for atom in seed["atoms"]
        if isinstance(atom.get("spec", {}).get("memory_binding"), dict)
    ]
    memory_write_atoms = [
        atom for atom in seed["atoms"] if atom.get("kind") == "memory"
    ]
    if not allow_intent_shift and (memory_value_atoms or memory_write_atoms) and not any(
        cue in lowered
        for cue in (
            "saved",
            "save",
            "remember",
            "remembered",
            "update",
            "preference",
            "usual",
            "habit",
            "memory",
            "history",
        )
    ):
        raise InstructionAlignmentError(
            "instruction rewrite dropped the memory operation cue"
        )

    template_texts = [
        value.casefold()
        for value in (
            [instruction_template]
            if isinstance(instruction_template, str)
            else instruction_template
        )
    ]

    private_properties = {
        str(atom["spec"].get("property", atom["spec"].get("fact", {}).get("property", ""))).casefold()
        for atom in memory_value_atoms + memory_write_atoms
    }
    public_boolean_properties = {
        str(atom["spec"]["property"]).casefold(): atom["spec"]["assertion"]["value"]
        for atom in seed["atoms"]
        if "memory_binding" not in atom["spec"]
        and isinstance(atom["spec"].get("assertion", {}).get("value"), bool)
        and atom["spec"].get("property")
        and str(atom["spec"]["property"]).casefold() not in private_properties
    }

    def private_value_counts(text: str, value: Any) -> dict[str, int]:
        """Return counts of private-value spellings in text."""
        if isinstance(value, bool):
            tokens = (
                ("true", "on", "enable", "enabled", "start", "activate", "activated")
                if value
                else ("false", "off", "disable", "disabled", "stop", "deactivate", "deactivated")
            )
        else:
            tokens = (str(value).casefold(),)
        if isinstance(value, bool):
            # Exempt explicit public operations only when the state word is
            # attached to their property, not every occurrence of that value.
            states = "(?:" + "|".join(tokens) + ")"
            for property_name, public_value in public_boolean_properties.items():
                if public_value is not value:
                    continue
                property_pattern = r"[_\s-]+".join(
                    re.escape(part) for part in re.split(r"[_\s-]+", property_name)
                )
                operation = (
                    rf"{states}\s+(?:the\s+)?{property_pattern}"
                    rf"|{property_pattern}\s*(?:\(\s*(?:value|enabled)\s*=\s*"
                    rf"|(?:is|to|=|:)\s*)?{states}"
                )
                text = re.sub(rf"(?<![a-z0-9_])(?:{operation})(?![a-z0-9_])", "", text)
        numeric = isinstance(value, (int, float)) and not isinstance(value, bool)
        counts = {}
        for token in tokens:
            suffix = r"(?![a-z0-9_]|\.\d)" if numeric else r"(?![a-z0-9_])"
            prefix = (
                r"(?<![a-z0-9_])(?<!\d\.)"
                if numeric
                else r"(?<![a-z0-9_])"
            )
            counts[token] = len(
                re.findall(f"{prefix}{re.escape(token)}{suffix}", text)
            )
        return counts

    private_values = [
        atom["spec"]["memory_binding"]["value"]
        for atom in memory_value_atoms
    ] + [
        atom["spec"]["fact"]["value"]
        for atom in memory_write_atoms
    ]
    leaked_values = [
        value
        for value in private_values
        if any(
            count
            > max(
                private_value_counts(template, value)[token]
                for template in template_texts
            )
            for token, count in private_value_counts(lowered, value).items()
        )
    ]
    if leaked_values:
        raise InstructionAlignmentError(
            "instruction rewrite exposed a memory-derived target value"
        )

    boolean_values = [
        atom["spec"].get("assertion", {}).get("value")
        for atom in seed["atoms"]
        if isinstance(atom["spec"].get("assertion"), dict)
        and isinstance(atom["spec"]["assertion"].get("value"), bool)
        and "memory_binding" not in atom["spec"]
    ]
    cues = {
        True: ("true", " on", "enable", "start", "activate"),
        False: ("false", " off", "disable", "stop", "deactivate"),
    }
    if any(not any(cue in lowered for cue in cues[value]) for value in boolean_values):
        raise InstructionAlignmentError("instruction rewrite dropped a boolean value")


# Complete task bundles and reference replay
# ------------------------------------------------------------------------


class DatasetValidationError(ValueError):
    """A failed dataset gate with structured repair context."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the DatasetValidationError."""
        super().__init__(message)
        self.code = code
        self.details = details or {}


def validate_dataset_case(
    world_root: str | Path,
    task_root: str | Path,
    *,
    domain_path: str | Path,
    domain: str | None = None,
    require_validation_metadata: bool = True,
    runtime_cache: DomainRuntimeCache | None = None,
    world_blueprint: WorldBlueprint | None = None,
) -> dict[str, Any]:
    """Load the separated assets and close the complete evaluation loop."""
    world = World(
        world_root,
        domain_path,
        domain=domain or (runtime_cache.domain if runtime_cache else load_json(Path(world_root) / "world_init.json")["domain"]["type"]),
        runtime_cache=runtime_cache,
        blueprint=world_blueprint,
    )
    bundle = TaskLoader(contract=world.contract).load(task_root, world)
    privacy = validate_public_assets(
        task=bundle.task,
        world_init=world.loaded_world.world_init,
        split_metadata=bundle.split_metadata,
    )
    if bundle.reference_trajectory is None:
        raise ValueError(
            "a validated dataset case requires private reference evidence"
        )
    if require_validation_metadata and bundle.validation_metadata is None:
        raise ValueError(
            "a validated dataset case requires private validation metadata"
        )
    if bundle.reference_trajectory["source"] not in {
        "ground_truth",
        "repair",
    }:
        raise ValueError(
            "reference trajectory source must be ground_truth or repair"
        )
    if (
        bundle.reference_trajectory["records"][-1]["termination"]["reason"]
        == "max_turns"
    ):
        raise ValueError("reference trajectory must not end at max_turns")
    TrajectoryExecutor(
        world,
        task_id=bundle.task_id,
    ).replay(bundle.reference_trajectory, validate_input=False)
    post_simulation = complete_background_simulation(world, bundle)
    reference_snapshot = world.get_state()
    report = evaluate_world(
        world,
        bundle,
        replay_reference_snapshot=reference_snapshot,
    )
    if not report["task_success"]:
        raise DatasetValidationError(
            "REFERENCE_TARGET_UNSATISFIED",
            "reference trajectory does not satisfy the private target",
            details={
                "failed_assertions": [
                    result
                    for result in report["assertions"]
                    if not result["passed"]
                ],
                "answer_success": report["answer_success"],
                "termination": report["termination"],
                "errors": report["errors"],
            },
        )
    if report["metrics"]["effect_replay_pass"] is not True:
        raise DatasetValidationError(
            "REFERENCE_REPLAY_NOT_EXACT",
            "reference replay snapshot is not exact",
            details={"termination": report["termination"]},
        )
    return {
        "code": "[PASS]",
        "world_id": reference_snapshot["world_id"],
        "task_id": bundle.task_id,
        "reference_present": True,
        "reference_snapshot": reference_snapshot,
        "evaluation_report": report,
        "privacy": privacy,
        "validation_metadata": bundle.validation_metadata,
        "post_simulation": post_simulation,
    }
