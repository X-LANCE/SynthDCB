from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterator

from jsonschema import Draft202012Validator

from .errors import EnvironmentContractError
from .jsonio import is_number, strict_equal
from .capabilities import collection_change_matches


def _json_path(error: Any) -> str:
    """Return the JSON path."""
    return "$" + "".join(f"[{part!r}]" for part in error.absolute_path)


def validate_property_catalog(catalog: dict[str, Any], path: str) -> None:
    """Validate the property catalog."""
    known = set(catalog["space_properties"])
    referenced = {
        name
        for names in catalog["space_types"].values()
        for name in names
    }
    if referenced != known:
        raise EnvironmentContractError(
            "CATALOG_PROPERTY_INVENTORY_MISMATCH",
            path,
            f"unreferenced={sorted(known - referenced)}, "
            f"undefined={sorted(referenced - known)}",
        )
    property_specs = {
        **catalog["space_properties"],
        **catalog["runtime_properties"],
    }
    for name, spec in property_specs.items():
        minimum = spec["minimum"]
        maximum = spec["maximum"]
        if minimum is not None and maximum is not None and minimum > maximum:
            raise EnvironmentContractError(
                "CATALOG_INVALID_RANGE",
                f"{path}:{name}",
                "minimum > maximum",
            )
    for name, spec in catalog["space_properties"].items():
        if spec["type"] not in {"integer", "number"}:
            continue
        minimum = spec["minimum"]
        maximum = spec["maximum"]
        precision = int(spec["precision"])
        values = [
            *spec["initial_values"],
            *(bound for item in spec["target_ranges"] for bound in (item["min"], item["max"])),
            spec["tolerance"],
        ]
        if spec["type"] == "integer" and any(type(value) is not int for value in values):
            raise EnvironmentContractError(
                "CATALOG_INVALID_NUMERIC_VALUE",
                f"{path}:{name}",
                "integer property requires integer configuration",
            )
        if any(round(float(value), precision) != float(value) for value in values):
            raise EnvironmentContractError(
                "CATALOG_INVALID_NUMERIC_VALUE",
                f"{path}:{name}",
                "value exceeds property precision",
            )
        bounded = [
            *spec["initial_values"],
            *(bound for item in spec["target_ranges"] for bound in (item["min"], item["max"])),
        ]
        if any(
            (minimum is not None and value < minimum)
            or (maximum is not None and value > maximum)
            for value in bounded
        ):
            raise EnvironmentContractError(
                "CATALOG_INVALID_NUMERIC_VALUE",
                f"{path}:{name}",
                "configured value is outside property bounds",
            )
        ranges = spec["target_ranges"]
        if any(item["min"] >= item["max"] for item in ranges) or any(
            left["max"] > right["min"] for left, right in zip(ranges, ranges[1:])
        ):
            raise EnvironmentContractError(
                "CATALOG_INVALID_TARGET_RANGES",
                f"{path}:{name}",
                "target ranges must be ascending, non-degenerate, and non-overlapping",
            )


