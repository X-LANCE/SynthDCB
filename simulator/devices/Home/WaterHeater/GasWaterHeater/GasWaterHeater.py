# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..WaterHeater import WaterHeater

class GasWaterHeater(WaterHeater):
    """
    GasWaterHeater
    Description: A gas-water-heater variant. It provides instantaneous or recirculating hot-water control.
    Version: 1.0.0
    Base: WaterHeater
    """

    def __init__(self, water_delivery_mode: str = None, *, power: bool | None = None, _defer_power_init: bool = False, **base_kwargs) -> None:
        _power_init_value = power if power is not None else False
        # initialize base WaterHeater class
        super().__init__(power=_power_init_value, _defer_power_init=True, **base_kwargs)
        # define properties
        self.water_delivery_mode = StringProperty(
            name='water_delivery_mode',
            description='Hot-water delivery mode.',
            default='instantaneous',
            choices=['instantaneous', 'recirculating']
        )

        # initialize properties
        if water_delivery_mode is not None: code = self.water_delivery_mode.internal_set(water_delivery_mode)
        self._power_managed_properties = (self.target_outlet_temperature, self.heating_state, self.water_delivery_mode,)
        self._power_initialized = False
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

        if not _defer_power_init:
            self.set_power(_power_init_value)

    def get_water_delivery_mode(self) -> tuple[str, dict]:
        """
        Return whether the gas water heater is configured for instantaneous or recirculating hot-water delivery. This operation fails while the water heater is powered off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- water_delivery_mode: Configured hot-water delivery mode. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        code, value = self.water_delivery_mode.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"water_delivery_mode": value}

    def set_water_delivery_mode(self, value: str) -> tuple[str, dict]:
        """
        Set the hot-water delivery mode while powered on. The value must be instantaneous or recirculating; invalid values leave the state unchanged.

        Args:
        - value: Hot-water delivery mode. (choices=['instantaneous', 'recirculating'])

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
        if type(value) is not str or value not in ("instantaneous", "recirculating"):
            return "[ERROR] INVALID_VALUE", {}
        code = self.water_delivery_mode.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}