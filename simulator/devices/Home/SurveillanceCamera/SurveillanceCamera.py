# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class SurveillanceCamera:
    """
    SurveillanceCamera
    Description: Surveillance camera. Users can query the video-monitoring state and set camera power, horizontal and vertical pan-tilt directions, night-vision mode, and motion-tracking state.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, video_monitoring: bool = None, horizontal_pan: str = None, vertical_pan: str = None, night_vision: str = None, motion_tracking: bool = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the surveillance camera is powered.',
            default=False
        )
        self.video_monitoring = BoolProperty(
            name='video_monitoring',
            description='Whether video monitoring is active.',
            default=False
        )
        self.horizontal_pan = StringProperty(
            name='horizontal_pan',
            description='Horizontal pan direction of the camera.',
            default='center',
            choices=['left', 'center', 'right']
        )
        self.vertical_pan = StringProperty(
            name='vertical_pan',
            description='Vertical tilt direction of the camera.',
            default='center',
            choices=['up', 'center', 'down']
        )
        self.night_vision = StringProperty(
            name='night_vision',
            description='Night-vision operating mode.',
            default='auto',
            choices=['auto', 'on', 'off']
        )
        self.motion_tracking = BoolProperty(
            name='motion_tracking',
            description='Whether automatic motion tracking is enabled.',
            default=False
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if video_monitoring is not None: code = self.video_monitoring.internal_set(video_monitoring)
        if horizontal_pan is not None: code = self.horizontal_pan.internal_set(horizontal_pan)
        if vertical_pan is not None: code = self.vertical_pan.internal_set(vertical_pan)
        if night_vision is not None: code = self.night_vision.internal_set(night_vision)
        if motion_tracking is not None: code = self.motion_tracking.internal_set(motion_tracking)
        self._power_managed_properties = (self.video_monitoring, self.horizontal_pan, self.vertical_pan, self.night_vision, self.motion_tracking,)
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

    def get_video_monitoring(self) -> tuple[str, dict]:
        """
        Return whether video monitoring is active. The camera must be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- video_monitoring: Whether video monitoring is active. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[POWER_OFF]", {}
        code, value = self.video_monitoring.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"video_monitoring": value}

    def set_video_monitoring(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable video monitoring. The camera must be powered on.

        Args:
        - value: Whether video monitoring should be active.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[POWER_OFF]", {}
        code = self.video_monitoring.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_horizontal_pan(self) -> tuple[str, dict]:
        """
        Return the horizontal pan direction. The camera must be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- horizontal_pan: The current horizontal pan direction. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[POWER_OFF]", {}
        code, value = self.horizontal_pan.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"horizontal_pan": value}

    def set_horizontal_pan(self, value: str) -> tuple[str, dict]:
        """
        Set the horizontal pan direction to left, center, or right. The camera must be powered on.

        Args:
        - value: The desired horizontal pan direction. (choices=['left', 'center', 'right'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[POWER_OFF]", {}
        code = self.horizontal_pan.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_vertical_pan(self) -> tuple[str, dict]:
        """
        Return the vertical tilt direction. The camera must be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- vertical_pan: The current vertical tilt direction. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[POWER_OFF]", {}
        code, value = self.vertical_pan.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"vertical_pan": value}

    def set_vertical_pan(self, value: str) -> tuple[str, dict]:
        """
        Set the vertical tilt direction to up, center, or down. The camera must be powered on.

        Args:
        - value: The desired vertical tilt direction. (choices=['up', 'center', 'down'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[POWER_OFF]", {}
        code = self.vertical_pan.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_night_vision(self) -> tuple[str, dict]:
        """
        Return the night-vision mode. The camera must be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- night_vision: The current night-vision mode. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[POWER_OFF]", {}
        code, value = self.night_vision.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"night_vision": value}

    def set_night_vision(self, value: str) -> tuple[str, dict]:
        """
        Set night vision to auto, on, or off. The camera must be powered on.

        Args:
        - value: The desired night-vision mode. (choices=['auto', 'on', 'off'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[POWER_OFF]", {}
        code = self.night_vision.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_motion_tracking(self) -> tuple[str, dict]:
        """
        Return whether motion tracking is enabled. The camera must be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- motion_tracking: Whether motion tracking is enabled. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[POWER_OFF]", {}
        code, value = self.motion_tracking.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"motion_tracking": value}

    def set_motion_tracking(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable motion tracking. The camera must be powered on.

        Args:
        - value: Whether motion tracking should be enabled.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[POWER_OFF]", {}
        code = self.motion_tracking.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}