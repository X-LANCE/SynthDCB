# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class WaterPurifier:
    """
    WaterPurifier
    Description: Water purifier. Users can query filter usage duration and filter life, and can query and enable flushing or backwashing modes. The filter usage duration can be reset.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, filter_usage_minutes: int = None, filter_life_percent: int = None, mode: str = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the water purifier is powered.',
            default=False
        )
        self.filter_usage_minutes = IntProperty(
            name='filter_usage_minutes',
            description='Filter usage duration in minutes since the last usage-duration reset.',
            default=0,
            mode=2,
            unit='min',
            minimum=0,
            step=1,
            step_origin=0
        )
        self.filter_life_percent = IntProperty(
            name='filter_life_percent',
            description='Remaining filter life as a percentage.',
            default=100,
            mode=2,
            unit='%',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.mode = StringProperty(
            name='mode',
            description='Current purifier operating mode.',
            default='normal',
            choices=['normal', 'flushing', 'backwashing']
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if filter_usage_minutes is not None: code = self.filter_usage_minutes.internal_set(filter_usage_minutes)
        if filter_life_percent is not None: code = self.filter_life_percent.internal_set(filter_life_percent)
        if mode is not None: code = self.mode.internal_set(mode)
        self._power_managed_properties = (self.filter_usage_minutes, self.filter_life_percent, self.mode,)
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

    def get_filter_usage_minutes(self) -> tuple[str, dict]:
        """
        Return the filter usage duration in minutes. This control is available only while the purifier is powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- filter_usage_minutes: Filter usage duration in minutes. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.filter_usage_minutes.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"filter_usage_minutes": value}

    def get_filter_life_percent(self) -> tuple[str, dict]:
        """
        Return the remaining filter life percentage. This control is available only while the purifier is powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)

        Response Data: A dictionary containing response data (type=dict)
        	- filter_life_percent: Remaining filter life percentage. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.filter_life_percent.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"filter_life_percent": value}

    def get_mode(self) -> tuple[str, dict]:
        """
        Return the current purifier mode. This control is available only while the purifier is powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)

        Response Data: A dictionary containing response data (type=dict)
        	- mode: Current purifier mode. (type=string)

        Error Codes:
        (no specified error codes)
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.mode.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"mode": value}

    def set_mode(self, value: str) -> tuple[str, dict]:
        """
        Enable normal, flushing, or backwashing mode. This control is available only while the purifier is powered.

        Args:
        - value: The mode to enable. (choices=['normal', 'flushing', 'backwashing'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- mode: The resulting purifier mode. (type=string)

        Error Codes:
        (no specified error codes)
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        if type(value) is not str or value not in ("normal", "flushing", "backwashing"):
            return "[INVALID_MODE]", {}
        code = self.mode.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"mode": value}

    def reset_filter_usage(self) -> tuple[str, dict]:
        """
        Reset the filter usage duration to zero. This changes only the tracked usage record and is available while the purifier is powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- filter_usage_minutes: The reset filter usage duration, which is zero minutes. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code = self.filter_usage_minutes.internal_set(0)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"filter_usage_minutes": 0}