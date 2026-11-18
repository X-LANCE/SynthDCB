# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, IntProperty, StringProperty


class RiceCooker:
    """
    RiceCooker
    Description: Rice cooker. Users can query and set the cooking program, rice type or texture, and keep-warm state, and can query the cooking stage and inner-pot state. A cooking program heats in stages; after cooking is complete, the device can enter keep-warm mode without continuing to cook.
    Version: 1.0.0
    Base: -
    """

    PROCESS = {
        "mode_property": "cooking_program",
        "start_function": "start_cooking",
        "pause_function": "pause_cooking",
        "resume_function": "resume_cooking",
        "modes": {
            "white_rice": [
                {"phase": "heating", "minutes": 20},
                {"phase": "cooking", "minutes": 25},
                {"phase": "resting", "minutes": 10},
            ],
            "brown_rice": [
                {"phase": "heating", "minutes": 25},
                {"phase": "cooking", "minutes": 45},
                {"phase": "resting", "minutes": 10},
            ],
            "quick_cook": [
                {"phase": "heating", "minutes": 15},
                {"phase": "cooking", "minutes": 20},
                {"phase": "resting", "minutes": 5},
            ],
            "porridge": [
                {"phase": "heating", "minutes": 20},
                {"phase": "cooking", "minutes": 50},
                {"phase": "resting", "minutes": 10},
            ],
        },
    }

    def __init__(
        self,
        power: bool = None,
        cooking_program: str = None,
        rice_type: str = None,
        texture: str = None,
        keep_warm: bool = None,
        inner_pot_state: str = None,
        status: str = None,
        phase: str = None,
        remaining_minutes: int = None,
        started_at_minute: int = None,
        progress_minutes: int = None,
        *,
        _defer_power_init: bool = False,
    ) -> None:
        _power_init_value = power if power is not None else False
        self.power = BoolProperty(
            name="power",
            description="Whether the rice cooker is powered.",
            default=False,
        )
        self.cooking_program = StringProperty(
            name="cooking_program",
            description="Selected cooking program.",
            default="white_rice",
            choices=["white_rice", "brown_rice", "quick_cook", "porridge"],
        )
        self.rice_type = StringProperty(
            name="rice_type",
            description="Selected rice type.",
            default="white_rice",
            choices=["white_rice", "brown_rice", "mixed_grain"],
        )
        self.texture = StringProperty(
            name="texture",
            description="Desired cooked texture.",
            default="standard",
            choices=["soft", "standard", "firm"],
        )
        self.keep_warm = BoolProperty(
            name="keep_warm",
            description="Whether keep-warm mode is enabled after cooking completes.",
            default=False,
        )
        self.inner_pot_state = StringProperty(
            name="inner_pot_state",
            description="Simulated state of the inner-pot contents.",
            default="empty",
            mode=2,
            choices=["empty", "uncooked", "cooking", "cooked"],
        )
        self.status = StringProperty(
            name="status",
            description="Current cooking process status.",
            default="idle",
            mode=2,
            choices=["idle", "running", "paused", "completed"],
        )
        self.phase = StringProperty(
            name="phase",
            description="Current cooking stage.",
            default="idle",
            mode=2,
            choices=["idle", "heating", "cooking", "resting", "completed"],
        )
        self.remaining_minutes = IntProperty(
            name="remaining_minutes",
            description="Minutes remaining in the selected cooking program.",
            default=0,
            mode=2,
            minimum=0,
            step=1,
            step_origin=0,
        )
        self.started_at_minute = IntProperty(
            name="started_at_minute",
            description="Elapsed world minute at which the current cooking run origin was established.",
            default=0,
            mode=2,
            minimum=0,
            step=1,
            step_origin=0,
        )
        self.progress_minutes = IntProperty(
            name="progress_minutes",
            description="Completed minutes in the current cooking program.",
            default=0,
            mode=2,
            minimum=0,
            step=1,
            step_origin=0,
        )
        code = self.power.internal_set(_power_init_value)

        if cooking_program is not None:
            code = self.cooking_program.internal_set(cooking_program)
        if rice_type is not None:
            code = self.rice_type.internal_set(rice_type)
        if texture is not None:
            code = self.texture.internal_set(texture)
        if keep_warm is not None:
            code = self.keep_warm.internal_set(keep_warm)
        if inner_pot_state is not None:
            code = self.inner_pot_state.internal_set(inner_pot_state)
        if status is not None:
            code = self.status.internal_set(status)
        if phase is not None:
            code = self.phase.internal_set(phase)
        if remaining_minutes is not None:
            code = self.remaining_minutes.internal_set(remaining_minutes)
        if started_at_minute is not None:
            code = self.started_at_minute.internal_set(started_at_minute)
        if progress_minutes is not None:
            code = self.progress_minutes.internal_set(progress_minutes)

        self._power_managed_properties = (
            self.cooking_program,
            self.rice_type,
            self.texture,
            self.keep_warm,
            self.inner_pot_state,
            self.status,
            self.phase,
            self.remaining_minutes,
            self.started_at_minute,
            self.progress_minutes,
        )
        self._power_initialized = False
        self._disabled = {
            "properties": [],
            "functions": [],
            "events": [],
        }

        if not _defer_power_init:
            self.set_power(_power_init_value)

    def get_power(self) -> tuple[str, dict]:
        """
        Get the current power state.
        """
        code, value = self.power.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"power": value}

    def set_power(self, value: bool) -> tuple[str, dict]:
        """
        Set power and update access for active dependent properties.
        """
        if self._power_initialized:
            current_code, current_value = self.power.get()
            if current_code != "[PASS]":
                return current_code, {}
            if type(value) is bool and current_value == value:
                return "[PASS]", {}

        code = self.power.set(value)
        if code != "[PASS]":
            return code, {}

        for prop in self._power_managed_properties:
            switch_code = prop.handle_power_switch(value)
            if switch_code != "[PASS]" and not switch_code.startswith("[NO_ACTION]"):
                return switch_code, {}

        self._power_initialized = True
        return "[PASS]", {}

    def _read(self, prop, name):
        code, value = prop.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {name: value}

    def _state(self):
        return self.status.get()

    def get_cooking_program(self) -> tuple[str, dict]:
        return self._read(self.cooking_program, "cooking_program")

    def set_cooking_program(self, value: str) -> tuple[str, dict]:
        code, state = self.status.get()
        if code != "[PASS]":
            return code, {}
        if state not in ("idle", "completed"):
            return "[PRECONDITION_ERROR]", {}
        code = self.cooking_program.set(value)
        return (code, {}) if code != "[PASS]" else ("[PASS]", {})

    def get_rice_type(self) -> tuple[str, dict]:
        return self._read(self.rice_type, "rice_type")

    def set_rice_type(self, value: str) -> tuple[str, dict]:
        code, state = self.status.get()
        if code != "[PASS]":
            return code, {}
        if state not in ("idle", "completed"):
            return "[PRECONDITION_ERROR]", {}
        code = self.rice_type.set(value)
        return (code, {}) if code != "[PASS]" else ("[PASS]", {})

    def get_texture(self) -> tuple[str, dict]:
        return self._read(self.texture, "texture")

    def set_texture(self, value: str) -> tuple[str, dict]:
        code, state = self.status.get()
        if code != "[PASS]":
            return code, {}
        if state not in ("idle", "completed"):
            return "[PRECONDITION_ERROR]", {}
        code = self.texture.set(value)
        return (code, {}) if code != "[PASS]" else ("[PASS]", {})

    def get_keep_warm(self) -> tuple[str, dict]:
        return self._read(self.keep_warm, "keep_warm")

    def set_keep_warm(self, value: bool) -> tuple[str, dict]:
        code, state = self.status.get()
        if code != "[PASS]":
            return code, {}
        if state != "completed":
            return "[PRECONDITION_ERROR]", {}
        code = self.keep_warm.set(value)
        return (code, {}) if code != "[PASS]" else ("[PASS]", {})

    def get_inner_pot_state(self) -> tuple[str, dict]:
        return self._read(self.inner_pot_state, "inner_pot_state")

    def get_status(self) -> tuple[str, dict]:
        return self._read(self.status, "status")

    def get_phase(self) -> tuple[str, dict]:
        return self._read(self.phase, "phase")

    def get_remaining_minutes(self) -> tuple[str, dict]:
        return self._read(self.remaining_minutes, "remaining_minutes")

    def start_cooking(self, mode: str) -> tuple[str, dict]:
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        code, state = self.status.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True or state not in ("idle", "completed"):
            return "[PRECONDITION_ERROR]", {}
        if not isinstance(mode, str) or mode not in self.PROCESS["modes"]:
            return "[INVALID_VALUE]", {}

        total = sum(item["minutes"] for item in self.PROCESS["modes"][mode])
        values = (
            (self.cooking_program, mode),
            (self.status, "running"),
            (self.phase, "heating"),
            (self.remaining_minutes, total),
            (self.progress_minutes, 0),
            (self.inner_pot_state, "cooking"),
            (self.keep_warm, False),
        )
        for prop, value in values:
            code = prop.internal_set(value)
            if code != "[PASS]":
                return code, {}
        return "[PASS]", {}

    def pause_cooking(self) -> tuple[str, dict]:
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        code, state = self.status.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True or state != "running":
            return "[PRECONDITION_ERROR]", {}
        code = self.status.internal_set("paused")
        return (code, {}) if code != "[PASS]" else ("[PASS]", {})

    def resume_cooking(self) -> tuple[str, dict]:
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        code, state = self.status.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True or state != "paused":
            return "[PRECONDITION_ERROR]", {}
        code = self.status.internal_set("running")
        return (code, {}) if code != "[PASS]" else ("[PASS]", {})

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, []
        if powered is not True:
            return "[PASS]", []
        code, state = self.status.get()
        if code != "[PASS]":
            return code, []
        if powered is not True or state != "running":
            return "[PASS]", []

        code, mode = self.cooking_program.get()
        if code != "[PASS]":
            return code, []
        code, start = self.started_at_minute.get()
        if code != "[PASS]":
            return code, []

        elapsed = context["time_state"]["elapsed_minutes"]
        progress = max(0, elapsed - start)
        stages = self.PROCESS["modes"][mode]
        total = sum(item["minutes"] for item in stages)

        if progress >= total:
            updates = (
                (self.progress_minutes, total),
                (self.remaining_minutes, 0),
                (self.status, "completed"),
                (self.phase, "completed"),
                (self.inner_pot_state, "cooked"),
            )
        else:
            accumulated = 0
            current = "idle"
            for item in stages:
                if progress < accumulated + item["minutes"]:
                    current = item["phase"]
                    break
                accumulated += item["minutes"]
            updates = (
                (self.progress_minutes, progress),
                (self.remaining_minutes, total - progress),
                (self.phase, current),
            )

        for prop, value in updates:
            code = prop.internal_set(value)
            if code != "[PASS]":
                return code, []
        return "[PASS]", []

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        pre_state = context["pre_state"]["objects"][context["object_id"]]["properties"]

        code, powered = self.power.get()
        if code != "[PASS]":
            return code, []

        if powered is not True:
            if pre_state["status"] == "running":
                code = self.status.internal_set("paused")
                if code != "[PASS]":
                    return code, []
            return "[PASS]", []

        code, state = self.status.get()
        if code != "[PASS]":
            return code, []

        if state == "running" and (
            pre_state["status"] != "running" or pre_state["power"] is not True
        ):
            code, progress = self.progress_minutes.get()
            if code != "[PASS]":
                return code, []
            code = self.started_at_minute.internal_set(
                context["time_state"]["elapsed_minutes"] - progress
            )
            if code != "[PASS]":
                return code, []

        return "[PASS]", []
