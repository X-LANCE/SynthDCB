# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty


class Refrigerator:
    """
    Refrigerator
    Description: Refrigerator. Users can query and set the target temperatures and operating modes for the refrigerator, freezer, and variable-temperature compartments. Fast-freeze and fast-cool modes can be queried and toggled.
    Version: 1.0.0
    Base: -
    """

    def __init__(
        self,
        power: bool = None,
        refrigerator_temperature: float = None,
        freezer_temperature: float = None,
        variable_temperature: float = None,
        refrigerator_mode: str = None,
        freezer_mode: str = None,
        variable_mode: str = None,
        fast_cool: bool = None,
        fast_freeze: bool = None,
        *,
        _defer_power_init: bool = False,
    ) -> None:
        _power_init_value = power if power is not None else False

        self.power = BoolProperty(
            name="power",
            description="Whether the refrigerator is powered.",
            default=False,
        )
        self.refrigerator_temperature = FloatProperty(
            name="refrigerator_temperature",
            description="Target temperature of the refrigerator compartment.",
            default=4.0,
            unit="degC",
            minimum=0,
            maximum=10,
            step=0.5,
            step_origin=0,
        )
        self.freezer_temperature = FloatProperty(
            name="freezer_temperature",
            description="Target temperature of the freezer compartment.",
            default=-18.0,
            unit="degC",
            minimum=-25,
            maximum=-10,
            step=0.5,
            step_origin=-25,
        )
        self.variable_temperature = FloatProperty(
            name="variable_temperature",
            description="Target temperature of the variable-temperature compartment.",
            default=1.0,
            unit="degC",
            minimum=-18,
            maximum=10,
            step=0.5,
            step_origin=-18,
        )
        self.refrigerator_mode = StringProperty(
            name="refrigerator_mode",
            description="Operating mode of the refrigerator compartment.",
            default="normal",
            choices=["normal", "vacation"],
        )
        self.freezer_mode = StringProperty(
            name="freezer_mode",
            description="Operating mode of the freezer compartment.",
            default="normal",
            choices=["normal", "eco"],
        )
        self.variable_mode = StringProperty(
            name="variable_mode",
            description="Operating mode of the variable-temperature compartment.",
            default="refrigerator",
            choices=["freezer", "soft_freeze", "refrigerator", "beverage"],
        )
        self.fast_cool = BoolProperty(
            name="fast_cool",
            description="Whether fast-cool mode is enabled for the refrigerator compartment.",
            default=False,
        )
        self.fast_freeze = BoolProperty(
            name="fast_freeze",
            description="Whether fast-freeze mode is enabled for the freezer compartment.",
            default=False,
        )

        code = self.power.internal_set(_power_init_value)

        if refrigerator_temperature is not None:
            code = self.refrigerator_temperature.internal_set(refrigerator_temperature)
        if freezer_temperature is not None:
            code = self.freezer_temperature.internal_set(freezer_temperature)
        if variable_temperature is not None:
            code = self.variable_temperature.internal_set(variable_temperature)
        if refrigerator_mode is not None:
            code = self.refrigerator_mode.internal_set(refrigerator_mode)
        if freezer_mode is not None:
            code = self.freezer_mode.internal_set(freezer_mode)
        if variable_mode is not None:
            code = self.variable_mode.internal_set(variable_mode)
        if fast_cool is not None:
            code = self.fast_cool.internal_set(fast_cool)
        if fast_freeze is not None:
            code = self.fast_freeze.internal_set(fast_freeze)

        self._power_managed_properties = (
            self.refrigerator_temperature,
            self.freezer_temperature,
            self.variable_temperature,
            self.refrigerator_mode,
            self.freezer_mode,
            self.variable_mode,
            self.fast_cool,
            self.fast_freeze,
        )
        self._power_initialized = False
        self._disabled = {"properties": [], "functions": [], "events": []}

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

    def _get(self, prop, key):
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        code, value = prop.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {key: value}

    def _set(self, prop, value):
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        code = prop.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_refrigerator_temperature(self):
        return self._get(self.refrigerator_temperature, "refrigerator_temperature")

    def set_refrigerator_temperature(self, value):
        return self._set(self.refrigerator_temperature, value)

    def get_freezer_temperature(self):
        return self._get(self.freezer_temperature, "freezer_temperature")

    def set_freezer_temperature(self, value):
        return self._set(self.freezer_temperature, value)

    def get_variable_temperature(self):
        return self._get(self.variable_temperature, "variable_temperature")

    def set_variable_temperature(self, value):
        return self._set(self.variable_temperature, value)

    def get_refrigerator_mode(self):
        return self._get(self.refrigerator_mode, "refrigerator_mode")

    def set_refrigerator_mode(self, value):
        return self._set(self.refrigerator_mode, value)

    def get_freezer_mode(self):
        return self._get(self.freezer_mode, "freezer_mode")

    def set_freezer_mode(self, value):
        return self._set(self.freezer_mode, value)

    def get_variable_mode(self):
        return self._get(self.variable_mode, "variable_mode")

    def set_variable_mode(self, value):
        return self._set(self.variable_mode, value)

    def get_fast_cool(self):
        return self._get(self.fast_cool, "fast_cool")

    def set_fast_cool(self, value):
        return self._set(self.fast_cool, value)

    def get_fast_freeze(self):
        return self._get(self.fast_freeze, "fast_freeze")

    def set_fast_freeze(self, value):
        return self._set(self.fast_freeze, value)