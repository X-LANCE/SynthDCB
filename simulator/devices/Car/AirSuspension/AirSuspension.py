# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class AirSuspension:
    """
    AirSuspension
    Description: Air suspension module with user-adjustable height. Supports selecting a target height from the fixed capability set and querying actual height, adjustment progress, and failure feedback.
    Version: 1.0.0
    Base: -
    """

    PROCESS = {'mode_property': 'target_height', 'start_function': 'select_height', 'modes': {'low': [{'phase': 'adjusting', 'minutes': 1}], 'normal': [{'phase': 'adjusting', 'minutes': 1}], 'high': [{'phase': 'adjusting', 'minutes': 1}]}}

    def __init__(self, target_height: str = None, actual_height: str = None, status: str = None, phase: str = None, remaining_minutes: int = None, started_at_minute: int = None, progress_minutes: int = None, failure_feedback: str = None) -> None:
        # define properties
        self.target_height = StringProperty(
            name='target_height',
            description='Height selected for the current or most recently started adjustment.',
            default='normal',
            mode=2,
            choices=['low', 'normal', 'high']
        )
        self.actual_height = StringProperty(
            name='actual_height',
            description='Current achieved suspension height. It changes to target_height when an adjustment completes.',
            default='normal',
            mode=2,
            choices=['low', 'normal', 'high']
        )
        self.status = StringProperty(
            name='status',
            description='Current lifecycle status of the height-adjustment process.',
            default='idle',
            mode=2,
            choices=['idle', 'running', 'paused', 'completed']
        )
        self.phase = StringProperty(
            name='phase',
            description='Current phase of the height-adjustment process.',
            default='idle',
            mode=2,
            choices=['idle', 'adjusting', 'completed']
        )
        self.remaining_minutes = IntProperty(
            name='remaining_minutes',
            description='Whole simulated minutes remaining in the current adjustment.',
            default=0,
            mode=2,
            unit='min',
            minimum=0,
            maximum=1,
            step=1,
            step_origin=0
        )
        self.started_at_minute = IntProperty(
            name='started_at_minute',
            description='Simulation elapsed-minute timestamp from which progress for the current adjustment is measured.',
            default=0,
            mode=2,
            unit='min',
            minimum=0,
            step=1,
            step_origin=0
        )
        self.progress_minutes = IntProperty(
            name='progress_minutes',
            description='Whole simulated minutes completed in the current or most recently completed adjustment.',
            default=0,
            mode=2,
            unit='min',
            minimum=0,
            maximum=1,
            step=1,
            step_origin=0
        )
        self.failure_feedback = StringProperty(
            name='failure_feedback',
            description='Failure feedback for the adjustment mechanism. The value is none when no deterministic mechanism failure has been reported.',
            default='none',
            mode=2,
            choices=['none']
        )

        # initialize properties
        if target_height is not None: code = self.target_height.internal_set(target_height)
        if actual_height is not None: code = self.actual_height.internal_set(actual_height)
        if status is not None: code = self.status.internal_set(status)
        if phase is not None: code = self.phase.internal_set(phase)
        if remaining_minutes is not None: code = self.remaining_minutes.internal_set(remaining_minutes)
        if started_at_minute is not None: code = self.started_at_minute.internal_set(started_at_minute)
        if progress_minutes is not None: code = self.progress_minutes.internal_set(progress_minutes)
        if failure_feedback is not None: code = self.failure_feedback.internal_set(failure_feedback)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_target_height(self) -> tuple[str, dict]:
        """
        Return the selected target suspension height without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- target_height: Selected target height: low, normal, or high. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.target_height.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'target_height': value})

    def get_actual_height(self) -> tuple[str, dict]:
        """
        Return the currently achieved suspension height without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- actual_height: Current achieved height: low, normal, or high. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.actual_height.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'actual_height': value})

    def get_status(self) -> tuple[str, dict]:
        """
        Return the lifecycle status of the height-adjustment process.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- status: Adjustment status: idle, running, paused, or completed. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.status.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'status': value})

    def get_phase(self) -> tuple[str, dict]:
        """
        Return the current phase of the height-adjustment process.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- phase: Current phase: idle, adjusting, or completed. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.phase.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'phase': value})

    def get_remaining_minutes(self) -> tuple[str, dict]:
        """
        Return the whole simulated minutes remaining in the current adjustment.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- remaining_minutes: Whole simulated minutes remaining. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.remaining_minutes.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'remaining_minutes': value})

    def get_started_at_minute(self) -> tuple[str, dict]:
        """
        Return the simulation elapsed-minute timestamp used as the origin of the current adjustment.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- started_at_minute: Simulation elapsed-minute timestamp for the adjustment origin. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.started_at_minute.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'started_at_minute': value})

    def get_progress_minutes(self) -> tuple[str, dict]:
        """
        Return the whole simulated minutes completed in the current or most recently completed adjustment.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- progress_minutes: Whole simulated adjustment minutes completed. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.progress_minutes.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'progress_minutes': value})

    def get_failure_feedback(self) -> tuple[str, dict]:
        """
        Return current adjustment failure feedback. This deterministic model returns none unless a modeled mechanism failure is present.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- failure_feedback: Current mechanism failure feedback. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.failure_feedback.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'failure_feedback': value})

    def select_height(self, height: str) -> tuple[str, dict]:
        """
        Start a one-minute adjustment toward low, normal, or high suspension height. The action is allowed only while the previous process is idle or completed. Starting sets progress to zero and actual_height remains unchanged until completion. Invalid targets or a failed status precondition leave all state unchanged.

        Args:
        - height:  (choices=['low', 'normal', 'high'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - INVALID_INPUT_ERROR: Height must be low, normal, or high.
        - PRECONDITION_FAILED: A new suspension-height adjustment cannot start while another adjustment is running or paused.
        """
        if type(height) is not str or height not in ('low', 'normal', 'high'):
            return ('[INVALID_INPUT_ERROR]', {})

        status_code, current_status = self.status.get()
        if status_code != '[PASS]':
            return (status_code, {})
        if current_status not in ('idle', 'completed'):
            return ('[PRECONDITION_FAILED]', {})

        code = self.target_height.internal_set(height)
        if code != '[PASS]':
            return (code, {})

        code = self.progress_minutes.internal_set(0)
        if code != '[PASS]':
            return (code, {})

        code = self.remaining_minutes.internal_set(1)
        if code != '[PASS]':
            return (code, {})

        code = self.phase.internal_set('adjusting')
        if code != '[PASS]':
            return (code, {})

        code = self.status.internal_set('running')
        if code != '[PASS]':
            return (code, {})

        return ('[PASS]', {})

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        After a successful action transitions the height-adjustment process into running, set started_at_minute to the current simulation elapsed minute minus progress_minutes. Actions that do not transition the process into running leave process timing state unchanged.

    Effect properties:
    - status: Indicates whether the process has transitioned into the running state.
    - started_at_minute: Stores the elapsed-minute origin used to calculate adjustment progress.
    - progress_minutes: Offsets the timing origin so any retained process progress is preserved.
        """
        status_code, current_status = self.status.get()
        if status_code != '[PASS]':
            return (status_code, [])

        previous_status = context['pre_state']['objects'][context['object_id']]['properties']['status']
        if current_status != 'running' or previous_status == 'running':
            return ('[PASS]', [])

        progress_code, progress = self.progress_minutes.get()
        if progress_code != '[PASS]':
            return (progress_code, [])

        elapsed_minutes = context['time_state']['elapsed_minutes']
        started_at = elapsed_minutes - progress
        code = self.started_at_minute.internal_set(started_at)
        if code != '[PASS]':
            return (code, [])

        return ('[PASS]', [])

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        While an adjustment is running, advance its progress using the declared one-minute adjusting phase. At the exact completion boundary, set actual_height to target_height, set remaining_minutes to zero, and mark the phase and status completed. Idle, paused, and completed adjustments do not advance.

    Effect properties:
    - target_height: Provides the height assigned to actual_height when adjustment completes.
    - actual_height: Stores the currently achieved suspension height.
    - status: Determines whether the adjustment advances and records completion.
    - phase: Records the active adjusting phase or completed phase.
    - remaining_minutes: Tracks whole simulated minutes remaining.
    - started_at_minute: Provides the elapsed-minute origin for deterministic progress.
    - progress_minutes: Tracks whole simulated minutes completed.
        """
        status_code, current_status = self.status.get()
        if status_code != '[PASS]':
            return (status_code, [])
        if current_status != 'running':
            return ('[PASS]', [])

        started_code, started_at = self.started_at_minute.get()
        if started_code != '[PASS]':
            return (started_code, [])

        progress_code, current_progress = self.progress_minutes.get()
        if progress_code != '[PASS]':
            return (progress_code, [])

        elapsed_minutes = context['time_state']['elapsed_minutes']
        elapsed_progress = max(0, elapsed_minutes - started_at)
        new_progress = min(1, max(current_progress, elapsed_progress))
        new_remaining = max(1 - new_progress, 0)

        if new_progress < 1:
            if new_progress != current_progress:
                code = self.progress_minutes.internal_set(new_progress)
                if code != '[PASS]':
                    return (code, [])

            code = self.remaining_minutes.internal_set(new_remaining)
            if code != '[PASS]':
                return (code, [])

            code = self.phase.internal_set('adjusting')
            if code != '[PASS]':
                return (code, [])

            return ('[PASS]', [])

        target_code, target = self.target_height.get()
        if target_code != '[PASS]':
            return (target_code, [])

        code = self.progress_minutes.internal_set(1)
        if code != '[PASS]':
            return (code, [])

        code = self.remaining_minutes.internal_set(0)
        if code != '[PASS]':
            return (code, [])

        code = self.actual_height.internal_set(target)
        if code != '[PASS]':
            return (code, [])

        code = self.phase.internal_set('completed')
        if code != '[PASS]':
            return (code, [])

        code = self.status.internal_set('completed')
        if code != '[PASS]':
            return (code, [])

        return ('[PASS]', [])