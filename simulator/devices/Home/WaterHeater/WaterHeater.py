# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class WaterHeater:
    """
    WaterHeater
    Description: Water heater. Users can query and set the target outlet-water temperature and heating state.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, target_outlet_temperature: float = None, heating_state: bool = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the water heater is powered.',
            default=False
        )
        self.target_outlet_temperature = FloatProperty(
            name='target_outlet_temperature',
            description='Target outlet-water temperature.',
            default=45.0,
            unit='degC',
            minimum=0.0,
            maximum=100.0,
            step=0.5,
            step_origin=0.0,
            precision=1
        )
        self.heating_state = BoolProperty(
            name='heating_state',
            description='Whether heating is enabled.',
            default=False
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if target_outlet_temperature is not None: code = self.target_outlet_temperature.internal_set(target_outlet_temperature)
        if heating_state is not None: code = self.heating_state.internal_set(heating_state)
        self._power_managed_properties = (self.target_outlet_temperature, self.heating_state,)
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

    def get_target_outlet_temperature(self) -> tuple[str, dict]:
        """
        Return the configured target outlet-water temperature. This operation fails while the water heater is powered off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- target_outlet_temperature: Target outlet-water temperature in degrees Celsius. (type=number)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        code, value = self.target_outlet_temperature.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"target_outlet_temperature": value}

    def set_target_outlet_temperature(self, value: float) -> tuple[str, dict]:
        """
        Set the target outlet-water temperature while powered on. The value must be between 0.0 and 100.0 degrees Celsius in 0.5-degree increments; invalid values leave the state unchanged.

        Args:
        - value: Target outlet-water temperature in degrees Celsius. (min=0.0, max=100.0)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        code = self.target_outlet_temperature.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_heating_state(self) -> tuple[str, dict]:
        """
        Return whether heating is enabled. This operation fails while the water heater is powered off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- heating_state: Whether heating is enabled. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        code, value = self.heating_state.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"heating_state": value}

    def set_heating_state(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable heating while powered on. This changes the heating enable state; invalid requests leave the state unchanged.

        Args:
        - value: Whether heating should be enabled.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        code = self.heating_state.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}