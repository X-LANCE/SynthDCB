# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Kettle:
    """
    Kettle
    Description: Electric kettle. Users can query and set the target water temperature and the heating and keep-warm states, and can query the current water temperature and boiling state. While heating, the device raises the water temperature in the kettle; after reaching the target, it stops heating or enters keep-warm mode.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, target_temperature: float = None, heating: bool = None, keep_warm: bool = None, current_temperature: float = None, boiling: bool = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the kettle is powered.',
            default=False
        )
        self.target_temperature = FloatProperty(
            name='target_temperature',
            description='Target water temperature for heating and keep-warm maintenance.',
            default=100.0,
            unit='degC',
            minimum=40.0,
            maximum=100.0,
            step=1.0,
            step_origin=0.0,
            precision=1
        )
        self.heating = BoolProperty(
            name='heating',
            description='Whether the kettle is actively heating toward the target temperature.',
            default=False
        )
        self.keep_warm = BoolProperty(
            name='keep_warm',
            description='Whether keep-warm maintenance is active. When enabled after heating reaches the target, the kettle maintains the target temperature; disabling it stops maintenance.',
            default=False
        )
        self.current_temperature = FloatProperty(
            name='current_temperature',
            description='Current water temperature inside the kettle.',
            default=20.0,
            mode=2,
            unit='degC',
            minimum=0.0,
            maximum=100.0,
            precision=1
        )
        self.boiling = BoolProperty(
            name='boiling',
            description='Whether the water temperature is exactly 100 degrees Celsius.',
            default=False,
            mode=2
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if target_temperature is not None: code = self.target_temperature.internal_set(target_temperature)
        if heating is not None: code = self.heating.internal_set(heating)
        if keep_warm is not None: code = self.keep_warm.internal_set(keep_warm)
        if current_temperature is not None: code = self.current_temperature.internal_set(current_temperature)
        if boiling is not None: code = self.boiling.internal_set(boiling)
        self._power_managed_properties = (self.target_temperature, self.heating, self.keep_warm, self.current_temperature, self.boiling,)
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

    def get_target_temperature(self) -> tuple[str, dict]:
        """
        Get the configured target temperature while powered.
        """
        code, value = self.target_temperature.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"target_temperature": value}

    def set_target_temperature(self, value: float) -> tuple[str, dict]:
        """
        Set the target temperature.
        """
        code = self.target_temperature.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_heating(self) -> tuple[str, dict]:
        """
        Get whether the kettle is actively heating while powered.
        """
        code, value = self.heating.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"heating": value}

    def set_heating(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable active heating while powered.
        """
        code = self.heating.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_keep_warm(self) -> tuple[str, dict]:
        """
        Get whether keep-warm maintenance is active while powered.
        """
        code, value = self.keep_warm.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"keep_warm": value}

    def set_keep_warm(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable keep-warm maintenance while powered.
        """
        code = self.keep_warm.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_current_temperature(self) -> tuple[str, dict]:
        """
        Get the current water temperature while powered.
        """
        code, value = self.current_temperature.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"current_temperature": value}

    def get_boiling(self) -> tuple[str, dict]:
        """
        Get whether the water is boiling while powered.
        """
        code, value = self.boiling.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"boiling": value}

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        Update water temperature during heating or keep-warm operation.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, []
        heating = self.heating.value
        keep_warm = self.keep_warm.value
        target = self.target_temperature.value
        current = self.current_temperature.value

        if powered and heating:
            current = min(round(current + 5.0, 1), target)
            code = self.current_temperature.internal_set(current)
            if code != "[PASS]":
                return code, []
            if current >= target:
                code = self.heating.internal_set(False)
                if code != "[PASS]":
                    return code, []
        elif powered and keep_warm and current < target:
            code = self.current_temperature.internal_set(target)
            if code != "[PASS]":
                return code, []

        current = self.current_temperature.value
        code = self.boiling.internal_set(current == 100.0)
        if code != "[PASS]":
            return code, []
        return "[PASS]", []

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        Stop heating and keep-warm maintenance after power is turned off.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, []

        if not powered:
            code = self.heating.internal_set(False)
            if code != "[PASS]":
                return code, []
            code = self.keep_warm.internal_set(False)
            if code != "[PASS]":
                return code, []

        return "[PASS]", []