# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..Window import Window

class Sunroof(Window):
    """
    Sunroof
    Description: Sunroof that inherits the opening controls of Window. Adds an independent sunshade opening property; adjusting the sunshade does not change the sunroof opening.
    Version: 1.0.0
    Base: Window
    """

    def __init__(self, sunshade_position: int = None, **base_kwargs) -> None:
        # initialize base Window class
        super().__init__(**base_kwargs)
        # define properties
        self.sunshade_position = IntProperty(
            name='sunshade_position',
            description='Sunshade opening percentage, where 0 is fully closed and 100 is fully open; independent of the sunroof opening percentage.',
            default=0,
            unit='%',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )

        # initialize properties
        if sunshade_position is not None: code = self.sunshade_position.internal_set(sunshade_position)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_sunshade_position(self) -> tuple[str, dict]:
        """
        Return the current sunshade opening percentage without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- sunshade_position: Current sunshade opening percentage, where 0 is fully closed and 100 is fully open. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.sunshade_position.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'sunshade_position': value})

    def set_sunshade_position(self, value: int) -> tuple[str, dict]:
        """
        Set the sunshade opening percentage to an integer from 0 through 100 inclusive without changing the inherited sunroof opening percentage. Invalid values are rejected and leave state unchanged.

        Args:
        - value: Desired sunshade opening percentage. (min=0, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - INVALID_INPUT_ERROR: The sunshade opening percentage must be an integer from 0 through 100.
        """
        code = self.sunshade_position.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})