# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Charging:
    """
    Charging
    Description: Charging control module. Supports opening and closing the charging-port cover, starting and ending charging, and setting the charge limit and charging speed level. Once charging starts, the vehicle battery level changes over time.
    Version: 1.0.0
    Base: -
    """

    PROCESS = {'mode_property': 'speed_level', 'start_function': 'start_charging', 'modes': {'low': [{'phase': 'charging', 'minutes': 400}], 'normal': [{'phase': 'charging', 'minutes': 200}], 'high': [{'phase': 'charging', 'minutes': 100}]}}

    def __init__(self, port_cover_open: bool = None, charge_limit: int = None, speed_level: str = None, battery_percent: int = None, status: str = None, phase: str = None, remaining_minutes: int = None, started_at_minute: int = None, progress_minutes: int = None) -> None:
        # define properties
        self.port_cover_open = BoolProperty(
            name='port_cover_open',
            description='Whether the charging-port cover is open.',
            default=False,
            mode=2
        )
        self.charge_limit = IntProperty(
            name='charge_limit',
            description='Battery percentage at which further battery increase is capped during charging.',
            default=80,
            unit='%',
            minimum=50,
            maximum=100,
            step=1,
            step_origin=50
        )
        self.speed_level = StringProperty(
            name='speed_level',
            description='Charging speed level used by the current or next charging cycle.',
            default='normal',
            choices=['low', 'normal', 'high']
        )
        self.battery_percent = IntProperty(
            name='battery_percent',
            description='Current vehicle battery level. It is changed internally by the charging process.',
            default=20,
            mode=2,
            unit='%',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.status = StringProperty(
            name='status',
            description='Charging-process status.',
            default='idle',
            mode=2,
            choices=['idle', 'running', 'paused', 'completed']
        )
        self.phase = StringProperty(
            name='phase',
            description='Current charging-process phase.',
            default='idle',
            mode=2,
            choices=['idle', 'charging', 'completed']
        )
        self.remaining_minutes = IntProperty(
            name='remaining_minutes',
            description='Whole minutes remaining in the active charging cycle.',
            default=0,
            mode=2,
            unit='minute',
            minimum=0,
            maximum=400,
            step=1,
            step_origin=0
        )
        self.started_at_minute = IntProperty(
            name='started_at_minute',
            description='Simulation elapsed-minute value corresponding to the beginning of the current charging cycle.',
            default=0,
            mode=2,
            unit='minute',
            minimum=0,
            step=1,
            step_origin=0
        )
        self.progress_minutes = IntProperty(
            name='progress_minutes',
            description='Whole minutes of progress accumulated in the current charging cycle.',
            default=0,
            mode=2,
            unit='minute',
            minimum=0,
            maximum=400,
            step=1,
            step_origin=0
        )

        # initialize properties
        if port_cover_open is not None: code = self.port_cover_open.internal_set(port_cover_open)
        if charge_limit is not None: code = self.charge_limit.internal_set(charge_limit)
        if speed_level is not None: code = self.speed_level.internal_set(speed_level)
        if battery_percent is not None: code = self.battery_percent.internal_set(battery_percent)
        if status is not None: code = self.status.internal_set(status)
        if phase is not None: code = self.phase.internal_set(phase)
        if remaining_minutes is not None: code = self.remaining_minutes.internal_set(remaining_minutes)
        if started_at_minute is not None: code = self.started_at_minute.internal_set(started_at_minute)
        if progress_minutes is not None: code = self.progress_minutes.internal_set(progress_minutes)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_port_cover_open(self) -> tuple[str, dict]:
        """
        Return whether the charging-port cover is open without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- port_cover_open: Whether the charging-port cover is open. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.port_cover_open.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'port_cover_open': value
        }
        return code, response

    def open_port_cover(self) -> tuple[str, dict]:
        """
        Open the charging-port cover. Calling this action when the cover is already open leaves it open.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.port_cover_open.internal_set(True)
        if code != '[PASS]':
            return (code, {})
        response = {}
        return code, response

    def close_port_cover(self) -> tuple[str, dict]:
        """
        Close the charging-port cover only when charging is idle or completed. An attempt to close it while charging is rejected and leaves state unchanged.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The charging-port cover cannot be closed while charging is active.
        """
        code, status = self.status.get()
        if code != '[PASS]':
            return (code, {})
        if status not in ('idle', 'completed'):
            return ('[PRECONDITION_FAILED]', {})
        code = self.port_cover_open.internal_set(False)
        if code != '[PASS]':
            return (code, {})
        response = {}
        return code, response

    def get_charge_limit(self) -> tuple[str, dict]:
        """
        Return the configured charging limit as a battery percentage.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- charge_limit: Configured charging limit percentage. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.charge_limit.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'charge_limit': value
        }
        return code, response

    def set_charge_limit(self, value: int) -> tuple[str, dict]:
        """
        Set the charge limit to an integer from 50 through 100 percent while charging is idle or completed. Invalid values or attempts made while charging leave state unchanged.

        Args:
        - value: Desired charge limit percentage. (min=50, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The charge limit cannot be changed while charging is active.
        - INVALID_INPUT_ERROR: Charge limit must be an integer from 50 through 100.
        """
        if type(value) is not int or value < 50 or value > 100:
            return ('[INVALID_INPUT_ERROR]', {})
        code, status = self.status.get()
        if code != '[PASS]':
            return (code, {})
        if status not in ('idle', 'completed'):
            return ('[PRECONDITION_FAILED]', {})
        code = self.charge_limit.set(value)
        if code != '[PASS]':
            return (code, {})
        response = {}
        return code, response

    def get_speed_level(self) -> tuple[str, dict]:
        """
        Return the selected charging speed level.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- speed_level: Selected charging speed: low, normal, or high. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.speed_level.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'speed_level': value
        }
        return code, response

    def set_speed_level(self, value: str) -> tuple[str, dict]:
        """
        Select low, normal, or high charging speed while charging is idle or completed. Invalid values or attempts made while charging leave state unchanged.

        Args:
        - value: Desired charging speed level. (choices=['low', 'normal', 'high'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The charging speed cannot be changed while charging is active.
        - INVALID_INPUT_ERROR: Charging speed must be low, normal, or high.
        """
        if type(value) is not str or value not in ('low', 'normal', 'high'):
            return ('[INVALID_INPUT_ERROR]', {})
        code, status = self.status.get()
        if code != '[PASS]':
            return (code, {})
        if status not in ('idle', 'completed'):
            return ('[PRECONDITION_FAILED]', {})
        code = self.speed_level.set(value)
        if code != '[PASS]':
            return (code, {})
        response = {}
        return code, response

    def get_battery_percent(self) -> tuple[str, dict]:
        """
        Return the current vehicle battery percentage without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- battery_percent: Current battery percentage. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.battery_percent.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'battery_percent': value
        }
        return code, response

    def get_status(self) -> tuple[str, dict]:
        """
        Return the charging-process status without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- status: Charging-process status. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.status.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'status': value
        }
        return code, response

    def get_phase(self) -> tuple[str, dict]:
        """
        Return the current charging-process phase without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- phase: Current charging-process phase. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.phase.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'phase': value
        }
        return code, response

    def get_remaining_minutes(self) -> tuple[str, dict]:
        """
        Return the whole minutes remaining in the active charging cycle.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- remaining_minutes: Whole minutes remaining in the charging cycle. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.remaining_minutes.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'remaining_minutes': value
        }
        return code, response

    def get_started_at_minute(self) -> tuple[str, dict]:
        """
        Return the simulation elapsed-minute value associated with the start of the current charging cycle.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- started_at_minute: Simulation elapsed minute at which the charging cycle began. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.started_at_minute.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'started_at_minute': value
        }
        return code, response

    def get_progress_minutes(self) -> tuple[str, dict]:
        """
        Return the whole minutes of progress accumulated in the current charging cycle.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- progress_minutes: Whole minutes of charging-cycle progress. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.progress_minutes.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'progress_minutes': value
        }
        return code, response

    def start_charging(self, speed_level: str) -> tuple[str, dict]:
        """
        Start a new charging cycle at the supplied speed. The operation succeeds only when status is idle or completed, the charging-port cover is open, and battery_percent is below charge_limit. Starting initializes progress to zero and selects the supplied speed. Invalid or disallowed requests leave all state unchanged.

        Args:
        - speed_level: Charging speed for the new cycle. (choices=['low', 'normal', 'high'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: Charging requires an open port cover, an idle or completed process, and a battery level below the charge limit.
        - INVALID_INPUT_ERROR: Charging speed must be low, normal, or high.
        """
        if type(speed_level) is not str or speed_level not in ('low', 'normal', 'high'):
            return ('[INVALID_INPUT_ERROR]', {})

        status_code, status = self.status.get()
        if status_code != '[PASS]':
            return (status_code, {})
        cover_code, cover_open = self.port_cover_open.get()
        if cover_code != '[PASS]':
            return (cover_code, {})
        battery_code, battery = self.battery_percent.get()
        if battery_code != '[PASS]':
            return (battery_code, {})
        limit_code, limit = self.charge_limit.get()
        if limit_code != '[PASS]':
            return (limit_code, {})

        if status not in ('idle', 'completed') or not cover_open or battery >= limit:
            return ('[PRECONDITION_FAILED]', {})

        durations = {
            'low': 400,
            'normal': 200,
            'high': 100
        }

        code = self.speed_level.set(speed_level)
        if code != '[PASS]':
            return (code, {})
        code = self.progress_minutes.internal_set(0)
        if code != '[PASS]':
            return (code, {})
        code = self.remaining_minutes.internal_set(durations[speed_level])
        if code != '[PASS]':
            return (code, {})
        code = self.phase.internal_set('charging')
        if code != '[PASS]':
            return (code, {})
        code = self.status.internal_set('running')
        if code != '[PASS]':
            return (code, {})

        response = {}
        return code, response

    def end_charging(self) -> tuple[str, dict]:
        """
        End an active charging cycle. This preserves battery_percent and all charging settings, clears process timing state, and returns status and phase to idle. The action is rejected unless charging is running.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: Charging can be ended only while the charging process is running.
        """
        code, status = self.status.get()
        if code != '[PASS]':
            return (code, {})
        if status != 'running':
            return ('[PRECONDITION_FAILED]', {})

        code = self.remaining_minutes.internal_set(0)
        if code != '[PASS]':
            return (code, {})
        code = self.started_at_minute.internal_set(0)
        if code != '[PASS]':
            return (code, {})
        code = self.progress_minutes.internal_set(0)
        if code != '[PASS]':
            return (code, {})
        code = self.phase.internal_set('idle')
        if code != '[PASS]':
            return (code, {})
        code = self.status.internal_set('idle')
        if code != '[PASS]':
            return (code, {})

        response = {}
        return code, response

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        While status is running, advance charging progress from the cycle start time and reduce remaining_minutes. Increase battery_percent by one point for each four elapsed progress minutes at low speed, each two elapsed progress minutes at normal speed, or each elapsed progress minute at high speed, without exceeding charge_limit. At the exact end of the selected cycle duration, set status and phase to completed and remaining_minutes to zero. Idle, paused, and completed states do not advance.

    Effect properties:
    - status: Determines whether the charging process advances.
    - phase: Tracks the active charging phase and completion.
    - speed_level: Determines cycle duration and battery increase rate.
    - charge_limit: Caps battery growth during the charging cycle.
    - battery_percent: Battery level updated by elapsed charging progress.
    - remaining_minutes: Tracks the remaining duration of the charging cycle.
    - started_at_minute: Provides the time origin used to calculate deterministic progress.
    - progress_minutes: Tracks elapsed charging-cycle progress and battery increments.
        """
        status_code, status = self.status.get()
        if status_code != '[PASS]':
            return (status_code, [])
        if status != 'running':
            return ('[PASS]', [])

        phase_code, phase = self.phase.get()
        if phase_code != '[PASS]':
            return (phase_code, [])
        speed_code, speed = self.speed_level.get()
        if speed_code != '[PASS]':
            return (speed_code, [])
        limit_code, charge_limit = self.charge_limit.get()
        if limit_code != '[PASS]':
            return (limit_code, [])
        battery_code, battery = self.battery_percent.get()
        if battery_code != '[PASS]':
            return (battery_code, [])
        remaining_code, remaining = self.remaining_minutes.get()
        if remaining_code != '[PASS]':
            return (remaining_code, [])
        started_code, started = self.started_at_minute.get()
        if started_code != '[PASS]':
            return (started_code, [])
        progress_code, old_progress = self.progress_minutes.get()
        if progress_code != '[PASS]':
            return (progress_code, [])

        durations = {
            'low': 400,
            'normal': 200,
            'high': 100
        }
        minutes_per_point = {
            'low': 4,
            'normal': 2,
            'high': 1
        }

        duration = durations[speed]
        elapsed_minute = context['time_state']['elapsed_minutes']
        calculated_progress = elapsed_minute - started
        if calculated_progress < old_progress:
            calculated_progress = old_progress
        new_progress = min(duration, calculated_progress)
        interval = minutes_per_point[speed]
        gained_points = (
            new_progress // interval
            - old_progress // interval
        )
        new_battery = min(charge_limit, battery + gained_points)
        new_remaining = max(duration - new_progress, 0)
        completed = new_progress >= duration

        if new_battery != battery:
            code = self.battery_percent.internal_set(new_battery)
            if code != '[PASS]':
                return (code, [])
        if new_progress != old_progress:
            code = self.progress_minutes.internal_set(new_progress)
            if code != '[PASS]':
                return (code, [])
        if new_remaining != remaining:
            code = self.remaining_minutes.internal_set(new_remaining)
            if code != '[PASS]':
                return (code, [])

        if completed:
            if phase != 'completed':
                code = self.phase.internal_set('completed')
                if code != '[PASS]':
                    return (code, [])
            code = self.status.internal_set('completed')
            if code != '[PASS]':
                return (code, [])

        return ('[PASS]', [])

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        When a successful action transitions the charging process into running, align started_at_minute with the current simulation time and accumulated progress so subsequent minute ticks advance from the correct time origin. Actions that do not transition the process into running leave the timing origin unchanged.

    Effect properties:
    - status: Identifies whether the charging process has transitioned into running.
    - started_at_minute: Stores the time origin used for deterministic charging progress.
    - progress_minutes: Offsets the time origin by any progress already accumulated.
        """
        status_code, status = self.status.get()
        if status_code != '[PASS]':
            return (status_code, [])

        previous_properties = context['pre_state']['objects'][context['object_id']]['properties']
        previous_status = previous_properties['status']

        if status != 'running' or previous_status == 'running':
            return ('[PASS]', [])

        progress_code, progress = self.progress_minutes.get()
        if progress_code != '[PASS]':
            return (progress_code, [])

        started = context['time_state']['elapsed_minutes'] - progress
        code = self.started_at_minute.internal_set(started)
        if code != '[PASS]':
            return (code, [])
        return ('[PASS]', [])