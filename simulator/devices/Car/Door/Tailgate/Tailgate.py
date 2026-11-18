# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..Door import Door

class Tailgate(Door):
    """
    Tailgate
    Description: Pickup cargo-bed tailgate that inherits Door locking, unlocking, and door-state queries. Represents the door connection between cargo_bed and exterior; opening and closing affect exchange between the cargo-bed Space and the outside. Instantiate only for vehicle models with a cargo bed.
    Version: 1.0.0
    Base: Door
    """

    def __init__(self, **base_kwargs) -> None:
        # initialize base Door class
        super().__init__(**base_kwargs)
        # define properties
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def manual_open(self) -> tuple[str, dict]:
        """
        Record a local manual action that places the tailgate in the fully open position. This is not a powered opening command. If the tailgate is closed and locked, the action is rejected and all state remains unchanged. Otherwise, including when it is already open, door_state is set to open and closure_feedback is set to false atomically; the lock state is unchanged.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: A closed, locked tailgate cannot be opened. Unlock it before moving it away from the closed position.
        """
        state_code, door_state = self.door_state.get()
        if state_code != '[PASS]':
            return (state_code, {})
        lock_code, locked = self.locked.get()
        if lock_code != '[PASS]':
            return (lock_code, {})
        if door_state == 'closed' and locked:
            return ('[PRECONDITION_FAILED]', {})

        code = self.door_state.internal_set('open')
        if code != '[PASS]':
            return (code, {})
        code = self.closure_feedback.internal_set(False)
        if code != '[PASS]':
            return (code, {})
        return (code, {})

    def manual_set_ajar(self) -> tuple[str, dict]:
        """
        Record a local manual action that places the tailgate in the ajar or unlatched position. This is not a powered movement command. If the tailgate is closed and locked, the action is rejected and all state remains unchanged. Otherwise, including when it is already ajar, door_state is set to ajar and closure_feedback is set to false atomically; the lock state is unchanged.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: A closed, locked tailgate cannot be set ajar. Unlock it before moving it away from the closed position.
        """
        state_code, door_state = self.door_state.get()
        if state_code != '[PASS]':
            return (state_code, {})
        lock_code, locked = self.locked.get()
        if lock_code != '[PASS]':
            return (lock_code, {})
        if door_state == 'closed' and locked:
            return ('[PRECONDITION_FAILED]', {})

        code = self.door_state.internal_set('ajar')
        if code != '[PASS]':
            return (code, {})
        code = self.closure_feedback.internal_set(False)
        if code != '[PASS]':
            return (code, {})
        return (code, {})