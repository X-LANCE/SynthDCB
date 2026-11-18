# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Fan:
    """
    Fan
    Description: Electric fan. Users can query and set fan speed, natural-wind or sleep-wind mode, oscillation state, and oscillation angle. A running fan does not change space temperature or humidity.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, fan_speed: int = None, wind_mode: str = None, oscillation: bool = None, oscillation_angle: int = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Device-wide electrical power state.',
            default=False
        )
        self.fan_speed = IntProperty(
            name='fan_speed',
            description='Selected fan speed: 1 is low, 2 is medium, and 3 is high. Retained across power changes and wind-mode changes.',
            default=1,
            minimum=1,
            maximum=3,
            step=1,
            step_origin=1
        )
        self.wind_mode = StringProperty(
            name='wind_mode',
            description='Selected wind profile: normal, natural-wind, or sleep-wind. Selecting a profile does not change the saved fan speed or start a timer.',
            default='normal',
            choices=['normal', 'natural-wind', 'sleep-wind']
        )
        self.oscillation = BoolProperty(
            name='oscillation',
            description='Whether horizontal oscillation is enabled while powered. Disabling oscillation preserves the configured sweep angle.',
            default=False
        )
        self.oscillation_angle = IntProperty(
            name='oscillation_angle',
            description='Configured total horizontal oscillation sweep width in degrees, not the instantaneous heading. It can be configured while powered whether oscillation is enabled or disabled.',
            default=90,
            unit='degrees',
            minimum=1,
            maximum=180,
            step=1,
            step_origin=1
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if fan_speed is not None: code = self.fan_speed.internal_set(fan_speed)
        if wind_mode is not None: code = self.wind_mode.internal_set(wind_mode)
        if oscillation is not None: code = self.oscillation.internal_set(oscillation)
        if oscillation_angle is not None: code = self.oscillation_angle.internal_set(oscillation_angle)
        self._power_managed_properties = (self.fan_speed, self.wind_mode, self.oscillation, self.oscillation_angle,)
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

    def get_fan_speed(self) -> tuple[str, dict]:
        """
        While powered, get the selected fan speed. Power-off access fails without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- fan_speed: Selected fan speed from 1 through 3. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        code, value = self.fan_speed.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"fan_speed": value}

    def set_fan_speed(self, value: int) -> tuple[str, dict]:
        """
        While powered, set the selected fan speed to 1, 2, or 3. The wind mode and other settings remain unchanged.

        Args:
        - value:  (min=1, max=3)

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
        if type(value) is not int or isinstance(value, bool) or value < 1 or value > 3:
            return "[ERROR] INVALID_FAN_SPEED", {}
        code = self.fan_speed.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_wind_mode(self) -> tuple[str, dict]:
        """
        While powered, get the selected wind profile: normal, natural-wind, or sleep-wind.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- wind_mode: Selected wind profile. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        code, value = self.wind_mode.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"wind_mode": value}

    def set_wind_mode(self, value: str) -> tuple[str, dict]:
        """
        While powered, select normal, natural-wind, or sleep-wind. The selected fan speed and oscillation settings remain unchanged; no timer or automatic configuration change is started.

        Args:
        - value:  (choices=['normal', 'natural-wind', 'sleep-wind'])

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
        if type(value) is not str or value not in ("normal", "natural-wind", "sleep-wind"):
            return "[ERROR] INVALID_WIND_MODE", {}
        code = self.wind_mode.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_oscillation(self) -> tuple[str, dict]:
        """
        While powered, get whether horizontal oscillation is enabled.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- oscillation: Whether horizontal oscillation is enabled. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        code, value = self.oscillation.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"oscillation": value}

    def set_oscillation(self, value: bool) -> tuple[str, dict]:
        """
        While powered, enable or disable horizontal oscillation. The configured oscillation angle remains unchanged.

        Args:
        - value:

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
        if type(value) is not bool:
            return "[ERROR] INVALID_TYPE", {}
        code = self.oscillation.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_oscillation_angle(self) -> tuple[str, dict]:
        """
        While powered, get the configured horizontal oscillation sweep width in degrees.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- oscillation_angle: Configured sweep width from 1 through 180 degrees. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        code, value = self.oscillation_angle.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"oscillation_angle": value}

    def set_oscillation_angle(self, value: int) -> tuple[str, dict]:
        """
        While powered, set the horizontal oscillation sweep width to an integer from 1 through 180 degrees inclusive. The oscillation state remains unchanged.

        Args:
        - value:  (min=1, max=180)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        if type(value) is not int or isinstance(value, bool) or value < 1 or value > 180:
            return "[ERROR] INVALID_OSCILLATION_ANGLE", {}
        code = self.oscillation_angle.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}