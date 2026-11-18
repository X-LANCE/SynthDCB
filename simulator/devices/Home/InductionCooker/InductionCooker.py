# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class InductionCooker:
    """
    InductionCooker
    Description: Induction cooker. Users can query and set the heating mode, power level, and target temperature.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, heating_mode: str = None, power_level: int = None, target_temperature: float = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the induction cooker is powered.',
            default=False
        )
        self.heating_mode = StringProperty(
            name='heating_mode',
            description='The heating control mode.',
            default='manual',
            choices=['manual', 'temperature']
        )
        self.power_level = IntProperty(
            name='power_level',
            description='The selected induction heating power level.',
            default=1,
            minimum=1,
            maximum=9,
            step=1,
            step_origin=1
        )
        self.target_temperature = FloatProperty(
            name='target_temperature',
            description='The target cooking temperature used by temperature mode.',
            default=100.0,
            unit='degC',
            minimum=30.0,
            maximum=240.0,
            step=1.0,
            step_origin=30.0,
            precision=1
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if heating_mode is not None: code = self.heating_mode.internal_set(heating_mode)
        if power_level is not None: code = self.power_level.internal_set(power_level)
        if target_temperature is not None: code = self.target_temperature.internal_set(target_temperature)
        self._power_managed_properties = (self.heating_mode, self.power_level, self.target_temperature,)
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

    def get_heating_mode(self) -> tuple[str, dict]:
        """
        Return the selected heating mode. This operation requires the cooker to be powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- heating_mode: The selected heating mode. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        code, value = self.heating_mode.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"heating_mode": value}

    def set_heating_mode(self, value: str) -> tuple[str, dict]:
        """
        Set the heating mode to manual or temperature control. This operation requires the cooker to be powered.

        Args:
        - value: The desired heating mode. (choices=['manual', 'temperature'])

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
        if type(value) is not str or value not in ("manual", "temperature"):
            return "[ERROR] INVALID_VALUE", {}
        code = self.heating_mode.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_power_level(self) -> tuple[str, dict]:
        """
        Return the selected heating power level. This operation requires the cooker to be powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- power_level: The selected heating power level. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        code, value = self.power_level.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"power_level": value}

    def set_power_level(self, value: int) -> tuple[str, dict]:
        """
        Set the heating power level from 1 through 9. This operation requires the cooker to be powered.

        Args:
        - value: The desired heating power level. (min=1, max=9)

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
        if type(value) is not int or isinstance(value, bool) or value < 1 or value > 9:
            return "[ERROR] INVALID_VALUE", {}
        code = self.power_level.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_target_temperature(self) -> tuple[str, dict]:
        """
        Return the configured target temperature. This operation requires the cooker to be powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- target_temperature: The configured target temperature in degrees Celsius. (type=number)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        code, value = self.target_temperature.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"target_temperature": value}

    def set_target_temperature(self, value: float) -> tuple[str, dict]:
        """
        Set the target cooking temperature from 30.0 through 240.0 degrees Celsius. This operation requires the cooker to be powered.

        Args:
        - value: The desired target temperature in degrees Celsius. (min=30.0, max=240.0)

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
        if type(value) not in (int, float) or isinstance(value, bool) or value < 30.0 or value > 240.0:
            return "[ERROR] INVALID_VALUE", {}
        code = self.target_temperature.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}