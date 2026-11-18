"""Organize instruction variants and review task reasonableness."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import re
import random
from typing import Any, Callable

from src.utils import json_payload
from src.utils.llm import call_llm_api, extract_json_from_answer

from . import prompt
from .target_references import reference_candidates


Completion = Callable[[str, str], tuple[str, dict[str, Any]]]


INSTRUCTION_STYLES = tuple(prompt.INSTRUCTION_STYLE_EXAMPLES)


def expand_device_references(artifacts, inventory, *, current_user=None, rng=None, config=None):
    """Sample a target phrase per template, preserving the target identity."""
    templates = [artifacts.instruction_template] if isinstance(artifacts.instruction_template, str) else artifacts.instruction_template
    candidates = reference_candidates(inventory, current_user, config)
    aliases = {inventory.device_names[target_id]: items for target_id, items in candidates.items()
               if any(inventory.device_names[target_id] in text for text in templates)}
    if not aliases:
        return artifacts
    rng = rng or random.Random(artifacts.reference_plan['task_id'])
    pattern = re.compile(r"(?<![\w])(?:" + "|".join(re.escape(name) for name in sorted(aliases, key=len, reverse=True)) + r")(?![\w])")
    variants, selections = [], []
    for text in templates:
        chosen = {}
        for name in dict.fromkeys(pattern.findall(text)):
            options = [item for item in aliases[name] if item['weight'] > 0]
            if not options:
                raise ValueError(f'no positive-weight unambiguous target reference for {name}')
            groups = {}
            for item in options:
                groups.setdefault(item['template'], []).append(item)
            group = rng.choices(list(groups.values()), weights=[items[0]['weight'] for items in groups.values()], k=1)[0]
            chosen[name] = rng.choice(group)
        variants.append(pattern.sub(lambda match: chosen[match[0]]['text'], text))
        selections.append(chosen)
    seed = deepcopy(artifacts.seed)
    seed["derived"]["target_reference_templates"] = list(templates)
    seed["derived"]["target_reference_rewrites"] = dict(zip(templates, variants))
    seed["derived"]["public_entity_aliases"] = {name: list(dict.fromkeys(item['text'] for item in items)) for name, items in aliases.items()}
    seed["derived"]["target_reference_sampling"] = selections
    for variant in seed["derived"].get("control_variants", []):
        variant["instruction"] = seed["derived"]["target_reference_rewrites"].get(variant["instruction"], variant["instruction"])
    return replace(artifacts, seed=seed, instruction_template=list(dict.fromkeys(variants)))


def build_instruction_variants(
    instruction_template: str | list[str],
    *,
    llm_instruction: str | None = None,
    llm_style: str | None = None,
) -> list[list[str]]:
    """Return JSON-safe [source, style, instruction] variants."""
    templates = (
        [instruction_template]
        if isinstance(instruction_template, str)
        else instruction_template
    )
    if not templates or any(
        not isinstance(instruction, str) or not instruction.strip()
        for instruction in templates
    ):
        raise ValueError("instruction templates must be non-empty strings")
    variants = [
        ["template", "direct", instruction]
        for instruction in dict.fromkeys(templates)
    ]
    if llm_instruction is None:
        return variants
    if llm_style not in INSTRUCTION_STYLES:
        raise ValueError(f"unknown LLM instruction style {llm_style!r}")
    if not isinstance(llm_instruction, str) or not llm_instruction.strip():
        raise ValueError("LLM instruction must be a non-empty string")
    variants.append(["llm", llm_style, llm_instruction])
    return variants


def review_task_reasonableness(
    *,
    task_id: str,
    task_family: str,
    task_subtype: str,
    instruction_template: str | list[str],
    seed_summary: dict[str, Any],
    world_summary: dict[str, Any],
    model_scenario: str = "generate",
    model: str | None = None,
    completion: Completion | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Ask the quality agent whether the generated intent is reasonable."""
    system = prompt.TASK_REASONABLENESS_SYSTEM_PROMPT
    user = prompt.TASK_REASONABLENESS_USER_PROMPT.format(
        task_id=task_id,
        task_family=task_family,
        task_subtype=task_subtype,
        world_summary=json_payload(world_summary),
        instruction_template=(
            instruction_template
            if isinstance(instruction_template, str)
            else json_payload(instruction_template)
        ),
        seed_summary=json_payload(seed_summary),
    )
    caller = completion or (
        lambda system_prompt, user_prompt: call_llm_api(
            system_prompt,
            user_prompt,
            model_scenario=model_scenario,
            model=model,
        )
    )
    code, response = caller(system, user)
    if code != "[PASS]":
        raise RuntimeError(f"task reasonableness review failed: {code}")
    code, payload = extract_json_from_answer(response["answer"])
    if code != "[PASS]" or not isinstance(payload, dict):
        raise ValueError("reasonableness review is not a JSON object")
    if set(payload) != {"judge", "explanation"}:
        raise ValueError(
            "reasonableness review must contain only judge and explanation"
        )
    if not isinstance(payload["judge"], bool):
        raise ValueError("reasonableness review judge must be boolean")
    if not isinstance(payload["explanation"], str):
        raise ValueError("reasonableness review explanation must be a string")
    if not payload["judge"] and not payload["explanation"].strip():
        raise ValueError("rejected reasonableness review requires an explanation")
    return deepcopy(payload), response
