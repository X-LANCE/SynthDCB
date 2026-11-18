# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class CabinLight:
    """
    CabinLight
    Description: Cabin light. Supports switching on and off and adjusting brightness. When on, it changes the illuminance of its Space according to its brightness.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, brightness: int = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the cabin light is powered on.',
            default=False
        )
        self.brightness = IntProperty(
            name='brightness',
            description='Cabin light brightness as an integer percentage. The setting persists while powered off.',
            default=100,
            unit='%',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if brightness is not None: code = self.brightness.internal_set(brightness)
        self._power_managed_properties = (self.brightness,)
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

    def get_brightness(self) -> tuple[str, dict]:
        """
        Return the brightness percentage. The cabin light must be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- brightness: Current brightness as an integer percentage from 0 through 100. (type=integer)

        Error Codes:
        - POWER_OFF: The cabin light must be powered on to read brightness.
        """
        code, value = self.brightness.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"brightness": value}

    def set_brightness(self, value: int) -> tuple[str, dict]:
        """
        Set brightness to an integer percentage from 0 through 100. The cabin light must be powered on. Invalid input or an unmet power precondition leaves state unchanged.

        Args:
        - value:  (min=0, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The cabin light must be powered on to change brightness.
        - INVALID_INPUT_ERROR: Brightness must be an integer from 0 through 100.
        """
        code = self.brightness.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        When powered on, contribute illuminance to the containing Space equal to the brightness value in lux. When powered off, contribute zero illuminance. Repeated updates replace the previous contribution rather than accumulating it.

    Effect properties:
    - power: Determines whether the light contributes illuminance.
    - brightness: Determines the illuminance contribution while the light is powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, []

        if powered:
            brightness_code, brightness = self.brightness.get()
            if brightness_code != "[PASS]":
                return brightness_code, []
            value = brightness
        else:
            value = 0

        effect = {
            "trigger": "after_action",
            "source": context["object_id"],
            "target": context["space_id"],
            "function": "set_contribution",
            "parameters": {
                "property": "illuminance",
                "value": value,
                "unit": "lux"
            }
        }
        return "[PASS]", [effect]