# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty


class Lamp:
    """
    Lamp
    Description: Lighting fixture. Users can query and set brightness and color temperature, and can also increase or decrease them incrementally. Turning the lamp off does not clear the configured brightness or color temperature. When the lamp is on, it changes the illuminance of its space according to brightness; color temperature changes only the perceived warmth or coolness of the light and does not determine illuminance intensity.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, brightness: int = None, color_temperature: int = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the lamp is powered on. Turning the lamp off preserves brightness and color temperature.',
            default=False
        )
        self.brightness = IntProperty(
            name='brightness',
            description='Configured brightness percentage. It persists while the lamp is off and is publicly accessible only while the lamp is on.',
            default=50,
            unit='%',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.color_temperature = IntProperty(
            name='color_temperature',
            description='Configured color temperature in kelvin. It persists while the lamp is off and affects perceived warmth or coolness, not illuminance intensity.',
            default=4000,
            unit='K',
            minimum=1000,
            maximum=6500,
            step=100,
            step_origin=1000
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if brightness is not None:
            code = self.brightness.internal_set(brightness)
        if color_temperature is not None:
            code = self.color_temperature.internal_set(color_temperature)
        self._power_managed_properties = (self.brightness, self.color_temperature,)
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
        Return the configured brightness percentage. The lamp must be powered on.
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
        Set brightness to an integer percentage from 0 through 100. The lamp must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        if type(value) is not int or value < 0 or value > 100:
            return "[INVALID_INPUT_ERROR]", {}
        code = self.brightness.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def increase_brightness(self, value: int = 1) -> tuple[str, dict]:
        """
        Increase brightness by the requested number of percentage points.
        """
        if type(value) is not int or value < 1:
            return "[INVALID_INPUT_ERROR]", {}
        code, response = self.get_brightness()
        if code != "[PASS]":
            return code, {}
        current = response["brightness"]
        return self.set_brightness(min(100, current + value))

    def decrease_brightness(self, value: int = 1) -> tuple[str, dict]:
        """
        Decrease brightness by the requested number of percentage points.
        """
        if type(value) is not int or value < 1:
            return "[INVALID_INPUT_ERROR]", {}
        code, response = self.get_brightness()
        if code != "[PASS]":
            return code, {}
        current = response["brightness"]
        return self.set_brightness(max(0, current - value))

    def get_color_temperature(self) -> tuple[str, dict]:
        """
        Return the configured color temperature in kelvin. The lamp must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.color_temperature.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"color_temperature": value}

    def set_color_temperature(self, value: int) -> tuple[str, dict]:
        """
        Set color temperature to an integer from 1000 K through 6500 K in 100 K increments.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        if type(value) is not int or value < 1000 or value > 6500 or value % 100 != 0:
            return "[INVALID_INPUT_ERROR]", {}
        code = self.color_temperature.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def increase_color_temperature(self, value: int = 1) -> tuple[str, dict]:
        """
        Increase color temperature by the requested number of 100 K steps.
        """
        if type(value) is not int or value < 1:
            return "[INVALID_INPUT_ERROR]", {}
        code, response = self.get_color_temperature()
        if code != "[PASS]":
            return code, {}
        current = response["color_temperature"]
        return self.set_color_temperature(min(6500, current + value * 100))

    def decrease_color_temperature(self, value: int = 1) -> tuple[str, dict]:
        """
        Decrease color temperature by the requested number of 100 K steps.
        """
        if type(value) is not int or value < 1:
            return "[INVALID_INPUT_ERROR]", {}
        code, response = self.get_color_temperature()
        if code != "[PASS]":
            return code, {}
        current = response["color_temperature"]
        return self.set_color_temperature(max(1000, current - value * 100))

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        The lamp emits an absolute illuminance contribution of zero while powered off.
        While powered on, its contribution in lux equals its brightness percentage multiplied by 10.
        Color temperature does not affect illuminance.
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
            contribution = brightness * 10

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