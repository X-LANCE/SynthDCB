# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class ClimateControl:
    """
    ClimateControl
    Description: Cabin climate control. Supports switching on and off, target temperature, fan speed, automatic/cooling/heating/fan-only modes, and fresh-air/recirculation settings, with front and rear windshield defogging modes. While running, the device adjusts cabin temperature according to its current operating mode; fan-only operation does not directly change temperature.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, enabled: bool = None, target_temperature: int = None, fan_speed: int = None, mode: str = None, recirculation: str = None, front_defogging: bool = None, rear_defogging: bool = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the climate-control device has electrical power. While false, temperature control is inactive and non-power public functions are unavailable.',
            default=False
        )
        self.enabled = BoolProperty(
            name='enabled',
            description='Whether cabin climate operation is enabled. This setting is retained when device power is turned off.',
            default=False
        )
        self.target_temperature = IntProperty(
            name='target_temperature',
            description='Requested cabin target temperature.',
            default=22,
            unit='degC',
            minimum=16,
            maximum=32,
            step=1,
            step_origin=16
        )
        self.fan_speed = IntProperty(
            name='fan_speed',
            description='Cabin fan speed level.',
            default=3,
            minimum=1,
            maximum=7,
            step=1,
            step_origin=1
        )
        self.mode = StringProperty(
            name='mode',
            description='Cabin climate operating mode.',
            default='auto',
            choices=['auto', 'cool', 'heat', 'fan']
        )
        self.recirculation = StringProperty(
            name='recirculation',
            description='Air-intake setting: internal recirculates cabin air, external uses fresh outside air, and auto selects automatically.',
            default='auto',
            choices=['internal', 'external', 'auto']
        )
        self.front_defogging = BoolProperty(
            name='front_defogging',
            description='Whether front windshield defogging mode is enabled.',
            default=False
        )
        self.rear_defogging = BoolProperty(
            name='rear_defogging',
            description='Whether rear windshield defogging mode is enabled.',
            default=False
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if enabled is not None: code = self.enabled.internal_set(enabled)
        if target_temperature is not None: code = self.target_temperature.internal_set(target_temperature)
        if fan_speed is not None: code = self.fan_speed.internal_set(fan_speed)
        if mode is not None: code = self.mode.internal_set(mode)
        if recirculation is not None: code = self.recirculation.internal_set(recirculation)
        if front_defogging is not None: code = self.front_defogging.internal_set(front_defogging)
        if rear_defogging is not None: code = self.rear_defogging.internal_set(rear_defogging)
        self._power_managed_properties = (self.enabled, self.target_temperature, self.fan_speed, self.mode, self.recirculation, self.front_defogging, self.rear_defogging,)
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

    def get_enabled(self) -> tuple[str, dict]:
        """
        Return whether cabin climate operation is enabled without changing state. Requires device power.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- enabled: Whether cabin climate operation is enabled. (type=boolean)

        Error Codes:
        - POWER_OFF: Device must be powered on.
        """
        code, value = self.enabled.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'enabled': value})

    def set_enabled(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable cabin climate operation while retaining all configured settings. Requires device power. Invalid input or unavailable power leaves state unchanged.

        Args:
        - value:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Device must be powered on.
        """
        code = self.enabled.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_target_temperature(self) -> tuple[str, dict]:
        """
        Return the requested cabin target temperature without changing state. Requires device power.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- target_temperature: Requested cabin target temperature in degrees Celsius. (type=integer)

        Error Codes:
        - POWER_OFF: Device must be powered on.
        """
        code, value = self.target_temperature.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'target_temperature': value})

    def set_target_temperature(self, value: int) -> tuple[str, dict]:
        """
        Set the requested cabin target temperature to an integer from 16 through 32 degrees Celsius. The setting can be changed in automatic, cooling, or heating mode; fan-only mode rejects the operation. Requires device power. Invalid input or a failed precondition leaves state unchanged.

        Args:
        - value:  (min=16, max=32)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Device must be powered on.
        - PRECONDITION_FAILED: Target temperature cannot be changed while fan-only mode is selected.
        """
        if type(value) is not int or value < 16 or value > 32:
            return ('[INVALID_INPUT_ERROR]', {})
        mode_code, mode_value = self.mode.get()
        if mode_code != '[PASS]':
            return (mode_code, {})
        if mode_value == 'fan':
            return ('[PRECONDITION_FAILED]', {})
        code = self.target_temperature.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_fan_speed(self) -> tuple[str, dict]:
        """
        Return the current cabin fan speed level without changing state. Requires device power.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- fan_speed: Current fan speed level from 1 through 7. (type=integer)

        Error Codes:
        - POWER_OFF: Device must be powered on.
        """
        code, value = self.fan_speed.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'fan_speed': value})

    def set_fan_speed(self, value: int) -> tuple[str, dict]:
        """
        Set the cabin fan speed to an integer level from 1 through 7. Requires device power. Invalid input or unavailable power leaves state unchanged.

        Args:
        - value:  (min=1, max=7)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Device must be powered on.
        """
        code = self.fan_speed.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_mode(self) -> tuple[str, dict]:
        """
        Return the selected cabin climate operating mode without changing state. Requires device power.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- mode: Selected operating mode: auto, cool, heat, or fan. (type=string)

        Error Codes:
        - POWER_OFF: Device must be powered on.
        """
        code, value = self.mode.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'mode': value})

    def set_mode(self, value: str) -> tuple[str, dict]:
        """
        Select automatic, cooling, heating, or fan-only operation. Requires device power. Invalid values or unavailable power leave state unchanged.

        Args:
        - value:  (choices=['auto', 'cool', 'heat', 'fan'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Device must be powered on.
        """
        code = self.mode.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_recirculation(self) -> tuple[str, dict]:
        """
        Return the selected air-intake setting without changing state. Internal means cabin-air recirculation and external means fresh outside air. Requires device power.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- recirculation: Selected air-intake setting: internal, external, or auto. (type=string)

        Error Codes:
        - POWER_OFF: Device must be powered on.
        """
        code, value = self.recirculation.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'recirculation': value})

    def set_recirculation(self, value: str) -> tuple[str, dict]:
        """
        Select internal cabin-air recirculation, external fresh-air intake, or automatic selection. Requires device power. Invalid values or unavailable power leave state unchanged.

        Args:
        - value:  (choices=['internal', 'external', 'auto'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Device must be powered on.
        """
        code = self.recirculation.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_front_defogging(self) -> tuple[str, dict]:
        """
        Return whether front windshield defogging mode is enabled without changing state. Requires device power.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- front_defogging: Whether front windshield defogging mode is enabled. (type=boolean)

        Error Codes:
        - POWER_OFF: Device must be powered on.
        """
        code, value = self.front_defogging.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'front_defogging': value})

    def set_front_defogging(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable front windshield defogging mode. Requires device power. Invalid input or unavailable power leaves state unchanged.

        Args:
        - value:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Device must be powered on.
        """
        code = self.front_defogging.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_rear_defogging(self) -> tuple[str, dict]:
        """
        Return whether rear windshield defogging mode is enabled without changing state. Requires device power.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- rear_defogging: Whether rear windshield defogging mode is enabled. (type=boolean)

        Error Codes:
        - POWER_OFF: Device must be powered on.
        """
        code, value = self.rear_defogging.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'rear_defogging': value})

    def set_rear_defogging(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable rear windshield defogging mode. Requires device power. Invalid input or unavailable power leaves state unchanged.

        Args:
        - value:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Device must be powered on.
        """
        code = self.rear_defogging.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        While both electrically powered and enabled, move cabin temperature toward target_temperature by at most 1 degree Celsius per minute. Auto mode may heat or cool, cool mode acts only when cabin temperature is above the target, heat mode acts only when cabin temperature is below the target, and fan mode emits no temperature effect. Emit no temperature effect while power is off, while climate operation is disabled, while the selected directional mode cannot move toward the target, or once the target is reached.

    Effect properties:
    - power: Determines whether the climate-control device can produce a cabin temperature effect.
    - enabled: Determines whether climate temperature control is active while the device is powered.
    - target_temperature: The cabin temperature approached while powered climate temperature control is active.
    - mode: Determines whether the device may heat, cool, do either, or emit no temperature effect.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, [])
        if not powered:
            return ('[PASS]', [])

        enabled_code, enabled = self.enabled.get()
        if enabled_code != '[PASS]':
            return (enabled_code, [])
        if not enabled:
            return ('[PASS]', [])

        mode_code, mode_value = self.mode.get()
        if mode_code != '[PASS]':
            return (mode_code, [])
        if mode_value == 'fan':
            return ('[PASS]', [])

        target_code, target = self.target_temperature.get()
        if target_code != '[PASS]':
            return (target_code, [])

        current = context['space_state']['temperature']
        if current == target:
            return ('[PASS]', [])
        if mode_value == 'cool' and current < target:
            return ('[PASS]', [])
        if mode_value == 'heat' and current > target:
            return ('[PASS]', [])

        return ('[PASS]', [{
            'trigger': 'tick',
            'source': context['object_id'],
            'target': context['space_id'],
            'function': 'approach',
            'parameters': {
                'property': 'temperature',
                'value': target,
                'rate_per_minute': 1,
                'unit': 'degC'
            }
        }])