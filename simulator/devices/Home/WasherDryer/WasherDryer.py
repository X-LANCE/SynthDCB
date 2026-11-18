# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class WasherDryer:
    """
    WasherDryer
    Description: Washer-dryer. Users can query and set the washing program, water temperature, spin speed, drying mode, and drying duration. The current stage and remaining time are queryable; preset stages associated with the washing program progress over time, and operation is started through a manual setting. Operation affects the room's noise level.
    Version: 1.0.0
    Base: -
    """
    PROCESS = {'mode_property': 'washing_program', 'start_function': 'start_cycle', 'pause_function': 'pause_cycle', 'resume_function': 'resume_cycle', 'modes': {'daily': [{'phase': 'wash', 'minutes': 25}, {'phase': 'rinse', 'minutes': 10}, {'phase': 'spin', 'minutes': 5}, {'phase': 'dry', 'minutes': {'property': 'drying_duration'}}], 'quick': [{'phase': 'wash', 'minutes': 10}, {'phase': 'rinse', 'minutes': 5}, {'phase': 'spin', 'minutes': 3}, {'phase': 'dry', 'minutes': {'property': 'drying_duration'}}]}}

    def __init__(self, power: bool=None, washing_program: str=None, water_temperature: int=None, spin_speed: int=None, drying_mode: str=None, drying_duration: int=None, status: str=None, phase: str=None, remaining_minutes: int=None, started_at_minute: int=None, progress_minutes: int=None, *, _defer_power_init: bool=False) -> None:
        _power_init_value = power if power is not None else False
        self.power = BoolProperty(name='power', description='Electrical power. Switching off pauses a running cycle without erasing configuration or progress.', default=False)
        self.washing_program = StringProperty(name='washing_program', description='Selected combined-cycle program. Daily has 25 wash, 10 rinse and 5 spin minutes; quick has 10 wash, 5 rinse and 3 spin minutes. Both then dry for drying_duration minutes.', default='daily', choices=['daily', 'quick'])
        self.water_temperature = IntProperty(name='water_temperature', description='Wash-water temperature setting; does not represent room temperature or change preset stage durations.', default=30, unit='degC', minimum=20, maximum=60, step=10, step_origin=20)
        self.spin_speed = IntProperty(name='spin_speed', description='Spin-stage drum speed setting. Changes spin noise, not spin duration.', default=800, unit='rpm', minimum=400, maximum=1200, step=200, step_origin=400)
        self.drying_mode = StringProperty(name='drying_mode', description='Normal or gentle drying intensity. Gentle uses quieter drying operation; both use the configured drying duration.', default='normal', choices=['normal', 'gentle'])
        self.drying_duration = IntProperty(name='drying_duration', description='Duration of the dry phase, fixed for the entire started cycle.', default=45, unit='minute', minimum=1, maximum=180, step=1)
        self.status = StringProperty(name='status', description='Persisted process status, changed only internally by process actions and events.', default='idle', mode=2, choices=['idle', 'running', 'paused', 'completed'])
        self.phase = StringProperty(name='phase', description='Current stage. Pausing preserves the active stage.', default='idle', mode=2, choices=['idle', 'wash', 'rinse', 'spin', 'dry', 'completed'])
        self.remaining_minutes = IntProperty(name='remaining_minutes', description='Minutes remaining in the entire cycle, including all unfinished stages; zero before first start and after completion.', default=0, mode=2, unit='minute', minimum=0)
        self.started_at_minute = IntProperty(name='started_at_minute', description='Elapsed-world-minute origin of running progress. On start or resume it becomes the current elapsed minute minus retained progress.', default=0, mode=2, unit='minute', minimum=0)
        self.progress_minutes = IntProperty(name='progress_minutes', description='Completed cycle minutes, retained during pauses and clamped to total duration at completion.', default=0, mode=2, unit='minute', minimum=0)
        code = self.power.internal_set(_power_init_value)
        if washing_program is not None:
            code = self.washing_program.internal_set(washing_program)
        if water_temperature is not None:
            code = self.water_temperature.internal_set(water_temperature)
        if spin_speed is not None:
            code = self.spin_speed.internal_set(spin_speed)
        if drying_mode is not None:
            code = self.drying_mode.internal_set(drying_mode)
        if drying_duration is not None:
            code = self.drying_duration.internal_set(drying_duration)
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
        self._power_managed_properties = (self.washing_program, self.water_temperature, self.spin_speed, self.drying_mode, self.drying_duration, self.status, self.phase, self.remaining_minutes, self.started_at_minute, self.progress_minutes)
        self._power_initialized = False
        self._disabled = {'properties': [], 'functions': [], 'events': []}
        if not _defer_power_init:
            self.set_power(_power_init_value)

    def get_power(self) -> tuple[str, dict]:
        """
        Get the current power state.
        """
        code, value = self.power.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'power': value})

    def set_power(self, value: bool) -> tuple[str, dict]:
        """
        Set power and update access for active dependent properties.
        """
        if self._power_initialized:
            current_code, current_value = self.power.get()
            if current_code != '[PASS]':
                return (current_code, {})
            if type(value) is bool and current_value == value:
                return ('[PASS]', {})
        code = self.power.set(value)
        if code != '[PASS]':
            return (code, {})
        for prop in self._power_managed_properties:
            switch_code = prop.handle_power_switch(value)
            if switch_code != '[PASS]' and (not switch_code.startswith('[NO_ACTION]')):
                return (switch_code, {})
        self._power_initialized = True
        return ('[PASS]', {})

    def get_washing_program(self) -> tuple[str, dict]:
        """
        Return the selected program under washing_program. Fail without changes if unpowered or arguments are invalid.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        return self._read(self.washing_program, 'washing_program')

    def set_washing_program(self, value: str) -> tuple[str, dict]:
        """
        Select daily or quick without starting operation; return an empty success object. Require power and idle or completed status. Invalid arguments or failed preconditions leave all state unchanged.

        Args:
        - value:  (choices=['daily', 'quick'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        return self._write(self.washing_program, value)

    def get_water_temperature(self) -> tuple[str, dict]:
        """
        Return the wash-water temperature setting in degC under water_temperature. Fail without changes if unpowered or arguments are invalid.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        return self._read(self.water_temperature, 'water_temperature')

    def set_water_temperature(self, value: int) -> tuple[str, dict]:
        """
        Set wash-water temperature to 20, 30, 40, 50 or 60 degC; return an empty success object. Require power and idle or completed status. Invalid arguments or failed preconditions leave all state unchanged.

        Args:
        - value:  (min=20, max=60)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        return self._write(self.water_temperature, value)

    def get_spin_speed(self) -> tuple[str, dict]:
        """
        Return spin speed in rpm under spin_speed. Fail without changes if unpowered or arguments are invalid.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        return self._read(self.spin_speed, 'spin_speed')

    def set_spin_speed(self, value: int) -> tuple[str, dict]:
        """
        Set spin speed from 400 through 1200 rpm in increments of 200; return an empty success object. Require power and idle or completed status. Invalid arguments or failed preconditions leave all state unchanged.

        Args:
        - value:  (min=400, max=1200)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        return self._write(self.spin_speed, value)

    def get_drying_mode(self) -> tuple[str, dict]:
        """
        Return normal or gentle under drying_mode. Fail without changes if unpowered or arguments are invalid.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        return self._read(self.drying_mode, 'drying_mode')

    def set_drying_mode(self, value: str) -> tuple[str, dict]:
        """
        Select normal or gentle drying without starting operation; return an empty success object. Require power and idle or completed status. Invalid arguments or failed preconditions leave all state unchanged.

        Args:
        - value:  (choices=['normal', 'gentle'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        return self._write(self.drying_mode, value)

    def get_drying_duration(self) -> tuple[str, dict]:
        """
        Return configured dry-phase minutes under drying_duration. Fail without changes if unpowered or arguments are invalid.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        return self._read(self.drying_duration, 'drying_duration')

    def set_drying_duration(self, value: int) -> tuple[str, dict]:
        """
        Set dry-phase duration to an integer from 1 through 180 minutes; return an empty success object. Require power and idle or completed status. Invalid arguments or failed preconditions leave all state unchanged.

        Args:
        - value:  (min=1, max=180)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        return self._write(self.drying_duration, value)

    def get_status(self) -> tuple[str, dict]:
        """
        Return process status under status. Fail without changes if unpowered or arguments are invalid.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        return self._read(self.status, 'status')

    def get_phase(self) -> tuple[str, dict]:
        """
        Return the current stage under phase. Fail without changes if unpowered or arguments are invalid.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        return self._read(self.phase, 'phase')

    def get_remaining_minutes(self) -> tuple[str, dict]:
        """
        Return whole-cycle remaining minutes under remaining_minutes. Fail without changes if unpowered or arguments are invalid.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        return self._read(self.remaining_minutes, 'remaining_minutes')

    def get_started_at_minute(self) -> tuple[str, dict]:
        """
        Return the persisted running-time origin under started_at_minute. Fail without changes if unpowered or arguments are invalid.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        return self._read(self.started_at_minute, 'started_at_minute')

    def get_progress_minutes(self) -> tuple[str, dict]:
        """
        Return completed cycle minutes under progress_minutes. Fail without changes if unpowered or arguments are invalid.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        return self._read(self.progress_minutes, 'progress_minutes')

    def start_cycle(self, program: str) -> tuple[str, dict]:
        """
        Manually select and start daily or quick. Require power and idle or completed status. Set washing_program to program, status to running, phase to wash, progress to zero and remaining time to the declared program total including drying_duration. Establish the running-time origin at the current elapsed minute. Configuration is frozen until completion, including while paused. Return an empty success object. Validate all arguments and preconditions before changes; failure preserves all state.

        Args:
        - program:  (choices=['daily', 'quick'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[POWER_OFF]', {})
        status_code, status = self.status.get()
        if status_code != '[PASS]':
            return (status_code, {})
        if status not in ('idle', 'completed'):
            return ('[INVALID_STATE]', {})
        total_code, total = self._total(program)
        if total_code != '[PASS]':
            return (total_code, {})
        elapsed = context_elapsed = 0
        code = self.washing_program.set(program)
        if code != '[PASS]':
            return (code, {})
        for prop, value in ((self.status, 'running'), (self.phase, 'wash'), (self.progress_minutes, 0), (self.remaining_minutes, total)):
            code = prop.internal_set(value)
            if code != '[PASS]':
                return (code, {})
        return ('[PASS]', {})

    def pause_cycle(self) -> tuple[str, dict]:
        """
        Pause a powered running cycle, preserving phase, remaining time, progress and configuration. Return an empty success object. Invalid arguments or failed preconditions leave all state unchanged.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != '[PASS]':
            return (code, {})
        if not powered:
            return ('[POWER_OFF]', {})
        code, status = self.status.get()
        if code != '[PASS]':
            return (code, {})
        if status != 'running':
            return ('[INVALID_STATE]', {})
        code = self.status.internal_set('paused')
        return (code, {}) if code == '[PASS]' else (code, {})

    def resume_cycle(self) -> tuple[str, dict]:
        """
        Resume a powered paused cycle without resetting progress, phase, remaining time or configuration. Set status to running and re-establish the running-time origin as current elapsed minute minus retained progress. Return an empty success object. Invalid arguments or failed preconditions leave all state unchanged.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != '[PASS]':
            return (code, {})
        if not powered:
            return ('[POWER_OFF]', {})
        code, status = self.status.get()
        if code != '[PASS]':
            return (code, {})
        if status != 'paused':
            return ('[INVALID_STATE]', {})
        code = self.status.internal_set('running')
        return (code, {}) if code == '[PASS]' else (code, {})

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        Power loss pauses a running cycle while preserving its progress, phase, remaining time and settings. Restoring power does not resume it. Each transition from a non-running status into running establishes started_at_minute as the current elapsed minute minus progress_minutes. This changes only internal process state.

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
            if pre['status'] == 'running':
                code = self.status.internal_set('paused')
                if code != '[PASS]':
                    return (code, [])
            return ('[PASS]', [])
        code, status = self.status.get()
        if code != '[PASS]':
            return (code, [])
        if status == 'running' and (pre['status'] != 'running' or pre['power'] is not True):
            code, progress = self.progress_minutes.get()
            if code != '[PASS]':
                return (code, [])
            code = self.started_at_minute.internal_set(context['time_state']['elapsed_minutes'] - progress)
            if code != '[PASS]':
                return (code, [])
        return ('[PASS]', [])

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        While powered and running, calculate progress as elapsed minutes minus started_at_minute, clamped between zero and the declared washing_program total. Use the preset wash, rinse and spin durations and drying_duration for the dry phase. Advance to the next phase at each exact cumulative boundary; remaining_minutes is total minus progress. At the final boundary set status and phase to completed and remaining_minutes to zero. Idle, paused, completed and unpowered cycles do not advance. Preserve all settings. After advancing, the device contributes 45 dBA during wash, 42 dBA during rinse, 50 plus spin_speed divided by 40 dBA during spin, and 48 dBA for normal drying or 43 dBA for gentle drying. Its noise contribution is zero whenever it is unpowered or not running. Apply the absolute contribution each time, including zero to clear previous output. Return this noise output solely as a set_contribution effect for the containing Home Space noise property, unit dBA, to be applied by the runtime reducer. No device-side noise property exists or is updated.

    Effect properties:
    - power: Required for process advancement and active noise.
    - washing_program: Selects the declared stage sequence and preset durations.
    - drying_duration: Determines dry-phase and total cycle duration.
    - spin_speed: Determines spin-stage noise.
    - drying_mode: Determines dry-stage noise.
    - status: Gates advancement and becomes completed at the end.
    - phase: Tracks the active stage and determines noise.
    - remaining_minutes: Updated to total duration minus progress.
    - started_at_minute: Persisted origin used to calculate running progress.
    - progress_minutes: Persisted elapsed process minutes, clamped to total duration.
        """
        code, powered = self.power.get()
        if code != '[PASS]':
            return (code, [])
        status = self.status.value
        if not powered or status != 'running':
            value = 0
        else:
            code, program = self.washing_program.get()
            if code != '[PASS]':
                return (code, [])
            code, origin = self.started_at_minute.get()
            if code != '[PASS]':
                return (code, [])
            code, duration = self.drying_duration.get()
            if code != '[PASS]':
                return (code, [])
            durations = [25, 10, 5, duration] if program == 'daily' else [10, 5, 3, duration]
            total = sum(durations)
            progress = max(0, min(context['time_state']['elapsed_minutes'] - origin, total))
            for prop, item in ((self.progress_minutes, progress), (self.remaining_minutes, total - progress)):
                code = prop.internal_set(item)
                if code != '[PASS]':
                    return (code, [])
            if progress >= total:
                self.phase.internal_set('completed')
                self.status.internal_set('completed')
                value = 0
            else:
                cumulative = 0
                phases = ('wash', 'rinse', 'spin', 'dry')
                selected = 'dry'
                for index in range(4):
                    if progress < cumulative + durations[index]:
                        selected = phases[index]
                        break
                    cumulative += durations[index]
                self.phase.internal_set(selected)
                if selected == 'wash':
                    value = 45
                elif selected == 'rinse':
                    value = 42
                elif selected == 'spin':
                    code, speed = self.spin_speed.get()
                    if code != '[PASS]':
                        return (code, [])
                    value = 50 + speed / 40
                else:
                    code, mode = self.drying_mode.get()
                    if code != '[PASS]':
                        return (code, [])
                    value = 48 if mode == 'normal' else 43
        return ('[PASS]', [{'trigger': 'tick', 'source': context['object_id'], 'target': context['space_id'], 'function': 'set_contribution', 'parameters': {'property': 'noise', 'value': value, 'unit': 'dBA'}}])

    def _read(self, prop, name):
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[POWER_OFF]', {})
        code, value = prop.get()
        return (code, {name: value}) if code == '[PASS]' else (code, {})

    def _write(self, prop, value):
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[POWER_OFF]', {})
        status_code, status = self.status.get()
        if status_code != '[PASS]':
            return (status_code, {})
        if status not in ('idle', 'completed'):
            return ('[INVALID_STATE]', {})
        code = prop.set(value)
        return (code, {}) if code == '[PASS]' else (code, {})

    def _total(self, program):
        code, duration = self.drying_duration.get()
        if code != '[PASS]':
            return (code, 0)
        base = 40 if program == 'daily' else 18
        return ('[PASS]', base + duration)
