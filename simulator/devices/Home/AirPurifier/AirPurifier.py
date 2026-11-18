# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class AirPurifier:
    """
    AirPurifier
    Description: Air purifier. Users can query and set the fan-speed level and target air quality, and can query but not directly modify the remaining filter life. While running, the device gradually moves the air quality of its space toward the configured target according to the fan-speed level; it produces no further purification effect when turned off or when the air quality has reached the target. Current air quality should be provided by the containing space rather than duplicated as device state.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, fan_speed: int = None, target_air_quality: int = None, filter_life: int = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the air purifier is powered.',
            default=False
        )
        self.fan_speed = IntProperty(
            name='fan_speed',
            description='Configured fan-speed level. Higher levels purify the space more quickly.',
            default=1,
            minimum=1,
            maximum=5,
            step=1,
            step_origin=1
        )
        self.target_air_quality = IntProperty(
            name='target_air_quality',
            description='Configured target air-quality index for the containing space.',
            default=50,
            unit='AQI',
            minimum=0,
            maximum=500,
            step=1,
            step_origin=0
        )
        self.filter_life = IntProperty(
            name='filter_life',
            description='Remaining filter life as a percentage. This value can be queried but not directly modified.',
            default=100,
            mode=2,
            unit='%',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if fan_speed is not None: code = self.fan_speed.internal_set(fan_speed)
        if target_air_quality is not None: code = self.target_air_quality.internal_set(target_air_quality)
        if filter_life is not None: code = self.filter_life.internal_set(filter_life)
        self._power_managed_properties = (self.fan_speed, self.target_air_quality, self.filter_life,)
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
        Return the configured fan-speed level. The purifier must be powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- fan_speed: Configured fan-speed level. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[ERROR] POWER_OFF", {}
        code, value = self.fan_speed.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"fan_speed": value}

    def set_fan_speed(self, value: int) -> tuple[str, dict]:
        """
        Set the fan-speed level from 1 through 5. The purifier must be powered; invalid values fail without changing state.

        Args:
        - value: Fan-speed level. (min=1, max=5)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[ERROR] POWER_OFF", {}
        if type(value) is not int or type(value) is bool or value < 1 or value > 5:
            return "[ERROR] INVALID_VALUE", {}
        code = self.fan_speed.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_target_air_quality(self) -> tuple[str, dict]:
        """
        Return the configured target air-quality index. The purifier must be powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- target_air_quality: Configured target air-quality index. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[ERROR] POWER_OFF", {}
        code, value = self.target_air_quality.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"target_air_quality": value}

    def set_target_air_quality(self, value: int) -> tuple[str, dict]:
        """
        Set the target air-quality index from 0 through 500. The purifier must be powered; invalid values fail without changing state.

        Args:
        - value: Target air-quality index. (min=0, max=500)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[ERROR] POWER_OFF", {}
        if type(value) is not int or type(value) is bool or value < 0 or value > 500:
            return "[ERROR] INVALID_VALUE", {}
        code = self.target_air_quality.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_filter_life(self) -> tuple[str, dict]:
        """
        Return the remaining filter life percentage. The purifier must be powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- filter_life: Remaining filter life percentage. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[ERROR] POWER_OFF", {}
        code, value = self.filter_life.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"filter_life": value}

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        While powered, move the containing space's air_quality toward target_air_quality using an approach effect. The approach rate is determined by fan_speed, with higher fan-speed levels producing faster movement. Emit no purification effect when powered off or when the space air_quality already equals the target.

    Effect properties:
    - power: Whether the air purifier is powered.
    - fan_speed: Configured fan-speed level controlling purification rate.
    - target_air_quality: Configured target air-quality index.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, []
        if powered is not True:
            return "[PASS]", []

        code, fan_speed = self.fan_speed.get()
        if code != "[PASS]":
            return code, []
        code, target_air_quality = self.target_air_quality.get()
        if code != "[PASS]":
            return code, []

        air_quality = context["space_state"]["air_quality"]
        if air_quality == target_air_quality:
            return "[PASS]", []

        rate = round(fan_speed * 1.0, 1)
        return "[PASS]", [{
            "trigger": "tick",
            "source": context["object_id"],
            "target": context["space_id"],
            "function": "approach",
            "parameters": {
                "property": "air_quality",
                "value": target_air_quality,
                "rate_per_minute": rate,
                "unit": "AQI"
            }
        }]