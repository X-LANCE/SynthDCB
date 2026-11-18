# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty


class BathroomHeater:
    """
    BathroomHeater
    Description: Bathroom heater. Users can separately query and set the lighting, heating, and fan states, and can set the heating intensity. Heating changes space temperature; lighting changes space brightness.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, lighting: bool = None, heating: bool = None, fan: bool = None, heating_intensity: int = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the bathroom heater has electrical power.',
            default=False
        )
        self.lighting = BoolProperty(
            name='lighting',
            description='Whether the bathroom heater lighting is enabled.',
            default=False
        )
        self.heating = BoolProperty(
            name='heating',
            description='Whether the bathroom heater is enabled for heating.',
            default=False
        )
        self.fan = BoolProperty(
            name='fan',
            description='Whether the bathroom heater fan is enabled.',
            default=False
        )
        self.heating_intensity = IntProperty(
            name='heating_intensity',
            description='Heating intensity level used when heating is enabled.',
            default=1,
            minimum=1,
            maximum=3,
            step=1,
            step_origin=1
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if lighting is not None: code = self.lighting.internal_set(lighting)
        if heating is not None: code = self.heating.internal_set(heating)
        if fan is not None: code = self.fan.internal_set(fan)
        if heating_intensity is not None: code = self.heating_intensity.internal_set(heating_intensity)
        self._power_managed_properties = (self.lighting, self.heating, self.fan, self.heating_intensity,)
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

    def get_lighting(self) -> tuple[str, dict]:
        """
        Get the lighting state. This operation is available only while the bathroom heater is powered.
        """
        code, value = self.lighting.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"lighting": value}

    def set_lighting(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable the bathroom heater lighting. This operation is available only while the bathroom heater is powered.
        """
        code = self.lighting.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_heating(self) -> tuple[str, dict]:
        """
        Get the heating state. This operation is available only while the bathroom heater is powered.
        """
        code, value = self.heating.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"heating": value}

    def set_heating(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable bathroom heating. This operation is available only while the bathroom heater is powered.
        """
        code = self.heating.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_fan(self) -> tuple[str, dict]:
        """
        Get the fan state. This operation is available only while the bathroom heater is powered.
        """
        code, value = self.fan.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"fan": value}

    def set_fan(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable the bathroom heater fan. This operation is available only while the bathroom heater is powered.
        """
        code = self.fan.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_heating_intensity(self) -> tuple[str, dict]:
        """
        Get the configured heating intensity. This operation is available only while the bathroom heater is powered.
        """
        code, value = self.heating_intensity.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"heating_intensity": value}

    def set_heating_intensity(self, value: int) -> tuple[str, dict]:
        """
        Set the heating intensity to an integer from 1 through 3. This operation is available only while the bathroom heater is powered. Invalid values leave the intensity unchanged.
        """
        code = self.heating_intensity.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        After a successful mutation, update this device's absolute contributions to the containing Home space. If power and lighting are both true, set the device's illuminance contribution to 300 lux; otherwise set its illuminance contribution to 0 lux. If power and heating are both true, set its temperature contribution to 0.5 degrees Celsius multiplied by heating_intensity; otherwise set its temperature contribution to 0 degrees Celsius. The lighting and temperature contributions are independent and are recalculated whenever this event is dispatched.

        Effect properties:
        - power: Whether the bathroom heater has electrical power.
        - lighting: Whether bathroom lighting is enabled.
        - heating: Whether bathroom heating is enabled.
        - heating_intensity: Configured heating intensity used to calculate the temperature contribution.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, []

        lighting = self.lighting.value

        heating = self.heating.value

        intensity = self.heating_intensity.value

        illuminance = 300 if powered is True and lighting is True else 0
        temperature = round(0.5 * intensity, 1) if powered is True and heating is True else 0

        effects = [
            {
                'trigger': 'after_action',
                'source': context['object_id'],
                'target': context['space_id'],
                'function': 'set_contribution',
                'parameters': {
                    'property': 'illuminance',
                    'value': illuminance,
                    'unit': 'lux'
                }
            },
            {
                'trigger': 'after_action',
                'source': context['object_id'],
                'target': context['space_id'],
                'function': 'set_contribution',
                'parameters': {
                    'property': 'temperature',
                    'value': temperature,
                    'unit': 'degC'
                }
            }
        ]
        return "[PASS]", effects