# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class System:
    """
    System
    Description: Phone system root object, placed in Setting, containing settings modules and applications through contains relations. Supports querying and setting airplane mode; the responses of individual wireless modules are defined by explicit dependencies. System does not duplicate module state or modify the simulation clock.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, airplane_mode: bool = None) -> None:
        # define properties
        self.airplane_mode = BoolProperty(
            name='airplane_mode',
            description='Whether airplane mode is requested for the phone. Wireless modules respond through their explicit dependencies rather than through duplicated state on this object.',
            default=False
        )

        # initialize properties
        if airplane_mode is not None: code = self.airplane_mode.internal_set(airplane_mode)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_airplane_mode(self) -> tuple[str, dict]:
        """
        Return whether airplane mode is currently requested without changing system or module state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- airplane_mode: Whether airplane mode is currently requested. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.airplane_mode.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'airplane_mode': value
        }
        return (code, response)

    def set_airplane_mode(self, value: bool) -> tuple[str, dict]:
        """
        Set whether airplane mode is requested. Wireless modules respond separately through explicit dependencies. Invalid input is rejected and leaves the setting unchanged.

        Args:
        - value: The requested airplane mode state.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.airplane_mode.set(value)
        response = {}
        return (code, response)