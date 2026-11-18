"""Proven environmental invariants for absent or statically bounded sources.

Unsupported hook expressions leave the World uncertified; simulation/search failure
is never evidence of an unreachable target.
"""
from collections import defaultdict
import ast
import inspect
import math
import textwrap

from src.object_model import BaseProperty, FloatProperty, IntProperty


class UnprovenEffect(ValueError):
    """The hook falls outside the supported static proof rules."""


def _hook_effects(hook, instance, property_name):
    tree = ast.parse(textwrap.dedent(inspect.getsource(hook)))
    if (sum(isinstance(node, ast.FunctionDef) for node in ast.walk(tree)) != 1
            or any(isinstance(node, ast.stmt) and not isinstance(node, (ast.FunctionDef, ast.Assign, ast.If, ast.Return, ast.Expr, ast.Pass))
                   for node in ast.walk(tree))
            or any(isinstance(node, (ast.NamedExpr, ast.Lambda)) for node in ast.walk(tree))):
        raise UnprovenEffect("hook has unsupported control flow or assignments")
    bindings = defaultdict(list)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bindings[target.id].append(node.value)
                elif isinstance(target, ast.Tuple):
                    if any(not isinstance(name, ast.Name) for name in target.elts):
                        raise UnprovenEffect("tuple assignment mutates a nonlocal expression")
                    if isinstance(node.value, ast.Tuple):
                        for name, value in zip(target.elts, node.value.elts, strict=True):
                            if isinstance(name, ast.Name):
                                bindings[name.id].append(value)
                    elif (isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute)
                          and node.value.func.attr == "get" and len(target.elts) == 2
                          and isinstance(target.elts[1], ast.Name)):
                        bindings[target.elts[1].id].append(ast.Attribute(value=node.value.func.value, attr="value"))
                    else:
                        raise UnprovenEffect("unsupported tuple assignment")
                else:
                    raise UnprovenEffect("hook mutates an expression used by its effect")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            pure = (isinstance(node.func, ast.Name) and node.func.id not in bindings
                    and node.func.id in {"round", "min", "max", "abs", "float", "int", "bool", "str", "type", "len", "isinstance"})
            property_access = isinstance(node.func, ast.Attribute) and node.func.attr == "get"
            if isinstance(node.func, ast.Attribute) and node.func.attr in {"set", "internal_set"}:
                owner = node.func.value
                property_access = (isinstance(owner, ast.Attribute) and isinstance(owner.value, ast.Name)
                                   and owner.value.id == "self" and isinstance(getattr(instance, owner.attr), BaseProperty))
            if not pure and not property_access:
                raise UnprovenEffect("hook delegates or mutates its effect containers")

    def expressions(node, seen=()):
        if not isinstance(node, ast.Name):
            return [node]
        if node.id in seen or node.id not in bindings:
            raise UnprovenEffect(f"unbounded local expression: {node.id}")
        return [item for value in bindings[node.id] for item in expressions(value, (*seen, node.id))]

    def fields(node):
        if not isinstance(node, ast.Dict) or any(not isinstance(key, ast.Constant) for key in node.keys):
            raise UnprovenEffect("effect is not a literal dictionary")
        return {key.value: value for key, value in zip(node.keys, node.values, strict=True)}

    def constants(node):
        values = expressions(node)
        if any(not isinstance(value, ast.Constant) for value in values):
            raise UnprovenEffect("effect property/function is not statically known")
        return {value.value for value in values}

    def bounds(node):
        values = []
        for value in expressions(node):
            if isinstance(value, ast.Constant) and type(value.value) in (int, float):
                values.append((value.value, value.value))
            elif (isinstance(value, ast.Attribute) and value.attr == "value"
                  and isinstance(value.value, ast.Attribute) and isinstance(value.value.value, ast.Name)
                  and value.value.value.id == "self"):
                prop = getattr(instance, value.value.attr)
                if not isinstance(prop, (FloatProperty, IntProperty)) or prop.minimum is None or prop.maximum is None:
                    raise UnprovenEffect("destination property lacks finite bounds")
                values.append((prop.minimum, prop.maximum))
            else:
                raise UnprovenEffect("destination is not a literal or bounded property")
        return min(item[0] for item in values), max(item[1] for item in values)

    effects = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Return):
            continue
        if not isinstance(node.value, ast.Tuple) or len(node.value.elts) != 2:
            raise UnprovenEffect("hook delegates its emitted effects")
        for emitted in expressions(node.value.elts[1]):
            if not isinstance(emitted, ast.List):
                raise UnprovenEffect("hook does not return a literal effect list")
            counts = defaultdict(int)
            for item in emitted.elts:
                for effect in expressions(item):
                    data = fields(effect)
                    parameters = fields(data["parameters"])
                    properties = constants(parameters["property"])
                    if property_name not in properties:
                        continue
                    counts[property_name] += 1
                    if constants(data["function"]) != {"approach"}:
                        raise UnprovenEffect(f"{property_name} has a non-approach effect")
                    for target in expressions(data["target"]):
                        if not (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)
                                and target.value.id == "context" and isinstance(target.slice, ast.Constant)
                                and target.slice.value == "space_id"):
                            raise UnprovenEffect(f"{property_name} effect can target another space")
                    effects.append(bounds(parameters["value"]))
            if counts[property_name] > 1:
                raise UnprovenEffect(f"one hook may emit multiple {property_name} approaches")
    return effects


def environmental_invariants(world, property_name):
    """Return proven intervals containing every reachable value of a space property."""
    if world._state.dynamics:
        return []
    writers = defaultdict(dict)
    try:
        for target_id, device in world._state.devices.items():
            effects = []
            for name in ("_on_tick", "_on_after_action"):
                hook = getattr(device.instance, name, None)
                if hook is not None:
                    effects.extend(_hook_effects(hook, device.instance, property_name))
            if effects:
                writers[device.space_id][target_id] = effects
    except UnprovenEffect:
        return []
    initial = world.get_initial_state()
    schema = world.loaded_world.domain.property_catalog["space_properties"].get(property_name)
    if schema is None:
        return []
    quantum = 10 ** -schema["precision"]
    result = []
    for space_id, space in initial["spaces"].items():
        if property_name not in space["properties"]:
            continue
        devices = writers.get(space_id, {})
        # Summed simultaneous approaches can overshoot even if each alone cannot.
        if len(devices) > 1:
            continue
        current = space["properties"][property_name]
        effects = next(iter(devices.values())) if devices else []
        lower = math.floor(min([current, *(item[0] for item in effects)]) / quantum) * quantum if effects else current
        upper = math.ceil(max([current, *(item[1] for item in effects)]) / quantum) * quantum if effects else current
        result.append({"space_id": space_id, "property": property_name, "initial_value": current,
                       "min": lower, "max": upper, "source_ids": sorted(devices),
                       "proof": "single_source_bounded_approach" if devices else f"no_{property_name}_source",
                       "schema": schema})
    return result


def temperature_invariants(world):
    """Return the temperature proofs used to construct UNREACHABLE_GOAL tasks."""
    return environmental_invariants(world, "temperature")
