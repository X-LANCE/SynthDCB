# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..Lamp import Lamp


class SimpleLamp(Lamp):
    """
    SimpleLamp
    Description: A simplified lamp subclass that inherits the base lamp's power control and lighting effect but provides only stepped brightness adjustment, with no color-temperature state or related operations.
    Version: 1.0.0
    Base: Lamp
    """

    def __init__(self, brightness: int = None, *, power: bool | None = None, _defer_power_init: bool = False, **base_kwargs) -> None:
        _power_init_value = power if power is not None else False
        # initialize base Lamp class
        super().__init__(power=_power_init_value, _defer_power_init=True, **base_kwargs)
        # define properties
        self.brightness = IntProperty(
            name='brightness',
            description='Configured coarse brightness level of the lamp. The value persists while the lamp is off but is publicly accessible only while the lamp is on.',
            default=2,
            unit='level',
            minimum=1,
            maximum=3,
            step=1,
            step_origin=1
        )

        # initialize properties
        if brightness is not None:
            code = self.brightness.internal_set(brightness)

        # disable inherited properties
        self.color_temperature.chmod(0)
        self._power_managed_properties = (self.brightness,)
        self._power_initialized = False
        self._disabled = {
            'properties': ['color_temperature'],
            'functions': ['decrease_color_temperature', 'get_color_temperature', 'increase_color_temperature', 'set_color_temperature'],
            'events': []
        }

        if not _defer_power_init:
            self.set_power(_power_init_value)

    def get_brightness(self) -> tuple[str, dict]:
        """
        Return the configured brightness level. The lamp must be powered on; otherwise the function fails without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- brightness: Configured coarse brightness level from 1 through 3. (type=integer)

        Error Codes:
        - POWER_OFF: The lamp must be powered on to read brightness.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.brightness.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"brightness": value}

    def set_brightness(self, value: int) -> tuple[str, dict]:
        """
        Set brightness to an integer level from 1 through 3. The lamp must be powered on. Invalid input leaves state unchanged.

        Args:
        - value: Exact coarse brightness level to set. (min=1, max=3)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The lamp must be powered on to change brightness.
        - INVALID_INPUT_ERROR: Brightness must be an integer from 1 through 3.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        if type(value) is not int or value < 1 or value > 3:
            return "[INVALID_INPUT_ERROR]", {}
        code = self.brightness.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def increase_brightness(self, value: int = 1) -> tuple[str, dict]:
        """
        Increase brightness by the requested number of levels, defaulting to 1. The result is capped at level 3. The lamp must be powered on, and invalid input leaves state unchanged.

        Args:
        - value: Number of levels by which to increase brightness. (min=1)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The lamp must be powered on to increase brightness.
        - INVALID_INPUT_ERROR: The increase must be an integer of at least 1.
        """
        if type(value) is not int or value < 1:
            return "[INVALID_INPUT_ERROR]", {}
        code, response = self.get_brightness()
        if code != "[PASS]":
            return code, {}
        current = response["brightness"]
        return self.set_brightness(min(3, current + value))

    def decrease_brightness(self, value: int = 1) -> tuple[str, dict]:
        """
        Decrease brightness by the requested number of levels, defaulting to 1. The result is floored at level 1. The lamp must be powered on, and invalid input leaves state unchanged.

        Args:
        - value: Number of levels by which to decrease brightness. (min=1)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The lamp must be powered on to read brightness.
        - INVALID_INPUT_ERROR: The decrease must be an integer of at least 1.
        """
        if type(value) is not int or value < 1:
            return "[INVALID_INPUT_ERROR]", {}
        code, response = self.get_brightness()
        if code != "[PASS]":
            return code, {}
        current = response["brightness"]
        return self.set_brightness(max(1, current - value))

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        The lamp emits an absolute illuminance contribution of zero while powered off. While powered on, its illuminance contribution in lux equals its configured brightness level, so levels 1, 2, and 3 contribute 1, 2, and 3 lux respectively.

        Effect properties:
        - power: Determines whether the lamp contributes illuminance.
        - brightness: Determines the lamp's stepped illuminance contribution while powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, []

        if powered is not True:
            contribution = 0
        else:
            brightness_code, brightness = self.brightness.get()
            if brightness_code != "[PASS]":
                return brightness_code, []
            contribution = brightness

        effect = {
            'trigger': 'after_action',
            'source': context['object_id'],
            'target': context['space_id'],
            'function': 'set_contribution',
            'parameters': {
                'property': 'illuminance',
                'value': contribution,
                'unit': 'lux'
            }
        }
        return "[PASS]", [effect]

    def decrease_color_temperature(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'decrease_color_temperature' is disabled in SimpleLamp.", {}

    def get_color_temperature(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'get_color_temperature' is disabled in SimpleLamp.", {}

    def increase_color_temperature(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'increase_color_temperature' is disabled in SimpleLamp.", {}

    def set_color_temperature(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'set_color_temperature' is disabled in SimpleLamp.", {}