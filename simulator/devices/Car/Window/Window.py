# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Window:
    """
    Window
    Description: Vehicle window. Supports querying and setting the opening percentage. The degree of opening affects illuminance and ambient sound level in the vehicle interior according to conditions outside the vehicle.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, position: int = None) -> None:
        # define properties
        self.position = IntProperty(
            name='position',
            description='Window opening percentage, where 0 is fully closed and 100 is fully open.',
            default=0,
            unit='%',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )

        # initialize properties
        if position is not None: code = self.position.internal_set(position)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_position(self) -> tuple[str, dict]:
        """
        Return the current window opening percentage without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- position: Current opening percentage, where 0 is fully closed and 100 is fully open. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.position.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'position': value})

    def set_position(self, value: int) -> tuple[str, dict]:
        """
        Set the window opening percentage to an integer from 0 through 100 inclusive. Invalid values are rejected and leave state unchanged.

        Args:
        - value: Desired opening percentage. (min=0, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - INVALID_INPUT_ERROR: The opening percentage must be an integer from 0 through 100.
        """
        code = self.position.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        Resolve the cabin and exterior by their space types in pre_state; the window may be mounted in a seat space. Emit effects to the cabin ID. Each minute while position is greater than zero, move cabin illuminance and ambient noise toward the corresponding exterior values by position percent of each current difference. Round each resulting change to the nearest integer, with half values rounded away from zero, and keep the resulting physical values within their supported bounds. At position zero, neither physical property changes.

    Effect properties:
    - position: Opening percentage that determines the strength of illuminance and ambient-noise coupling between the exterior and cabin.
        """
        code, position = self.position.get()
        if code != '[PASS]':
            return (code, [])
        if position == 0:
            return ('[PASS]', [])

        exterior = next(
            space
            for space in context['pre_state']['spaces'].values()
            if space['type'] == 'exterior'
        )

        cabin_id, cabin = next(
            (space_id, space)
            for space_id, space in context['pre_state']['spaces'].items()
            if space['type'] == 'cabin'
        )
        cabin_illuminance = cabin['properties']['illuminance']
        exterior_illuminance = exterior['properties']['illuminance']
        cabin_noise = cabin['properties']['noise']
        exterior_noise = exterior['properties']['noise']

        illuminance_rate = int(
            abs(exterior_illuminance - cabin_illuminance) * position / 100 + 0.5
        )
        noise_rate = int(
            abs(exterior_noise - cabin_noise) * position / 100 + 0.5
        )

        effects = []

        if exterior_illuminance != cabin_illuminance and illuminance_rate > 0:
            effects.append({
                'trigger': 'tick',
                'source': context['object_id'],
                'target': cabin_id,
                'function': 'approach',
                'parameters': {
                    'property': 'illuminance',
                    'value': exterior_illuminance,
                    'rate_per_minute': illuminance_rate,
                    'unit': 'lux'
                }
            })

        if exterior_noise != cabin_noise and noise_rate > 0:
            effects.append({
                'trigger': 'tick',
                'source': context['object_id'],
                'target': cabin_id,
                'function': 'approach',
                'parameters': {
                    'property': 'noise',
                    'value': exterior_noise,
                    'rate_per_minute': noise_rate,
                    'unit': 'dBA'
                }
            })

        return ('[PASS]', effects)