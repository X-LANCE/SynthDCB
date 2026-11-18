# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class CoffeeMaker:
    """
    CoffeeMaker
    Description: Coffee maker. Users can query and set the brewing program, cup volume, strength, and current extraction state, and can perform brew, pause, and cleaning actions. During extraction, the device dispenses the beverage according to the selected cup volume and strength; normal beverage preparation is unavailable while the cleaning program is running.
    Version: 1.0.0
    Base: -
    """

    PROCESS = {'mode_property': 'program', 'start_function': 'brew', 'pause_function': 'pause', 'resume_function': 'resume', 'modes': {'espresso': [{'phase': 'extraction', 'minutes': 5}], 'coffee': [{'phase': 'extraction', 'minutes': 8}], 'cleaning': [{'phase': 'cleaning', 'minutes': 15}]}}

    def __init__(self, power: bool = None, program: str = None, cup_volume: int = None, strength: int = None, status: str = None, phase: str = None, remaining_minutes: int = None, started_at_minute: int = None, progress_minutes: int = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the coffee maker is powered.',
            default=False
        )
        self.program = StringProperty(
            name='program',
            description='Selected coffee preparation or cleaning program.',
            default='coffee',
            choices=['espresso', 'coffee', 'cleaning']
        )
        self.cup_volume = IntProperty(
            name='cup_volume',
            description='Selected beverage volume in milliliters.',
            default=200,
            unit='ml',
            minimum=30,
            maximum=500,
            step=10,
            step_origin=0
        )
        self.strength = IntProperty(
            name='strength',
            description='Selected coffee strength level.',
            default=2,
            minimum=1,
            maximum=3,
            step=1,
            step_origin=1
        )
        self.status = StringProperty(
            name='status',
            description='Current process status.',
            default='idle',
            mode=2,
            choices=['idle', 'running', 'paused', 'completed']
        )
        self.phase = StringProperty(
            name='phase',
            description='Current process phase, or idle or completed when no phase is active.',
            default='idle',
            mode=2
        )
        self.remaining_minutes = IntProperty(
            name='remaining_minutes',
            description='Minutes remaining in the selected process.',
            default=0,
            mode=2,
            minimum=0,
            step=1,
            step_origin=0
        )
        self.started_at_minute = IntProperty(
            name='started_at_minute',
            description='Elapsed-world minute at which the current process origin was established.',
            default=0,
            mode=2,
            step=1,
            step_origin=0
        )
        self.progress_minutes = IntProperty(
            name='progress_minutes',
            description='Completed minutes in the current process.',
            default=0,
            mode=2,
            minimum=0,
            step=1,
            step_origin=0
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if program is not None: code = self.program.internal_set(program)
        if cup_volume is not None: code = self.cup_volume.internal_set(cup_volume)
        if strength is not None: code = self.strength.internal_set(strength)
        if status is not None: code = self.status.internal_set(status)
        if phase is not None: code = self.phase.internal_set(phase)
        if remaining_minutes is not None: code = self.remaining_minutes.internal_set(remaining_minutes)
        if started_at_minute is not None: code = self.started_at_minute.internal_set(started_at_minute)
        if progress_minutes is not None: code = self.progress_minutes.internal_set(progress_minutes)
        self._power_managed_properties = (self.program, self.cup_volume, self.strength, self.status, self.phase, self.remaining_minutes, self.started_at_minute, self.progress_minutes,)
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

    def get_program(self) -> tuple[str, dict]:
        """
        Returns the selected program while powered on.
        """
        code, value = self.program.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"program": value}

    def set_program(self, value: str) -> tuple[str, dict]:
        """
        Selects espresso or coffee while powered on and not processing. Cleaning is started with clean.
        """
        if value not in ("espresso", "coffee"):
            return "[ERROR] Invalid program.", {}
        code, status = self.status.get()
        if code != "[PASS]":
            return code, {}
        if status not in ("idle", "completed"):
            return "[ERROR] Process unavailable.", {}
        code = self.program.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_cup_volume(self) -> tuple[str, dict]:
        """
        Returns the selected cup volume while powered on.
        """
        code, value = self.cup_volume.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"cup_volume": value}

    def set_cup_volume(self, value: int) -> tuple[str, dict]:
        """
        Sets the cup volume from 30 through 500 milliliters in 10 milliliter steps while powered on and idle or completed.
        """
        if type(value) is not int or isinstance(value, bool) or value < 30 or value > 500 or value % 10 != 0:
            return "[ERROR] Invalid cup volume.", {}
        code, status = self.status.get()
        if code != "[PASS]":
            return code, {}
        if status not in ("idle", "completed"):
            return "[ERROR] Process unavailable.", {}
        code = self.cup_volume.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_strength(self) -> tuple[str, dict]:
        """
        Returns the selected strength while powered on.
        """
        code, value = self.strength.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"strength": value}

    def set_strength(self, value: int) -> tuple[str, dict]:
        """
        Sets coffee strength from level 1 through 3 while powered on and idle or completed.
        """
        if type(value) is not int or isinstance(value, bool) or value < 1 or value > 3:
            return "[ERROR] Invalid strength.", {}
        code, status = self.status.get()
        if code != "[PASS]":
            return code, {}
        if status not in ("idle", "completed"):
            return "[ERROR] Process unavailable.", {}
        code = self.strength.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_status(self) -> tuple[str, dict]:
        """
        Returns the current extraction or cleaning process state while powered on.
        """
        code, phase = self.phase.get()
        if code != "[PASS]":
            return code, {}
        code, remaining = self.remaining_minutes.get()
        if code != "[PASS]":
            return code, {}
        code, progress = self.progress_minutes.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {
            "phase": phase,
            "remaining_minutes": remaining,
            "progress_minutes": progress
        }

    def brew(self, program: str) -> tuple[str, dict]:
        """
        Starts beverage extraction using the selected espresso or coffee program.
        """
        if program not in ("espresso", "coffee"):
            return "[ERROR] Invalid beverage program.", {}
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[ERROR] Device is powered off.", {}
        code, status = self.status.get()
        if code != "[PASS]":
            return code, {}
        if status not in ("idle", "completed"):
            return "[ERROR] Process unavailable.", {}
        code = self.program.set(program)
        if code != "[PASS]":
            return code, {}
        code = self.status.internal_set("running")
        if code != "[PASS]":
            return code, {}
        code = self.phase.internal_set("extraction")
        if code != "[PASS]":
            return code, {}
        code = self.progress_minutes.internal_set(0)
        if code != "[PASS]":
            return code, {}
        code = self.remaining_minutes.internal_set(5 if program == "espresso" else 8)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def pause(self) -> tuple[str, dict]:
        """
        Pauses an active extraction or cleaning process.
        """
        code, status = self.status.get()
        if code != "[PASS]":
            return code, {}
        if status != "running":
            return "[ERROR] No active process.", {}
        code = self.status.internal_set("paused")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def resume(self) -> tuple[str, dict]:
        """
        Resumes a paused extraction or cleaning process without resetting its progress.
        """
        code, status = self.status.get()
        if code != "[PASS]":
            return code, {}
        if status != "paused":
            return "[ERROR] Process is not paused.", {}
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[ERROR] Device is powered off.", {}
        code = self.status.internal_set("running")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def clean(self, program: str) -> tuple[str, dict]:
        """
        Starts the cleaning program.
        """
        if program != "cleaning":
            return "[ERROR] Invalid cleaning program.", {}
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[ERROR] Device is powered off.", {}
        code, status = self.status.get()
        if code != "[PASS]":
            return code, {}
        if status not in ("idle", "completed"):
            return "[ERROR] Process unavailable.", {}
        code = self.program.set("cleaning")
        if code != "[PASS]":
            return code, {}
        code = self.status.internal_set("running")
        if code != "[PASS]":
            return code, {}
        code = self.phase.internal_set("cleaning")
        if code != "[PASS]":
            return code, {}
        code = self.progress_minutes.internal_set(0)
        if code != "[PASS]":
            return code, {}
        code = self.remaining_minutes.internal_set(15)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        Advances the active extraction or cleaning process according to its selected program and elapsed time. An unpowered process does not advance.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, []
        status = self.status.value
        if powered is not True or status != "running":
            return "[PASS]", []
        program = self.program.value
        origin = self.started_at_minute.value
        progress = self.progress_minutes.value
        elapsed = context["time_state"]["elapsed_minutes"]
        total = 5 if program == "espresso" else 8 if program == "coffee" else 15
        new_progress = max(progress, min(total, elapsed - origin))
        code = self.progress_minutes.internal_set(new_progress)
        if code != "[PASS]":
            return code, []
        code = self.remaining_minutes.internal_set(max(total - new_progress, 0))
        if code != "[PASS]":
            return code, []
        if new_progress >= total:
            code = self.status.internal_set("completed")
            if code != "[PASS]":
                return code, []
            code = self.phase.internal_set("completed")
            if code != "[PASS]":
                return code, []
        return "[PASS]", []

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        When power changes from on to off during a running process, pauses that process while preserving its progress.
        """
        pre_state = context["pre_state"]["objects"][context["object_id"]]["properties"]
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, []
        previous_status = pre_state["status"]
        if powered is not True:
            if previous_status == "running":
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
        if status == "running" and previous_status != "running":
            code = self.started_at_minute.internal_set(
                context["time_state"]["elapsed_minutes"] - progress
            )
            if code != "[PASS]":
                return code, []
        return "[PASS]", []