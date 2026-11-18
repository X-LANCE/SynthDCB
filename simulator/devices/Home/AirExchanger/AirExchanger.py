# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class AirExchanger:
    """
    AirExchanger
    Description: Fresh-air exchanger. Users can query and set the ventilation mode and fan speed, and can query indoor and outdoor air quality and filter state. While running, the device draws in and filters outdoor air to gradually improve the air quality of its space; heat-exchange mode maintains ventilation while reducing the temperature changes.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool=None, ventilation_mode: str=None, fan_speed: int=None, indoor_air_quality: int=None, outdoor_air_quality: int=None, outdoor_temperature: float=None, filter_state: str=None, *, _defer_power_init: bool=False) -> None:
        _power_init_value = power if power is not None else False
        self.power = BoolProperty(name='power', description='Whether the air exchanger is powered.', default=False)
        self.ventilation_mode = StringProperty(name='ventilation_mode', description='Ventilation mode: normal exchanges air directly; heat_exchange maintains ventilation while reducing the temperature effect of incoming outdoor air.', default='normal', choices=['normal', 'heat_exchange'])
        self.fan_speed = IntProperty(name='fan_speed', description='Fan speed level used while the air exchanger is running.', default=1, minimum=1, maximum=3, step=1, step_origin=1)
        self.indoor_air_quality = IntProperty(name='indoor_air_quality', description='Device-reported indoor air quality index, synchronized on each tick with the containing Space air_quality value.', default=100, mode=2, minimum=0, maximum=500, step=1, step_origin=0)
        self.outdoor_air_quality = IntProperty(name='outdoor_air_quality', description='Outdoor air quality index used as the filtered incoming-air source.', default=50, mode=2, minimum=0, maximum=500, step=1, step_origin=0)
        self.outdoor_temperature = FloatProperty(name='outdoor_temperature', description='Outdoor air temperature used to calculate the ventilation temperature contribution.', default=10.0, mode=2, minimum=-50, maximum=80, precision=1)
        self.filter_state = StringProperty(name='filter_state', description='Current filter maintenance state. Normal provides full filtration, needs_cleaning provides half filtration, and replace provides no filtration improvement.', default='normal', mode=2, choices=['normal', 'needs_cleaning', 'replace'])
        code = self.power.internal_set(_power_init_value)
        if ventilation_mode is not None:
            code = self.ventilation_mode.internal_set(ventilation_mode)
        if fan_speed is not None:
            code = self.fan_speed.internal_set(fan_speed)
        if indoor_air_quality is not None:
            code = self.indoor_air_quality.internal_set(indoor_air_quality)
        if outdoor_air_quality is not None:
            code = self.outdoor_air_quality.internal_set(outdoor_air_quality)
        if outdoor_temperature is not None:
            code = self.outdoor_temperature.internal_set(outdoor_temperature)
        if filter_state is not None:
            code = self.filter_state.internal_set(filter_state)
        self._power_managed_properties = (self.ventilation_mode, self.fan_speed, self.indoor_air_quality, self.outdoor_air_quality, self.outdoor_temperature, self.filter_state)
        self._power_initialized = False
        self._disabled = {'properties': [], 'functions': [], 'events': []}
        if not _defer_power_init:
            self.set_power(_power_init_value)

    def get_power(self) -> tuple[str, dict]:
        """
        Get the current power state.
        """
        code, value = self.power.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'power': value})

    def set_power(self, value: bool) -> tuple[str, dict]:
        """
        Set power and update access for active dependent properties.
        """
        if self._power_initialized:
            current_code, current_value = self.power.get()
            if current_code != '[PASS]':
                return (current_code, {})
            if type(value) is bool and current_value == value:
                return ('[PASS]', {})
        code = self.power.set(value)
        if code != '[PASS]':
            return (code, {})
        for prop in self._power_managed_properties:
            switch_code = prop.handle_power_switch(value)
            if switch_code != '[PASS]' and (not switch_code.startswith('[NO_ACTION]')):
                return (switch_code, {})
        self._power_initialized = True
        return ('[PASS]', {})

    def get_ventilation_mode(self) -> tuple[str, dict]:
        code, power = self.power.get()
        if code != '[PASS]':
            return (code, {})
        if power is not True:
            return ('[ERROR] POWER_OFF', {})
        code, value = self.ventilation_mode.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'ventilation_mode': value})

    def set_ventilation_mode(self, value: str) -> tuple[str, dict]:
        code, power = self.power.get()
        if code != '[PASS]':
            return (code, {})
        if power is not True:
            return ('[ERROR] POWER_OFF', {})
        if type(value) is not str or value not in ('normal', 'heat_exchange'):
            return ('[ERROR] INVALID_VENTILATION_MODE', {})
        code = self.ventilation_mode.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_fan_speed(self) -> tuple[str, dict]:
        code, power = self.power.get()
        if code != '[PASS]':
            return (code, {})
        if power is not True:
            return ('[ERROR] POWER_OFF', {})
        code, value = self.fan_speed.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'fan_speed': value})

    def set_fan_speed(self, value: int) -> tuple[str, dict]:
        code, power = self.power.get()
        if code != '[PASS]':
            return (code, {})
        if power is not True:
            return ('[ERROR] POWER_OFF', {})
        if type(value) is not int or type(value) is bool or value < 1 or (value > 3):
            return ('[ERROR] INVALID_FAN_SPEED', {})
        code = self.fan_speed.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_indoor_air_quality(self) -> tuple[str, dict]:
        code, power = self.power.get()
        if code != '[PASS]':
            return (code, {})
        if power is not True:
            return ('[ERROR] POWER_OFF', {})
        code, value = self.indoor_air_quality.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'indoor_air_quality': value})

    def get_outdoor_air_quality(self) -> tuple[str, dict]:
        code, power = self.power.get()
        if code != '[PASS]':
            return (code, {})
        if power is not True:
            return ('[ERROR] POWER_OFF', {})
        code, value = self.outdoor_air_quality.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'outdoor_air_quality': value})

    def get_outdoor_temperature(self) -> tuple[str, dict]:
        code, power = self.power.get()
        if code != '[PASS]':
            return (code, {})
        if power is not True:
            return ('[ERROR] POWER_OFF', {})
        code, value = self.outdoor_temperature.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'outdoor_temperature': value})

    def get_filter_state(self) -> tuple[str, dict]:
        code, power = self.power.get()
        if code != '[PASS]':
            return (code, {})
        if power is not True:
            return ('[ERROR] POWER_OFF', {})
        code, value = self.filter_state.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'filter_state': value})

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        code, power = self.power.get()
        if code != '[PASS]':
            return (code, [])
        current_quality = context['space_state']['air_quality']
        code = self.indoor_air_quality.internal_set(current_quality)
        if code != '[PASS]':
            return (code, [])
        if power is not True:
            return ('[PASS]', [])
        code, mode = self.ventilation_mode.get()
        if code != '[PASS]':
            return (code, [])
        code, fan_speed = self.fan_speed.get()
        if code != '[PASS]':
            return (code, [])
        code, outdoor_quality = self.outdoor_air_quality.get()
        if code != '[PASS]':
            return (code, [])
        code, outdoor_temperature = self.outdoor_temperature.get()
        if code != '[PASS]':
            return (code, [])
        code, filter_state = self.filter_state.get()
        if code != '[PASS]':
            return (code, [])
        rate = fan_speed * 2
        if filter_state == 'needs_cleaning':
            rate = (rate + 1) // 2
        elif filter_state == 'replace':
            rate = 0
        effects = []
        if rate > 0 and current_quality != outdoor_quality:
            effects.append({'trigger': 'tick', 'source': context['object_id'], 'target': context['space_id'], 'function': 'approach', 'parameters': {'property': 'air_quality', 'value': outdoor_quality, 'rate_per_minute': rate, 'unit': 'AQI'}})
        temperature_difference = outdoor_temperature - context['space_state']['temperature']
        multiplier = 0.1 if mode == 'normal' else 0.02
        temperature_delta = round(multiplier * temperature_difference, 1)
        if temperature_delta != 0:
            effects.append({'trigger': 'tick', 'source': context['object_id'], 'target': context['space_id'], 'function': 'approach', 'parameters': {'property': 'temperature', 'value': outdoor_temperature, 'rate_per_minute': abs(temperature_delta), 'unit': 'degC'}})
        return ('[PASS]', effects)
