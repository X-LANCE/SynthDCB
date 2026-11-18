# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..Humidifier import Humidifier

class EvaporativeHumidifier(Humidifier):
    """
    EvaporativeHumidifier
    Description: A humidifier subclass that uses a fan to move air through a wet medium and increase humidity through natural evaporation. It inherits all functions and properties.
    Version: 1.0.0
    Base: Humidifier
    """

    def __init__(self, *, power: bool | None = None, _defer_power_init: bool = False, **base_kwargs) -> None:
        _power_init_value = power if power is not None else False
        # initialize base Humidifier class
        super().__init__(power=_power_init_value, _defer_power_init=True, **base_kwargs)
        # define properties
        self._power_managed_properties = (self.sleep_mode, self.target_humidity, self.humidification_intensity,)
        self._power_initialized = False
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

        if not _defer_power_init:
            self.set_power(_power_init_value)

    pass