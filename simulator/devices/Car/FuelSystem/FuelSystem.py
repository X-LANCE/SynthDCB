# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class FuelSystem:
    """
    FuelSystem
    Description: Fuel system module. Supports querying remaining fuel and the fuel filler flap state, and requesting the filler flap to unlock.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, remaining_fuel: int = None, filler_flap_state: str = None) -> None:
        # define properties
        self.remaining_fuel = IntProperty(
            name='remaining_fuel',
            description='Remaining fuel as a percentage of usable fuel-tank capacity.',
            default=50,
            mode=2,
            unit='%',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.filler_flap_state = StringProperty(
            name='filler_flap_state',
            description='Current lock state of the fuel filler flap.',
            default='locked',
            mode=2,
            choices=['locked', 'unlocked']
        )

        # initialize properties
        if remaining_fuel is not None: code = self.remaining_fuel.internal_set(remaining_fuel)
        if filler_flap_state is not None: code = self.filler_flap_state.internal_set(filler_flap_state)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_remaining_fuel(self) -> tuple[str, dict]:
        """
        Return the remaining fuel as an integer percentage from 0 through 100 without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- remaining_fuel: Remaining fuel as a percentage of usable fuel-tank capacity. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.remaining_fuel.get()
        if code != '[PASS]':
            return (code, {})
        return (code, {'remaining_fuel': value})

    def get_filler_flap_state(self) -> tuple[str, dict]:
        """
        Return whether the fuel filler flap is locked or unlocked without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- filler_flap_state: Current filler-flap state: locked or unlocked. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.filler_flap_state.get()
        if code != '[PASS]':
            return (code, {})
        return (code, {'filler_flap_state': value})

    def request_filler_flap_unlock(self) -> tuple[str, dict]:
        """
        Request the fuel filler flap to unlock. The request immediately sets the flap state to unlocked and is idempotent when the flap is already unlocked. Remaining fuel is unchanged.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.filler_flap_state.internal_set('unlocked')
        if code != '[PASS]':
            return (code, {})
        return (code, {})