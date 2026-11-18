# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class RangeHood:
    """
    RangeHood
    Description: Range hood. Users can query and set the fan-speed level and lighting. The self-cleaning mode can be started.
    Version: 1.0.0
    Base: -
    """
    PROCESS = {'mode_property': 'cleaning_mode', 'start_function': 'start_self_cleaning', 'pause_function': 'pause_self_cleaning', 'resume_function': 'resume_self_cleaning', 'modes': {'self_clean': [{'phase': 'heating', 'minutes': 5}, {'phase': 'cleaning', 'minutes': 10}, {'phase': 'cooling', 'minutes': 5}]}}

    def __init__(self, power: bool=None, fan_speed: int=None, light: bool=None, cleaning_mode: str=None, status: str=None, phase: str=None, remaining_minutes: int=None, started_at_minute: int=None, progress_minutes: int=None, *, _defer_power_init: bool=False) -> None:
        _power_init_value = power if power is not None else False
        self.power = BoolProperty(name='power', description='Whether the range hood is powered.', default=False)
        self.fan_speed = IntProperty(name='fan_speed', description='Configured fan-speed level. The value persists while powered off and is publicly accessible only while powered on.', default=0, unit='level', minimum=0, maximum=3, step=1, step_origin=0)
        self.light = BoolProperty(name='light', description='Whether the range hood light is enabled. The value persists while powered off and is publicly accessible only while powered on.', default=False)
        self.cleaning_mode = StringProperty(name='cleaning_mode', description='Self-cleaning process mode.', default='self_clean', choices=['self_clean'])
        self.status = StringProperty(name='status', description='Self-cleaning process status.', default='idle', mode=2, choices=['idle', 'running', 'paused', 'completed'])
        self.phase = StringProperty(name='phase', description='Current self-cleaning phase, or idle/completed when no phase is active.', default='idle', mode=2, choices=['idle', 'heating', 'cleaning', 'cooling', 'completed'])
        self.remaining_minutes = IntProperty(name='remaining_minutes', description='Minutes remaining in the self-cleaning process.', default=0, mode=2, unit='min', minimum=0, maximum=60, step=1, step_origin=0)
        self.started_at_minute = IntProperty(name='started_at_minute', description='Elapsed-world-minute origin used to calculate self-cleaning progress.', default=0, mode=2, unit='min', minimum=0, step=1, step_origin=0)
        self.progress_minutes = IntProperty(name='progress_minutes', description='Elapsed minutes completed in the self-cleaning process.', default=0, mode=2, unit='min', minimum=0, maximum=60, step=1, step_origin=0)
        code = self.power.internal_set(_power_init_value)
        if fan_speed is not None:
            code = self.fan_speed.internal_set(fan_speed)
        if light is not None:
            code = self.light.internal_set(light)
        if cleaning_mode is not None:
            code = self.cleaning_mode.internal_set(cleaning_mode)
        if status is not None:
            code = self.status.internal_set(status)
        if phase is not None:
            code = self.phase.internal_set(phase)
        if remaining_minutes is not None:
            code = self.remaining_minutes.internal_set(remaining_minutes)
        if started_at_minute is not None:
            code = self.started_at_minute.internal_set(started_at_minute)
        if progress_minutes is not None:
            code = self.progress_minutes.internal_set(progress_minutes)
        self._power_managed_properties = (self.fan_speed, self.light, self.cleaning_mode, self.status, self.phase, self.remaining_minutes, self.started_at_minute, self.progress_minutes)
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

    def get_fan_speed(self) -> tuple[str, dict]:
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if powered is not True:
            return ('[POWER_OFF]', {})
        code, value = self.fan_speed.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'fan_speed': value})

    def set_fan_speed(self, value: int) -> tuple[str, dict]:
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if powered is not True:
            return ('[POWER_OFF]', {})
        if type(value) is not int or isinstance(value, bool) or value < 0 or (value > 3):
            return ('[ERROR] INVALID_FAN_SPEED', {})
        code = self.fan_speed.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_light(self) -> tuple[str, dict]:
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if powered is not True:
            return ('[POWER_OFF]', {})
        code, value = self.light.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'light': value})

    def set_light(self, value: bool) -> tuple[str, dict]:
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if powered is not True:
            return ('[POWER_OFF]', {})
        if type(value) is not bool:
            return ('[ERROR] INVALID_LIGHT', {})
        code = self.light.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_cleaning_status(self) -> tuple[str, dict]:
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if powered is not True:
            return ('[POWER_OFF]', {})
        values = {}
        for name, prop in (('status', self.status), ('phase', self.phase), ('remaining_minutes', self.remaining_minutes), ('progress_minutes', self.progress_minutes)):
            code, value = prop.get()
            if code != '[PASS]':
                return (code, {})
            values[name] = value
        return ('[PASS]', values)

    def start_self_cleaning(self, mode: str) -> tuple[str, dict]:
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if powered is not True:
            return ('[POWER_OFF]', {})
        if type(mode) is not str or mode != 'self_clean':
            return ('[ERROR] INVALID_MODE', {})
        status_code, status = self.status.get()
        if status_code != '[PASS]':
            return (status_code, {})
        if status not in ('idle', 'completed'):
            return ('[ERROR] INVALID_STATE', {})
        mode_code = self.cleaning_mode.set(mode)
        if mode_code != '[PASS]':
            return (mode_code, {})
        for prop, value in ((self.status, 'running'), (self.phase, 'heating'), (self.remaining_minutes, 20), (self.progress_minutes, 0)):
            code = prop.internal_set(value)
            if code != '[PASS]':
                return (code, {})
        return ('[PASS]', {})

    def pause_self_cleaning(self) -> tuple[str, dict]:
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if powered is not True:
            return ('[POWER_OFF]', {})
        code, status = self.status.get()
        if code != '[PASS]':
            return (code, {})
        if status != 'running':
            return ('[ERROR] INVALID_STATE', {})
        code = self.status.internal_set('paused')
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def resume_self_cleaning(self) -> tuple[str, dict]:
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if powered is not True:
            return ('[POWER_OFF]', {})
        code, status = self.status.get()
        if code != '[PASS]':
            return (code, {})
        if status != 'paused':
            return ('[ERROR] INVALID_STATE', {})
        code = self.status.internal_set('running')
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        pre_state = context['pre_state']['objects'][context['object_id']]['properties']
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, [])
        status = self.status.value
        if powered is not True:
            if pre_state['status'] == 'running':
                code = self.status.internal_set('paused')
                if code != '[PASS]':
                    return (code, [])
            status = 'paused' if pre_state['status'] == 'running' else status
        progress = self.progress_minutes.value
        if powered is True and status == 'running':
            if pre_state['status'] != 'running' or pre_state['power'] is not True:
                elapsed = context['time_state']['elapsed_minutes']
                code = self.started_at_minute.internal_set(elapsed - progress)
                if code != '[PASS]':
                    return (code, [])
        fan_speed = self.fan_speed.value
        light = self.light.value
        noise = fan_speed * 10 if powered is True else 0
        illuminance = 300 if powered is True and light is True else 0
        effects = [{'trigger': 'after_action', 'source': context['object_id'], 'target': context['space_id'], 'function': 'set_contribution', 'parameters': {'property': 'noise', 'value': noise, 'unit': 'dBA'}}, {'trigger': 'after_action', 'source': context['object_id'], 'target': context['space_id'], 'function': 'set_contribution', 'parameters': {'property': 'illuminance', 'value': illuminance, 'unit': 'lux'}}]
        return ('[PASS]', effects)

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, [])
        if powered is not True:
            return ('[PASS]', [])
        status_code, status = self.status.get()
        if status_code != '[PASS]':
            return (status_code, [])
        if powered is not True or status != 'running':
            return ('[PASS]', [])
        origin_code, origin = self.started_at_minute.get()
        if origin_code != '[PASS]':
            return (origin_code, [])
        elapsed = context['time_state']['elapsed_minutes']
        progress = elapsed - origin
        if progress < 0:
            progress = 0
        if progress > 20:
            progress = 20
        code = self.progress_minutes.internal_set(progress)
        if code != '[PASS]':
            return (code, [])
        remaining = 20 - progress
        code = self.remaining_minutes.internal_set(remaining)
        if code != '[PASS]':
            return (code, [])
        if progress >= 20:
            for prop, value in ((self.status, 'completed'), (self.phase, 'completed'), (self.remaining_minutes, 0), (self.progress_minutes, 20)):
                code = prop.internal_set(value)
                if code != '[PASS]':
                    return (code, [])
        elif progress < 5:
            code = self.phase.internal_set('heating')
            if code != '[PASS]':
                return (code, [])
        elif progress < 15:
            code = self.phase.internal_set('cleaning')
            if code != '[PASS]':
                return (code, [])
        else:
            code = self.phase.internal_set('cooling')
            if code != '[PASS]':
                return (code, [])
        return ('[PASS]', [])
