# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Door:
    """
    Door
    Description: Vehicle door lock and door state module, instantiated for each actual side door or tailgate. Supports locking, unlocking, and querying lock state, door opening/closing state, and closure feedback; a locked door is not necessarily closed. The base class does not provide powered opening or closing; manual operation is updated through local environment actions. Door opening and closing contribute to exchange between the corresponding Space and the outside.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, locked: bool = None, door_state: str = None, closure_feedback: bool = None) -> None:
        # define properties
        self.locked = BoolProperty(
            name='locked',
            description='Whether the door lock is engaged. This state does not imply that the door is physically closed.',
            default=False,
            mode=2
        )
        self.door_state = StringProperty(
            name='door_state',
            description='Physical door position reported by local manual environment actions.',
            default='closed',
            mode=2,
            choices=['closed', 'ajar', 'open']
        )
        self.closure_feedback = BoolProperty(
            name='closure_feedback',
            description='Whether the door is fully closed and latched. Manual environment actions set this to true only after complete closure.',
            default=True,
            mode=2
        )

        # initialize properties
        if locked is not None: code = self.locked.internal_set(locked)
        if door_state is not None: code = self.door_state.internal_set(door_state)
        if closure_feedback is not None: code = self.closure_feedback.internal_set(closure_feedback)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_locked(self) -> tuple[str, dict]:
        """
        Return whether the door lock is engaged. The result does not indicate whether the door is physically closed.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- locked: Whether the door lock is engaged. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.locked.get()
        if code != '[PASS]':
            return (code, {})
        return (code, {'locked': value})

    def lock(self) -> tuple[str, dict]:
        """
        Engage the door lock without changing the physical door position or closure feedback. The action is idempotent and may be used even when the door is open or ajar.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.locked.internal_set(True)
        if code != '[PASS]':
            return (code, {})
        return (code, {})

    def unlock(self) -> tuple[str, dict]:
        """
        Disengage the door lock without changing the physical door position or closure feedback. The action is idempotent.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.locked.internal_set(False)
        if code != '[PASS]':
            return (code, {})
        return (code, {})

    def get_door_state(self) -> tuple[str, dict]:
        """
        Return the manually reported physical door position: closed, ajar, or open. This function does not move the door.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- door_state: Physical door position: closed, ajar, or open. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.door_state.get()
        if code != '[PASS]':
            return (code, {})
        return (code, {'door_state': value})

    def get_closure_feedback(self) -> tuple[str, dict]:
        """
        Return whether the door is fully closed and latched. This feedback is independent of the lock state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- closure_feedback: Whether the door is fully closed and latched. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.closure_feedback.get()
        if code != '[PASS]':
            return (code, {})
        return (code, {'closure_feedback': value})

    def manual_open(self) -> tuple[str, dict]:
        """
        Record a local manual action that places the door in the fully open position. This is not a powered opening command. The door state and closure feedback are updated atomically, and the lock state is unchanged.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.door_state.internal_set('open')
        if code != '[PASS]':
            return (code, {})
        code = self.closure_feedback.internal_set(False)
        if code != '[PASS]':
            return (code, {})
        return (code, {})

    def manual_set_ajar(self) -> tuple[str, dict]:
        """
        Record a local manual action that leaves the door partially closed or unlatched. This is not a powered movement command. The door state and closure feedback are updated atomically, and the lock state is unchanged.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.door_state.internal_set('ajar')
        if code != '[PASS]':
            return (code, {})
        code = self.closure_feedback.internal_set(False)
        if code != '[PASS]':
            return (code, {})
        return (code, {})

    def manual_close(self) -> tuple[str, dict]:
        """
        Record a local manual action that fully closes and latches the door. This is not a powered closing command. The door state and closure feedback are updated atomically, and the lock state is unchanged.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.door_state.internal_set('closed')
        if code != '[PASS]':
            return (code, {})
        code = self.closure_feedback.internal_set(True)
        if code != '[PASS]':
            return (code, {})
        return (code, {})

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        For a seat-mounted door, use the cabin space resolved by type; for a trunk or cargo door, use its own space. Each minute while closure_feedback is false, move the corresponding interior Space temperature and noise fully to the current exterior values to represent exchange through the unsealed opening. When closure_feedback is true, produce no exchange effect.

    Effect properties:
    - closure_feedback: Determines whether the door is sealed or permits exchange with the exterior.
        """
        code, closure_feedback = self.closure_feedback.get()
        if code != '[PASS]':
            return (code, [])
        if closure_feedback:
            return ('[PASS]', [])

        exterior = next(
            space
            for space in context['pre_state']['spaces'].values()
            if space['type'] == 'exterior'
        )

        interior_id = context['space_id']
        interior = context['pre_state']['spaces'][interior_id]
        if interior['type'] in ('driver_seat', 'front_passenger_seat', 'passenger_seat'):
            interior_id, interior = next(
                (space_id, space)
                for space_id, space in context['pre_state']['spaces'].items()
                if space['type'] == 'cabin'
            )
        current_temperature = interior['properties']['temperature']
        current_noise = interior['properties']['noise']
        exterior_temperature = exterior['properties']['temperature']
        exterior_noise = exterior['properties']['noise']

        effects = []

        if current_temperature != exterior_temperature:
            temperature_target = round(exterior_temperature, 1)
            temperature_rate = round(abs(exterior_temperature - current_temperature), 1)
            if temperature_rate > 0:
                effects.append({
                    'trigger': 'tick',
                    'source': context['object_id'],
                    'target': interior_id,
                    'function': 'approach',
                    'parameters': {
                        'property': 'temperature',
                        'value': temperature_target,
                        'rate_per_minute': temperature_rate,
                        'unit': 'degC'
                    }
                })

        if current_noise != exterior_noise:
            noise_target = round(exterior_noise, 1)
            noise_rate = round(abs(exterior_noise - current_noise), 1)
            if noise_rate > 0:
                effects.append({
                    'trigger': 'tick',
                    'source': context['object_id'],
                    'target': interior_id,
                    'function': 'approach',
                    'parameters': {
                        'property': 'noise',
                        'value': noise_target,
                        'rate_per_minute': noise_rate,
                        'unit': 'dBA'
                    }
                })

        return ('[PASS]', effects)