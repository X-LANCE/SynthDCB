# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class BathroomMirror:
    """
    BathroomMirror
    Description: Bathroom mirror. Users can query and set lighting brightness, the defogging state, and the automatic-lighting function. Its lighting changes room brightness.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, brightness: int = None, defogging: bool = None, automatic_lighting: bool = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the bathroom mirror is powered. When false, non-power properties remain configured but are not publicly accessible or changeable.',
            default=False
        )
        self.brightness = IntProperty(
            name='brightness',
            description='Configured mirror-light brightness percentage. This value persists while the mirror is powered off and is publicly accessible only while power is on.',
            default=50,
            unit='%',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.defogging = BoolProperty(
            name='defogging',
            description="Whether the mirror's defogging function is enabled. This setting persists while the mirror is powered off and is publicly accessible only while power is on.",
            default=False
        )
        self.automatic_lighting = BoolProperty(
            name='automatic_lighting',
            description='Whether automatic lighting is enabled. This setting persists while the mirror is powered off and is publicly accessible only while power is on.',
            default=False
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if brightness is not None: code = self.brightness.internal_set(brightness)
        if defogging is not None: code = self.defogging.internal_set(defogging)
        if automatic_lighting is not None: code = self.automatic_lighting.internal_set(automatic_lighting)
        self._power_managed_properties = (self.brightness, self.defogging, self.automatic_lighting,)
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

    def get_brightness(self) -> tuple[str, dict]:
        """
        Return the configured lighting brightness percentage. The mirror must be powered on; otherwise the function fails without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- brightness: Configured brightness from 0 through 100 percent. (type=integer)

        Error Codes:
        - POWER_OFF: The mirror must be powered on to read brightness.
        """
        code, value = self.brightness.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"brightness": value}

    def set_brightness(self, value: int) -> tuple[str, dict]:
        """
        Set the mirror-light brightness to an integer percentage from 0 through 100. The mirror must be powered on. Invalid input leaves state unchanged.

        Args:
        - value: Desired lighting brightness percentage. (min=0, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The mirror must be powered on to change brightness.
        - INVALID_INPUT_ERROR: value must be an integer from 0 through 100.
        """
        if type(value) is not int or value < 0 or value > 100:
            return "[INVALID_INPUT_ERROR]", {}
        code = self.brightness.set(value)
        return code, {}

    def get_defogging(self) -> tuple[str, dict]:
        """
        Return whether defogging is enabled. The mirror must be powered on; otherwise the function fails without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- defogging: Whether defogging is enabled. (type=boolean)

        Error Codes:
        - POWER_OFF: The mirror must be powered on to read defogging.
        """
        code, value = self.defogging.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"defogging": value}

    def set_defogging(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable the mirror's defogging function. The mirror must be powered on. Invalid input leaves state unchanged.

        Args:
        - value: Whether defogging should be enabled.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The mirror must be powered on to change defogging.
        - INVALID_INPUT_ERROR: value must be a boolean.
        """
        if type(value) is not bool:
            return "[INVALID_INPUT_ERROR]", {}
        code = self.defogging.set(value)
        return code, {}

    def get_automatic_lighting(self) -> tuple[str, dict]:
        """
        Return whether automatic lighting is enabled. The mirror must be powered on; otherwise the function fails without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- automatic_lighting: Whether automatic lighting is enabled. (type=boolean)

        Error Codes:
        - POWER_OFF: The mirror must be powered on to read automatic lighting.
        """
        code, value = self.automatic_lighting.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"automatic_lighting": value}

    def set_automatic_lighting(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable the automatic-lighting setting. The mirror must be powered on. This changes only the setting; no presence sensor or automatic trigger is modeled. Invalid input leaves state unchanged.

        Args:
        - value: Whether automatic lighting should be enabled.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The mirror must be powered on to change automatic lighting.
        - INVALID_INPUT_ERROR: value must be a boolean.
        """
        if type(value) is not bool:
            return "[INVALID_INPUT_ERROR]", {}
        code = self.automatic_lighting.set(value)
        return code, {}

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        Recalculate the mirror's absolute illuminance contribution after a successful state-changing action. The contribution is zero when power is off; when power is on, it is equal to the configured brightness percentage multiplied by 10 lux.

        Effect properties:
        - power: Determines whether the mirror contributes light.
        - brightness: Determines the mirror's illuminance contribution while powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, []
        if powered is not True:
            contribution = 0
        else:
            brightness_code, brightness = self.brightness.get()
            if brightness_code != "[PASS]":
                return brightness_code, []
            contribution = brightness * 10
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
        return "[PASS]", [effect]