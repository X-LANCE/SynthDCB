# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class SeatHeater:
    """
    SeatHeater
    Description: Seat heating function. Supports switching on and off and adjusting seat temperature. When enabled, the temperature of the seat Space gradually rises toward the target; the device cannot actively cool. When disabled, the temperature gradually approaches cabin temperature.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, target_temperature: int = None, cabin_temperature_reference: int = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether seat heating is powered on.',
            default=False
        )
        self.target_temperature = IntProperty(
            name='target_temperature',
            description='Requested heating target for the containing seat Space.',
            default=28,
            unit='degC',
            minimum=16,
            maximum=35,
            step=1,
            step_origin=16
        )
        self.cabin_temperature_reference = IntProperty(
            name='cabin_temperature_reference',
            description='Deterministic passive equilibrium reference representing cabin temperature. While the heater is off, the containing seat Space approaches this temperature.',
            default=22,
            unit='degC',
            minimum=-50,
            maximum=80,
            step=1,
            step_origin=-50
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if target_temperature is not None: code = self.target_temperature.internal_set(target_temperature)
        if cabin_temperature_reference is not None: code = self.cabin_temperature_reference.internal_set(cabin_temperature_reference)
        self._power_managed_properties = (self.target_temperature, self.cabin_temperature_reference,)
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
        Return the requested heating target for the seat. Requires the seat heater to be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- target_temperature: Requested heating target in degrees Celsius. (type=integer)

        Error Codes:
        - POWER_OFF: The seat heater must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.target_temperature.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"target_temperature": value}

    def set_target_temperature(self, value: int) -> tuple[str, dict]:
        """
        Set the heating target to an integer from 16 through 35 degrees Celsius. Requires the seat heater to be powered on. Invalid input or a failed power precondition leaves state unchanged.

        Args:
        - value:  (min=16, max=35)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The seat heater must be powered on.
        - INVALID_INPUT_ERROR: Target temperature must be an integer from 16 through 35 degrees Celsius.
        """
        if type(value) is not int or value < 16 or value > 35:
            return "[INVALID_INPUT_ERROR]", {}
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code = self.target_temperature.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_cabin_temperature_reference(self) -> tuple[str, dict]:
        """
        Return the deterministic cabin-temperature reference used for passive seat-temperature equalization. Requires the seat heater to be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- cabin_temperature_reference: Passive equilibrium reference in degrees Celsius. (type=integer)

        Error Codes:
        - POWER_OFF: The seat heater must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.cabin_temperature_reference.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"cabin_temperature_reference": value}

    def set_cabin_temperature_reference(self, value: int) -> tuple[str, dict]:
        """
        Set the deterministic cabin-temperature reference used after power-off to an integer from -50 through 80 degrees Celsius. This setting must represent the cabin temperature for the simulated scenario. Requires the seat heater to be powered on. Invalid input or a failed power precondition leaves state unchanged.

        Args:
        - value:  (min=-50, max=80)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The seat heater must be powered on.
        - INVALID_INPUT_ERROR: Cabin temperature reference must be an integer from -50 through 80 degrees Celsius.
        """
        if type(value) is not int or value < -50 or value > 80:
            return "[INVALID_INPUT_ERROR]", {}
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code = self.cabin_temperature_reference.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        While powered on and the containing seat Space seat_temperature is below target_temperature, approach target_temperature by at most 1 degree Celsius per minute; emit no effect when the seat is at or above the target, so the heater never actively cools. While powered off, approach cabin_temperature_reference from either direction by at most 1 degree Celsius per minute. Emit no effect when the applicable target has already been reached.

    Effect properties:
    - power: Determines whether the seat is actively heated or passively approaches equilibrium.
    - target_temperature: Determines the active heating target while power is on.
    - cabin_temperature_reference: Determines the passive equilibrium target while power is off.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, []

        current = context["space_state"]["seat_temperature"]
        if powered:
            target_code, target = self.target_temperature.get()
            if target_code != "[PASS]":
                return target_code, []
            if current >= target:
                return "[PASS]", []
        else:
            target = context["pre_state"]["objects"][context["object_id"]]["properties"]["cabin_temperature_reference"]
            if current == target:
                return "[PASS]", []

        effect = {
            "trigger": "tick",
            "source": context["object_id"],
            "target": context["space_id"],
            "function": "approach",
            "parameters": {
                "property": "seat_temperature",
                "value": target,
                "rate_per_minute": 1,
                "unit": "degC"
            }
        }
        return "[PASS]", [effect]