# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..WasherDryer import WasherDryer

class Dryer(WasherDryer):
    """
    Dryer
    Description: Dryer. It supports only drying-related functions.
    Version: 1.0.0
    Base: WasherDryer
    """

    PROCESS = {'mode_property': 'cycle_mode', 'start_function': 'start_cycle', 'pause_function': 'pause_cycle', 'resume_function': 'resume_cycle', 'modes': {'dry_only': [{'phase': 'dry', 'minutes': {'property': 'drying_duration'}}]}}

    def __init__(self, cycle_mode: str = None, phase: str = None, *, power: bool | None = None, _defer_power_init: bool = False, **base_kwargs) -> None:
        _power_init_value = power if power is not None else False
        # initialize base WasherDryer class
        super().__init__(power=_power_init_value, _defer_power_init=True, **base_kwargs)
        # define properties
        self.cycle_mode = StringProperty(
            name='cycle_mode',
            description='Selected dry-only cycle mode.',
            default='dry_only',
            mode=2,
            choices=['dry_only']
        )
        self.phase = StringProperty(
            name='phase',
            description='Current drying-process phase.',
            default='idle',
            mode=2,
            choices=['idle', 'dry', 'completed']
        )

        # initialize properties
        if cycle_mode is not None: code = self.cycle_mode.internal_set(cycle_mode)
        if phase is not None: code = self.phase.internal_set(phase)

        # disable inherited properties
        self.spin_speed.chmod(0)
        self.washing_program.chmod(0)
        self.water_temperature.chmod(0)
        self._power_managed_properties = (self.drying_mode, self.drying_duration, self.status, self.phase, self.remaining_minutes, self.started_at_minute, self.progress_minutes, self.cycle_mode,)
        self._power_initialized = False
        self._disabled = {
            'properties': ['spin_speed', 'washing_program', 'water_temperature'],
            'functions': ['get_spin_speed', 'get_washing_program', 'get_water_temperature', 'set_spin_speed', 'set_washing_program', 'set_water_temperature'],
            'events': []
        }

        if not _defer_power_init:
            self.set_power(_power_init_value)

    def start_cycle(self, program: str = 'dry_only') -> tuple[str, dict]:
        """
        The program argument has the single value dry_only. Start the dry_only cycle while powered and idle or completed. Set cycle_mode to dry_only, status to running, phase to dry, progress_minutes to zero, started_at_minute to the current elapsed minute, and remaining_minutes to drying_duration. Configuration remains fixed until completion, including while paused. Invalid arguments or failed preconditions leave all state unchanged.

        Args:
        - program:  (choices=['dry_only'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        if program != "dry_only":
            return "[INVALID_ARGUMENT]", {}
        if self.status.value not in ("idle", "completed"):
            return "[INVALID_STATE]", {}
        for prop, value in ((self.cycle_mode, program), (self.status, "running"),
                            (self.phase, "dry"), (self.progress_minutes, 0),
                            (self.remaining_minutes, self.drying_duration.value)):
            code = prop.internal_set(value)
            if code != "[PASS]":
                return code, {}
        return "[PASS]", {}

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        While powered and running, calculate progress as elapsed minutes minus started_at_minute, clamped between zero and the declared drying_duration. Keep phase dry until the configured duration is reached. Update progress_minutes and remaining_minutes accordingly; at the final boundary set status and phase to completed and remaining_minutes to zero. Idle, paused, completed and unpowered cycles do not advance. Preserve all settings. While powered and running, contribute 48 dBA for normal drying or 43 dBA for gentle drying. Contribute zero whenever unpowered or not running. Apply the absolute noise contribution each time, including zero to clear previous output. Return this noise output solely as a set_contribution effect for the containing Home Space noise property, in dBA.

    Effect properties:
    - power: Determines whether the process advances and produces noise.
    - drying_duration: Determines the total dry-only process duration.
    - drying_mode: Determines normal or gentle drying noise.
    - status: Gates advancement and becomes completed at the end.
    - phase: Tracks the drying phase.
    - started_at_minute: Running-time origin used to calculate progress.
    - progress_minutes: Completed drying minutes, clamped to the configured duration.
    - remaining_minutes: Configured duration minus completed drying minutes.
        """
        noise = 0
        if self.power.value is True and self.status.value == "running":
            total = self.drying_duration.value
            progress = max(0, min(total, context["time_state"]["elapsed_minutes"] - self.started_at_minute.value))
            self.progress_minutes.internal_set(progress)
            self.remaining_minutes.internal_set(total - progress)
            if progress == total:
                self.status.internal_set("completed")
                self.phase.internal_set("completed")
            else:
                self.phase.internal_set("dry")
                noise = 48 if self.drying_mode.value == "normal" else 43
        return "[PASS]", [{"trigger": "tick", "source": context["object_id"],
                          "target": context["space_id"], "function": "set_contribution",
                          "parameters": {"property": "noise", "value": noise, "unit": "dBA"}}]

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        This hook has two separate action-dependent branches. After set_power switches power off while the process status is running, set status=paused and preserve phase, progress, remaining time and origin. Restoring power does not resume a paused process and does not rebase the origin. After start_cycle or resume_cycle transitions status from a non-running value to running while powered, set started_at_minute to the current elapsed world minute minus progress_minutes. pause_cycle preserves the origin and progress. These are conditional branches of the shared hook; there is no origin update caused by set_power. Emit no Space effects.

    Effect properties:
    - power: Power loss pauses operation.
    - status: Identifies transitions into running and power-loss pauses.
    - started_at_minute: Running-time origin established on start or resume.
    - progress_minutes: Retained progress used to establish the running-time origin.
        """
        return super()._on_after_action(context)

    def get_spin_speed(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'get_spin_speed' is disabled in Dryer.", {}

    def get_washing_program(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'get_washing_program' is disabled in Dryer.", {}

    def get_water_temperature(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'get_water_temperature' is disabled in Dryer.", {}

    def set_spin_speed(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'set_spin_speed' is disabled in Dryer.", {}

    def set_washing_program(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'set_washing_program' is disabled in Dryer.", {}

    def set_water_temperature(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'set_water_temperature' is disabled in Dryer.", {}