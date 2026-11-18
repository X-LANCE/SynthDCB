# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class RobotVacuum:
    """
    RobotVacuum
    Description: Robot vacuum. Users can query and set the cleaning mode, suction level, mopping-water level, and cleaning area, and can perform start, pause, recharge, and return-to-base actions. The device moves across and cleans the floor; the mopping-water level is effective only in mopping mode, and the base station can provide dust collection, mop washing, or drying states. The single process includes deterministic return, base service and charging phases. Read-only cleaning output counters record actual vacuum/mopping work; paused or skipped time never creates cleaning output.
    Version: 1.0.0
    Base: -
    """
    PROCESS = {'mode_property': 'operation_mode', 'start_function': 'start', 'pause_function': 'pause', 'resume_function': 'resume', 'modes': {'vacuum': [{'phase': 'cleaning', 'minutes': 30}, {'phase': 'returning', 'minutes': 5}, {'phase': 'dust_collection', 'minutes': 3}, {'phase': 'charging', 'minutes': 30}], 'mop': [{'phase': 'cleaning', 'minutes': 30}, {'phase': 'returning', 'minutes': 5}, {'phase': 'mop_washing', 'minutes': 5}, {'phase': 'drying', 'minutes': 30}, {'phase': 'charging', 'minutes': 30}], 'vacuum_and_mop': [{'phase': 'cleaning', 'minutes': 30}, {'phase': 'returning', 'minutes': 5}, {'phase': 'dust_collection', 'minutes': 3}, {'phase': 'mop_washing', 'minutes': 5}, {'phase': 'drying', 'minutes': 30}, {'phase': 'charging', 'minutes': 30}], 'recharge': [{'phase': 'returning', 'minutes': 5}, {'phase': 'charging', 'minutes': 30}]}}

    def __init__(self, power: bool=None, cleaning_mode: str=None, suction_level: int=None, mopping_water_level: int=None, cleaning_area: str=None, status: str=None, phase: str=None, remaining_minutes: int=None, started_at_minute: int=None, progress_minutes: int=None, base_state: str=None, operation_mode: str=None, vacuum_cleaned_units: int=None, mopped_units: int=None, *, _defer_power_init: bool=False) -> None:
        _power_init_value = power if power is not None else False
        self.power = BoolProperty(name='power', description='Whether the robot vacuum is powered and available for non-power controls.', default=False)
        self.cleaning_mode = StringProperty(name='cleaning_mode', description='Configured cleaning mode. Mopping-water level affects cleaning only in mop and vacuum_and_mop modes.', default='vacuum_and_mop', choices=['vacuum', 'mop', 'vacuum_and_mop'])
        self.suction_level = IntProperty(name='suction_level', description='Configured suction level from 1 through 4.', default=2, minimum=1, maximum=4, step=1, step_origin=1)
        self.mopping_water_level = IntProperty(name='mopping_water_level', description='Configured mopping-water level from 0 through 3. It has a cleaning effect only in mop and vacuum_and_mop modes.', default=1, minimum=0, maximum=3, step=1, step_origin=0)
        self.cleaning_area = StringProperty(name='cleaning_area', description='Configured non-empty single-line descriptive label for the floor area to clean.', default='全屋', pattern='^[^\\r\\n]+$', max_length=100)
        self.status = StringProperty(name='status', description='Current robot and cleaning lifecycle state.', default='idle', mode=2, choices=['idle', 'running', 'paused', 'completed'])
        self.phase = StringProperty(name='phase', description='Current process phase, or idle or completed when no phase is active.', default='idle', mode=2, choices=['idle', 'cleaning', 'returning', 'dust_collection', 'mop_washing', 'drying', 'charging', 'completed'])
        self.remaining_minutes = IntProperty(name='remaining_minutes', description='Minutes remaining in the complete cleaning and base-station process.', default=0, mode=2, minimum=0, step=1, step_origin=0)
        self.started_at_minute = IntProperty(name='started_at_minute', description='Logical elapsed-minute origin adjusted for retained or skipped progress. It may be negative after an early return-to-base skips the remaining cleaning segment.', default=0, mode=2, minimum=-1000, step=1, step_origin=0)
        self.progress_minutes = IntProperty(name='progress_minutes', description='Minutes of process progress retained across pauses and resumes.', default=0, mode=2, minimum=0, step=1, step_origin=0)
        self.base_state = StringProperty(name='base_state', description='Current base-station phase, retained while paused; idle outside dust_collection, mop_washing and drying. status and power determine whether that phase is advancing.', default='idle', mode=2, choices=['idle', 'dust_collection', 'mop_washing', 'drying'])
        self.operation_mode = StringProperty(name='operation_mode', description='Persisted mode of the single active cleaning or recharge process.', default='vacuum_and_mop', mode=2, choices=['vacuum', 'mop', 'vacuum_and_mop', 'recharge'])
        self.vacuum_cleaned_units = IntProperty(name='vacuum_cleaned_units', description='Cumulative simulated cleaning output in the most recent process run; retained after completion, reset on a new start or recharge.', default=0, mode=2, minimum=0, maximum=120, step=1, step_origin=0)
        self.mopped_units = IntProperty(name='mopped_units', description='Cumulative simulated cleaning output in the most recent process run; retained after completion, reset on a new start or recharge.', default=0, mode=2, minimum=0, maximum=90, step=1, step_origin=0)
        code = self.power.internal_set(_power_init_value)
        if cleaning_mode is not None:
            code = self.cleaning_mode.internal_set(cleaning_mode)
        if suction_level is not None:
            code = self.suction_level.internal_set(suction_level)
        if mopping_water_level is not None:
            code = self.mopping_water_level.internal_set(mopping_water_level)
        if cleaning_area is not None:
            code = self.cleaning_area.internal_set(cleaning_area)
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
        if base_state is not None:
            code = self.base_state.internal_set(base_state)
        if operation_mode is not None:
            code = self.operation_mode.internal_set(operation_mode)
        if vacuum_cleaned_units is not None:
            code = self.vacuum_cleaned_units.internal_set(vacuum_cleaned_units)
        if mopped_units is not None:
            code = self.mopped_units.internal_set(mopped_units)
        self._power_managed_properties = (self.cleaning_mode, self.suction_level, self.mopping_water_level, self.cleaning_area, self.status, self.phase, self.remaining_minutes, self.started_at_minute, self.progress_minutes, self.base_state, self.operation_mode, self.vacuum_cleaned_units, self.mopped_units)
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

    def get_cleaning_mode(self) -> tuple[str, dict]:
        """
        Get the configured cleaning mode while powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.cleaning_mode.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'cleaning_mode': value})

    def set_cleaning_mode(self, value: str) -> tuple[str, dict]:
        """
        Set the cleaning mode while powered on and no process is running. Settings can change only in idle or completed state, so the selected run configuration is stable across a pause.

        Args:
        - value:  (choices=['vacuum', 'mop', 'vacuum_and_mop'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        status_code, status = self.status.get()
        if status_code != '[PASS]':
            return (status_code, {})
        if status not in ('idle', 'completed'):
            return ('[ERROR] Invalid process state.', {})
        code = self.cleaning_mode.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_suction_level(self) -> tuple[str, dict]:
        """
        Get the configured suction level while powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.suction_level.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'suction_level': value})

    def set_suction_level(self, value: int) -> tuple[str, dict]:
        """
        Set suction level from 1 through 4 while powered on and not running. Settings can change only in idle or completed state, so the selected run configuration is stable across a pause.

        Args:
        - value:  (min=1, max=4)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        status_code, status = self.status.get()
        if status_code != '[PASS]':
            return (status_code, {})
        if status not in ('idle', 'completed'):
            return ('[ERROR] Invalid process state.', {})
        code = self.suction_level.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_mopping_water_level(self) -> tuple[str, dict]:
        """
        Get the configured mopping-water level while powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.mopping_water_level.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'mopping_water_level': value})

    def set_mopping_water_level(self, value: int) -> tuple[str, dict]:
        """
        Set mopping-water level from 0 through 3 while powered on and not running. Settings can change only in idle or completed state, so the selected run configuration is stable across a pause.

        Args:
        - value:  (min=0, max=3)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        status_code, status = self.status.get()
        if status_code != '[PASS]':
            return (status_code, {})
        if status not in ('idle', 'completed'):
            return ('[ERROR] Invalid process state.', {})
        code = self.mopping_water_level.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_cleaning_area(self) -> tuple[str, dict]:
        """
        Get the configured cleaning area while powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.cleaning_area.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'cleaning_area': value})

    def set_cleaning_area(self, value: str) -> tuple[str, dict]:
        """
        Set a non-empty single-line cleaning-area label while powered on and not running. Settings can change only in idle or completed state, so the selected run configuration is stable across a pause.

        Args:
        - value:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        status_code, status = self.status.get()
        if status_code != '[PASS]':
            return (status_code, {})
        if status not in ('idle', 'completed'):
            return ('[ERROR] Invalid process state.', {})
        code = self.cleaning_area.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_status(self) -> tuple[str, dict]:
        """
        Get the process status while powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.status.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'status': value})

    def get_phase(self) -> tuple[str, dict]:
        """
        Get the current process phase while powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.phase.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'phase': value})

    def get_remaining_minutes(self) -> tuple[str, dict]:
        """
        Get the remaining process duration while powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.remaining_minutes.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'remaining_minutes': value})

    def get_progress_minutes(self) -> tuple[str, dict]:
        """
        Get retained process progress while powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.progress_minutes.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'progress_minutes': value})

    def get_base_state(self) -> tuple[str, dict]:
        """
        Get the base-station state while powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.base_state.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'base_state': value})

    def start(self, mode: str) -> tuple[str, dict]:
        """
        Start a fresh cleaning or recharge process from idle or completed state. The requested cleaning mode and the configured cleaning_area select the floor-cleaning run. Set operation_mode to the supplied mode, status=running, phase to the first declared phase, progress_minutes=0, remaining_minutes to the sum of the mode phase durations, base_state=idle, vacuum_cleaned_units=0 and mopped_units=0. For a cleaning mode also assign cleaning_mode to that mode; recharge preserves cleaning_mode. The after_action hook establishes the logical time origin. Invalid arguments leave all state unchanged.

        Args:
        - mode:  (choices=['vacuum', 'mop', 'vacuum_and_mop', 'recharge'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        status_code, status = self.status.get()
        if status_code != '[PASS]':
            return (status_code, {})
        if status not in ('idle', 'completed'):
            return ('[ERROR] Invalid process state.', {})
        if mode not in ('vacuum', 'mop', 'vacuum_and_mop', 'recharge'):
            return ('[ERROR] Invalid mode.', {})
        durations = {'vacuum': 68, 'mop': 100, 'vacuum_and_mop': 103, 'recharge': 35}
        phases = {'vacuum': 'cleaning', 'mop': 'cleaning', 'vacuum_and_mop': 'cleaning', 'recharge': 'returning'}
        code, _ = self.operation_mode.get()
        if code != '[PASS]':
            return (code, {})
        writes = [(self.operation_mode, mode), (self.status, 'running'), (self.phase, phases[mode]), (self.progress_minutes, 0), (self.remaining_minutes, durations[mode]), (self.base_state, 'idle'), (self.vacuum_cleaned_units, 0), (self.mopped_units, 0)]
        if mode != 'recharge':
            writes.append((self.cleaning_mode, mode))
        for prop, value in writes:
            code = prop.internal_set(value)
            if code != '[PASS]':
                return (code, {})
        return ('[PASS]', {})

    def pause(self) -> tuple[str, dict]:
        """
        Pause the running process and retain its progress.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, status = self.status.get()
        if code != '[PASS]':
            return (code, {})
        if status != 'running':
            return ('[ERROR] Process is not running.', {})
        code = self.status.internal_set('paused')
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def resume(self) -> tuple[str, dict]:
        """
        Resume a paused process without resetting its progress.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, status = self.status.get()
        if code != '[PASS]':
            return (code, {})
        if status != 'paused':
            return ('[ERROR] Process is not paused.', {})
        code = self.status.internal_set('running')
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def recharge(self, mode: str='recharge') -> tuple[str, dict]:
        """
        Cancel the current process if any, and begin a single returning-then-charging process in recharge mode. Set operation_mode to the supplied mode, status=running, phase to the first declared phase, progress_minutes=0, remaining_minutes to the sum of the mode phase durations, base_state=idle, vacuum_cleaned_units=0 and mopped_units=0. For a cleaning mode also assign cleaning_mode to that mode; recharge preserves cleaning_mode. The after_action hook establishes the logical time origin. Invalid arguments leave all state unchanged.

        Args:
        - mode:  (choices=['recharge'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, _ = self.status.get()
        if code != '[PASS]':
            return (code, {})
        if mode != 'recharge':
            return ('[ERROR] Invalid mode.', {})
        for prop, value in ((self.operation_mode, mode), (self.status, 'running'),
                            (self.phase, 'returning'), (self.progress_minutes, 0),
                            (self.remaining_minutes, 35), (self.base_state, 'idle'),
                            (self.vacuum_cleaned_units, 0), (self.mopped_units, 0)):
            code = prop.internal_set(value)
            if code != '[PASS]':
                return (code, {})
        return ('[PASS]', {})

    def return_to_base(self) -> tuple[str, dict]:
        """
        While powered, if phase=cleaning and status is running or paused, stop further floor cleaning and skip directly to the returning boundary: set progress_minutes=30, phase=returning, status=running, remaining_minutes to the selected operation_mode total minus 30, and base_state=idle. Preserve achieved vacuum_cleaned_units and mopped_units; skipped cleaning time produces no cleaning output. The after_action hook rebases started_at_minute to the current elapsed minute minus progress_minutes, even if that origin is negative. If already paused in returning, set status=running and rebase the origin while preserving progress. In idle, completed, already-running returning, or any base-station phase, succeed without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        status_code, status = self.status.get()
        if status_code != '[PASS]':
            return (status_code, {})
        phase_code, phase = self.phase.get()
        if phase_code != '[PASS]':
            return (phase_code, {})
        if phase == 'cleaning' and status in ('running', 'paused'):
            mode_code, mode = self.operation_mode.get()
            if mode_code != '[PASS]':
                return (mode_code, {})
            total = {'vacuum': 68, 'mop': 100, 'vacuum_and_mop': 103, 'recharge': 35}[mode]
            for prop, value in ((self.progress_minutes, 30), (self.phase, 'returning'), (self.status, 'running'), (self.remaining_minutes, total - 30), (self.base_state, 'idle')):
                code = prop.internal_set(value)
                if code != '[PASS]':
                    return (code, {})
        elif phase == 'returning' and status == 'paused':
            code = self.status.internal_set('running')
            if code != '[PASS]':
                return (code, {})
        return ('[PASS]', {})

    def get_operation_mode(self) -> tuple[str, dict]:
        """
        Return operation_mode while powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- operation_mode: Persisted mode of the single active cleaning or recharge process. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.operation_mode.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'operation_mode': value})

    def get_vacuum_cleaned_units(self) -> tuple[str, dict]:
        """
        Return vacuum_cleaned_units while powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- vacuum_cleaned_units: Cumulative simulated cleaning output in the most recent process run; retained after completion, reset on a new start or recharge. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.vacuum_cleaned_units.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'vacuum_cleaned_units': value})

    def get_mopped_units(self) -> tuple[str, dict]:
        """
        Return mopped_units while powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- mopped_units: Cumulative simulated cleaning output in the most recent process run; retained after completion, reset on a new start or recharge. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.mopped_units.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'mopped_units': value})

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        While powered and running, compute new progress as elapsed world minutes minus started_at_minute, clamped to the selected operation_mode total duration. Before replacing progress_minutes, calculate actually traversed cleaning minutes as max(0, min(new progress,30)-min(previous progress_minutes,30)) for a cleaning mode, or zero in recharge mode. Increase vacuum_cleaned_units by those minutes times suction_level in vacuum or vacuum_and_mop mode, and increase mopped_units by those minutes times mopping_water_level in mop or vacuum_and_mop mode. These internal outputs quantify the most recent run on its selected cleaning_area; they are not Space properties. Thus water has no cleaning effect in vacuum mode, and an action that skips cleaning produces no fabricated cleaning output. Persist the new progress, set remaining_minutes=total-progress, and select phases at their exact cumulative duration boundaries. At the final boundary set status and phase to completed and remaining_minutes=0. Set base_state to the phase during dust_collection, mop_washing or drying, otherwise idle. Paused and unpowered processes do not advance or change cleaning outputs. After processing, return one absolute set_contribution effect to the containing Home Space noise property, unit dBA: while powered and running, cleaning is 20+5*suction_level dBA for vacuum-containing modes or 20 for mop-only, returning is 20, dust_collection is 45, mop_washing is 25, drying is 15, and charging is zero. All idle, completed, paused or unpowered states contribute zero; always emit zero to clear stale output. Emit this Space noise effect only on tick.

    Effect properties:
    - power: Process progress, stable run configuration, cleaning output, or noise input.
    - suction_level: Process progress, stable run configuration, cleaning output, or noise input.
    - mopping_water_level: Process progress, stable run configuration, cleaning output, or noise input.
    - cleaning_area: Process progress, stable run configuration, cleaning output, or noise input.
    - status: Process progress, stable run configuration, cleaning output, or noise input.
    - phase: Process progress, stable run configuration, cleaning output, or noise input.
    - remaining_minutes: Process progress, stable run configuration, cleaning output, or noise input.
    - started_at_minute: Process progress, stable run configuration, cleaning output, or noise input.
    - progress_minutes: Process progress, stable run configuration, cleaning output, or noise input.
    - base_state: Process progress, stable run configuration, cleaning output, or noise input.
    - operation_mode: Process progress, stable run configuration, cleaning output, or noise input.
    - vacuum_cleaned_units: Process progress, stable run configuration, cleaning output, or noise input.
    - mopped_units: Process progress, stable run configuration, cleaning output, or noise input.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, [])
        status = self.status.value
        progress = self.progress_minutes.value
        mode = self.operation_mode.value
        phase = self.phase.value
        total = {'vacuum': 68, 'mop': 100, 'vacuum_and_mop': 103, 'recharge': 35}[mode]
        new_progress = progress
        if powered is True and status == 'running':
            origin_code, origin = self.started_at_minute.get()
            if origin_code != '[PASS]':
                return (origin_code, [])
            elapsed = context['time_state']['elapsed_minutes']
            new_progress = min(max(elapsed - origin, progress), total)
            cleaning_before = min(progress, 30)
            cleaning_after = min(new_progress, 30)
            worked = max(0, cleaning_after - cleaning_before)
            if mode in ('vacuum', 'vacuum_and_mop'):
                suction_code, suction = self.suction_level.get()
                if suction_code != '[PASS]':
                    return (suction_code, [])
                value_code, vacuumed = self.vacuum_cleaned_units.get()
                if value_code != '[PASS]':
                    return (value_code, [])
                self.vacuum_cleaned_units.internal_set(min(120, vacuumed + worked * suction))
            if mode in ('mop', 'vacuum_and_mop'):
                water_code, water = self.mopping_water_level.get()
                if water_code != '[PASS]':
                    return (water_code, [])
                value_code, mopped = self.mopped_units.get()
                if value_code != '[PASS]':
                    return (value_code, [])
                self.mopped_units.internal_set(min(90, mopped + worked * water))
            self.progress_minutes.internal_set(new_progress)
            self.remaining_minutes.internal_set(total - new_progress)
            boundaries = {'vacuum': ['cleaning', 'returning', 'dust_collection', 'charging'], 'mop': ['cleaning', 'returning', 'mop_washing', 'drying', 'charging'], 'vacuum_and_mop': ['cleaning', 'returning', 'dust_collection', 'mop_washing', 'drying', 'charging'], 'recharge': ['returning', 'charging']}
            lengths = {'vacuum': [30, 35, 38, 68], 'mop': [30, 35, 40, 70, 100], 'vacuum_and_mop': [30, 35, 38, 43, 73, 103], 'recharge': [5, 35]}
            selected = boundaries[mode][-1]
            for name, boundary in zip(boundaries[mode], lengths[mode]):
                if new_progress < boundary:
                    selected = name
                    break
            self.phase.internal_set(selected)
            if new_progress >= total:
                self.status.internal_set('completed')
                self.phase.internal_set('completed')
                self.remaining_minutes.internal_set(0)
            self.base_state.internal_set(selected if selected in ('dust_collection', 'mop_washing', 'drying') else 'idle')
        status = self.status.value
        phase = self.phase.value
        noise = 0
        if powered is True and status == 'running':
            noise = {'cleaning': 20, 'returning': 20, 'dust_collection': 45, 'mop_washing': 25, 'drying': 15, 'charging': 0}.get(phase, 0)
            if phase == 'cleaning' and mode in ('vacuum', 'vacuum_and_mop'):
                suction_code, suction = self.suction_level.get()
                if suction_code != '[PASS]':
                    return (suction_code, [])
                noise = 20 + 5 * suction
        return ('[PASS]', [{'trigger': 'tick', 'source': context['object_id'], 'target': context['space_id'], 'function': 'set_contribution', 'parameters': {'property': 'noise', 'value': noise, 'unit': 'dBA'}}])

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        Power loss changes a running status to paused and preserves all progress, phases and outputs; power-on never resumes it. For a new start, recharge, resume or return-to-base transition into running, establish started_at_minute as the current elapsed world minute minus progress_minutes. Identify a new or rebased run by a non-running previous status, a changed operation_mode, a changed phase, or changed progress_minutes; an unchanged already-running process keeps its origin. These origin updates are reachable through the process actions, not through set_power. Emit no Space effects here.

    Effect properties:
    - power: Read process transition input or internally updated status/origin.
    - status: Read process transition input or internally updated status/origin.
    - operation_mode: Read process transition input or internally updated status/origin.
    - phase: Read process transition input or internally updated status/origin.
    - progress_minutes: Read process transition input or internally updated status/origin.
    - started_at_minute: Read process transition input or internally updated status/origin.
        """
        pre = context['pre_state']['objects'][context['object_id']]['properties']
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, [])
        status = self.status.value
        if powered is not True:
            if pre['status'] == 'running':
                code = self.status.internal_set('paused')
                if code != '[PASS]':
                    return (code, [])
            return ('[PASS]', [])
        if status == 'running' and (pre['status'] != 'running' or pre['power'] is not True or pre['operation_mode'] != self.operation_mode.get()[1] or (pre['phase'] != self.phase.get()[1]) or (pre['progress_minutes'] != self.progress_minutes.get()[1])):
            progress_code, progress = self.progress_minutes.get()
            if progress_code != '[PASS]':
                return (progress_code, [])
            code = self.started_at_minute.internal_set(context['time_state']['elapsed_minutes'] - progress)
            if code != '[PASS]':
                return (code, [])
        return ('[PASS]', [])
