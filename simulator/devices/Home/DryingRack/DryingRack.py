# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class DryingRack:
    """
    DryingRack
    Description: Clothes-drying rack. Users can query and set the current height, and the device supports lighting. Raising or lowering it changes the position of the drying rods.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, height: int = None, light: bool = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the drying rack is powered.',
            default=False
        )
        self.height = IntProperty(
            name='height',
            description='Current height of the drying rods.',
            default=50,
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.light = BoolProperty(
            name='light',
            description='Whether the drying rack light is on.',
            default=False
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if height is not None: code = self.height.internal_set(height)
        if light is not None: code = self.light.internal_set(light)
        self._power_managed_properties = (self.height, self.light,)
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

    def get_height(self) -> tuple[str, dict]:
        """
        Return the current drying-rod height while the rack is powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- height: Current drying-rod height. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.height.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"height": value}

    def set_height(self, value: int) -> tuple[str, dict]:
        """
        Set the drying-rod height to an integer from 0 through 100 while the rack is powered. Invalid values leave the height unchanged.

        Args:
        - value: Desired drying-rod height. (min=0, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.height.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_light(self) -> tuple[str, dict]:
        """
        Return whether the drying rack light is on while the rack is powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- light: Whether the drying rack light is on. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.light.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"light": value}

    def set_light(self, value: bool) -> tuple[str, dict]:
        """
        Turn the drying rack light on or off while the rack is powered.

        Args:
        - value: Whether the light should be on.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.light.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        Recalculate the drying rack's illuminance contribution after a successful change to power, height, or light. When the rack is powered and its light is on, emit an illuminance contribution that increases with the rod height; otherwise emit a zero contribution.

        Effect properties:
        - power: Whether the drying rack is powered.
        - height: Current height of the drying rods.
        - light: Whether the drying rack light is on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, []
        lit = self.light.value
        height = self.height.value

        contribution = height if powered is True and lit is True else 0
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