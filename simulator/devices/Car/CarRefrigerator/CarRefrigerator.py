# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class CarRefrigerator:
    """
    CarRefrigerator
    Description: Vehicle refrigerator. Supports switching on and off, target temperature, and queries of internal temperature and operating state. Internal temperature changes through the cooling process and is separate from the shared cabin temperature. The base class cannot actively heat.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, target_temperature: int = None, internal_temperature: int = None, operating_state: str = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the vehicle refrigerator is powered.',
            default=False
        )
        self.target_temperature = IntProperty(
            name='target_temperature',
            description='Requested refrigerator internal temperature.',
            default=4,
            unit='degC',
            minimum=0,
            maximum=15,
            step=1,
            step_origin=0
        )
        self.internal_temperature = IntProperty(
            name='internal_temperature',
            description='Current temperature inside the refrigerator compartment. This value is separate from cabin temperature and is updated by the cooling process.',
            default=20,
            mode=2,
            unit='degC',
            minimum=-50,
            maximum=80,
            step=1,
            step_origin=-50
        )
        self.operating_state = StringProperty(
            name='operating_state',
            description='Cooling activity recorded by the most recent minute update while the device is accessible.',
            default='idle',
            mode=2,
            choices=['idle', 'cooling']
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if target_temperature is not None: code = self.target_temperature.internal_set(target_temperature)
        if internal_temperature is not None: code = self.internal_temperature.internal_set(internal_temperature)
        if operating_state is not None: code = self.operating_state.internal_set(operating_state)
        self._power_managed_properties = (self.target_temperature, self.internal_temperature, self.operating_state,)
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
        Return the configured target temperature in degrees Celsius. Requires power on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- target_temperature: Configured refrigerator target temperature in degrees Celsius. (type=integer)

        Error Codes:
        - POWER_OFF: The refrigerator must be powered on.
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
        Set the target temperature to an integer from 0 through 15 degrees Celsius. The base refrigerator cools toward the target but does not actively heat if its internal temperature is already below the target. Invalid input or an off power state leaves all properties unchanged.

        Args:
        - value:  (min=0, max=15)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The refrigerator must be powered on.
        - INVALID_INPUT_ERROR: Target temperature must be an integer from 0 through 15 degrees Celsius.
        """
        if type(value) is not int or value < 0 or value > 15:
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

    def get_internal_temperature(self) -> tuple[str, dict]:
        """
        Return the current refrigerator-compartment temperature in degrees Celsius. This is not the shared cabin temperature. Requires power on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- internal_temperature: Current temperature inside the refrigerator compartment in degrees Celsius. (type=integer)

        Error Codes:
        - POWER_OFF: The refrigerator must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.internal_temperature.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"internal_temperature": value}

    def get_operating_state(self) -> tuple[str, dict]:
        """
        Return whether the refrigerator was idle or cooling at the most recent minute update. Requires power on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- operating_state: Most recently evaluated activity: idle or cooling. (type=string)

        Error Codes:
        - POWER_OFF: The refrigerator must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.operating_state.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"operating_state": value}

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        Each minute while powered, lower internal_temperature toward target_temperature by at most 1 degree Celsius and report cooling while the temperature remains above the target. Stop at the target. If internal_temperature is at or below the target, leave it unchanged and report idle; never raise the internal temperature. While unpowered, leave internal_temperature unchanged and report idle.

    Effect properties:
    - power: Determines whether the cooling process may run.
    - target_temperature: Lower temperature limit approached by active cooling.
    - internal_temperature: Current compartment temperature used to determine cooling progress.
    - operating_state: Activity state updated by each minute evaluation to cooling or idle.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, []

        if powered is not True:
            state_code = self.operating_state.internal_set("idle")
            if state_code != "[PASS]":
                return state_code, []
            return "[PASS]", []

        target_code, target = self.target_temperature.get()
        if target_code != "[PASS]":
            return target_code, []

        temperature_code, current_temperature = self.internal_temperature.get()
        if temperature_code != "[PASS]":
            return temperature_code, []

        if current_temperature <= target:
            state_code = self.operating_state.internal_set("idle")
            if state_code != "[PASS]":
                return state_code, []
            return "[PASS]", []

        next_temperature = max(target, current_temperature - 1)
        temperature_code = self.internal_temperature.internal_set(next_temperature)
        if temperature_code != "[PASS]":
            return temperature_code, []

        state_code = self.operating_state.internal_set("cooling")
        if state_code != "[PASS]":
            return state_code, []

        return "[PASS]", []