# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Curtain:
    """
    Curtain
    Description: Curtain. Users can query and set its open or closed state and opening percentage, and can also open or close it incrementally. Moving the curtain changes the degree of light blocking in its space.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, open_state: str=None, position: int=None) -> None:
        self.open_state = StringProperty(name='open_state', description='Derived open or closed state of the curtain. It is closed at 0 percent and open above 0 percent.', default='closed', mode=2, choices=['open', 'closed'])
        self.position = IntProperty(name='position', description='Opening percentage of the curtain, where 0 is fully closed and 100 is fully open.', default=0, unit='%', minimum=0, maximum=100, step=1, step_origin=0)
        if open_state is not None:
            code = self.open_state.internal_set(open_state)
        if position is not None:
            code = self.position.internal_set(position)
        self._disabled = {'properties': [], 'functions': [], 'events': []}
        self.open_state.internal_set('open' if self.position.value > 0 else 'closed')

    def get_open_state(self) -> tuple[str, dict]:
        """
        Return the curtain's derived open or closed state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- open_state: The curtain's state: open when position is above 0, otherwise closed. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.open_state.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'open_state': value})

    def set_open_state(self, value: str) -> tuple[str, dict]:
        """
        Set the curtain to open or closed. Opening sets the position to 100 percent; closing sets it to 0 percent. Invalid values leave the curtain unchanged.

        Args:
        - value: Desired curtain state. (choices=['open', 'closed'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        if type(value) is not str or value not in ('open', 'closed'):
            return ('[INVALID_INPUT_ERROR]', {})
        position = 100 if value == 'open' else 0
        code = self.position.set(position)
        if code != '[PASS]':
            return (code, {})
        code = self.open_state.internal_set(value)
        if code != '[PASS]':
            self.position.internal_set(0 if value == 'closed' else 100)
            return (code, {})
        return ('[PASS]', {})

    def get_position(self) -> tuple[str, dict]:
        """
        Return the curtain's opening percentage.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- position: The curtain opening percentage from 0 to 100. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.position.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'position': value})

    def set_position(self, value: int) -> tuple[str, dict]:
        """
        Set the curtain opening percentage and derive its open or closed state. Position 0 is closed; any position above 0 is open. Invalid values leave the curtain unchanged.

        Args:
        - value: Desired curtain opening percentage. (min=0, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        if type(value) is not int or isinstance(value, bool) or value < 0 or (value > 100):
            return ('[INVALID_INPUT_ERROR]', {})
        state = 'closed' if value == 0 else 'open'
        code = self.position.set(value)
        if code != '[PASS]':
            return (code, {})
        code = self.open_state.internal_set(state)
        if code != '[PASS]':
            self.position.internal_set(value)
            return (code, {})
        return ('[PASS]', {})

    def open_incrementally(self, percentage_points: int) -> tuple[str, dict]:
        """
        Increase the curtain opening percentage by the requested positive number of percentage points, capped at 100, and update its derived state.

        Args:
        - percentage_points: Positive number of percentage points by which to open the curtain. (min=1, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        if type(percentage_points) is not int or isinstance(percentage_points, bool) or percentage_points < 1 or (percentage_points > 100):
            return ('[INVALID_INPUT_ERROR]', {})
        code, current = self.position.get()
        if code != '[PASS]':
            return (code, {})
        new_position = min(100, current + percentage_points)
        return self.set_position(new_position)

    def close_incrementally(self, percentage_points: int) -> tuple[str, dict]:
        """
        Decrease the curtain opening percentage by the requested positive number of percentage points, floored at 0, and update its derived state.

        Args:
        - percentage_points: Positive number of percentage points by which to close the curtain. (min=1, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        if type(percentage_points) is not int or isinstance(percentage_points, bool) or percentage_points < 1 or (percentage_points > 100):
            return ('[INVALID_INPUT_ERROR]', {})
        code, current = self.position.get()
        if code != '[PASS]':
            return (code, {})
        new_position = max(0, current - percentage_points)
        return self.set_position(new_position)

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        After a successful curtain mutation, contribute position multiplied by 6 lux to the containing space's illuminance. A fully closed curtain contributes zero.

    Effect properties:
    - position: The curtain opening percentage determines its illuminance contribution.
        """
        code, position = self.position.get()
        if code != '[PASS]':
            return (code, [])
        return ('[PASS]', [{'trigger': 'after_action', 'source': context['object_id'], 'target': context['space_id'], 'function': 'set_contribution', 'parameters': {'property': 'illuminance', 'value': position * 6, 'unit': 'lux'}}])
