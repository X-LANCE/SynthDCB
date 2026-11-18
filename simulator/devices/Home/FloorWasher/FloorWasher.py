# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class FloorWasher:
    """
    FloorWasher
    Description: Floor washer. Users can query and set the cleaning mode and suction level, and can query the dirty-water tank, clean-water tank, roller-brush, and self-cleaning states.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, cleaning_mode: str = None, suction_level: int = None, dirty_water_tank: str = None, clean_water_tank: str = None, roller_brush: str = None, self_cleaning: str = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the floor washer is powered.',
            default=False
        )
        self.cleaning_mode = StringProperty(
            name='cleaning_mode',
            description='Selected floor-cleaning mode.',
            default='auto',
            choices=['auto', 'max']
        )
        self.suction_level = IntProperty(
            name='suction_level',
            description='Selected suction level from 1 to 3.',
            default=2,
            minimum=1,
            maximum=3,
            step=1,
            step_origin=1
        )
        self.dirty_water_tank = StringProperty(
            name='dirty_water_tank',
            description='Current dirty-water tank state.',
            default='available',
            mode=2,
            choices=['available', 'full']
        )
        self.clean_water_tank = StringProperty(
            name='clean_water_tank',
            description='Current clean-water tank state.',
            default='sufficient',
            mode=2,
            choices=['sufficient', 'low', 'empty']
        )
        self.roller_brush = StringProperty(
            name='roller_brush',
            description='Current roller-brush maintenance state.',
            default='clean',
            mode=2,
            choices=['clean', 'needs_cleaning']
        )
        self.self_cleaning = StringProperty(
            name='self_cleaning',
            description='Current self-cleaning state.',
            default='idle',
            mode=2,
            choices=['idle', 'cleaning', 'completed']
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if cleaning_mode is not None: code = self.cleaning_mode.internal_set(cleaning_mode)
        if suction_level is not None: code = self.suction_level.internal_set(suction_level)
        if dirty_water_tank is not None: code = self.dirty_water_tank.internal_set(dirty_water_tank)
        if clean_water_tank is not None: code = self.clean_water_tank.internal_set(clean_water_tank)
        if roller_brush is not None: code = self.roller_brush.internal_set(roller_brush)
        if self_cleaning is not None: code = self.self_cleaning.internal_set(self_cleaning)
        self._power_managed_properties = (self.cleaning_mode, self.suction_level, self.dirty_water_tank, self.clean_water_tank, self.roller_brush, self.self_cleaning,)
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

    def get_cleaning_mode(self) -> tuple[str, dict]:
        """
        Get the selected cleaning mode. The floor washer must be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- cleaning_mode: Selected floor-cleaning mode. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.cleaning_mode.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"cleaning_mode": value}

    def set_cleaning_mode(self, value: str) -> tuple[str, dict]:
        """
        Set the cleaning mode to auto or max. The floor washer must be powered on.

        Args:
        - value:  (choices=['auto', 'max'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        if type(value) is not str or value not in ('auto', 'max'):
            return "[ERROR] Invalid cleaning mode.", {}
        code = self.cleaning_mode.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_suction_level(self) -> tuple[str, dict]:
        """
        Get the selected suction level. The floor washer must be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- suction_level: Selected suction level from 1 to 3. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.suction_level.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"suction_level": value}

    def set_suction_level(self, value: int) -> tuple[str, dict]:
        """
        Set the suction level from 1 to 3. The floor washer must be powered on.

        Args:
        - value:  (min=1, max=3)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        if type(value) is not int or isinstance(value, bool) or value < 1 or value > 3:
            return "[ERROR] Invalid suction level.", {}
        code = self.suction_level.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_dirty_water_tank(self) -> tuple[str, dict]:
        """
        Get the dirty-water tank state. The floor washer must be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- dirty_water_tank: Current dirty-water tank state. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.dirty_water_tank.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"dirty_water_tank": value}

    def get_clean_water_tank(self) -> tuple[str, dict]:
        """
        Get the clean-water tank state. The floor washer must be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- clean_water_tank: Current clean-water tank state. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.clean_water_tank.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"clean_water_tank": value}

    def get_roller_brush(self) -> tuple[str, dict]:
        """
        Get the roller-brush maintenance state. The floor washer must be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- roller_brush: Current roller-brush maintenance state. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.roller_brush.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"roller_brush": value}

    def get_self_cleaning(self) -> tuple[str, dict]:
        """
        Get the self-cleaning state. The floor washer must be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- self_cleaning: Current self-cleaning state. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.self_cleaning.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"self_cleaning": value}