# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..CarRefrigerator import CarRefrigerator

class CoolingHeatingCarRefrigerator(CarRefrigerator):
    """
    CoolingHeatingCarRefrigerator
    Description: Vehicle refrigerator with cooling and heating. Adds a heating mode and target temperature ranges specific to each mode.
    Version: 1.0.0
    Base: CarRefrigerator
    """

    def __init__(self, mode: str = None, target_temperature: int = None, internal_temperature: int = None, operating_state: str = None, *, power: bool | None = None, _defer_power_init: bool = False, **base_kwargs) -> None:
        _power_init_value = power if power is not None else False
        # initialize base CarRefrigerator class
        super().__init__(power=_power_init_value, _defer_power_init=True, **base_kwargs)
        # define properties
        self.mode = StringProperty(
            name='mode',
            description='Selected refrigerator temperature-control mode.',
            default='cooling',
            choices=['cooling', 'heating']
        )
        self.target_temperature = IntProperty(
            name='target_temperature',
            description='Requested compartment temperature. Valid targets are 0 through 15 degrees Celsius in cooling mode and 35 through 50 degrees Celsius in heating mode.',
            default=4,
            unit='degC',
            minimum=0,
            maximum=50,
            step=1,
            step_origin=0
        )
        self.internal_temperature = IntProperty(
            name='internal_temperature',
            description='Current temperature inside the refrigerator compartment. This value is separate from cabin temperature and is updated by the cooling or heating temperature-control process.',
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
            description='Temperature-control activity recorded by the most recent minute update. It is set to idle when the device is unpowered.',
            default='idle',
            mode=2,
            choices=['idle', 'cooling', 'heating']
        )

        # initialize properties
        if mode is not None: code = self.mode.internal_set(mode)
        if target_temperature is not None: code = self.target_temperature.internal_set(target_temperature)
        if internal_temperature is not None: code = self.internal_temperature.internal_set(internal_temperature)
        if operating_state is not None: code = self.operating_state.internal_set(operating_state)
        self._power_managed_properties = (self.target_temperature, self.internal_temperature, self.operating_state, self.mode,)
        self._power_initialized = False
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

        if not _defer_power_init:
            self.set_power(_power_init_value)

    def get_mode(self) -> tuple[str, dict]:
        """
        Return the selected cooling or heating mode. Requires power on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- mode: Selected refrigerator mode: cooling or heating. (type=string)

        Error Codes:
        - POWER_OFF: The refrigerator must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        code, value = self.mode.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"mode": value}

    def set_mode(self, value: str) -> tuple[str, dict]:
        """
        Select cooling or heating mode. Requires power on. When the selected mode differs from the current mode, target_temperature is reset to 4 degrees Celsius for cooling or 40 degrees Celsius for heating so the resulting configuration is valid. Selecting the current mode leaves the existing target unchanged. Invalid input or an off power state leaves all properties unchanged.

        Args:
        - value:  (choices=['cooling', 'heating'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The refrigerator must be powered on.
        - INVALID_INPUT_ERROR: Mode must be cooling or heating.
        """
        if type(value) is not str or value not in ("cooling", "heating"):
            return "[INVALID_INPUT_ERROR]", {}

        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        mode_code, current_mode = self.mode.get()
        if mode_code != "[PASS]":
            return mode_code, {}
        if current_mode == value:
            return "[PASS]", {}

        reset_target = 4 if value == "cooling" else 40

        target_code = self.target_temperature.set(reset_target)
        if target_code != "[PASS]":
            return target_code, {}

        mode_code = self.mode.set(value)
        if mode_code != "[PASS]":
            return mode_code, {}

        return "[PASS]", {}

    def set_target_temperature(self, value: int) -> tuple[str, dict]:
        """
        Set the target temperature for the selected mode. Cooling mode accepts integers from 0 through 15 degrees Celsius; heating mode accepts integers from 35 through 50 degrees Celsius. Invalid input, a target outside the selected mode's range, or an off power state leaves all properties unchanged.

        Args:
        - value:  (min=0, max=50)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The refrigerator must be powered on.
        - INVALID_INPUT_ERROR: Target temperature must be an integer from 0 through 15 degrees Celsius in cooling mode or from 35 through 50 degrees Celsius in heating mode.
        """
        if type(value) is not int or value < 0 or value > 50:
            return "[INVALID_INPUT_ERROR]", {}

        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        mode_code, current_mode = self.mode.get()
        if mode_code != "[PASS]":
            return mode_code, {}

        if current_mode == "cooling":
            if value > 15:
                return "[INVALID_INPUT_ERROR]", {}
        elif current_mode == "heating":
            if value < 35:
                return "[INVALID_INPUT_ERROR]", {}
        else:
            return "[INVALID_INPUT_ERROR]", {}

        code = self.target_temperature.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_operating_state(self) -> tuple[str, dict]:
        """
        Return whether the refrigerator was idle, cooling, or heating at the most recent minute update. Requires power on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- operating_state: Most recently evaluated activity: idle, cooling, or heating. (type=string)

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
        Each minute while powered in cooling mode, lower internal_temperature toward target_temperature by at most 1 degree Celsius without heating; report cooling when a decrease occurs and idle when already at or below the target. Each minute while powered in heating mode, raise internal_temperature toward target_temperature by at most 1 degree Celsius without cooling; report heating when an increase occurs and idle when already at or above the target. Never overshoot the target. While unpowered, leave internal_temperature unchanged and report idle.

    Effect properties:
    - power: Determines whether temperature control may run.
    - mode: Determines whether the device may cool or heat.
    - target_temperature: Mode-compatible compartment temperature approached by active control.
    - internal_temperature: Current compartment temperature used to determine temperature-control progress.
    - operating_state: Activity state updated by each minute evaluation to idle, cooling, or heating.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, []

        if powered is not True:
            state_code = self.operating_state.internal_set("idle")
            if state_code != "[PASS]":
                return state_code, []
            return "[PASS]", []

        mode_code, current_mode = self.mode.get()
        if mode_code != "[PASS]":
            return mode_code, []

        target_code, target = self.target_temperature.get()
        if target_code != "[PASS]":
            return target_code, []

        temperature_code, current_temperature = self.internal_temperature.get()
        if temperature_code != "[PASS]":
            return temperature_code, []

        if current_mode == "cooling":
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

        if current_mode == "heating":
            if current_temperature >= target:
                state_code = self.operating_state.internal_set("idle")
                if state_code != "[PASS]":
                    return state_code, []
                return "[PASS]", []

            next_temperature = min(target, current_temperature + 1)
            temperature_code = self.internal_temperature.internal_set(next_temperature)
            if temperature_code != "[PASS]":
                return temperature_code, []

            state_code = self.operating_state.internal_set("heating")
            if state_code != "[PASS]":
                return state_code, []
            return "[PASS]", []

        return "[INVALID_INPUT_ERROR]", []