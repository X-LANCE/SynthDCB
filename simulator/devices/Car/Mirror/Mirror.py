# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Mirror:
    """
    Mirror
    Description: Powered exterior mirror, instantiated separately for the left and right sides. Supports querying and adjusting horizontal and vertical mirror positions, and controlling folding and unfolding.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, horizontal_position: int = None, vertical_position: int = None, folded: bool = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether electrical power to the mirror controls is on.',
            default=False
        )
        self.horizontal_position = IntProperty(
            name='horizontal_position',
            description='Normalized horizontal mirror position from -100 at the left adjustment limit through 0 at center to 100 at the right adjustment limit.',
            default=0,
            unit='%',
            minimum=-100,
            maximum=100,
            step=1,
            step_origin=-100
        )
        self.vertical_position = IntProperty(
            name='vertical_position',
            description='Normalized vertical mirror position from -100 at the downward adjustment limit through 0 at center to 100 at the upward adjustment limit.',
            default=0,
            unit='%',
            minimum=-100,
            maximum=100,
            step=1,
            step_origin=-100
        )
        self.folded = BoolProperty(
            name='folded',
            description='Whether the exterior mirror is folded inward.',
            default=False,
            mode=2
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if horizontal_position is not None: code = self.horizontal_position.internal_set(horizontal_position)
        if vertical_position is not None: code = self.vertical_position.internal_set(vertical_position)
        if folded is not None: code = self.folded.internal_set(folded)
        self._power_managed_properties = (self.horizontal_position, self.vertical_position, self.folded,)
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

    def get_horizontal_position(self) -> tuple[str, dict]:
        """
        Return the normalized horizontal mirror position. The query is rejected while power is off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- horizontal_position: Normalized horizontal position from -100 at the left limit to 100 at the right limit. (type=integer)

        Error Codes:
        - PRECONDITION_FAILED: Mirror power must be on.
        """
        power_code, power_value = self.power.get()
        if power_code != '[PASS]':
            return power_code, {}
        if not power_value:
            return '[PRECONDITION_FAILED]', {}

        code, value = self.horizontal_position.get()
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {'horizontal_position': value}

    def set_horizontal_position(self, value: int) -> tuple[str, dict]:
        """
        Set the normalized horizontal mirror position to an integer from -100 through 100. The action is rejected while power is off, and invalid input leaves state unchanged.

        Args:
        - value:  (min=-100, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: Mirror power must be on.
        - INVALID_INPUT_ERROR: Horizontal position must be an integer from -100 through 100.
        """
        if type(value) is not int or value < -100 or value > 100:
            return '[INVALID_INPUT_ERROR]', {}

        power_code, power_value = self.power.get()
        if power_code != '[PASS]':
            return power_code, {}
        if not power_value:
            return '[PRECONDITION_FAILED]', {}

        code = self.horizontal_position.set(value)
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {}

    def get_vertical_position(self) -> tuple[str, dict]:
        """
        Return the normalized vertical mirror position. The query is rejected while power is off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- vertical_position: Normalized vertical position from -100 at the downward limit to 100 at the upward limit. (type=integer)

        Error Codes:
        - PRECONDITION_FAILED: Mirror power must be on.
        """
        power_code, power_value = self.power.get()
        if power_code != '[PASS]':
            return power_code, {}
        if not power_value:
            return '[PRECONDITION_FAILED]', {}

        code, value = self.vertical_position.get()
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {'vertical_position': value}

    def set_vertical_position(self, value: int) -> tuple[str, dict]:
        """
        Set the normalized vertical mirror position to an integer from -100 through 100. The action is rejected while power is off, and invalid input leaves state unchanged.

        Args:
        - value:  (min=-100, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: Mirror power must be on.
        - INVALID_INPUT_ERROR: Vertical position must be an integer from -100 through 100.
        """
        if type(value) is not int or value < -100 or value > 100:
            return '[INVALID_INPUT_ERROR]', {}

        power_code, power_value = self.power.get()
        if power_code != '[PASS]':
            return power_code, {}
        if not power_value:
            return '[PRECONDITION_FAILED]', {}

        code = self.vertical_position.set(value)
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {}

    def get_folded(self) -> tuple[str, dict]:
        """
        Return whether the exterior mirror is folded inward. The query is rejected while power is off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- folded: Whether the exterior mirror is folded inward. (type=boolean)

        Error Codes:
        - PRECONDITION_FAILED: Mirror power must be on.
        """
        power_code, power_value = self.power.get()
        if power_code != '[PASS]':
            return power_code, {}
        if not power_value:
            return '[PRECONDITION_FAILED]', {}

        code, value = self.folded.get()
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {'folded': value}

    def fold(self) -> tuple[str, dict]:
        """
        Fold the exterior mirror inward. The action succeeds only while power is on and the mirror is currently unfolded; otherwise it is rejected without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: Mirror power must be on and the mirror must be unfolded.
        """
        power_code, power_value = self.power.get()
        if power_code != '[PASS]':
            return power_code, {}
        if not power_value:
            return '[PRECONDITION_FAILED]', {}

        folded_code, folded_value = self.folded.get()
        if folded_code != '[PASS]':
            return folded_code, {}
        if folded_value:
            return '[PRECONDITION_FAILED]', {}

        code = self.folded.internal_set(True)
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {}

    def unfold(self) -> tuple[str, dict]:
        """
        Unfold the exterior mirror. The action succeeds only while power is on and the mirror is currently folded; otherwise it is rejected without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: Mirror power must be on and the mirror must be folded.
        """
        power_code, power_value = self.power.get()
        if power_code != '[PASS]':
            return power_code, {}
        if not power_value:
            return '[PRECONDITION_FAILED]', {}

        folded_code, folded_value = self.folded.get()
        if folded_code != '[PASS]':
            return folded_code, {}
        if not folded_value:
            return '[PRECONDITION_FAILED]', {}

        code = self.folded.internal_set(False)
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {}