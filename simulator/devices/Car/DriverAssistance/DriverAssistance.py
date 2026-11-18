# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class DriverAssistance:
    """
    DriverAssistance
    Description: Driver assistance settings and state module. Supports switching cruise control on and off, setting target speed, and enabling assistance functions such as lane keeping and automatic following.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, cruise_control_enabled: bool = None, target_speed: int = None, lane_keeping_enabled: bool = None, automatic_following_enabled: bool = None) -> None:
        # define properties
        self.cruise_control_enabled = BoolProperty(
            name='cruise_control_enabled',
            description='Whether cruise-control assistance is enabled as a local driver setting.',
            default=False
        )
        self.target_speed = IntProperty(
            name='target_speed',
            description="Configured cruise-control target speed. This setting does not directly change the vehicle's actual speed.",
            default=60,
            unit='km/h',
            minimum=0,
            maximum=240,
            step=1,
            step_origin=0
        )
        self.lane_keeping_enabled = BoolProperty(
            name='lane_keeping_enabled',
            description='Whether lane-keeping assistance is enabled as a local driver setting.',
            default=False
        )
        self.automatic_following_enabled = BoolProperty(
            name='automatic_following_enabled',
            description='Whether automatic-following assistance is enabled as a local driver setting.',
            default=False
        )

        # initialize properties
        if cruise_control_enabled is not None: code = self.cruise_control_enabled.internal_set(cruise_control_enabled)
        if target_speed is not None: code = self.target_speed.internal_set(target_speed)
        if lane_keeping_enabled is not None: code = self.lane_keeping_enabled.internal_set(lane_keeping_enabled)
        if automatic_following_enabled is not None: code = self.automatic_following_enabled.internal_set(automatic_following_enabled)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_cruise_control_enabled(self) -> tuple[str, dict]:
        """
        Return whether cruise-control assistance is enabled. This setting does not indicate that cruise control is actively controlling the vehicle.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- cruise_control_enabled: Whether cruise-control assistance is enabled. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.cruise_control_enabled.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'cruise_control_enabled': value})

    def set_cruise_control_enabled(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable cruise-control assistance. This changes only the local assistance setting and does not directly change vehicle speed. Invalid input leaves state unchanged.

        Args:
        - value:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.cruise_control_enabled.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_target_speed(self) -> tuple[str, dict]:
        """
        Return the configured cruise-control target speed without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- target_speed: Configured cruise-control target speed in kilometers per hour. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.target_speed.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'target_speed': value})

    def set_target_speed(self, value: int) -> tuple[str, dict]:
        """
        Set the cruise-control target speed to an integer from 0 through 240 km/h. The setting may be configured while cruise control is disabled and does not directly alter actual vehicle speed. Invalid input leaves state unchanged.

        Args:
        - value:  (min=0, max=240)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - INVALID_INPUT_ERROR: Target speed must be an integer from 0 through 240 km/h.
        """
        if type(value) is not int or value < 0 or value > 240:
            return ('[INVALID_INPUT_ERROR]', {})
        code = self.target_speed.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_lane_keeping_enabled(self) -> tuple[str, dict]:
        """
        Return whether lane-keeping assistance is enabled. Enablement does not assert that lane keeping is currently active.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- lane_keeping_enabled: Whether lane-keeping assistance is enabled. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.lane_keeping_enabled.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'lane_keeping_enabled': value})

    def set_lane_keeping_enabled(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable lane-keeping assistance as a local driver setting. This does not assert active steering control. Invalid input leaves state unchanged.

        Args:
        - value:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.lane_keeping_enabled.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_automatic_following_enabled(self) -> tuple[str, dict]:
        """
        Return whether automatic-following assistance is enabled. Enablement does not assert that the vehicle is currently following another vehicle.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- automatic_following_enabled: Whether automatic-following assistance is enabled. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.automatic_following_enabled.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'automatic_following_enabled': value})

    def set_automatic_following_enabled(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable automatic-following assistance as a local driver setting. This does not assert active longitudinal control or alter actual vehicle speed. Invalid input leaves state unchanged.

        Args:
        - value:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.automatic_following_enabled.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})