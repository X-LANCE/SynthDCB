# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class PetFeeder:
    """
    PetFeeder
    Description: Pet feeder. Users can query and set the feeding portion and feeding mode, perform an immediate-feeding action, and query the remaining food in the hopper. A feeding action dispenses the configured portion; if the hopper contains insufficient food or the device is jammed, it cannot complete the full feeding.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, feeding_portion: int = None, feeding_mode: str = None, remaining_food: int = None, jammed: bool = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the feeder is powered.',
            default=False
        )
        self.feeding_portion = IntProperty(
            name='feeding_portion',
            description='Configured amount dispensed by one feeding action, in portions.',
            default=1,
            minimum=1,
            maximum=5,
            step=1,
            step_origin=1
        )
        self.feeding_mode = StringProperty(
            name='feeding_mode',
            description='Feeding mode used by the immediate-feeding action.',
            default='normal',
            choices=['normal', 'slow']
        )
        self.remaining_food = IntProperty(
            name='remaining_food',
            description='Food remaining in the hopper, in portions.',
            default=20,
            mode=2,
            minimum=0,
            maximum=1000,
            step=1,
            step_origin=0
        )
        self.jammed = BoolProperty(
            name='jammed',
            description='Whether the dispensing mechanism is jammed.',
            default=False,
            mode=2
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if feeding_portion is not None: code = self.feeding_portion.internal_set(feeding_portion)
        if feeding_mode is not None: code = self.feeding_mode.internal_set(feeding_mode)
        if remaining_food is not None: code = self.remaining_food.internal_set(remaining_food)
        if jammed is not None: code = self.jammed.internal_set(jammed)
        self._power_managed_properties = (self.feeding_portion, self.feeding_mode, self.remaining_food, self.jammed,)
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

    def get_feeding_portion(self) -> tuple[str, dict]:
        """
        Return the configured feeding portion while the feeder is powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- feeding_portion: Configured portions dispensed per feeding. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.feeding_portion.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"feeding_portion": value}

    def set_feeding_portion(self, value: int) -> tuple[str, dict]:
        """
        Set the feeding portion to an integer from 1 through 5 while the feeder is powered. Invalid values leave the setting unchanged.

        Args:
        - value:  (min=1, max=5)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        if type(value) is not int or isinstance(value, bool) or value < 1 or value > 5:
            return "[INVALID_VALUE]", {}
        code = self.feeding_portion.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_feeding_mode(self) -> tuple[str, dict]:
        """
        Return the feeding mode while the feeder is powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- feeding_mode: Current feeding mode. (type=string)

        Error Codes:
        (no specified error codes)
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.feeding_mode.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"feeding_mode": value}

    def set_feeding_mode(self, value: str) -> tuple[str, dict]:
        """
        Set the feeding mode to normal or slow while the feeder is powered.

        Args:
        - value:  (choices=['normal', 'slow'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        if type(value) is not str or value not in ("normal", "slow"):
            return "[INVALID_VALUE]", {}
        code = self.feeding_mode.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_remaining_food(self) -> tuple[str, dict]:
        """
        Return the remaining food in the hopper while the feeder is powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- remaining_food: Food remaining in the hopper, in portions. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.remaining_food.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"remaining_food": value}

    def feed_now(self) -> tuple[str, dict]:
        """
        Immediately dispense the configured feeding portion while powered. The action deducts the full portion only when the hopper contains at least that many portions and the dispensing mechanism is not jammed. Otherwise it fails atomically and leaves the hopper unchanged.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- success: Whether the full configured portion was dispensed. (type=boolean)

        Error Codes:
        - powered_off: The feeder is not powered.
        - insufficient_food: The hopper contains fewer portions than configured.
        - jammed: The dispensing mechanism is jammed.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[powered_off]", {}

        portion_code, portion = self.feeding_portion.get()
        if portion_code != "[PASS]":
            return portion_code, {}
        food_code, food = self.remaining_food.get()
        if food_code != "[PASS]":
            return food_code, {}
        jammed_code, jammed = self.jammed.get()
        if jammed_code != "[PASS]":
            return jammed_code, {}

        if jammed is True:
            return "[jammed]", {"success": False}
        if food < portion:
            return "[insufficient_food]", {"success": False}

        code = self.remaining_food.internal_set(food - portion)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"success": True}