# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty


class Sunshade:
    """
    Sunshade
    Description: Independent powered sunshade. Supports querying and setting the shade opening, stopping motion, and querying motion feedback. The degree of shading affects light and solar heat load in the corresponding area without changing the glass opening. Instantiate only for an independent shading mechanism not already owned by an existing Sunroof module, avoiding two sets of state for the same shade. Candidate selection and spatial/environmental constraints apply; action contracts are simulation designs.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, opening: int = None, target_opening: int = None, motion_state: str = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether electrical power is available for shade movement and non-power public operations. Turning power off suspends movement while retaining the current opening and target.',
            default=False
        )
        self.opening = IntProperty(
            name='opening',
            description='Current physical shade opening percentage. Zero is fully closed for maximum shading, and 100 is fully open.',
            default=0,
            mode=2,
            unit='%',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.target_opening = IntProperty(
            name='target_opening',
            description='Internally retained opening percentage toward which the shade moves when powered.',
            default=0,
            mode=0,
            unit='%',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.motion_state = StringProperty(
            name='motion_state',
            description='Directional motion feedback. Opening or closing indicates the pending movement direction; movement is suspended while power is off.',
            default='stopped',
            mode=2,
            choices=['opening', 'closing', 'stopped']
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if opening is not None: code = self.opening.internal_set(opening)
        if target_opening is not None: code = self.target_opening.internal_set(target_opening)
        if motion_state is not None: code = self.motion_state.internal_set(motion_state)
        self._power_managed_properties = (self.opening, self.motion_state,)
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

    def get_opening(self) -> tuple[str, dict]:
        """
        Return the current physical shade opening percentage without changing state. This function is unavailable while power is off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- opening: Current opening percentage from 0 for fully closed through 100 for fully open. (type=integer)

        Error Codes:
        - POWER_OFF: The sunshade must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return power_code, {}
        if not powered:
            return '[POWER_OFF]', {}

        code, value = self.opening.get()
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {'opening': value}

    def set_opening(self, value: int) -> tuple[str, dict]:
        """
        Command an integer opening percentage from 0 through 100 while powered. A value above the current opening starts or retargets opening motion; a value below it starts or retargets closing motion. A value equal to the current opening stops motion immediately. The shade subsequently moves by up to 20 percentage points per minute and stops exactly at the target. Invalid input or unavailable power leaves all state unchanged.

        Args:
        - value: Desired shade opening percentage. (min=0, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The sunshade must be powered on.
        - INVALID_INPUT_ERROR: Opening must be an integer from 0 through 100.
        """
        if type(value) is not int or value < 0 or value > 100:
            return '[INVALID_INPUT_ERROR]', {}

        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return power_code, {}
        if not powered:
            return '[POWER_OFF]', {}

        opening_code, current_opening = self.opening.get()
        if opening_code != '[PASS]':
            return opening_code, {}

        if value > current_opening:
            next_motion_state = 'opening'
        elif value < current_opening:
            next_motion_state = 'closing'
        else:
            next_motion_state = 'stopped'

        target_code = self.target_opening.internal_set(value)
        if target_code != '[PASS]':
            return target_code, {}

        motion_code = self.motion_state.internal_set(next_motion_state)
        if motion_code != '[PASS]':
            return motion_code, {}

        return '[PASS]', {}

    def stop_motion(self) -> tuple[str, dict]:
        """
        Stop shade motion at its current physical opening while powered. The current opening becomes the retained target, so later ticks do not resume the interrupted command. Calling this while already stopped is idempotent. If power is off, the operation is rejected without mutation.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The sunshade must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return power_code, {}
        if not powered:
            return '[POWER_OFF]', {}

        opening_code, current_opening = self.opening.get()
        if opening_code != '[PASS]':
            return opening_code, {}

        target_code = self.target_opening.internal_set(current_opening)
        if target_code != '[PASS]':
            return target_code, {}

        motion_code = self.motion_state.internal_set('stopped')
        if motion_code != '[PASS]':
            return motion_code, {}

        return '[PASS]', {}

    def get_motion_state(self) -> tuple[str, dict]:
        """
        Return whether the shade has an opening, closing, or stopped motion state without changing state. This function is unavailable while power is off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- motion_state: Current directional motion feedback: opening, closing, or stopped. (type=string)

        Error Codes:
        - POWER_OFF: The sunshade must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return power_code, {}
        if not powered:
            return '[POWER_OFF]', {}

        code, value = self.motion_state.get()
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {'motion_state': value}

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        While powered, move opening toward target_opening by up to 20 percentage points per elapsed minute in the indicated direction and stop exactly at the target. While unpowered, do not advance the opening or discard the pending target. For each elapsed minute, set the transmitted illuminance contribution in the containing Space to opening multiplied by 10 lux and add opening divided by 1000 degrees Celsius to that Space's temperature as solar heat load. These passive effects depend on physical opening even while power is off; a fully closed shade contributes zero transmitted illuminance and zero solar heating.

    Effect properties:
    - power: Determines whether pending shade movement may advance.
    - opening: Determines current transmitted illuminance and solar heat load and is advanced only while powered.
    - target_opening: Defines the retained endpoint toward which the powered shade moves.
    - motion_state: Defines the pending movement direction and changes to stopped when the target is reached.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return power_code, []

        previous_properties = context['pre_state']['objects'][context['object_id']]['properties']
        minutes = context['minutes']

        if powered:
            opening_code, current_opening = self.opening.get()
            if opening_code != '[PASS]':
                return opening_code, []

            motion_code, motion = self.motion_state.get()
            if motion_code != '[PASS]':
                return motion_code, []

            target = previous_properties['target_opening']
            maximum_change = 20 * minutes
            new_opening = current_opening
            new_motion = motion

            if motion == 'opening':
                if target > current_opening:
                    new_opening = min(target, current_opening + maximum_change)
                    if new_opening == target:
                        new_motion = 'stopped'
                else:
                    new_motion = 'stopped'
            elif motion == 'closing':
                if target < current_opening:
                    new_opening = max(target, current_opening - maximum_change)
                    if new_opening == target:
                        new_motion = 'stopped'
                else:
                    new_motion = 'stopped'

            if new_opening != current_opening:
                opening_write_code = self.opening.internal_set(new_opening)
                if opening_write_code != '[PASS]':
                    return opening_write_code, []

            if new_motion != motion:
                motion_write_code = self.motion_state.internal_set(new_motion)
                if motion_write_code != '[PASS]':
                    return motion_write_code, []

            physical_opening = new_opening
        else:
            physical_opening = previous_properties['opening']

        illuminance = physical_opening * 10
        solar_heat = round(physical_opening * minutes / 1000, 3)

        effects = [
            {
                'trigger': 'tick',
                'source': context['object_id'],
                'target': context['space_id'],
                'function': 'set_contribution',
                'parameters': {
                    'property': 'illuminance',
                    'value': illuminance,
                    'unit': 'lux'
                }
            },
            {
                'trigger': 'tick',
                'source': context['object_id'],
                'target': context['space_id'],
                'function': 'delta',
                'parameters': {
                    'property': 'temperature',
                    'value': solar_heat,
                    'unit': 'degC'
                }
            }
        ]
        return '[PASS]', effects