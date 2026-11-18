# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class AmbientLight:
    """
    AmbientLight
    Description: Interior ambient light with adjustable color, instantiated for each independently controlled area. Supports switching on and off, brightness, and color settings. The available colors or color space are fixed capabilities. A brightness setting is distinct from seat illuminance; the environment model calculates the actual lighting contribution. It does not replace existing reading lights.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, brightness: int = None, color: str = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the ambient light is powered. When false, it contributes no illuminance and its non-power settings are inaccessible through public functions.',
            default=False
        )
        self.brightness = IntProperty(
            name='brightness',
            description='Ambient-light brightness setting as an integer percentage. The setting persists while powered off but is publicly accessible only while powered on.',
            default=50,
            unit='%',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.color = StringProperty(
            name='color',
            description='Ambient-light color in the fixed 24-bit sRGB hexadecimal format #RRGGBB. The setting persists while powered off but is publicly accessible only while powered on.',
            default='#FFFFFF',
            pattern='^#[0-9A-Fa-f]{6}$',
            max_length=7
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if brightness is not None: code = self.brightness.internal_set(brightness)
        if color is not None: code = self.color.internal_set(color)
        self._power_managed_properties = (self.brightness, self.color,)
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
        Return the current brightness percentage. Requires the ambient light to be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- brightness: Current brightness setting from 0 through 100 percent. (type=integer)

        Error Codes:
        - POWER_OFF: The ambient light must be powered on.
        """
        code, value = self.brightness.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"brightness": value}

    def set_brightness(self, value: int) -> tuple[str, dict]:
        """
        Set brightness to an integer percentage from 0 through 100. Requires the ambient light to be powered on. Invalid input or a failed power precondition leaves state unchanged.

        Args:
        - value: Desired brightness percentage. (min=0, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The ambient light must be powered on.
        - INVALID_INPUT_ERROR: Brightness must be an integer from 0 through 100.
        """
        if type(value) is not int or value < 0 or value > 100:
            return "[INVALID_INPUT_ERROR]", {}

        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        code = self.brightness.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_color(self) -> tuple[str, dict]:
        """
        Return the selected 24-bit sRGB color in #RRGGBB format. Requires the ambient light to be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- color: Selected color in 24-bit sRGB hexadecimal #RRGGBB format. (type=string)

        Error Codes:
        - POWER_OFF: The ambient light must be powered on.
        """
        code, value = self.color.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"color": value}

    def set_color(self, value: str) -> tuple[str, dict]:
        """
        Set the color using the fixed 24-bit sRGB hexadecimal format #RRGGBB, for example #FF0000. Requires the ambient light to be powered on. Invalid input or a failed power precondition leaves state unchanged.

        Args:
        - value: Desired 24-bit sRGB color in #RRGGBB format.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The ambient light must be powered on.
        - INVALID_INPUT_ERROR: Color must use the 24-bit sRGB hexadecimal format #RRGGBB.
        """
        if (
            type(value) is not str
            or len(value) != 7
            or value[0] != "#"
            or any(character not in "0123456789ABCDEFabcdef" for character in value[1:])
        ):
            return "[INVALID_INPUT_ERROR]", {}

        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        code = self.color.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        Set the ambient light's contribution to illuminance in its containing area to the brightness percentage expressed in lux while powered, otherwise set the contribution to zero. Repeated updates replace the prior contribution rather than accumulating it.

    Effect properties:
    - power: Determines whether the light contributes illuminance.
    - brightness: Determines the illuminance contribution while the light is powered.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, []

        if powered:
            brightness_code, brightness = self.brightness.get()
            if brightness_code != "[PASS]":
                return brightness_code, []
            contribution = brightness
        else:
            contribution = 0

        effect = {
            "trigger": "after_action",
            "source": context["object_id"],
            "target": context["space_id"],
            "function": "set_contribution",
            "parameters": {
                "property": "illuminance",
                "value": contribution,
                "unit": "lux"
            }
        }
        return "[PASS]", [effect]