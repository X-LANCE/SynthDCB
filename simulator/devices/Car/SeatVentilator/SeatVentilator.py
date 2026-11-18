# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class SeatVentilator:
    """
    SeatVentilator
    Description: Seat ventilation module, instantiated for seats equipped with ventilation mechanisms. Supports switching on and off, ventilation levels, and operating-state queries. It provides local heat dissipation at the seat, is not a separate cooling air conditioner, and does not directly set seat air temperature. Seat surface temperature belongs to the seat Space.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, ventilation_level: int = None, dissipation_reference_temperature: float = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the seat ventilation mechanism is operating.',
            default=False
        )
        self.ventilation_level = IntProperty(
            name='ventilation_level',
            description='Selected ventilation intensity level, retained when the module is powered off.',
            default=1,
            minimum=1,
            maximum=3,
            step=1,
            step_origin=1
        )
        self.dissipation_reference_temperature = FloatProperty(
            name='dissipation_reference_temperature',
            description='Fixed internal seat-surface thermal reference used by the deterministic ventilation model. It is not a user temperature setting or a cabin temperature measurement.',
            default=22.0,
            mode=0,
            unit='degC',
            precision=1
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if ventilation_level is not None: code = self.ventilation_level.internal_set(ventilation_level)
        if dissipation_reference_temperature is not None: code = self.dissipation_reference_temperature.internal_set(dissipation_reference_temperature)
        self._power_managed_properties = (self.ventilation_level,)
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

    def get_ventilation_level(self) -> tuple[str, dict]:
        """
        Return the selected ventilation intensity level from 1 through 3. The module must be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- ventilation_level: Selected ventilation intensity level from 1 through 3. (type=integer)

        Error Codes:
        - POWER_OFF: The seat ventilation module must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        code, value = self.ventilation_level.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"ventilation_level": value}

    def set_ventilation_level(self, value: int) -> tuple[str, dict]:
        """
        Set the ventilation intensity to an integer level from 1 through 3. The module must be powered on. Invalid input or a failed power precondition leaves state unchanged.

        Args:
        - value:  (min=1, max=3)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The seat ventilation module must be powered on.
        - INVALID_INPUT_ERROR: Ventilation level must be an integer from 1 through 3.
        """
        if type(value) is not int or value < 1 or value > 3:
            return "[INVALID_INPUT_ERROR]", {}

        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        code = self.ventilation_level.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        While powered and the containing seat Space seat_temperature is above dissipation_reference_temperature, approach seat_temperature downward toward that reference by at most ventilation_level degrees Celsius per minute. Emit no effect while powered off, when the seat is at or below the reference, or once the reference is reached. Ventilation never heats the seat or reduces its temperature below the internal reference.

    Effect properties:
    - power: Determines whether seat ventilation produces heat dissipation.
    - ventilation_level: Determines the maximum seat-temperature reduction per minute.
    - dissipation_reference_temperature: Provides the local device-state target for seat-surface heat dissipation.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, []
        if powered is not True:
            return "[PASS]", []

        level_code, level = self.ventilation_level.get()
        if level_code != "[PASS]":
            return level_code, []

        reference = context["pre_state"]["objects"][context["object_id"]]["properties"]["dissipation_reference_temperature"]
        current_temperature = context["space_state"]["seat_temperature"]

        if current_temperature <= reference:
            return "[PASS]", []

        effect = {
            "trigger": "tick",
            "source": context["object_id"],
            "target": context["space_id"],
            "function": "approach",
            "parameters": {
                "property": "seat_temperature",
                "value": round(reference, 1),
                "rate_per_minute": level,
                "unit": "degC"
            }
        }
        return "[PASS]", [effect]