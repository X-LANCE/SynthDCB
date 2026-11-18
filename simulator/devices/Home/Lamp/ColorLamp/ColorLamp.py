# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..Lamp import Lamp


class ColorLamp(Lamp):
    """
    ColorLamp
    Description: A lamp subclass that supports colored lighting and adds light-mode and color states to the base lamp. In white-light mode, color temperature can be adjusted but colored light cannot; in color mode, light color can be adjusted globally or by color channel but color temperature cannot. Brightness can be adjusted in both modes, and space illuminance remains determined by the inherited power and brightness states.
    Version: 1.0.0
    Base: Lamp
    """

    def __init__(
        self,
        light_mode: str = None,
        color: str = None,
        *,
        power: bool | None = None,
        _defer_power_init: bool = False,
        **base_kwargs
    ) -> None:
        _power_init_value = power if power is not None else False
        # initialize base Lamp class
        super().__init__(power=_power_init_value, _defer_power_init=True, **base_kwargs)

        # define properties
        self.light_mode = StringProperty(
            name='light_mode',
            description='Current light mode. In white mode, color temperature is adjustable and colored light is unavailable. In color mode, color is adjustable and color temperature is unavailable. The setting persists while the lamp is off and is publicly accessible only while the lamp is on.',
            default='white',
            choices=['white', 'color']
        )
        self.color = StringProperty(
            name='color',
            description='Configured global light color as a six-digit hexadecimal RGB value in the form #RRGGBB. It is publicly accessible and adjustable only while the lamp is powered on in color mode.',
            default='#FFFFFF',
            pattern='^#[0-9A-Fa-f]{6}$',
            max_length=7
        )

        # initialize properties
        if light_mode is not None:
            code = self.light_mode.internal_set(light_mode)
        if color is not None:
            code = self.color.internal_set(color)

        self._power_managed_properties = (
            self.brightness,
            self.color_temperature,
            self.light_mode,
            self.color,
        )
        self._power_initialized = False
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

        if not _defer_power_init:
            self.set_power(_power_init_value)

    def get_light_mode(self) -> tuple[str, dict]:
        """
        Return the current light mode. The lamp must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.light_mode.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"light_mode": value}

    def set_light_mode(self, value: str) -> tuple[str, dict]:
        """
        Set the light mode to white or color. The lamp must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        if type(value) is not str or value not in ("white", "color"):
            return "[INVALID_INPUT_ERROR]", {}
        code = self.light_mode.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_color(self) -> tuple[str, dict]:
        """
        Return the configured global hexadecimal RGB color.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        mode_code, mode = self.light_mode.get()
        if mode_code != "[PASS]":
            return mode_code, {}
        if mode != "color":
            return "[WRONG_MODE]", {}
        code, value = self.color.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"color": value}

    def set_color(self, value: str) -> tuple[str, dict]:
        """
        Set the global light color to a six-digit hexadecimal RGB value.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        mode_code, mode = self.light_mode.get()
        if mode_code != "[PASS]":
            return mode_code, {}
        if mode != "color":
            return "[WRONG_MODE]", {}
        if (
            type(value) is not str
            or len(value) != 7
            or value[0] != "#"
            or any(char not in "0123456789abcdefABCDEF" for char in value[1:])
        ):
            return "[INVALID_INPUT_ERROR]", {}
        code = self.color.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def set_color_channel(self, channel: str, value: int) -> tuple[str, dict]:
        """
        Set one RGB channel to an integer from 0 through 255.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        mode_code, mode = self.light_mode.get()
        if mode_code != "[PASS]":
            return mode_code, {}
        if mode != "color":
            return "[WRONG_MODE]", {}
        if (
            type(channel) is not str
            or channel not in ("red", "green", "blue")
            or type(value) is not int
            or value < 0
            or value > 255
        ):
            return "[INVALID_INPUT_ERROR]", {}
        color_code, current = self.color.get()
        if color_code != "[PASS]":
            return color_code, {}
        digits = list(current[1:])
        index = {"red": 0, "green": 2, "blue": 4}[channel]
        digits[index:index + 2] = list(format(value, "02X"))
        return self.set_color("#" + "".join(digits))

    def get_color_temperature(self) -> tuple[str, dict]:
        """
        Return the configured color temperature in kelvin.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        mode_code, mode = self.light_mode.get()
        if mode_code != "[PASS]":
            return mode_code, {}
        if mode != "white":
            return "[WRONG_MODE]", {}
        code, value = self.color_temperature.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"color_temperature": value}

    def set_color_temperature(self, value: int) -> tuple[str, dict]:
        """
        Set color temperature in white-light mode.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        if type(value) is not int or value < 1000 or value > 6500 or value % 100 != 0:
            return "[INVALID_INPUT_ERROR]", {}
        mode_code, mode = self.light_mode.get()
        if mode_code != "[PASS]":
            return mode_code, {}
        if mode != "white":
            return "[WRONG_MODE]", {}
        code = self.color_temperature.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def increase_color_temperature(self, value: int = 1) -> tuple[str, dict]:
        """
        Increase color temperature by 100 K steps.
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
        Decrease color temperature by 100 K steps.
        """
        if type(value) is not int or value < 1:
            return "[INVALID_INPUT_ERROR]", {}
        code, response = self.get_color_temperature()
        if code != "[PASS]":
            return code, {}
        current = response["color_temperature"]
        return self.set_color_temperature(max(1000, current - value * 100))