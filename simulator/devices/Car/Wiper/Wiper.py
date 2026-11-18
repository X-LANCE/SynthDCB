# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Wiper:
    """
    Wiper
    Description: Vehicle wiper, instantiated for each actual front or rear glass mechanism. Supports off, single wipe, continuous wiping, intermittent wiping, and the speed or interval levels available on that mechanism, as well as triggering the corresponding washer action. Supports querying current operating state. A single action ends on completion; a requested level is not equivalent to a cleaning result. Available levels and washer behavior are simulation designs specific to the vehicle model.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, operating_state: str = None, level: int = None) -> None:
        # define properties
        self.operating_state = StringProperty(
            name='operating_state',
            description='Current sustained wiper operating state.',
            default='off',
            mode=2,
            choices=['off', 'continuous', 'intermittent']
        )
        self.level = IntProperty(
            name='level',
            description='Mechanism-specific wiping level. It represents speed during continuous wiping and interval selection during intermittent wiping.',
            default=1,
            minimum=1,
            maximum=3,
            step=1,
            step_origin=1
        )

        # initialize properties
        if operating_state is not None: code = self.operating_state.internal_set(operating_state)
        if level is not None: code = self.level.internal_set(level)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_operating_state(self) -> tuple[str, dict]:
        """
        Return the current sustained operating state without changing it. Single-wipe and washer actions complete synchronously and therefore do not remain as queryable sustained states.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- operating_state: Current sustained state: off, continuous, or intermittent. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.operating_state.get()
        if code != '[PASS]':
            return (code, {})
        return (code, {'operating_state': value})

    def get_level(self) -> tuple[str, dict]:
        """
        Return the configured mechanism-specific level without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- level: Configured wiping level from 1 through 3. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.level.get()
        if code != '[PASS]':
            return (code, {})
        return (code, {'level': value})

    def set_level(self, value: int) -> tuple[str, dict]:
        """
        Set the mechanism-specific wiping level to an integer from 1 through 3. The new level applies immediately to sustained operation and to subsequent single-wipe or washer actions. Invalid input is rejected and leaves state unchanged.

        Args:
        - value:  (min=1, max=3)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - INVALID_INPUT_ERROR: Level must be an integer from 1 through 3.
        """
        if type(value) is not int or value < 1 or value > 3:
            return ('[INVALID_INPUT_ERROR]', {})
        code = self.level.set(value)
        if code != '[PASS]':
            return (code, {})
        return (code, {})

    def start_continuous(self) -> tuple[str, dict]:
        """
        Start continuous wiping at the configured level. This replaces any previous sustained operating state and succeeds idempotently if continuous wiping is already selected.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.operating_state.internal_set('continuous')
        if code != '[PASS]':
            return (code, {})
        return (code, {})

    def start_intermittent(self) -> tuple[str, dict]:
        """
        Start intermittent wiping using the configured interval level. This replaces any previous sustained operating state and succeeds idempotently if intermittent wiping is already selected.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.operating_state.internal_set('intermittent')
        if code != '[PASS]':
            return (code, {})
        return (code, {})

    def stop(self) -> tuple[str, dict]:
        """
        Stop sustained wiping. The configured level is preserved, and calling this action while already off succeeds without further change.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.operating_state.internal_set('off')
        if code != '[PASS]':
            return (code, {})
        return (code, {})

    def wipe_once(self) -> tuple[str, dict]:
        """
        Perform one wipe at the configured level and complete before returning. The action preserves the current sustained operating state and reports command completion; it does not claim that the glass was cleaned.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- completed: True when the simulated single-wipe command has completed. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, level = self.level.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'completed': True})

    def trigger_washer(self) -> tuple[str, dict]:
        """
        Trigger the washer for this wiper mechanism, spray the corresponding glass, and perform one wipe at the configured level before returning. The action preserves the current sustained operating state, does not track washer-fluid quantity, and does not claim a cleaning result.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- completed: True when the simulated washer-and-wipe command has completed. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, level = self.level.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'completed': True})