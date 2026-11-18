# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Heater:
    """
    Heater
    Description: Electric heater. Users can query and set the target temperature, heating mode, and heating intensity. While running and when space temperature is below the target, the device produces a heating effect; it stops heating after the target is reached.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, target_temperature: float = None, heating_mode: str = None, heating_intensity: int = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the heater is electrically powered.',
            default=False
        )
        self.target_temperature = FloatProperty(
            name='target_temperature',
            description='Desired room temperature at which the heater stops producing heat.',
            default=21.0,
            unit='degC',
            minimum=16.0,
            maximum=30.0,
            step=0.5,
            step_origin=0.0,
            precision=1
        )
        self.heating_mode = StringProperty(
            name='heating_mode',
            description='Heating behavior selected for the heater. The off mode disables heating while retaining the configured target temperature and intensity.',
            default='off',
            choices=['off', 'heat']
        )
        self.heating_intensity = IntProperty(
            name='heating_intensity',
            description='Heating intensity used while heating is enabled.',
            default=3,
            minimum=1,
            maximum=5,
            step=1,
            step_origin=1
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if target_temperature is not None: code = self.target_temperature.internal_set(target_temperature)
        if heating_mode is not None: code = self.heating_mode.internal_set(heating_mode)
        if heating_intensity is not None: code = self.heating_intensity.internal_set(heating_intensity)
        self._power_managed_properties = (self.target_temperature, self.heating_mode, self.heating_intensity,)
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
        Return the configured target temperature while the heater is powered.
        """
        code, value = self.target_temperature.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"target_temperature": value}

    def set_target_temperature(self, value: float) -> tuple[str, dict]:
        """
        Set the target room temperature while the heater is powered. Values must be between 16.0 and 30.0 degrees Celsius in 0.5-degree increments; invalid values leave the state unchanged.
        """
        code = self.target_temperature.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_heating_mode(self) -> tuple[str, dict]:
        """
        Return the selected heating mode while the heater is powered.
        """
        code, value = self.heating_mode.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"heating_mode": value}

    def set_heating_mode(self, value: str) -> tuple[str, dict]:
        """
        Set the heating mode while the heater is powered. The heat mode permits temperature-controlled heating; the off mode stops heating. Invalid modes leave the state unchanged.
        """
        code = self.heating_mode.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_heating_intensity(self) -> tuple[str, dict]:
        """
        Return the configured heating intensity while the heater is powered.
        """
        code, value = self.heating_intensity.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"heating_intensity": value}

    def set_heating_intensity(self, value: int) -> tuple[str, dict]:
        """
        Set the heating intensity while the heater is powered. The value must be an integer from 1 through 5; invalid values leave the state unchanged.
        """
        code = self.heating_intensity.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        While powered and in heat mode, compare the room temperature from space_state with target_temperature. If the room is below the target, emit an approach effect toward target_temperature, with the heating rate determined by heating_intensity. If the room is at or above the target, or if the heater is unpowered or in off mode, emit a zero temperature contribution so that no heating remains active.

        Effect properties:
        - power: Whether the heater is electrically powered.
        - target_temperature: Desired room temperature.
        - heating_mode: Selected heating mode.
        - heating_intensity: Configured heating intensity.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, []
        mode = self.heating_mode.value
        target_temperature = self.target_temperature.value
        intensity = self.heating_intensity.value

        source = context["object_id"]
        target = context["space_id"]
        room_temperature = context["space_state"]["temperature"]

        if powered is True and mode == "heat" and room_temperature < target_temperature:
            rate = round(0.2 * intensity, 1)
            return "[PASS]", [{
                "trigger": "tick",
                "source": source,
                "target": target,
                "function": "approach",
                "parameters": {
                    "property": "temperature",
                    "value": target_temperature,
                    "rate_per_minute": rate,
                    "unit": "degC"
                }
            }]

        return "[PASS]", [{
            "trigger": "tick",
            "source": source,
            "target": target,
            "function": "set_contribution",
            "parameters": {
                "property": "temperature",
                "value": 0,
                "unit": "degC"
            }
        }]