# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..WaterHeater import WaterHeater

class ElectricWaterHeater(WaterHeater):
    """
    ElectricWaterHeater
    Description: An electric-water-heater variant. It provides heat retention and stored-water volume-level settings.
    Version: 1.0.0
    Base: WaterHeater
    """

    def __init__(self, heat_retention: bool = None, stored_water_volume_level: str = None, *, power: bool | None = None, _defer_power_init: bool = False, **base_kwargs) -> None:
        _power_init_value = power if power is not None else False
        # initialize base WaterHeater class
        super().__init__(power=_power_init_value, _defer_power_init=True, **base_kwargs)
        # define properties
        self.heat_retention = BoolProperty(
            name='heat_retention',
            description='Whether heat retention is enabled as a configuration setting. This setting persists across power changes and does not change the heating enable setting.',
            default=False
        )
        self.stored_water_volume_level = StringProperty(
            name='stored_water_volume_level',
            description='Configured stored-water preparation level: low, medium, or high. This is a relative volume setting, not a measurement of available water or a change to physical tank capacity. It persists across power changes.',
            default='medium',
            choices=['low', 'medium', 'high']
        )

        # initialize properties
        if heat_retention is not None: code = self.heat_retention.internal_set(heat_retention)
        if stored_water_volume_level is not None: code = self.stored_water_volume_level.internal_set(stored_water_volume_level)
        self._power_managed_properties = (self.target_outlet_temperature, self.heating_state, self.heat_retention, self.stored_water_volume_level,)
        self._power_initialized = False
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

        if not _defer_power_init:
            self.set_power(_power_init_value)

    def get_heat_retention(self) -> tuple[str, dict]:
        """
        Return the configured heat-retention enable setting. Fails while power is false; does not change state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- heat_retention: Whether heat retention is configured as enabled. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        code, value = self.heat_retention.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"heat_retention": value}

    def set_heat_retention(self, value: bool) -> tuple[str, dict]:
        """
        Set the heat-retention enable setting to the supplied boolean while powered on. Changes only this configuration setting, without changing heating_state or target temperature. Returns an empty response on success. Invalid arguments or power being false cause failure and leave all state unchanged.

        Args:
        - value: Whether heat retention should be enabled.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        if type(value) is not bool:
            return "[ERROR] INVALID_TYPE", {}
        code = self.heat_retention.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_stored_water_volume_level(self) -> tuple[str, dict]:
        """
        Return the configured stored-water volume level as low, medium, or high. Fails while power is false; does not change state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- stored_water_volume_level: Configured relative stored-water preparation level: low, medium, or high. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        code, value = self.stored_water_volume_level.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"stored_water_volume_level": value}

    def set_stored_water_volume_level(self, value: str) -> tuple[str, dict]:
        """
        Set the stored-water preparation level while powered on. Accepts exactly low, medium, or high, in increasing relative volume order. Changes only the configured level; it does not report instantaneous water availability or alter physical tank capacity. Returns an empty response on success. Invalid arguments or power being false cause failure and leave all state unchanged.

        Args:
        - value: Desired relative stored-water preparation level. (choices=['low', 'medium', 'high'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        if type(value) is not str or value not in ('low', 'medium', 'high'):
            return "[ERROR] INVALID_VALUE", {}
        code = self.stored_water_volume_level.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}