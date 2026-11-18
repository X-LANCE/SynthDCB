# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty


class Dishwasher:
    """
    Dishwasher
    Description: Dishwasher. Users can query and set the washing program, cleaning intensity, drying state, and detergent dispensing. The current stage and remaining time are queryable; preset stages associated with the washing program progress over time, and operation is started through a manual setting.
    Version: 1.0.0
    Base: -
    """

    PROCESS = {'mode_property': 'washing_program', 'start_function': 'start_cycle', 'pause_function': 'pause_cycle', 'resume_function': 'resume_cycle', 'modes': {'eco': [{'phase': 'wash', 'minutes': 45}, {'phase': 'rinse', 'minutes': 20}, {'phase': 'dry', 'minutes': 30}], 'normal': [{'phase': 'wash', 'minutes': 60}, {'phase': 'rinse', 'minutes': 25}, {'phase': 'dry', 'minutes': 40}], 'intensive': [{'phase': 'wash', 'minutes': 90}, {'phase': 'rinse', 'minutes': 30}, {'phase': 'dry', 'minutes': 50}]}}

    def __init__(self, power: bool = None, washing_program: str = None, cleaning_intensity: str = None, drying_state: bool = None, detergent_dispensing: bool = None, status: str = None, phase: str = None, remaining_minutes: int = None, started_at_minute: int = None, progress_minutes: int = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the dishwasher is powered.',
            default=False
        )
        self.washing_program = StringProperty(
            name='washing_program',
            description='Selected washing program.',
            default='normal',
            choices=['eco', 'normal', 'intensive']
        )
        self.cleaning_intensity = StringProperty(
            name='cleaning_intensity',
            description='Configured cleaning intensity.',
            default='standard',
            choices=['light', 'standard', 'strong']
        )
        self.drying_state = BoolProperty(
            name='drying_state',
            description='Whether the drying stage is enabled. When false, the declared dry stage is skipped and its duration is removed from the process.',
            default=True
        )
        self.detergent_dispensing = BoolProperty(
            name='detergent_dispensing',
            description='Whether automatic detergent dispensing is enabled.',
            default=True
        )
        self.status = StringProperty(
            name='status',
            description='Current dishwasher process status.',
            default='idle',
            mode=2,
            choices=['idle', 'running', 'paused', 'completed']
        )
        self.phase = StringProperty(
            name='phase',
            description='Current washing stage.',
            default='idle',
            mode=2,
            choices=['idle', 'wash', 'rinse', 'dry', 'completed']
        )
        self.remaining_minutes = IntProperty(
            name='remaining_minutes',
            description='Minutes remaining in the selected dishwasher program, excluding a disabled drying stage.',
            default=0,
            mode=2,
            minimum=0,
            step=1,
            step_origin=0
        )
        self.started_at_minute = IntProperty(
            name='started_at_minute',
            description='Elapsed world minute at which the current process origin was established.',
            default=0,
            mode=2,
            minimum=0,
            step=1,
            step_origin=0
        )
        self.progress_minutes = IntProperty(
            name='progress_minutes',
            description='Completed minutes from the beginning of the selected process.',
            default=0,
            mode=2,
            minimum=0,
            step=1,
            step_origin=0
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if washing_program is not None: code = self.washing_program.internal_set(washing_program)
        if cleaning_intensity is not None: code = self.cleaning_intensity.internal_set(cleaning_intensity)
        if drying_state is not None: code = self.drying_state.internal_set(drying_state)
        if detergent_dispensing is not None: code = self.detergent_dispensing.internal_set(detergent_dispensing)
        if status is not None: code = self.status.internal_set(status)
        if phase is not None: code = self.phase.internal_set(phase)
        if remaining_minutes is not None: code = self.remaining_minutes.internal_set(remaining_minutes)
        if started_at_minute is not None: code = self.started_at_minute.internal_set(started_at_minute)
        if progress_minutes is not None: code = self.progress_minutes.internal_set(progress_minutes)
        self._power_managed_properties = (self.washing_program, self.cleaning_intensity, self.drying_state, self.detergent_dispensing, self.status, self.phase, self.remaining_minutes, self.started_at_minute, self.progress_minutes,)
        self._power_initialized = False
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
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

    def _read(self, prop, key):
        code, value = prop.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {key: value}

    def _powered(self):
        code, value = self.power.get()
        if code != "[PASS]":
            return code, False
        if value is not True:
            return "[DEVICE_NOT_POWERED]", False
        return "[PASS]", True

    def _configurable(self):
        code, powered = self._powered()
        if code != "[PASS]":
            return code
        code, status = self.status.get()
        if code != "[PASS]":
            return code
        if status not in ("idle", "completed"):
            return "[INVALID_STATE]"
        return "[PASS]"

    def get_washing_program(self) -> tuple[str, dict]:
        return self._read(self.washing_program, "washing_program")

    def set_washing_program(self, value: str) -> tuple[str, dict]:
        code = self._configurable()
        if code != "[PASS]":
            return code, {}
        code = self.washing_program.set(value)
        return code, {}

    def get_cleaning_intensity(self) -> tuple[str, dict]:
        return self._read(self.cleaning_intensity, "cleaning_intensity")

    def set_cleaning_intensity(self, value: str) -> tuple[str, dict]:
        code = self._configurable()
        if code != "[PASS]":
            return code, {}
        code = self.cleaning_intensity.set(value)
        return code, {}

    def get_drying_state(self) -> tuple[str, dict]:
        return self._read(self.drying_state, "drying_state")

    def set_drying_state(self, value: bool) -> tuple[str, dict]:
        code = self._configurable()
        if code != "[PASS]":
            return code, {}
        code = self.drying_state.set(value)
        return code, {}

    def get_detergent_dispensing(self) -> tuple[str, dict]:
        return self._read(self.detergent_dispensing, "detergent_dispensing")

    def set_detergent_dispensing(self, value: bool) -> tuple[str, dict]:
        code = self._configurable()
        if code != "[PASS]":
            return code, {}
        code = self.detergent_dispensing.set(value)
        return code, {}

    def get_status(self) -> tuple[str, dict]:
        return self._read(self.status, "status")

    def get_phase(self) -> tuple[str, dict]:
        return self._read(self.phase, "phase")

    def get_remaining_minutes(self) -> tuple[str, dict]:
        return self._read(self.remaining_minutes, "remaining_minutes")

    def start_cycle(self, mode: str) -> tuple[str, dict]:
        code, powered = self._powered()
        if code != "[PASS]":
            return code, {}
        if mode not in self.PROCESS["modes"]:
            return "[INVALID_VALUE]", {}
        code, status = self.status.get()
        if code != "[PASS]":
            return code, {}
        if status not in ("idle", "completed"):
            return "[INVALID_STATE]", {}
        code, drying = self.drying_state.get()
        if code != "[PASS]":
            return code, {}

        stages = [
            stage for stage in self.PROCESS["modes"][mode]
            if stage["phase"] != "dry" or drying
        ]
        total = sum(stage["minutes"] for stage in stages)

        code = self.washing_program.set(mode)
        if code != "[PASS]":
            return code, {}

        for prop, value in (
            (self.status, "running"),
            (self.phase, stages[0]["phase"]),
            (self.progress_minutes, 0),
            (self.remaining_minutes, total),
        ):
            code = prop.internal_set(value)
            if code != "[PASS]":
                return code, {}
        return "[PASS]", {}

    def pause_cycle(self) -> tuple[str, dict]:
        code, powered = self._powered()
        if code != "[PASS]":
            return code, {}
        code, status = self.status.get()
        if code != "[PASS]":
            return code, {}
        if status != "running":
            return "[INVALID_STATE]", {}
        code = self.status.internal_set("paused")
        return code, {}

    def resume_cycle(self) -> tuple[str, dict]:
        code, powered = self._powered()
        if code != "[PASS]":
            return code, {}
        code, status = self.status.get()
        if code != "[PASS]":
            return code, {}
        if status != "paused":
            return "[INVALID_STATE]", {}
        code = self.status.internal_set("running")
        return code, {}

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, []
        if powered is not True:
            return "[PASS]", []
        code, status = self.status.get()
        if code != "[PASS]":
            return code, []
        if powered is not True or status != "running":
            return "[PASS]", []

        code, program = self.washing_program.get()
        if code != "[PASS]":
            return code, []
        code, drying = self.drying_state.get()
        if code != "[PASS]":
            return code, []
        code, started = self.started_at_minute.get()
        if code != "[PASS]":
            return code, []

        stages = [
            stage for stage in self.PROCESS["modes"][program]
            if stage["phase"] != "dry" or drying
        ]
        total = sum(stage["minutes"] for stage in stages)
        elapsed = context["time_state"]["elapsed_minutes"]
        progress = max(0, min(total, elapsed - started))

        for prop, value in (
            (self.progress_minutes, progress),
            (self.remaining_minutes, max(total - progress, 0)),
        ):
            code = prop.internal_set(value)
            if code != "[PASS]":
                return code, []

        if progress >= total:
            code = self.phase.internal_set("completed")
            if code != "[PASS]":
                return code, []
            code = self.status.internal_set("completed")
            if code != "[PASS]":
                return code, []
            return "[PASS]", []

        offset = 0
        current = stages[-1]["phase"]
        for stage in stages:
            if progress < offset + stage["minutes"]:
                current = stage["phase"]
                break
            offset += stage["minutes"]

        code = self.phase.internal_set(current)
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

        code, status = self.status.get()
        if code != "[PASS]":
            return code, []
        code, progress = self.progress_minutes.get()
        if code != "[PASS]":
            return code, []

        if status == "running" and (
            pre_state["status"] != "running"
            or pre_state["power"] is not True
        ):
            elapsed = context["time_state"]["elapsed_minutes"]
            code = self.started_at_minute.internal_set(elapsed - progress)
            if code != "[PASS]":
                return code, []

        return "[PASS]", []