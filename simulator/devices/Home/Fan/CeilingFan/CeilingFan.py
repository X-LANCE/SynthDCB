# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..Fan import Fan

class CeilingFan(Fan):
    """
    CeilingFan
    Description: A ceiling-fan variant. It is a simple fan that supports only fan-speed adjustment.
    Version: 1.0.0
    Base: Fan
    """

    def __init__(self, fan_speed: int = None, *, power: bool | None = None, _defer_power_init: bool = False, **base_kwargs) -> None:
        _power_init_value = power if power is not None else False
        # initialize base Fan class
        super().__init__(power=_power_init_value, _defer_power_init=True, **base_kwargs)
        # define properties
        self.fan_speed = IntProperty(
            name='fan_speed',
            description='Selected fan speed: 1 is low, 2 is medium, and 3 is high. Retained across power changes.',
            default=1,
            minimum=1,
            maximum=3,
            step=1,
            step_origin=1
        )

        # initialize properties
        if fan_speed is not None: code = self.fan_speed.internal_set(fan_speed)

        # disable inherited properties
        self.oscillation.chmod(0)
        self.oscillation_angle.chmod(0)
        self.wind_mode.chmod(0)
        self._power_managed_properties = (self.fan_speed,)
        self._power_initialized = False
        self._disabled = {
            'properties': ['oscillation', 'oscillation_angle', 'wind_mode'],
            'functions': ['get_oscillation', 'get_oscillation_angle', 'get_wind_mode', 'set_oscillation', 'set_oscillation_angle', 'set_wind_mode'],
            'events': []
        }

        if not _defer_power_init:
            self.set_power(_power_init_value)

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
        While powered, set the selected fan speed to 1, 2, or 3. The configured fan speed is changed without changing device power.

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

    def get_oscillation(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'get_oscillation' is disabled in CeilingFan.", {}

    def get_oscillation_angle(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'get_oscillation_angle' is disabled in CeilingFan.", {}

    def get_wind_mode(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'get_wind_mode' is disabled in CeilingFan.", {}

    def set_oscillation(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'set_oscillation' is disabled in CeilingFan.", {}

    def set_oscillation_angle(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'set_oscillation_angle' is disabled in CeilingFan.", {}

    def set_wind_mode(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'set_wind_mode' is disabled in CeilingFan.", {}