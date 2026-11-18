# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class ExteriorLight:
    """
    ExteriorLight
    Description: Vehicle exterior lighting and signaling module. Supports driver selection of lighting mode, low/high-beam requests, turn signals, and hazard lights, with queries of actual illumination feedback. Automatic lighting uses local environment inputs.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, lighting_mode: str = None, beam_request: str = None, turn_signal: str = None, hazard_lights: bool = None, actual_beam_state: str = None, actual_illumination: int = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the exterior-light module is powered. When false, it produces no exterior illuminance and non-power public functions are unavailable.',
            default=False
        )
        self.lighting_mode = StringProperty(
            name='lighting_mode',
            description='Driver-selected exterior lighting mode. This controls parking and headlight illumination but does not change the stored signal requests.',
            default='off',
            choices=['off', 'parking', 'headlights', 'auto']
        )
        self.beam_request = StringProperty(
            name='beam_request',
            description='Driver-requested beam applied in headlights mode and whenever automatic mode activates the headlights.',
            default='low',
            choices=['low', 'high']
        )
        self.turn_signal = StringProperty(
            name='turn_signal',
            description='Driver-requested directional turn signal. The request remains stored while hazard lights are active.',
            default='off',
            choices=['off', 'left', 'right']
        )
        self.hazard_lights = BoolProperty(
            name='hazard_lights',
            description='Whether both direction indicators are requested as hazard lights.',
            default=False
        )
        self.actual_beam_state = StringProperty(
            name='actual_beam_state',
            description='Actual front-lighting feedback after applying power, the selected lighting mode, the beam request, and the automatic-lighting policy.',
            default='off',
            mode=2,
            choices=['off', 'parking', 'low', 'high']
        )
        self.actual_illumination = IntProperty(
            name='actual_illumination',
            description="The module's current absolute contribution to exterior illuminance. It is cleared immediately when power is turned off and otherwise includes front lighting and signals.",
            default=0,
            mode=2,
            unit='lux',
            minimum=0,
            maximum=1700,
            step=1,
            step_origin=0
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if lighting_mode is not None: code = self.lighting_mode.internal_set(lighting_mode)
        if beam_request is not None: code = self.beam_request.internal_set(beam_request)
        if turn_signal is not None: code = self.turn_signal.internal_set(turn_signal)
        if hazard_lights is not None: code = self.hazard_lights.internal_set(hazard_lights)
        if actual_beam_state is not None: code = self.actual_beam_state.internal_set(actual_beam_state)
        if actual_illumination is not None: code = self.actual_illumination.internal_set(actual_illumination)
        self._power_managed_properties = (self.lighting_mode, self.beam_request, self.turn_signal, self.hazard_lights, self.actual_beam_state, self.actual_illumination,)
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

    def get_lighting_mode(self) -> tuple[str, dict]:
        """
        Return the driver-selected exterior lighting mode. Requires module power.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- lighting_mode: Selected mode: off, parking, headlights, or auto. (type=string)

        Error Codes:
        - POWER_OFF: The exterior-light module must be powered on.
        """
        code, value = self.lighting_mode.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'lighting_mode': value})

    def set_lighting_mode(self, mode: str) -> tuple[str, dict]:
        """
        Select off, parking, headlights, or auto mode. Auto mode activates the requested beam according to exterior ambient illuminance after excluding this module's own contribution. Requires module power. Invalid input or a failed power precondition leaves state unchanged.

        Args:
        - mode:  (choices=['off', 'parking', 'headlights', 'auto'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The exterior-light module must be powered on.
        - INVALID_INPUT_ERROR: Mode must be off, parking, headlights, or auto.
        """
        code = self.lighting_mode.set(mode)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_beam_request(self) -> tuple[str, dict]:
        """
        Return the stored low- or high-beam request. Requires module power.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- beam_request: Requested beam: low or high. (type=string)

        Error Codes:
        - POWER_OFF: The exterior-light module must be powered on.
        """
        code, value = self.beam_request.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'beam_request': value})

    def set_beam_request(self, beam: str) -> tuple[str, dict]:
        """
        Request low or high beam. The request is retained in every lighting mode and is applied in headlights mode or when automatic mode activates the headlights. Requires module power. Invalid input or a failed power precondition leaves state unchanged.

        Args:
        - beam:  (choices=['low', 'high'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The exterior-light module must be powered on.
        - INVALID_INPUT_ERROR: Beam request must be low or high.
        """
        code = self.beam_request.set(beam)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_turn_signal(self) -> tuple[str, dict]:
        """
        Return the stored directional turn-signal request. Hazard lights can override its physical indication without erasing the request. Requires module power.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- turn_signal: Directional request: off, left, or right. (type=string)

        Error Codes:
        - POWER_OFF: The exterior-light module must be powered on.
        """
        code, value = self.turn_signal.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'turn_signal': value})

    def set_turn_signal(self, signal: str) -> tuple[str, dict]:
        """
        Set the directional turn-signal request to off, left, or right. While hazard lights are active, both indicators remain requested and this directional request is retained for use after hazards are disabled. Requires module power. Invalid input or a failed power precondition leaves state unchanged.

        Args:
        - signal:  (choices=['off', 'left', 'right'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The exterior-light module must be powered on.
        - INVALID_INPUT_ERROR: Turn signal must be off, left, or right.
        """
        code = self.turn_signal.set(signal)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_hazard_lights(self) -> tuple[str, dict]:
        """
        Return whether hazard lights are requested. Requires module power.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- hazard_lights: Whether both direction indicators are requested as hazard lights. (type=boolean)

        Error Codes:
        - POWER_OFF: The exterior-light module must be powered on.
        """
        code, value = self.hazard_lights.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'hazard_lights': value})

    def set_hazard_lights(self, enabled: bool) -> tuple[str, dict]:
        """
        Enable or disable hazard lights. Enabling hazards requests both direction indicators while preserving the stored directional turn-signal request. Requires module power. A failed power precondition or invalid input leaves state unchanged.

        Args:
        - enabled:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The exterior-light module must be powered on.
        """
        code = self.hazard_lights.set(enabled)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_actual_beam_state(self) -> tuple[str, dict]:
        """
        Return actual front-lighting feedback. In automatic mode this can differ from the stored beam request because headlights remain inactive in bright conditions. Requires module power.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- actual_beam_state: Actual front-lighting state: off, parking, low, or high. (type=string)

        Error Codes:
        - POWER_OFF: The exterior-light module must be powered on.
        """
        code, value = self.actual_beam_state.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'actual_beam_state': value})

    def get_actual_illumination(self) -> tuple[str, dict]:
        """
        Return this module's current absolute contribution to exterior illuminance, including front lighting and signals. Requires module power.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- actual_illumination: Current absolute exterior illuminance contribution in lux. (type=integer)

        Error Codes:
        - POWER_OFF: The exterior-light module must be powered on.
        """
        code, value = self.actual_illumination.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'actual_illumination': value})

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        Each minute, replace this module's exterior illuminance contribution. While power is off, keep actual_beam_state off, keep actual_illumination at zero, and contribute zero illuminance while preserving all driver requests. While powered, determine ambient exterior illuminance by subtracting this module's previous absolute contribution from aggregate exterior illuminance, with a minimum ambient value of zero. Off mode provides no front-light illumination. Parking mode sets actual_beam_state to parking and contributes 100 lux. Headlights mode sets actual_beam_state to the requested low or high beam and contributes 800 or 1600 lux respectively. In auto mode, activate the requested beam when ambient illuminance is at most 200 lux and set the beam state to off when ambient illuminance is at least 1000 lux. Between 201 and 999 lux, preserve activation only when the previous actual_beam_state was low or high, applying the current beam request; treat previous off or parking state as inactive and set actual_beam_state to off. While powered, add 100 lux for hazards, otherwise 50 lux for an active directional signal. Store the emitted total in actual_illumination so later automatic-lighting decisions can exclude this module's own output.

    Effect properties:
    - power: Gates all exterior-light output and keeps beam and illumination feedback cleared while off.
    - lighting_mode: Determines whether front lighting is off, parking, manually active, or automatically controlled.
    - beam_request: Determines whether active headlights use low or high beam.
    - turn_signal: Determines whether one directional signal contributes illumination when hazards are disabled.
    - hazard_lights: Determines whether both direction indicators contribute illumination.
    - actual_beam_state: Retains automatic-headlight activation within the hysteresis band and receives updated front-lighting feedback.
    - actual_illumination: Records the module's previous absolute contribution so automatic lighting can exclude it from ambient illuminance.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, [])

        if not powered:
            beam_code = self.actual_beam_state.internal_set('off')
            if beam_code != '[PASS]':
                return (beam_code, [])
            illumination_code = self.actual_illumination.internal_set(0)
            if illumination_code != '[PASS]':
                return (illumination_code, [])
            effect = {
                'trigger': 'tick',
                'source': context['object_id'],
                'target': context['space_id'],
                'function': 'set_contribution',
                'parameters': {
                    'property': 'illuminance',
                    'value': 0,
                    'unit': 'lux'
                }
            }
            return ('[PASS]', [effect])

        mode_code, mode = self.lighting_mode.get()
        if mode_code != '[PASS]':
            return (mode_code, [])

        request_code, beam_request = self.beam_request.get()
        if request_code != '[PASS]':
            return (request_code, [])

        signal_code, turn_signal = self.turn_signal.get()
        if signal_code != '[PASS]':
            return (signal_code, [])

        hazard_code, hazards = self.hazard_lights.get()
        if hazard_code != '[PASS]':
            return (hazard_code, [])

        previous_beam_code, previous_beam = self.actual_beam_state.get()
        if previous_beam_code != '[PASS]':
            return (previous_beam_code, [])

        previous_illumination_code, previous_illumination = self.actual_illumination.get()
        if previous_illumination_code != '[PASS]':
            return (previous_illumination_code, [])

        ambient_illuminance = max(
            0,
            context['space_state']['illuminance'] - previous_illumination
        )

        actual_beam = 'off'
        front_illumination = 0

        if mode == 'parking':
            actual_beam = 'parking'
            front_illumination = 100
        elif mode == 'headlights':
            actual_beam = beam_request
            if beam_request == 'low':
                front_illumination = 800
            else:
                front_illumination = 1600
        elif mode == 'auto':
            headlights_active = False
            if ambient_illuminance <= 200:
                headlights_active = True
            elif ambient_illuminance < 1000 and previous_beam in ('low', 'high'):
                headlights_active = True

            if headlights_active:
                actual_beam = beam_request
                if beam_request == 'low':
                    front_illumination = 800
                else:
                    front_illumination = 1600

        total_illumination = front_illumination
        if hazards:
            total_illumination += 100
        elif turn_signal != 'off':
            total_illumination += 50

        beam_code = self.actual_beam_state.internal_set(actual_beam)
        if beam_code != '[PASS]':
            return (beam_code, [])

        illumination_code = self.actual_illumination.internal_set(total_illumination)
        if illumination_code != '[PASS]':
            return (illumination_code, [])

        effect = {
            'trigger': 'tick',
            'source': context['object_id'],
            'target': context['space_id'],
            'function': 'set_contribution',
            'parameters': {
                'property': 'illuminance',
                'value': total_illumination,
                'unit': 'lux'
            }
        }
        return ('[PASS]', [effect])

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        After a successful public mutation, when power is false, set actual_beam_state to off, set actual_illumination to zero, and immediately replace the module's exterior illuminance contribution with zero. When power remains true, preserve the current actual beam and illumination feedback and retain the current actual_illumination contribution until the normal lighting update recalculates it.

    Effect properties:
    - power: Determines whether feedback and the exterior illuminance contribution must be cleared immediately.
    - actual_beam_state: Front-lighting feedback that is set to off whenever power is false.
    - actual_illumination: Illumination feedback that is set to zero whenever power is false and otherwise supplies the retained absolute contribution.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, [])

        if not powered:
            beam_code = self.actual_beam_state.internal_set('off')
            if beam_code != '[PASS]':
                return (beam_code, [])
            illumination_code = self.actual_illumination.internal_set(0)
            if illumination_code != '[PASS]':
                return (illumination_code, [])
            contribution = 0
        else:
            illumination_code, contribution = self.actual_illumination.get()
            if illumination_code != '[PASS]':
                return (illumination_code, [])

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
        return ('[PASS]', [effect])
