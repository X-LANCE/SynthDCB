# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class RearEntertainmentDisplay:
    """
    RearEntertainmentDisplay
    Description: Rear entertainment display module. A projection entertainment screen at the rear of the cabin, supporting raising and lowering the projection screen, switching the projector on and off, and adjusting brightness.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, screen_position: str = None, brightness: int = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the rear entertainment projector is powered on.',
            default=False
        )
        self.screen_position = StringProperty(
            name='screen_position',
            description='Physical position of the projection screen. Raised means stowed; lowered means deployed for viewing.',
            default='raised',
            mode=2,
            choices=['raised', 'lowered']
        )
        self.brightness = IntProperty(
            name='brightness',
            description='Projector brightness setting as an integer percentage. The setting persists while powered off.',
            default=50,
            unit='%',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if screen_position is not None: code = self.screen_position.internal_set(screen_position)
        if brightness is not None: code = self.brightness.internal_set(brightness)
        self._power_managed_properties = (self.screen_position, self.brightness,)
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

    def get_screen_position(self) -> tuple[str, dict]:
        """
        Return whether the projection screen is raised or lowered. Projector power must be on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- screen_position: Current projection-screen position: raised or lowered. (type=string)

        Error Codes:
        - POWER_OFF: Projector power must be on to read the screen position.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if not powered:
            return "[POWER_OFF]", {}

        code, value = self.screen_position.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"screen_position": value}

    def raise_screen(self) -> tuple[str, dict]:
        """
        Raise the projection screen into its stowed position. The action is idempotent and requires projector power to be on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Projector power must be on to raise the screen.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if not powered:
            return "[POWER_OFF]", {}

        code = self.screen_position.internal_set("raised")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def lower_screen(self) -> tuple[str, dict]:
        """
        Lower the projection screen into its deployed viewing position. The action is idempotent and requires projector power to be on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Projector power must be on to lower the screen.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if not powered:
            return "[POWER_OFF]", {}

        code = self.screen_position.internal_set("lowered")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_brightness(self) -> tuple[str, dict]:
        """
        Return the projector brightness percentage. Projector power must be on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- brightness: Current projector brightness as an integer percentage from 0 through 100. (type=integer)

        Error Codes:
        - POWER_OFF: Projector power must be on to read brightness.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if not powered:
            return "[POWER_OFF]", {}

        code, value = self.brightness.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"brightness": value}

    def set_brightness(self, value: int) -> tuple[str, dict]:
        """
        Set projector brightness to an integer percentage from 0 through 100. Projector power must be on. Invalid input or an unmet power precondition leaves state unchanged.

        Args:
        - value:  (min=0, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Projector power must be on to change brightness.
        - INVALID_INPUT_ERROR: Brightness must be an integer from 0 through 100.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if not powered:
            return "[POWER_OFF]", {}

        code = self.brightness.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        When powered on, contribute illuminance to the containing Space equal to the brightness value in lux. When powered off, contribute zero illuminance. Repeated updates replace the previous contribution rather than accumulating it.

    Effect properties:
    - power: Determines whether the projector contributes illuminance.
    - brightness: Determines the projector illuminance contribution while powered on.
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