class ContractValidator:
    REQUIRED_SESSION_TOOLS = {
        "session_get_capabilities",
        "session_get_devices",
        "session_get_relations",
        "session_get_spaces",
        "session_get_space_state",
        "session_get_space_devices",
        "session_get_device_tools",
        "session_sleep_time",
        "session_submit_answer",
        "session_submit_report",
        "session_finish",
    }
    REQUIRED_MEMORY_TOOLS = {
        "memory_read",
        "memory_create",
        "memory_update",
    }
    SESSION_TOOL_RULES = {
        "session_get_capabilities": (False, set(), set()),
        "session_get_devices": (False, {"space_id"}, {"space_id"}),
        "session_get_relations": (False, set(), set()),
        "session_get_spaces": (False, set(), set()),
        "session_get_space_state": (False, {"space_id"}, {"space_id"}),
        "session_get_space_devices": (False, {"space_id"}, {"space_id"}),
        "session_get_device_tools": (False, {"device_id"}, {"device_id"}),
        "session_sleep_time": (True, set(), {"minutes"}),
        "session_submit_answer": (False, {"value"}, {"value"}),
        "session_submit_report": (
            False,
            {"status", "reason_code", "description"},
            {"status", "reason_code", "description", "affected_properties"},
        ),
        "session_finish": (False, set(), set()),
    }
    MEMORY_TOOL_RULES = {
        "memory_read": (False, set(), set()),
        "memory_create": (
            True,
            {"content"},
            {"content", "user_id"},
        ),
        "memory_update": (
            True,
            {"memory_id", "content"},
            {"memory_id", "content"},
        ),
    }

    def __init__(self, package: Any) -> None:
        """Initialize the ContractValidator."""
        self.package = package
        self.catalogs: dict[str, dict[str, Any]] = {}
        self.format_checker = package.format_checker

    def bind_domain_catalogs(
        self,
        catalogs: dict[str, dict[str, Any]],
    ) -> None:
        """Bind the domain catalogs."""
        self.catalogs = dict(catalogs)

    def validate_schema(
        self,
        instance: Any,
        schema_id: str,
        *,
        code: str = "SCHEMA_VALIDATION_ERROR",
    ) -> None:
        """Validate the schema."""
        self.package.validate_schema(instance, schema_id, code=code)

    def validate_world_init(self, request: dict[str, Any]) -> None:
        """Validate the world init."""
        self.validate_schema(request, "urn:dcb:v2:schema:world-init")

    def validate_resolved_world(self, world: dict[str, Any]) -> None:
        """Validate the resolved world."""
        self.validate_schema(world, "urn:dcb:v2:schema:resolved-world")
        self.validate_schema(
            world,
            "urn:dcb:v2:schema:domain",
            code="DOMAIN_SCHEMA_VALIDATION_ERROR",
        )
        domain_type = world["domain"]["type"]
        try:
            catalog = self.catalogs[domain_type]
        except KeyError as exc:
            raise EnvironmentContractError(
                "UNKNOWN_DOMAIN",
                "$.domain.type",
                domain_type,
            ) from exc

        spaces = set(world["spaces"])
        objects = set(world["objects"])
        collisions = spaces & objects
        reserved = {"session", "memory"} & (spaces | objects)
        if collisions or reserved:
            detail = sorted(collisions or reserved)
            raise EnvironmentContractError("TARGET_ID_COLLISION", "$", str(detail))
        for device_id, spec in world["objects"].items():
            space_id = spec.get("space_id")
            if space_id is not None and space_id not in spaces:
                raise EnvironmentContractError(
                    "UNKNOWN_SPACE_REFERENCE",
                    f"$.objects.{device_id}.space_id",
                    space_id,
                )
        for index, connection in enumerate(world["domain"]["metadata"]["connections"]):
            for field in ("space_1", "space_2"):
                if connection[field] not in spaces:
                    raise EnvironmentContractError(
                        "UNKNOWN_SPACE_REFERENCE",
                        f"$.domain.metadata.connections[{index}].{field}",
                        connection[field],
                    )
            if "device_id" in connection:
                device_id = connection["device_id"]
                if device_id not in objects or world["objects"][device_id].get("space_id") not in (connection["space_1"], connection["space_2"]):
                    raise EnvironmentContractError("INVALID_CONNECTION_DEVICE", "$.domain.metadata.connections", device_id)

        from graphlib import TopologicalSorter, CycleError
        graphs = {"contains": {}, "depends_on": {}}
        parents = set()
        for relation in world["domain"]["metadata"].get("relations", []):
            source, target = relation["source_id"], relation["target_id"]
            if source not in objects or target not in objects or source == target:
                raise EnvironmentContractError("INVALID_RELATION", "$.domain.metadata.relations", str(relation))
            if relation["type"] == "contains":
                if target in parents:
                    raise EnvironmentContractError("MULTIPLE_PARENTS", "$.domain.metadata.relations", target)
                parents.add(target)
            graphs[relation["type"]].setdefault(target, set()).add(source)
        try:
            for graph in graphs.values():
                tuple(TopologicalSorter(graph).static_order())
        except CycleError as error:
            raise EnvironmentContractError("CYCLIC_RELATION", "$.domain.metadata.relations", str(error)) from error

        for space_id, space in world["spaces"].items():
            try:
                expected = set(catalog["space_types"][space["type"]])
            except KeyError as exc:
                raise EnvironmentContractError(
                    "UNKNOWN_SPACE_TYPE", f"$.spaces.{space_id}.type", space["type"]
                ) from exc
            actual = set(space["properties"])
            if actual != expected:
                raise EnvironmentContractError(
                    "DOMAIN_PROPERTY_INVENTORY_MISMATCH",
                    f"$.spaces.{space_id}.properties",
                    f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}",
                )

        time_policy = world["runtime"]["time_policy"]
        max_elapsed = time_policy.get("max_elapsed_minutes")
        elapsed = world["runtime"]["time_state"]["elapsed_minutes"]
        if max_elapsed is not None and elapsed >= max_elapsed:
            raise EnvironmentContractError(
                "ELAPSED_LIMIT_ALREADY_REACHED",
                "$.runtime.time_state.elapsed_minutes",
                "initial elapsed_minutes must be below max_elapsed_minutes",
            )

    def validate_snapshot(
        self, snapshot: dict[str, Any], world: dict[str, Any], *, label: str
    ) -> None:
        """Validate the snapshot."""
        self.validate_schema(snapshot, "urn:dcb:v2:schema:state-snapshot")
        if snapshot["world_id"] != world["world_id"]:
            raise EnvironmentContractError("WORLD_ID_MISMATCH", f"{label}.world_id", "IDs differ")
        if snapshot["domain"]["type"] != world["domain"]["type"]:
            raise EnvironmentContractError("DOMAIN_MISMATCH", f"{label}.domain.type", "types differ")
        if set(snapshot["spaces"]) != set(world["spaces"]):
            raise EnvironmentContractError("SNAPSHOT_SPACE_SET_MISMATCH", f"{label}.spaces", "IDs differ")
        if set(snapshot["objects"]) != set(world["objects"]):
            raise EnvironmentContractError("SNAPSHOT_OBJECT_SET_MISMATCH", f"{label}.objects", "IDs differ")

    @staticmethod
    def assertions(target: dict[str, Any]) -> Iterator[tuple[str, str, str, dict[str, Any]]]:
        """Yield assertions."""
        for scope in ("objects", "spaces"):
            for target_id, target_spec in target[scope].items():
                for prop, assertion in target_spec["properties"].items():
                    yield scope[:-1], target_id, prop, assertion
        for runtime_scope in ("time_state", "weather_state"):
            for prop, assertion in target["runtime"].get(
                runtime_scope,
                {},
            ).items():
                yield "runtime", runtime_scope, prop, assertion

    def validate_target(
        self,
        target: dict[str, Any],
        world: dict[str, Any],
        initial: dict[str, Any],
    ) -> None:
        """Validate the target."""
        self.validate_schema(target, "urn:dcb:v2:schema:target")
        workflow = target.get("workflow")
        if "evaluation_end_minute" in target:
            if workflow is not None or target["evaluation_end_minute"] <= initial["runtime"]["time_state"]["elapsed_minutes"]:
                raise EnvironmentContractError("INVALID_EVALUATION_HORIZON", "$.evaluation_end_minute", "use one fixed horizon after task start")
        if workflow is not None:
            transitions = workflow["transitions"]
            if not transitions and not target["expected_reports"]:
                raise EnvironmentContractError("EMPTY_WORKFLOW", "$.workflow.transitions", "Workflow requires a transition or an explicit infeasibility report")
            ids = {event["id"] for event in transitions}
            if len(ids) != len(transitions):
                raise EnvironmentContractError("INVALID_WORKFLOW", "$.workflow.transitions", "transition IDs must be unique")
            for event in transitions:
                properties = initial[f"{event['scope']}s"].get(event["target_id"], {}).get("properties", {})
                if event["property"] not in properties:
                    raise EnvironmentContractError("INVALID_WORKFLOW", "$.workflow.transitions", "unknown transition property")
                if "predicate" in event:
                    predicate = event["predicate"]
                    value = properties[event["property"]]
                    if not is_number(value) or (predicate["op"] == "range" and predicate["min"] > predicate["max"]):
                        raise EnvironmentContractError("INVALID_WORKFLOW", "$.workflow.transitions", "environment predicate requires a numeric property and valid range")
                    satisfied = self.evaluate_assertion(predicate, value, value)
                else:
                    satisfied = strict_equal(event["from"], event["to"]) or strict_equal(properties[event["property"]], event["to"])
                if satisfied:
                    raise EnvironmentContractError("INVALID_WORKFLOW", "$.workflow.transitions", "transition must be nontrivial and not initially satisfied")
            for relation in workflow["relations"]:
                kind = relation["kind"]
                references = ([relation["before"], relation["after"]] if kind == "ordered" else relation["events"] if kind == "synchronize" else [relation["event"]])
                if not set(references).issubset(ids) or (kind == "ordered" and (relation["before"] == relation["after"] or relation["min_minutes"] > relation["max_minutes"])):
                    raise EnvironmentContractError("INVALID_WORKFLOW", "$.workflow.relations", "unknown transition or invalid ordering window")
        assertions = list(self.assertions(target))
        if (
            not assertions
            and not target["expected_answers"]
            and not target["expected_reports"]
            and not target.get("expected_memory_mutations", [])
            and workflow is None
        ):
            raise EnvironmentContractError(
                "EMPTY_TARGET",
                "$",
                "state assertions, answers, reports, and memory mutations are all empty",
            )
        catalog = self.catalogs[world["domain"]["type"]]
        for index, mutation in enumerate(
            target.get("expected_memory_mutations", [])
        ):
            source = mutation["source"]
            scope = source["scope"]
            target_id = source["target_id"]
            prop = source["property"]
            if scope not in {"object", "space"}:
                raise EnvironmentContractError(
                    "INVALID_MEMORY_SOURCE",
                    f"$.expected_memory_mutations[{index}].source",
                    scope,
                )
            collection = initial[f"{scope}s"]
            if target_id not in collection:
                raise EnvironmentContractError(
                    "UNKNOWN_TARGET",
                    f"$.expected_memory_mutations[{index}].source.target_id",
                    target_id,
                )
            if prop not in collection[target_id]["properties"]:
                raise EnvironmentContractError(
                    "UNKNOWN_TARGET_PROPERTY",
                    f"$.expected_memory_mutations[{index}].source.property",
                    prop,
                )
        for scope, target_id, prop, assertion in assertions:
            path = f"$.{scope}.{target_id}.{prop}"
            if scope == "object":
                if target_id not in initial["objects"]:
                    raise EnvironmentContractError("UNKNOWN_TARGET", path, target_id)
                properties = initial["objects"][target_id]["properties"]
                allowed = None
            elif scope == "space":
                if target_id not in initial["spaces"]:
                    raise EnvironmentContractError("UNKNOWN_TARGET", path, target_id)
                properties = initial["spaces"][target_id]["properties"]
                allowed = catalog["space_properties"].get(prop, {}).get("allowed_operators")
            else:
                properties = initial["runtime"].get(target_id, {})
                allowed = catalog["runtime_properties"].get(prop, {}).get("allowed_operators")
            if prop not in properties:
                raise EnvironmentContractError("UNKNOWN_TARGET_PROPERTY", path, prop)
            initial_value = properties[prop]
            op = assertion["op"]
            if allowed is None:
                allowed = (
                    ["eq", "one_of", "range", "gte", "lte", "delta_at_least", "closer_to", "unchanged"]
                    if is_number(initial_value)
                    else ["eq", "one_of", "unchanged"]
                )
                if isinstance(initial_value, dict):
                    allowed.append("collection_change")
            if op not in allowed:
                raise EnvironmentContractError("OPERATOR_NOT_ALLOWED", path, op)
            if op == "range" and assertion["min"] > assertion["max"]:
                raise EnvironmentContractError("INVALID_RANGE", path, "min must be <= max")
            if op == "collection_change":
                updates, removes = set(assertion["update"]), set(assertion["remove"])
                if not (updates | removes).issubset(initial_value) or updates & removes:
                    raise EnvironmentContractError("INVALID_COLLECTION_CHANGE", path, "updated/deleted IDs must exist and cannot overlap")

    def validate_task(self, task: dict[str, Any]) -> None:
        """Validate the task."""
        self.validate_schema(task, "urn:dcb:v2:schema:task")

    def validate_trajectory(self, trajectory: dict[str, Any]) -> None:
        """Validate schema plus the final and unique termination semantics."""
        self.validate_schema(
            trajectory,
            "urn:dcb:v2:schema:trajectory",
        )
        records = trajectory["records"]
        if records[-1]["kind"] != "termination":
            raise EnvironmentContractError(
                "TRAJECTORY_TERMINATION_NOT_FINAL",
                "$.records",
                "the unique termination record must be last",
            )
        termination = records[-1]["termination"]
        terminal_turn = termination["turn_id"]
        prior_turn_ids: list[str] = []
        seen_turns: list[str] = []
        closed_turns: set[str] = set()
        call_ids: set[str] = set()
        expected_sequence = 1
        for index, record in enumerate(records[:-1]):
            if record["kind"] == "tool_exchange":
                call = record["call"]
                result = record["result"]
                turn_id = call["turn_id"]
                if (
                    result["call_id"] != call["call_id"]
                    or result["turn_id"] != turn_id
                ):
                    raise EnvironmentContractError(
                        "TRAJECTORY_CALL_RESULT_LINK_MISMATCH",
                        f"$.records[{index}]",
                        "ToolCall and ToolResult identifiers differ",
                    )
                if call["call_id"] in call_ids:
                    raise EnvironmentContractError(
                        "TRAJECTORY_DUPLICATE_CALL_ID",
                        f"$.records[{index}].call.call_id",
                        call["call_id"],
                    )
                call_ids.add(call["call_id"])
                if result["sequence"] != expected_sequence:
                    raise EnvironmentContractError(
                        "TRAJECTORY_TOOL_SEQUENCE_MISMATCH",
                        f"$.records[{index}].result.sequence",
                        f"expected {expected_sequence}",
                    )
                expected_sequence += 1
            else:
                turn_id = record["boundary"]["turn_id"]
                if turn_id in closed_turns:
                    raise EnvironmentContractError(
                        "TRAJECTORY_DUPLICATE_TURN_BOUNDARY",
                        f"$.records[{index}].boundary.turn_id",
                        turn_id,
                    )
                closed_turns.add(turn_id)
            if turn_id in closed_turns and record["kind"] == "tool_exchange":
                raise EnvironmentContractError(
                    "TRAJECTORY_RECORD_AFTER_TURN_BOUNDARY",
                    f"$.records[{index}]",
                    turn_id,
                )
            if prior_turn_ids and turn_id != prior_turn_ids[-1]:
                if prior_turn_ids[-1] not in closed_turns:
                    raise EnvironmentContractError(
                        "TRAJECTORY_TURN_BOUNDARY_MISSING",
                        f"$.records[{index}]",
                        prior_turn_ids[-1],
                    )
                if turn_id in seen_turns:
                    raise EnvironmentContractError(
                        "TRAJECTORY_NONCONTIGUOUS_TURN",
                        f"$.records[{index}]",
                        turn_id,
                    )
                seen_turns.append(turn_id)
            elif not prior_turn_ids:
                seen_turns.append(turn_id)
            prior_turn_ids.append(turn_id)
        if prior_turn_ids and terminal_turn != prior_turn_ids[-1]:
            raise EnvironmentContractError(
                "TRAJECTORY_TERMINATION_TURN_MISMATCH",
                "$.records[-1].termination.turn_id",
                f"expected {prior_turn_ids[-1]!r}, got {terminal_turn!r}",
            )
        if termination["turn_index"] != max(len(seen_turns), 1):
            raise EnvironmentContractError(
                "TRAJECTORY_TERMINATION_INDEX_MISMATCH",
                "$.records[-1].termination.turn_index",
                f"expected {max(len(seen_turns), 1)}",
            )
        successful_finish = any(
            record["kind"] == "tool_exchange"
            and record["call"]["command"]
            == {
                "target": "session",
                "function": "finish",
                "parameters": {},
            }
            and record["result"]["status"] == "success"
            for record in records[:-1]
        )
        if (termination["reason"] == "session_finish") is not successful_finish:
            raise EnvironmentContractError(
                "TRAJECTORY_FINISH_TERMINATION_MISMATCH",
                "$.records[-1].termination.reason",
                "successful session_finish and termination reason differ",
            )
        if (
            termination["reason"] == "max_turns"
            and terminal_turn not in closed_turns
        ):
            raise EnvironmentContractError(
                "TRAJECTORY_MAX_TURNS_BOUNDARY_MISSING",
                "$.records[-1].termination.turn_id",
                terminal_turn,
            )
        if termination["reason"] == "max_turns" and (
            termination["limits"]["max_turns"]
            != termination["turn_index"]
        ):
            raise EnvironmentContractError(
                "TRAJECTORY_MAX_TURNS_LIMIT_MISMATCH",
                "$.records[-1].termination.limits.max_turns",
                "max-turn termination must occur on the configured final turn",
            )
        if termination["reason"] == "elapsed_time_limit":
            max_elapsed = termination["limits"]["max_elapsed_minutes"]
            if (
                max_elapsed is None
                or termination["elapsed_minutes"] != max_elapsed
            ):
                raise EnvironmentContractError(
                    "TRAJECTORY_ELAPSED_LIMIT_MISMATCH",
                    "$.records[-1].termination.elapsed_minutes",
                    "elapsed termination must equal its non-null limit",
                )

    def validate_tool_catalog(
        self, catalog: dict[str, Any], world: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
        """Validate the tool catalog."""
        self.validate_schema(catalog, "urn:dcb:v2:schema:tool-catalog")
        if catalog["world_id"] != world["world_id"]:
            raise EnvironmentContractError("WORLD_ID_MISMATCH", "$.world_id", catalog["world_id"])
        target_kinds = {
            "session": "session",
            "memory": "memory",
            **{space_id: "space" for space_id in world["spaces"]},
            **{device_id: "device" for device_id in world["objects"]},
        }
        index: dict[str, dict[str, Any]] = {}
        for position, tool in enumerate(catalog["tools"]):
            tool_id = tool["tool_id"]
            if tool_id in index:
                raise EnvironmentContractError("DUPLICATE_TOOL_ID", f"$.tools[{position}]", tool_id)
            if tool_id != f"{tool['target']}_{tool['function']}":
                raise EnvironmentContractError("TOOL_ID_MISMATCH", f"$.tools[{position}]", tool_id)
            if target_kinds.get(tool["target"]) != tool["target_kind"]:
                raise EnvironmentContractError("TARGET_KIND_MISMATCH", f"$.tools[{position}]", tool_id)
            Draft202012Validator.check_schema(tool["parameters_schema"])
            index[tool_id] = tool
        required_session = self.REQUIRED_SESSION_TOOLS.copy()
        if not world["spaces"]:
            required_session -= {"session_get_spaces", "session_get_space_state", "session_get_space_devices"}
        missing = (required_session | self.REQUIRED_MEMORY_TOOLS) - set(index)
        if missing:
            raise EnvironmentContractError("SESSION_TOOL_MISSING", "$.tools", str(sorted(missing)))
        for tool_id, (mutation, required, properties) in self.SESSION_TOOL_RULES.items():
            if tool_id not in required_session:
                continue
            tool = index[tool_id]
            schema = tool["parameters_schema"]
            if tool["mutation"] is not mutation:
                raise EnvironmentContractError("SESSION_TOOL_MUTATION_MISMATCH", tool_id, str(mutation))
            if set(schema["required"]) != required or set(schema["properties"]) != properties:
                raise EnvironmentContractError("SESSION_TOOL_SIGNATURE_MISMATCH", tool_id, str(schema))
        for tool_id, (mutation, required, properties) in self.MEMORY_TOOL_RULES.items():
            tool = index[tool_id]
            schema = tool["parameters_schema"]
            if tool["mutation"] is not mutation:
                raise EnvironmentContractError(
                    "MEMORY_TOOL_MUTATION_MISMATCH", tool_id, str(mutation)
                )
            if set(schema["required"]) != required or set(schema["properties"]) != properties:
                raise EnvironmentContractError(
                    "MEMORY_TOOL_SIGNATURE_MISMATCH", tool_id, str(schema)
                )
        return index

    def validate_memory(self, memory: dict[str, Any]) -> None:
        """Validate the memory."""
        self.validate_schema(memory, "urn:dcb:v2:schema:memory")
        identifiers = [item["memory_id"] for item in memory["records"]]
        if len(identifiers) != len(set(identifiers)):
            raise EnvironmentContractError(
                "DUPLICATE_MEMORY_ID", "$.records", str(identifiers)
            )

    def validate_command(
        self,
        command: dict[str, Any],
        tool_index: dict[str, dict[str, Any]],
    ) -> None:
        """Validate the command."""
        self.validate_schema(command, "urn:dcb:v2:schema:command")
        tool_id = f"{command['target']}_{command['function']}"
        if tool_id not in tool_index:
            code = "UNKNOWN_TARGET" if not any(
                item["target"] == command["target"] for item in tool_index.values()
            ) else "UNKNOWN_FUNCTION"
            raise EnvironmentContractError(code, "$.target", tool_id)
        errors = sorted(
            Draft202012Validator(
                tool_index[tool_id]["parameters_schema"],
                format_checker=self.format_checker,
            ).iter_errors(command["parameters"]),
            key=lambda error: (list(error.absolute_path), error.message),
        )
        if errors:
            raise EnvironmentContractError("INVALID_PARAMETERS", _json_path(errors[0]), errors[0].message)

    def validate_effect(self, effect: dict[str, Any], world: dict[str, Any]) -> None:
        """Validate the effect."""
        self.validate_schema(effect, "urn:dcb:v2:schema:effect")
        if effect["target"] not in world["spaces"]:
            raise EnvironmentContractError("UNKNOWN_EFFECT_TARGET", "$.target", effect["target"])
        if effect["source"] not in world["objects"]:
            raise EnvironmentContractError("UNKNOWN_EFFECT_SOURCE", "$.source", effect["source"])
        prop = effect["parameters"]["property"]
        if prop not in world["spaces"][effect["target"]]["properties"]:
            raise EnvironmentContractError("UNKNOWN_EFFECT_PROPERTY", "$.parameters.property", prop)
        spec = self.catalogs[world["domain"]["type"]]["space_properties"][prop]
        if effect["function"] not in spec["allowed_effect_functions"]:
            raise EnvironmentContractError("EFFECT_FUNCTION_NOT_ALLOWED", "$.function", effect["function"])
        if effect["parameters"]["unit"] != spec["unit"]:
            raise EnvironmentContractError(
                "EFFECT_UNIT_MISMATCH", "$.parameters.unit", f"expected {spec['unit']!r}"
            )

    def validate_effect_batch(self, effects: list[dict[str, Any]], world: dict[str, Any]) -> None:
        """Validate the effect batch."""
        groups: dict[tuple[str, str], list[str]] = {}
        for effect in effects:
            self.validate_effect(effect, world)
            key = (effect["target"], effect["parameters"]["property"])
            groups.setdefault(key, []).append(effect["function"])
        for key, functions in groups.items():
            if "approach" in functions and "delta" in functions:
                raise EnvironmentContractError("EFFECT_CONFLICT", str(key), str(functions))

    def validate_audit_record(self, record: dict[str, Any]) -> None:
        """Validate the audit record."""
        self.validate_schema(record, "urn:dcb:v2:schema:audit-record")

    @staticmethod
    def state_value(snapshot: dict[str, Any], scope: str, target_id: str, prop: str) -> Any:
        """Return the state value."""
        if scope == "runtime":
            return snapshot["runtime"][target_id][prop]
        return snapshot[f"{scope}s"][target_id]["properties"][prop]

    @staticmethod
    def evaluate_assertion(assertion: dict[str, Any], initial: Any, final: Any) -> bool:
        """Return whether the assertion holds between the initial and final states."""
        op = assertion["op"]
        if op == "eq":
            return strict_equal(final, assertion["value"])
        if op == "one_of":
            return any(strict_equal(final, value) for value in assertion["values"])
        if op == "unchanged":
            return strict_equal(final, initial)
        if op == "collection_change":
            return collection_change_matches(assertion, initial, final)
        initial_number = float(initial)
        final_number = float(final)
        if op == "range":
            return float(assertion["min"]) <= final_number <= float(assertion["max"])
        if op == "gte":
            return final_number >= float(assertion["value"])
        if op == "lte":
            return final_number <= float(assertion["value"])
        if op == "delta_at_least":
            delta = final_number - initial_number
            if assertion["direction"] == "decrease":
                delta = -delta
            return delta >= float(assertion["value"])
        target = float(assertion["value"])
        improvement = abs(initial_number - target) - abs(final_number - target)
        return abs(final_number - target) < abs(initial_number - target) and improvement >= float(
            assertion.get("min_improvement", 0)
        )

    def validate_target_satisfaction(
        self,
        target: dict[str, Any],
        initial: dict[str, Any],
        final: dict[str, Any],
    ) -> None:
        """Validate the target satisfaction."""
        for scope, target_id, prop, assertion in self.assertions(target):
            if not self.evaluate_assertion(
                assertion,
                self.state_value(initial, scope, target_id, prop),
                self.state_value(final, scope, target_id, prop),
            ):
                raise EnvironmentContractError(
                    "POSITIVE_FIXTURE_ASSERTION_FAILED",
                    f"{scope}.{target_id}.{prop}",
                    str(assertion),
                )

    def copy(self, value: Any) -> Any:
        """Return a copy of the value."""
        return deepcopy(value)
