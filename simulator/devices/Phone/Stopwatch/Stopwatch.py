# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Stopwatch:
    """
    Stopwatch
    Description: Stopwatch application, placed in Application. Supports start, pause, resume, reset, and queries. While running, elapsed time accumulates each minute; while paused, it is retained. Reset clears elapsed time and returns to idle. There is no preset completion time.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, status: str = None, elapsed_minutes: int = None) -> None:
        # define properties
        self.status = StringProperty(
            name='status',
            description='Current stopwatch state. The state changes only through stopwatch actions.',
            default='idle',
            mode=2,
            choices=['idle', 'running', 'paused']
        )
        self.elapsed_minutes = IntProperty(
            name='elapsed_minutes',
            description='Total number of whole minutes accumulated by the stopwatch.',
            default=0,
            mode=2,
            unit='minutes',
            minimum=0,
            step=1,
            step_origin=0
        )

        # initialize properties
        if status is not None: code = self.status.internal_set(status)
        if elapsed_minutes is not None: code = self.elapsed_minutes.internal_set(elapsed_minutes)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_status(self) -> tuple[str, dict]:
        """
        Return the current stopwatch status without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- status: Current stopwatch status: idle, running, or paused. (type=string)

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

    def get_elapsed_minutes(self) -> tuple[str, dict]:
        """
        Return the total number of whole minutes accumulated by the stopwatch without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- elapsed_minutes: Total accumulated whole minutes. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.elapsed_minutes.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'elapsed_minutes': value
        }
        return code, response

    def start(self) -> tuple[str, dict]:
        """
        Start the stopwatch from idle while preserving its current elapsed-minute value. The operation fails without changing state unless the stopwatch is idle.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, current_status = self.status.get()
        if code != '[PASS]':
            return code, {}
        if current_status != 'idle':
            return '[PRECONDITION_FAILED]', {}
        code = self.status.internal_set('running')
        if code != '[PASS]':
            return code, {}
        response = {}
        return code, response

    def pause(self) -> tuple[str, dict]:
        """
        Pause a running stopwatch while retaining elapsed time. The operation fails without changing state unless the stopwatch is running.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, current_status = self.status.get()
        if code != '[PASS]':
            return code, {}
        if current_status != 'running':
            return '[PRECONDITION_FAILED]', {}
        code = self.status.internal_set('paused')
        if code != '[PASS]':
            return code, {}
        response = {}
        return code, response

    def resume(self) -> tuple[str, dict]:
        """
        Resume a paused stopwatch without resetting its elapsed time. The operation fails without changing state unless the stopwatch is paused.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, current_status = self.status.get()
        if code != '[PASS]':
            return code, {}
        if current_status != 'paused':
            return '[PRECONDITION_FAILED]', {}
        code = self.status.internal_set('running')
        if code != '[PASS]':
            return code, {}
        response = {}
        return code, response

    def reset(self) -> tuple[str, dict]:
        """
        Reset the stopwatch from any state by setting its status to idle and clearing elapsed time to zero.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.status.internal_set('idle')
        if code != '[PASS]':
            return code, {}
        code = self.elapsed_minutes.internal_set(0)
        if code != '[PASS]':
            return code, {}
        response = {}
        return code, response

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        While the stopwatch is running, add each elapsed whole minute to the accumulated elapsed time. When idle or paused, retain all stopwatch state unchanged.

    Effect properties:
    - status: Determines whether elapsed time should accumulate.
    - elapsed_minutes: Accumulated whole minutes updated while the stopwatch is running.
        """
        minutes = context['minutes']
        if type(minutes) is not int or minutes < 0:
            return '[INVALID_VALUE]', []

        code, current_status = self.status.get()
        if code != '[PASS]':
            return code, []
        if current_status != 'running':
            return '[PASS]', []

        code, current_elapsed = self.elapsed_minutes.get()
        if code != '[PASS]':
            return code, []

        code = self.elapsed_minutes.internal_set(current_elapsed + minutes)
        if code != '[PASS]':
            return code, []

        return '[PASS]', []