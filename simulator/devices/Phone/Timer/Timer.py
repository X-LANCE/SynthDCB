# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Timer:
    """
    Timer
    Description: Countdown timer application, placed in Application. Duration is 1–60 whole minutes. Supports start, pause, resume, cancel, and queries of read-only progress; duration cannot be changed while running or paused. Reaching zero completes the timer and leaves it in the completed state. Resume preserves elapsed time; cancel resets it to zero.
    Version: 1.0.0
    Base: -
    """

    PROCESS = {'mode_property': 'mode', 'start_function': 'start', 'pause_function': 'pause', 'resume_function': 'resume', 'modes': {'countdown': [{'phase': 'countdown', 'minutes': {'property': 'duration_minutes'}}]}}

    def __init__(self, duration_minutes: int = None, mode: str = None, status: str = None, phase: str = None, remaining_minutes: int = None, started_at_minute: int = None, progress_minutes: int = None) -> None:
        # define properties
        self.duration_minutes = IntProperty(
            name='duration_minutes',
            description='Configured countdown duration in whole minutes. This setting is frozen while the timer is running or paused.',
            default=3,
            unit='minutes',
            minimum=1,
            maximum=60,
            step=1,
            step_origin=1
        )
        self.mode = StringProperty(
            name='mode',
            description='Selected countdown process mode.',
            default='countdown',
            mode=2,
            choices=['countdown']
        )
        self.status = StringProperty(
            name='status',
            description='Current countdown process status.',
            default='idle',
            mode=2,
            choices=['idle', 'running', 'paused', 'completed']
        )
        self.phase = StringProperty(
            name='phase',
            description='Current countdown phase.',
            default='idle',
            mode=2,
            choices=['idle', 'countdown', 'completed']
        )
        self.remaining_minutes = IntProperty(
            name='remaining_minutes',
            description='Whole minutes remaining in the current countdown.',
            default=0,
            mode=2,
            unit='minutes',
            minimum=0,
            maximum=60,
            step=1,
            step_origin=0
        )
        self.started_at_minute = IntProperty(
            name='started_at_minute',
            description='Elapsed world minute used as the monotonic origin for the current countdown progress.',
            default=0,
            mode=2,
            unit='minutes',
            minimum=0,
            step=1,
            step_origin=0
        )
        self.progress_minutes = IntProperty(
            name='progress_minutes',
            description='Whole minutes elapsed in the current countdown.',
            default=0,
            mode=2,
            unit='minutes',
            minimum=0,
            maximum=60,
            step=1,
            step_origin=0
        )

        # initialize properties
        if duration_minutes is not None: code = self.duration_minutes.internal_set(duration_minutes)
        if mode is not None: code = self.mode.internal_set(mode)
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

    def get_duration_minutes(self) -> tuple[str, dict]:
        """
        Return the configured countdown duration in whole minutes.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- duration_minutes: Configured countdown duration in whole minutes. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.duration_minutes.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'duration_minutes': value
        }
        return code, response

    def set_duration_minutes(self, duration_minutes: int) -> tuple[str, dict]:
        """
        Set the countdown duration to a whole number from 1 through 60 minutes. The duration may be changed only while the timer is idle or completed. Invalid values or process states leave all properties unchanged.

        Args:
        - duration_minutes:  (min=1, max=60)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The duration cannot be changed while the timer is running or paused.
        """
        code, status = self.status.get()
        if code != '[PASS]':
            return code, {}
        if status not in ('idle', 'completed'):
            return '[PRECONDITION_FAILED]', {}
        code = self.duration_minutes.set(duration_minutes)
        return code, {}

    def get_mode(self) -> tuple[str, dict]:
        """
        Return the selected countdown process mode.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- mode: Selected countdown process mode. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.mode.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'mode': value
        }
        return code, response

    def get_status(self) -> tuple[str, dict]:
        """
        Return the current countdown process status.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- status: Current countdown process status. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.status.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'status': value
        }
        return code, response

    def get_phase(self) -> tuple[str, dict]:
        """
        Return the current countdown phase.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- phase: Current countdown phase. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.phase.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'phase': value
        }
        return code, response

    def get_remaining_minutes(self) -> tuple[str, dict]:
        """
        Return the whole number of minutes remaining in the countdown.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- remaining_minutes: Whole minutes remaining in the countdown. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.remaining_minutes.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'remaining_minutes': value
        }
        return code, response

    def get_started_at_minute(self) -> tuple[str, dict]:
        """
        Return the elapsed world minute used as the monotonic origin for the current countdown progress.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- started_at_minute: Elapsed world minute used as the origin for countdown progress. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.started_at_minute.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'started_at_minute': value
        }
        return code, response

    def get_progress_minutes(self) -> tuple[str, dict]:
        """
        Return the whole number of minutes elapsed in the current countdown.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- progress_minutes: Whole minutes elapsed in the countdown. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.progress_minutes.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'progress_minutes': value
        }
        return code, response

    def start(self, mode: str) -> tuple[str, dict]:
        """
        Start a new countdown from idle or completed state. Starting resets progress to zero, initializes remaining time from the configured duration, and enters the countdown phase. Calls in other states fail without changing any property.

        Args:
        - mode:  (choices=['countdown'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: A new countdown can start only while the timer is idle or completed.
        """
        code, status = self.status.get()
        if code != '[PASS]':
            return code, {}
        if status not in ('idle', 'completed'):
            return '[PRECONDITION_FAILED]', {}

        code, duration = self.duration_minutes.get()
        if code != '[PASS]':
            return code, {}

        code = self.mode.internal_set(mode)
        if code != '[PASS]':
            return code, {}

        code = self.phase.internal_set('countdown')
        if code != '[PASS]':
            return code, {}

        code = self.remaining_minutes.internal_set(duration)
        if code != '[PASS]':
            return code, {}

        code = self.started_at_minute.internal_set(0)
        if code != '[PASS]':
            return code, {}

        code = self.progress_minutes.internal_set(0)
        if code != '[PASS]':
            return code, {}

        code = self.status.internal_set('running')
        if code != '[PASS]':
            return code, {}

        return '[PASS]', {}

    def pause(self) -> tuple[str, dict]:
        """
        Pause a running countdown while preserving its elapsed progress and remaining time. The call fails without changing state unless the timer is running.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The timer can be paused only while running.
        """
        code, status = self.status.get()
        if code != '[PASS]':
            return code, {}
        if status != 'running':
            return '[PRECONDITION_FAILED]', {}

        code = self.status.internal_set('paused')
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {}

    def resume(self) -> tuple[str, dict]:
        """
        Resume a paused countdown without resetting its elapsed progress or remaining time. The call fails without changing state unless the timer is paused.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The timer can be resumed only while paused.
        """
        code, status = self.status.get()
        if code != '[PASS]':
            return code, {}
        if status != 'paused':
            return '[PRECONDITION_FAILED]', {}

        code = self.started_at_minute.internal_set(0)
        if code != '[PASS]':
            return code, {}

        code = self.status.internal_set('running')
        if code != '[PASS]':
            return code, {}

        return '[PASS]', {}

    def cancel(self) -> tuple[str, dict]:
        """
        Cancel a running, paused, or completed countdown and reset its process state to idle with zero progress and zero remaining minutes. The call fails without changing state when the timer is already idle.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: There is no active or completed countdown to cancel while the timer is idle.
        """
        code, status = self.status.get()
        if code != '[PASS]':
            return code, {}
        if status == 'idle':
            return '[PRECONDITION_FAILED]', {}
        if status not in ('running', 'paused', 'completed'):
            return '[PRECONDITION_FAILED]', {}

        code = self.phase.internal_set('idle')
        if code != '[PASS]':
            return code, {}

        code = self.remaining_minutes.internal_set(0)
        if code != '[PASS]':
            return code, {}

        code = self.started_at_minute.internal_set(0)
        if code != '[PASS]':
            return code, {}

        code = self.progress_minutes.internal_set(0)
        if code != '[PASS]':
            return code, {}

        code = self.status.internal_set('idle')
        if code != '[PASS]':
            return code, {}

        return '[PASS]', {}

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        While the countdown is running, advances elapsed progress according to monotonic elapsed whole minutes and the configured duration. Remaining time never becomes negative. At the exact duration boundary, the timer enters completed status and phase with zero remaining minutes. Idle, paused, and completed timers do not advance.

    Effect properties:
    - duration_minutes: Configured duration that determines the countdown completion boundary.
    - mode: Selected process mode used to identify the countdown schedule.
    - status: Current process status used to determine whether progress advances.
    - phase: Current process phase updated when the countdown completes.
    - remaining_minutes: Whole minutes remaining in the countdown.
    - started_at_minute: Monotonic elapsed-minute origin used to calculate current progress.
    - progress_minutes: Whole minutes already elapsed in the countdown.
        """
        code, status = self.status.get()
        if code != '[PASS]':
            return code, []
        if status != 'running':
            return '[PASS]', []

        code, duration = self.duration_minutes.get()
        if code != '[PASS]':
            return code, []

        code, current_progress = self.progress_minutes.get()
        if code != '[PASS]':
            return code, []

        code, origin = self.started_at_minute.get()
        if code != '[PASS]':
            return code, []

        elapsed_minutes = context['time_state']['elapsed_minutes']
        calculated_progress = elapsed_minutes - origin
        progress = min(duration, max(current_progress, calculated_progress))
        remaining = max(duration - progress, 0)

        code = self.progress_minutes.internal_set(progress)
        if code != '[PASS]':
            return code, []

        code = self.remaining_minutes.internal_set(remaining)
        if code != '[PASS]':
            return code, []

        if progress == duration:
            code = self.phase.internal_set('completed')
            if code != '[PASS]':
                return code, []

            code = self.status.internal_set('completed')
            if code != '[PASS]':
                return code, []

        return '[PASS]', []

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        When a successful start or resume action transitions the timer into running status, records the monotonic elapsed-minute origin so accumulated progress is preserved. Other successful actions do not advance countdown time.

    Effect properties:
    - duration_minutes: Configured countdown duration.
    - mode: Selected countdown process mode.
    - status: Current status used to detect a transition into running.
    - phase: Current countdown phase.
    - remaining_minutes: Whole minutes remaining after the successful action.
    - started_at_minute: Monotonic elapsed-minute origin maintained for running progress.
    - progress_minutes: Accumulated progress preserved when the timer resumes.
        """
        previous_properties = context['pre_state']['objects'][context['object_id']]['properties']

        code, status = self.status.get()
        if code != '[PASS]':
            return code, []

        code, progress = self.progress_minutes.get()
        if code != '[PASS]':
            return code, []

        if status == 'running' and previous_properties['status'] != 'running':
            origin = context['time_state']['elapsed_minutes'] - progress
            code = self.started_at_minute.internal_set(origin)
            if code != '[PASS]':
                return code, []

        return '[PASS]', []