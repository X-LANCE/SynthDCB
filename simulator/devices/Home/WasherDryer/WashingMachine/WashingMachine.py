# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..WasherDryer import WasherDryer

class WashingMachine(WasherDryer):
    """
    WashingMachine
    Description: Washing machine. It supports only laundry-related functions.
    Version: 1.0.0
    Base: WasherDryer
    """

    PROCESS = {'mode_property': 'washing_program', 'start_function': 'start_cycle', 'pause_function': 'pause_cycle', 'resume_function': 'resume_cycle', 'modes': {'daily': [{'phase': 'wash', 'minutes': 25}, {'phase': 'rinse', 'minutes': 10}, {'phase': 'spin', 'minutes': 5}], 'quick': [{'phase': 'wash', 'minutes': 10}, {'phase': 'rinse', 'minutes': 5}, {'phase': 'spin', 'minutes': 3}]}}

    def __init__(self, washing_program: str = None, phase: str = None, *, power: bool | None = None, _defer_power_init: bool = False, **base_kwargs) -> None:
        _power_init_value = power if power is not None else False
        # initialize base WasherDryer class
        super().__init__(power=_power_init_value, _defer_power_init=True, **base_kwargs)
        # define properties
        self.washing_program = StringProperty(
            name='washing_program',
            description='Selected wash-only program. Daily has 25 wash, 10 rinse and 5 spin minutes; quick has 10 wash, 5 rinse and 3 spin minutes.',
            default='daily',
            choices=['daily', 'quick']
        )
        self.phase = StringProperty(
            name='phase',
            description='Current washing stage. Pausing preserves the active stage; the cycle completes after spin without a drying stage.',
            default='idle',
            mode=2,
            choices=['idle', 'wash', 'rinse', 'spin', 'completed']
        )

        # initialize properties
        if washing_program is not None: code = self.washing_program.internal_set(washing_program)
        if phase is not None: code = self.phase.internal_set(phase)

        # disable inherited properties
        self.drying_duration.chmod(0)
        self.drying_mode.chmod(0)
        self._power_managed_properties = (self.washing_program, self.water_temperature, self.spin_speed, self.status, self.phase, self.remaining_minutes, self.started_at_minute, self.progress_minutes,)
        self._power_initialized = False
        self._disabled = {
            'properties': ['drying_duration', 'drying_mode'],
            'functions': ['get_drying_duration', 'get_drying_mode', 'set_drying_duration', 'set_drying_mode'],
            'events': []
        }

        if not _defer_power_init:
            self.set_power(_power_init_value)

    def start_cycle(self, program: str) -> tuple[str, dict]:
        """
        Manually select and start the daily or quick wash-only cycle. Require power and idle or completed status. Set washing_program to program, status to running, phase to wash, progress_minutes to zero and remaining_minutes to the declared wash-only program total: 40 minutes for daily or 18 minutes for quick. Establish started_at_minute at the current elapsed minute. Configuration remains frozen while running or paused. Return an empty success object. Validate all arguments and preconditions before changes; failure preserves all state.

        Args:
        - program:  (choices=['daily', 'quick'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        if not isinstance(program, str) or program not in self.PROCESS['modes']:
            return ('[INVALID_ARGUMENT]', {})
        code, powered = self.power.get()
        if code != '[PASS]':
            return (code, {})
        if not powered:
            return ('[POWER_OFF]', {})
        code, status = self.status.get()
        if code != '[PASS]':
            return (code, {})
        if status not in ('idle', 'completed'):
            return ('[INVALID_STATE]', {})
        stages = self.PROCESS['modes'][program]
        total = sum(stage['minutes'] for stage in stages)
        code = self.washing_program.set(program)
        if code != '[PASS]':
            return (code, {})
        for prop, value in (
            (self.phase, stages[0]['phase']),
            (self.progress_minutes, 0),
            (self.remaining_minutes, total),
            (self.status, 'running'),
        ):
            code = prop.internal_set(value)
            if code != '[PASS]':
                return (code, {})
        return ('[PASS]', {})

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        While powered and running, calculate progress_minutes as elapsed minutes minus started_at_minute, clamped between zero and the declared washing_program total. Use only the declared wash, rinse and spin durations. Advance phase at each exact cumulative boundary and set remaining_minutes to total minus progress_minutes. At the final boundary set status and phase to completed and remaining_minutes to zero. Idle, paused, completed and unpowered cycles do not advance. Preserve all settings. During wash contribute 45 dBA, during rinse contribute 42 dBA, and during spin contribute 50 plus spin_speed divided by 40 dBA. The absolute noise contribution is zero whenever power is false or status is not running. Reapply the contribution each minute, including zero to clear previous output. Emit this absolute noise contribution solely as a set_contribution effect for the containing Home Space noise property, unit dBA; it is not a device-side noise state.

    Effect properties:
    - power: Required for process advancement and active noise.
    - washing_program: Selects the declared wash-only stages and durations.
    - spin_speed: Determines spin-stage noise.
    - status: Gates advancement and active noise; becomes completed at the end.
    - phase: Tracks the active washing stage and determines noise.
    - remaining_minutes: Updated to the total washing duration minus progress.
    - started_at_minute: Persisted origin used to calculate running progress.
    - progress_minutes: Persisted elapsed process minutes, clamped to the declared wash-only total.
        """
        code, powered = self.power.get()
        if code != '[PASS]':
            return (code, [])
        contribution = 0
        if powered:
            code, status = self.status.get()
            if code != '[PASS]':
                return (code, [])
            if status == 'running':
                code, program = self.washing_program.get()
                if code != '[PASS]':
                    return (code, [])
                code, origin = self.started_at_minute.get()
                if code != '[PASS]':
                    return (code, [])
                if program not in self.PROCESS['modes']:
                    return ('[INVALID_STATE]', [])
                stages = self.PROCESS['modes'][program]
                total = sum(stage['minutes'] for stage in stages)
                progress = max(0, min(context['time_state']['elapsed_minutes'] - origin, total))
                selected = 'completed'
                boundary = 0
                for stage in stages:
                    boundary += stage['minutes']
                    if progress < boundary:
                        selected = stage['phase']
                        break
                if selected == 'wash':
                    contribution = 45
                elif selected == 'rinse':
                    contribution = 42
                elif selected == 'spin':
                    code, speed = self.spin_speed.get()
                    if code != '[PASS]':
                        return (code, [])
                    contribution = 50 + speed // 40
                for prop, value in (
                    (self.progress_minutes, progress),
                    (self.remaining_minutes, total - progress),
                    (self.phase, selected),
                ):
                    code = prop.internal_set(value)
                    if code != '[PASS]':
                        return (code, [])
                if selected == 'completed':
                    code = self.status.internal_set('completed')
                    if code != '[PASS]':
                        return (code, [])
        return ('[PASS]', [{
            'trigger': 'tick',
            'source': context['object_id'],
            'target': context['space_id'],
            'function': 'set_contribution',
            'parameters': {
                'property': 'noise',
                'value': contribution,
                'unit': 'dBA',
            },
        }])

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        This hook has two separate action-dependent branches. After set_power switches power off while the process status is running, set status=paused and preserve phase, progress, remaining time and origin. Restoring power does not resume a paused process and does not rebase the origin. After start_cycle or resume_cycle transitions status from a non-running value to running while powered, set started_at_minute to the current elapsed world minute minus progress_minutes. pause_cycle preserves the origin and progress. These are conditional branches of the shared hook; there is no origin update caused by set_power. Emit no Space effects.

    Effect properties:
    - power: Power loss pauses operation.
    - status: Identifies transitions into running and power-loss pauses.
    - started_at_minute: Running-time origin established on start or resume.
    - progress_minutes: Retained progress used to establish the running-time origin.
        """
        pre = context['pre_state']['objects'][context['object_id']]['properties']
        code, powered = self.power.get()
        if code != '[PASS]':
            return (code, [])
        if not powered:
            if pre['power'] is True and pre['status'] == 'running':
                code = self.status.internal_set('paused')
                if code != '[PASS]':
                    return (code, [])
            return ('[PASS]', [])
        if pre['power'] is not True:
            return ('[PASS]', [])
        code, status = self.status.get()
        if code != '[PASS]':
            return (code, [])
        if status == 'running' and pre['status'] != 'running':
            code, progress = self.progress_minutes.get()
            if code != '[PASS]':
                return (code, [])
            code = self.started_at_minute.internal_set(
                context['time_state']['elapsed_minutes'] - progress
            )
            if code != '[PASS]':
                return (code, [])
        return ('[PASS]', [])

    def get_drying_duration(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'get_drying_duration' is disabled in WashingMachine.", {}

    def get_drying_mode(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'get_drying_mode' is disabled in WashingMachine.", {}

    def set_drying_duration(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'set_drying_duration' is disabled in WashingMachine.", {}

    def set_drying_mode(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'set_drying_mode' is disabled in WashingMachine.", {}