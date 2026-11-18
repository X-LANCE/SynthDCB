# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class AdaptiveDamping:
    """
    AdaptiveDamping
    Description: Variable damping module with user-selectable modes. Supports selecting a damping mode from a fixed set and querying the effective state. Its configuration is independent of air-suspension height control, so inheritance from AirSuspension is not required.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, damping_mode: str = None, effective_state: str = None) -> None:
        # define properties
        self.damping_mode = StringProperty(
            name='damping_mode',
            description='User-selected damping mode.',
            default='standard',
            choices=['comfort', 'standard', 'sport']
        )
        self.effective_state = StringProperty(
            name='effective_state',
            description='Effective damping state currently applied by the module.',
            default='standard',
            mode=2,
            choices=['comfort', 'standard', 'sport']
        )

        # initialize properties
        if damping_mode is not None: code = self.damping_mode.internal_set(damping_mode)
        if effective_state is not None: code = self.effective_state.internal_set(effective_state)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_damping_mode(self) -> tuple[str, dict]:
        """
        Return the user-selected damping mode without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- damping_mode: Selected damping mode: comfort, standard, or sport. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.damping_mode.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'damping_mode': value})

    def set_damping_mode(self, mode: str) -> tuple[str, dict]:
        """
        Select comfort, standard, or sport damping. A valid selection is applied immediately to both the configured mode and effective state. Invalid input is rejected and leaves all state unchanged.

        Args:
        - mode:  (choices=['comfort', 'standard', 'sport'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - INVALID_INPUT_ERROR: Damping mode must be comfort, standard, or sport.
        """
        if type(mode) is not str or mode not in ('comfort', 'standard', 'sport'):
            return ('[INVALID_INPUT_ERROR]', {})

        code = self.damping_mode.set(mode)
        if code != '[PASS]':
            return (code, {})

        code = self.effective_state.internal_set(mode)
        if code != '[PASS]':
            return (code, {})

        return ('[PASS]', {})

    def get_effective_state(self) -> tuple[str, dict]:
        """
        Return the effective damping state currently applied by the module without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- effective_state: Effective damping state: comfort, standard, or sport. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.effective_state.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'effective_state': value})