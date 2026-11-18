# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..BathroomHeater import BathroomHeater


class WarmAirBathroomHeater(BathroomHeater):
    """
    WarmAirBathroomHeater
    Description: A warm-air bathroom-heater variant. It switches between ventilation and air-supply functions through the fan mode, and heating can be enabled only after switching to the air-supply function.
    Version: 1.0.0
    Base: BathroomHeater
    """

    def __init__(self, fan: str = None, *, power: bool | None = None, _defer_power_init: bool = False, **base_kwargs) -> None:
        _power_init_value = power if power is not None else False
        # initialize base BathroomHeater class
        super().__init__(power=_power_init_value, _defer_power_init=True, **base_kwargs)
        # define properties
        self.fan = StringProperty(
            name='fan',
            description='Current fan function. ventilation exhausts bathroom air, while air_supply circulates warm air into the bathroom.',
            default='ventilation',
            choices=['ventilation', 'air_supply']
        )

        # initialize properties
        if fan is not None: code = self.fan.internal_set(fan)
        self._power_managed_properties = (self.lighting, self.heating, self.fan, self.heating_intensity,)
        self._power_initialized = False
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

        if not _defer_power_init:
            self.set_power(_power_init_value)

    def get_fan(self) -> tuple[str, dict]:
        """
        Get the current fan function. This operation is available only while the bathroom heater is powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- fan: Current fan function: ventilation or air_supply. (type=string)

        Error Codes:
        (no specified error codes)
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[ERROR] POWER_OFF", {}

        code, value = self.fan.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"fan": value}

    def set_fan(self, value: str) -> tuple[str, dict]:
        """
        Set the fan function to ventilation or air_supply. This operation is available only while the bathroom heater is powered. Changing the fan function does not automatically change the heating state.

        Args:
        - value: Desired fan function. (choices=['ventilation', 'air_supply'])

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
            return "[ERROR] POWER_OFF", {}
        if type(value) is not str or value not in ("ventilation", "air_supply"):
            return "[ERROR] INVALID_FAN_FUNCTION", {}

        code = self.fan.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def set_heating(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable bathroom heating. This operation is available only while the bathroom heater is powered. Heating may be enabled only when the fan function is air_supply; disabling heating is allowed in either fan function. Invalid requests leave the heating state unchanged.

        Args:
        - value: Desired heating state.

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
            return "[ERROR] POWER_OFF", {}
        if type(value) is not bool:
            return "[ERROR] INVALID_TYPE", {}

        fan_code, fan = self.fan.get()
        if fan_code != "[PASS]":
            return fan_code, {}
        if value is True and fan != "air_supply":
            return "[ERROR] INVALID_FAN_FUNCTION", {}

        code = self.heating.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}