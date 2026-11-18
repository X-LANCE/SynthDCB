# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class FragranceDiffuser:
    """
    FragranceDiffuser
    Description: Fragrance diffuser. Users can query and set the fragrance output state.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, output_state: bool = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Device-wide electrical power state.',
            default=False
        )
        self.output_state = BoolProperty(
            name='output_state',
            description='Whether fragrance output is enabled. Actual release requires both power and output_state to be true. Preserve this setting over power cycles.',
            default=False
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if output_state is not None: code = self.output_state.internal_set(output_state)
        self._power_managed_properties = (self.output_state,)
        self._power_initialized = False
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

        if not _defer_power_init:
            self.set_power(_power_init_value)

    def get_power(self) -> tuple[str, dict]:
        """
        Get the current power state.
        """
        code, value = self.power.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"power": value}

    def set_power(self, value: bool) -> tuple[str, dict]:
        """
        Set power and update access for active dependent properties.
        """
        if self._power_initialized:
            current_code, current_value = self.power.get()
            if current_code != "[PASS]":
                return current_code, {}
            if type(value) is bool and current_value == value:
                return "[PASS]", {}
        code = self.power.set(value)
        if code != "[PASS]":
            return code, {}
        for prop in self._power_managed_properties:
            switch_code = prop.handle_power_switch(value)
            if switch_code != "[PASS]" and not switch_code.startswith("[NO_ACTION]"):
                return switch_code, {}
        self._power_initialized = True
        return "[PASS]", {}

    def get_output_state(self) -> tuple[str, dict]:
        """
        Return whether fragrance output is enabled. This function is available only while the diffuser is powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- output_state: Whether fragrance output is enabled. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[ERROR] POWER_OFF", {}
        code, value = self.output_state.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"output_state": value}

    def set_output_state(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable fragrance output. The diffuser must be powered on. Invalid or unavailable operations leave the state unchanged.

        Args:
        - value: Whether fragrance output should be enabled.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- output_state: Updated fragrance output state. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[ERROR] POWER_OFF", {}
        if type(value) is not bool:
            return "[ERROR] INVALID_TYPE", {}
        code = self.output_state.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"output_state": value}