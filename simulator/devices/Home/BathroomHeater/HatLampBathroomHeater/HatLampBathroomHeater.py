# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..BathroomHeater import BathroomHeater


class HatLampBathroomHeater(BathroomHeater):
    """
    HatLampBathroomHeater
    Description: A heat-lamp bathroom-heater variant. Its heating mode changes space brightness.
    Version: 1.0.0
    Base: BathroomHeater
    """

    def __init__(self, *, power: bool | None = None, _defer_power_init: bool = False, **base_kwargs) -> None:
        _power_init_value = power if power is not None else False
        # initialize base BathroomHeater class
        super().__init__(power=_power_init_value, _defer_power_init=True, **base_kwargs)
        # define properties
        self._power_managed_properties = (self.lighting, self.heating, self.fan, self.heating_intensity,)
        self._power_initialized = False
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

        if not _defer_power_init:
            self.set_power(_power_init_value)

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        After a successful mutation, update this device's absolute illuminance contribution to the containing Home space. If power and lighting are both true, contribute 300 lux from lighting. If power and heating are both true, additionally contribute 300 lux multiplied by heating_intensity from the heat lamp. The total illuminance contribution is the sum of these independent contributions, and is recalculated whenever this event is dispatched.

        Effect properties:
        - power: Whether the bathroom heater has electrical power.
        - lighting: Whether lighting is enabled.
        - heating: Whether heating is enabled.
        - heating_intensity: Configured intensity used to calculate the heat-lamp illuminance contribution.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return power_code, []

        contribution = 0
        if powered is True:
            lighting_code, lighting = self.lighting.get()
            if lighting_code != '[PASS]':
                return lighting_code, []

            heating_code, heating = self.heating.get()
            if heating_code != '[PASS]':
                return heating_code, []

            intensity_code, intensity = self.heating_intensity.get()
            if intensity_code != '[PASS]':
                return intensity_code, []

            if lighting is True:
                contribution += 300
            if heating is True:
                contribution += 300 * intensity

        effect = {
            'trigger': 'after_action',
            'source': context['object_id'],
            'target': context['space_id'],
            'function': 'set_contribution',
            'parameters': {
                'property': 'illuminance',
                'value': contribution,
                'unit': 'lux'
            }
        }
        return '[PASS]', [effect]