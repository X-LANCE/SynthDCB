# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class WindowOpener:
    """
    WindowOpener
    Description: Smart window opener. Users can query and set the window's open or closed state and opening percentage, and can perform open, close, and stop actions. The opening percentage is updated while the device moves. Opening or closing the window affects the temperature, humidity, and air quality of its space according to differences between indoor and outdoor environments. Open/closed state is computed from the actual opening percentage. Motion has a persisted duration and origin, pauses on power loss, and physical ventilation through an open window continues independently of motor power.
    Version: 1.0.0
    Base: -
    """
    PROCESS = {'mode_property': 'motion_mode', 'start_function': 'open', 'pause_function': 'stop', 'modes': {'opening': [{'phase': 'opening', 'minutes': {'property': 'travel_minutes'}}], 'closing': [{'phase': 'closing', 'minutes': {'property': 'travel_minutes'}}]}}

    def __init__(self, power: bool=None, opening_percentage: int=None, target_opening_percentage: int=None, motion_mode: str=None, movement_minutes: int=None, status: str=None, phase: str=None, remaining_minutes: int=None, started_at_minute: int=None, progress_minutes: int=None, start_opening_percentage: int=None, travel_minutes: int=None, outdoor_temperature: float=None, outdoor_humidity: int=None, outdoor_air_quality: int=None, *, _defer_power_init: bool=False) -> None:
        _power_init_value = power if power is not None else False
        self.power = BoolProperty(name='power', description='Whether the window opener is powered.', default=False)
        self.opening_percentage = IntProperty(name='opening_percentage', description='Current window opening percentage, from 0 fully closed to 100 fully open.', default=0, mode=2, unit='%', minimum=0, maximum=100, step=1, step_origin=0)
        self.target_opening_percentage = IntProperty(name='target_opening_percentage', description='Requested window opening percentage, from 0 fully closed to 100 fully open.', default=0, mode=2, unit='%', minimum=0, maximum=100, step=1, step_origin=0)
        self.motion_mode = StringProperty(name='motion_mode', description='Direction selected for the movement process.', default='opening', mode=2, choices=['opening', 'closing'])
        self.movement_minutes = IntProperty(name='movement_minutes', description='Minutes required to travel from fully closed to fully open.', default=1, mode=2, minimum=1, maximum=1440, step=1, step_origin=1)
        self.status = StringProperty(name='status', description='Persisted movement process status.', default='idle', mode=2, choices=['idle', 'running', 'paused', 'completed'])
        self.phase = StringProperty(name='phase', description='Persisted process phase.', default='idle', mode=2, choices=['idle', 'opening', 'closing', 'completed'])
        self.remaining_minutes = IntProperty(name='remaining_minutes', description='Remaining whole minutes in the current movement process.', default=0, mode=2, minimum=0, maximum=1440, step=1, step_origin=0)
        self.started_at_minute = IntProperty(name='started_at_minute', description='Elapsed world minute at which the current running process began, adjusted for completed progress.', default=0, mode=2, minimum=0, step=1, step_origin=0)
        self.progress_minutes = IntProperty(name='progress_minutes', description='Whole minutes completed in the current movement process.', default=0, mode=2, minimum=0, maximum=1440, step=1, step_origin=0)
        self.start_opening_percentage = IntProperty(name='start_opening_percentage', description='Opening percentage at the start of the current movement, persisted for deterministic interpolation.', default=0, mode=2, unit='%', minimum=0, maximum=100, step=1, step_origin=0)
        self.travel_minutes = IntProperty(name='travel_minutes', description='Computed whole-minute duration for the current nonzero travel: max(1, ceil(abs(target_opening_percentage - start_opening_percentage) * movement_minutes / 100)). The value is nominal and unused for an already-at-target no-op.', default=1, mode=2, minimum=1, maximum=1440, step=1, step_origin=0)
        self.outdoor_temperature = FloatProperty(name='outdoor_temperature', description='External environment parameter supplied at initialization for physical exchange; not a duplicate of indoor Space state.', default=22.0, mode=2, unit='degC', minimum=-50, maximum=80, precision=1)
        self.outdoor_humidity = IntProperty(name='outdoor_humidity', description='External environment parameter supplied at initialization for physical exchange; not a duplicate of indoor Space state.', default=50, mode=2, unit='%RH', minimum=0, maximum=100, step=1, step_origin=0)
        self.outdoor_air_quality = IntProperty(name='outdoor_air_quality', description='External environment parameter supplied at initialization for physical exchange; not a duplicate of indoor Space state.', default=30, mode=2, unit='AQI', minimum=0, maximum=500, step=1, step_origin=0)
        code = self.power.internal_set(_power_init_value)
        if opening_percentage is not None:
            code = self.opening_percentage.internal_set(opening_percentage)
        if target_opening_percentage is not None:
            code = self.target_opening_percentage.internal_set(target_opening_percentage)
        if motion_mode is not None:
            code = self.motion_mode.internal_set(motion_mode)
        if movement_minutes is not None:
            code = self.movement_minutes.internal_set(movement_minutes)
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
        if start_opening_percentage is not None:
            code = self.start_opening_percentage.internal_set(start_opening_percentage)
        if travel_minutes is not None:
            code = self.travel_minutes.internal_set(travel_minutes)
        if outdoor_temperature is not None:
            code = self.outdoor_temperature.internal_set(outdoor_temperature)
        if outdoor_humidity is not None:
            code = self.outdoor_humidity.internal_set(outdoor_humidity)
        if outdoor_air_quality is not None:
            code = self.outdoor_air_quality.internal_set(outdoor_air_quality)
        self._power_managed_properties = (self.opening_percentage, self.target_opening_percentage, self.motion_mode, self.movement_minutes, self.status, self.phase, self.remaining_minutes, self.started_at_minute, self.progress_minutes, self.start_opening_percentage, self.travel_minutes, self.outdoor_temperature, self.outdoor_humidity, self.outdoor_air_quality)
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

    def get_opening_percentage(self) -> tuple[str, dict]:
        """
        Return the current window opening percentage.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        return self._get(self.opening_percentage, 'opening_percentage')

    def set_opening_percentage(self, value: int) -> tuple[str, dict]:
        """
        Request target opening the value argument. When already running toward the same target, return success without changing any state. Otherwise set target_opening_percentage to the request and start_opening_percentage to the current opening_percentage, reset progress_minutes to zero, and compute travel_minutes=max(1, ceil(abs(target_opening_percentage-start_opening_percentage)*movement_minutes/100)). If the current opening equals the target, set status and phase to completed and remaining_minutes to zero without starting motion; retain the previous motion_mode. Otherwise choose motion_mode=opening if target exceeds current opening, or closing if below; set status=running, phase=motion_mode and remaining_minutes=travel_minutes. The after_action transition establishes started_at_minute at the current elapsed world minute. Invalid input changes no state.

        Args:
        - value:  (min=0, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        return self._request(value)

    def get_motion_mode(self) -> tuple[str, dict]:
        """
        Return the selected movement direction.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        return self._get(self.motion_mode, 'motion_mode')

    def get_status(self) -> tuple[str, dict]:
        """
        Return the persisted movement process status.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        return self._get(self.status, 'status')

    def open(self, mode: str='opening') -> tuple[str, dict]:
        """
        Request target opening 100. When already running toward the same target, return success without changing any state. Otherwise set target_opening_percentage to the request and start_opening_percentage to the current opening_percentage, reset progress_minutes to zero, and compute travel_minutes=max(1, ceil(abs(target_opening_percentage-start_opening_percentage)*movement_minutes/100)). If the current opening equals the target, set status and phase to completed and remaining_minutes to zero without starting motion; retain the previous motion_mode. Otherwise choose motion_mode=opening if target exceeds current opening, or closing if below; set status=running, phase=motion_mode and remaining_minutes=travel_minutes. The after_action transition establishes started_at_minute at the current elapsed world minute. Invalid input changes no state.

        Args:
        - mode:  (choices=['opening'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        if mode != 'opening':
            return ('[ERROR] INVALID_VALUE', {})
        return self._request(100)

    def close(self, mode: str='closing') -> tuple[str, dict]:
        """
        Request target opening 0. When already running toward the same target, return success without changing any state. Otherwise set target_opening_percentage to the request and start_opening_percentage to the current opening_percentage, reset progress_minutes to zero, and compute travel_minutes=max(1, ceil(abs(target_opening_percentage-start_opening_percentage)*movement_minutes/100)). If the current opening equals the target, set status and phase to completed and remaining_minutes to zero without starting motion; retain the previous motion_mode. Otherwise choose motion_mode=opening if target exceeds current opening, or closing if below; set status=running, phase=motion_mode and remaining_minutes=travel_minutes. The after_action transition establishes started_at_minute at the current elapsed world minute. Invalid input changes no state.

        Args:
        - mode:  (choices=['closing'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        if mode != 'closing':
            return ('[ERROR] INVALID_VALUE', {})
        return self._request(0)

    def stop(self) -> tuple[str, dict]:
        """
        While powered and running, pause movement by setting status=paused. Preserve the current opening, phase, target, travel duration, origin and progress. A later open, close or percentage request starts a new movement from the retained opening.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != '[PASS]':
            return (code, {})
        code, status = self.status.get()
        if code != '[PASS]':
            return (code, {})
        if power is True and status == 'running':
            code = self.status.internal_set('paused')
            if code != '[PASS]':
                return (code, {})
        return ('[PASS]', {})

    def get_phase(self) -> tuple[str, dict]:
        """
        Return the current movement phase.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        return self._get(self.phase, 'phase')

    def get_remaining_minutes(self) -> tuple[str, dict]:
        """
        Return the remaining whole movement minutes.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        return self._get(self.remaining_minutes, 'remaining_minutes')

    def set_open_state(self, value: bool) -> tuple[str, dict]:
        """
        Request target opening 100 when value is true, or 0 when false. When already running toward the same target, return success without changing any state. Otherwise set target_opening_percentage to the request and start_opening_percentage to the current opening_percentage, reset progress_minutes to zero, and compute travel_minutes=max(1, ceil(abs(target_opening_percentage-start_opening_percentage)*movement_minutes/100)). If the current opening equals the target, set status and phase to completed and remaining_minutes to zero without starting motion; retain the previous motion_mode. Otherwise choose motion_mode=opening if target exceeds current opening, or closing if below; set status=running, phase=motion_mode and remaining_minutes=travel_minutes. The after_action transition establishes started_at_minute at the current elapsed world minute. Invalid input changes no state.

        Args:
        - value:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        if type(value) is not bool:
            return ('[ERROR] INVALID_VALUE', {})
        return self._request(100 if value else 0)

    def get_open_state(self) -> tuple[str, dict]:
        """
        While powered, return open_state=true exactly when opening_percentage is greater than zero; fully closed is false. This is a computed response, with no duplicate stored Boolean state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- open_state: Whether any part of the window is open. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.opening_percentage.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'open_state': value > 0})

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        During powered running motion, let progress_minutes be the current elapsed world minute minus started_at_minute, clamped to [0, travel_minutes]. Let distance=floor(100*progress_minutes/movement_minutes). Set opening_percentage to start_opening_percentage plus or minus min(distance, abs(target_opening_percentage-start_opening_percentage)), using motion_mode for direction. Set remaining_minutes=travel_minutes-progress_minutes. At progress_minutes=travel_minutes set opening_percentage exactly to target_opening_percentage, status and phase to completed, and remaining_minutes=0. Idle, paused, completed and unpowered motion preserves its persisted progress and position. After that update, a nonzero opening physically exchanges indoor and outdoor environments even when the motor is unpowered. For each minute, let fraction=opening_percentage/100 and emit only delta effects to the containing Home Space: temperature delta=round(0.05*fraction*(outdoor_temperature-Space temperature), 1) degC; humidity delta=round(0.05*fraction*(outdoor_humidity-Space humidity)) %RH; air_quality delta=round(0.10*fraction*(outdoor_air_quality-Space air_quality)) AQI. Round to nearest with ties to even. A closed window emits no effects; omit any zero delta. The runtime reducer applies these effects. Never also emit these effects from after_action.

    Effect properties:
    - power: Persisted movement state or physical exchange input/output.
    - opening_percentage: Persisted movement state or physical exchange input/output.
    - target_opening_percentage: Persisted movement state or physical exchange input/output.
    - motion_mode: Persisted movement state or physical exchange input/output.
    - movement_minutes: Persisted movement state or physical exchange input/output.
    - status: Persisted movement state or physical exchange input/output.
    - phase: Persisted movement state or physical exchange input/output.
    - remaining_minutes: Persisted movement state or physical exchange input/output.
    - started_at_minute: Persisted movement state or physical exchange input/output.
    - progress_minutes: Persisted movement state or physical exchange input/output.
    - start_opening_percentage: Persisted movement state or physical exchange input/output.
    - travel_minutes: Persisted movement state or physical exchange input/output.
    - outdoor_temperature: Persisted movement state or physical exchange input/output.
    - outdoor_humidity: Persisted movement state or physical exchange input/output.
    - outdoor_air_quality: Persisted movement state or physical exchange input/output.
        """
        code, powered = self.power.get()
        if code != '[PASS]':
            return (code, [])
        if powered is True and self.status.value == 'running':
            duration = self.travel_minutes.value
            progress = max(0, min(duration, context['time_state']['elapsed_minutes'] - self.started_at_minute.value))
            start, target = (self.start_opening_percentage.value, self.target_opening_percentage.value)
            distance = min(abs(target - start), 100 * progress // self.movement_minutes.value)
            position = start + distance if target >= start else start - distance
            updates = [(self.progress_minutes, progress), (self.opening_percentage, position), (self.remaining_minutes, duration - progress)]
            if progress >= duration:
                updates += [(self.opening_percentage, target), (self.status, 'completed'), (self.phase, 'completed'), (self.remaining_minutes, 0)]
            for prop, value in updates:
                code = prop.internal_set(value)
                if code != '[PASS]':
                    return (code, [])
        fraction = self.opening_percentage.value / 100
        if fraction == 0:
            return ('[PASS]', [])
        space = context['space_state']
        changes = (('temperature', round(0.05 * fraction * (self.outdoor_temperature.value - space['temperature']), 1), 'degC'), ('humidity', round(0.05 * fraction * (self.outdoor_humidity.value - space['humidity'])), '%RH'), ('air_quality', round(0.1 * fraction * (self.outdoor_air_quality.value - space['air_quality'])), 'AQI'))
        effects = [{'trigger': 'tick', 'source': context['object_id'], 'target': context['space_id'], 'function': 'delta', 'parameters': {'property': name, 'value': value, 'unit': unit}} for name, value, unit in changes if value != 0]
        return ('[PASS]', effects)

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        When power is false and status is running, internally set status=paused, preserving phase, opening, target, origin and progress. Powering on never resumes movement. When powered with status running, establish started_at_minute at the current elapsed world minute only if the previous status was not running or the target changed. A repeated request for the already-running target is a no-op and never resets the origin. Emit no Space effects here.

    Effect properties:
    - power: Required for the conditional power-loss pause or new-target time origin.
    - status: Required for the conditional power-loss pause or new-target time origin.
    - target_opening_percentage: Required for the conditional power-loss pause or new-target time origin.
    - started_at_minute: Required for the conditional power-loss pause or new-target time origin.
        """
        pre = context['pre_state']['objects'][context['object_id']]['properties']
        code, powered = self.power.get()
        if code != '[PASS]':
            return (code, [])
        status = self.status.value
        if powered is not True and status == 'running':
            code = self.status.internal_set('paused')
            if code != '[PASS]':
                return (code, [])
        elif powered is True and status == 'running' and (pre['status'] != 'running' or pre['target_opening_percentage'] != self.target_opening_percentage.value):
            code = self.started_at_minute.internal_set(context['time_state']['elapsed_minutes'])
            if code != '[PASS]':
                return (code, [])
        return ('[PASS]', [])

    def _get(self, prop, key):
        code, value = prop.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {key: value})

    def _request(self, target):
        if type(target) is not int or target < 0 or target > 100:
            return ('[ERROR] INVALID_VALUE', {})
        code, current = self.opening_percentage.get()
        if code != '[PASS]':
            return (code, {})
        code, old_target = self.target_opening_percentage.get()
        if code != '[PASS]':
            return (code, {})
        code, status = self.status.get()
        if code != '[PASS]':
            return (code, {})
        if status == 'running' and old_target == target:
            return ('[PASS]', {})
        code, movement = self.movement_minutes.get()
        if code != '[PASS]':
            return (code, {})
        distance = abs(target - current)
        travel = max(1, (distance * movement + 99) // 100)
        updates = [(self.target_opening_percentage, target), (self.start_opening_percentage, current), (self.progress_minutes, 0), (self.travel_minutes, travel)]
        if target == current:
            updates += [(self.status, 'completed'), (self.phase, 'completed'), (self.remaining_minutes, 0)]
        else:
            direction = 'opening' if target > current else 'closing'
            updates += [(self.motion_mode, direction), (self.status, 'running'), (self.phase, direction), (self.remaining_minutes, travel)]
        for prop, value in updates:
            code = prop.internal_set(value)
            if code != '[PASS]':
                return (code, {})
        return ('[PASS]', {})
