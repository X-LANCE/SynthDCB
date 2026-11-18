# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class WaterDispenser:
    """
    WaterDispenser
    Description: Water dispenser. Users can query and set the keep-warm temperature and child-lock function.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, keep_warm_temperature: int = None, child_lock: bool = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the water dispenser is powered.',
            default=False
        )
        self.keep_warm_temperature = IntProperty(
            name='keep_warm_temperature',
            description='Configured temperature maintained for keeping water warm, in degrees Celsius.',
            default=85,
            unit='degC',
            minimum=40,
            maximum=100,
            step=5,
            step_origin=0
        )
        self.child_lock = BoolProperty(
            name='child_lock',
            description='Whether the dispenser child-lock function is enabled.',
            default=False
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if keep_warm_temperature is not None: code = self.keep_warm_temperature.internal_set(keep_warm_temperature)
        if child_lock is not None: code = self.child_lock.internal_set(child_lock)
        self._power_managed_properties = (self.keep_warm_temperature, self.child_lock,)
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

    def get_keep_warm_temperature(self) -> tuple[str, dict]:
        """
        Get the configured keep-warm temperature. This function is available only while the dispenser is powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- keep_warm_temperature: The configured keep-warm temperature in degrees Celsius. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.keep_warm_temperature.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"keep_warm_temperature": value}

    def set_keep_warm_temperature(self, value: int) -> tuple[str, dict]:
        """
        Set the keep-warm temperature to an integer from 40 through 100 degrees Celsius in 5-degree increments. This function is available only while the dispenser is powered. Invalid values leave the setting unchanged.

        Args:
        - value: The desired keep-warm temperature in degrees Celsius. (min=40, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- keep_warm_temperature: The resulting keep-warm temperature in degrees Celsius. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[ERROR] POWER_OFF", {}
        if type(value) is not int or value < 40 or value > 100 or value % 5 != 0:
            return "[ERROR] INVALID_TEMPERATURE", {}
        code = self.keep_warm_temperature.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"keep_warm_temperature": value}

    def get_child_lock(self) -> tuple[str, dict]:
        """
        Get whether the child-lock function is enabled. This function is available only while the dispenser is powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- child_lock: Whether the child-lock function is enabled. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.child_lock.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"child_lock": value}

    def set_child_lock(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable the child-lock function. This function is available only while the dispenser is powered.

        Args:
        - value: Whether to enable the child-lock function.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- child_lock: The resulting child-lock state. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[ERROR] POWER_OFF", {}
        if type(value) is not bool:
            return "[ERROR] INVALID_CHILD_LOCK", {}
        code = self.child_lock.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"child_lock": value}