# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Display:
    """
    Display
    Description: Display settings, placed in Setting. Supports 0–100% brightness, automatic brightness, dark mode, and screen-off timeouts of 1/2/5/10 minutes. Each setting is stored independently, without changing virtual Space properties.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, brightness: int = None, automatic_brightness: bool = None, dark_mode: bool = None, screen_off_timeout_minutes: str = None) -> None:
        # define properties
        self.brightness = IntProperty(
            name='brightness',
            description='Configured display brightness as a whole-number percentage from 0 through 100.',
            default=50,
            unit='percent',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.automatic_brightness = BoolProperty(
            name='automatic_brightness',
            description='Whether automatic brightness adjustment is enabled.',
            default=False
        )
        self.dark_mode = BoolProperty(
            name='dark_mode',
            description='Whether dark mode is enabled.',
            default=False
        )
        self.screen_off_timeout_minutes = StringProperty(
            name='screen_off_timeout_minutes',
            description='Configured inactivity timeout before the screen turns off, represented as 1, 2, 5, or 10 minutes.',
            default='5',
            unit='minutes',
            choices=['1', '2', '5', '10']
        )

        # initialize properties
        if brightness is not None: code = self.brightness.internal_set(brightness)
        if automatic_brightness is not None: code = self.automatic_brightness.internal_set(automatic_brightness)
        if dark_mode is not None: code = self.dark_mode.internal_set(dark_mode)
        if screen_off_timeout_minutes is not None: code = self.screen_off_timeout_minutes.internal_set(screen_off_timeout_minutes)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_brightness(self) -> tuple[str, dict]:
        """
        Return the configured display brightness percentage without changing any setting.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- brightness: Configured display brightness percentage. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.brightness.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'brightness': value
        }
        return code, response

    def set_brightness(self, value: int) -> tuple[str, dict]:
        """
        Set display brightness to a whole-number percentage from 0 through 100. Invalid values are rejected and leave all settings unchanged.

        Args:
        - value:  (min=0, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.brightness.set(value)
        response = {}
        return code, response

    def get_automatic_brightness(self) -> tuple[str, dict]:
        """
        Return whether automatic brightness adjustment is enabled without changing any setting.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- automatic_brightness: Whether automatic brightness adjustment is enabled. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.automatic_brightness.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'automatic_brightness': value
        }
        return code, response

    def set_automatic_brightness(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable automatic brightness adjustment. This changes only the automatic brightness setting.

        Args:
        - value:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.automatic_brightness.set(value)
        response = {}
        return code, response

    def get_dark_mode(self) -> tuple[str, dict]:
        """
        Return whether dark mode is enabled without changing any setting.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- dark_mode: Whether dark mode is enabled. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.dark_mode.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'dark_mode': value
        }
        return code, response

    def set_dark_mode(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable dark mode. This changes only the dark mode setting.

        Args:
        - value:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.dark_mode.set(value)
        response = {}
        return code, response

    def get_screen_off_timeout_minutes(self) -> tuple[str, dict]:
        """
        Return the configured screen-off timeout as one of the supported minute values: 1, 2, 5, or 10.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- screen_off_timeout_minutes: Configured screen-off timeout in minutes, represented as 1, 2, 5, or 10. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.screen_off_timeout_minutes.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'screen_off_timeout_minutes': value
        }
        return code, response

    def set_screen_off_timeout_minutes(self, value: str) -> tuple[str, dict]:
        """
        Set the screen-off timeout to exactly 1, 2, 5, or 10 minutes. Unsupported values are rejected and leave all settings unchanged.

        Args:
        - value:  (choices=['1', '2', '5', '10'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.screen_off_timeout_minutes.set(value)
        response = {}
        return code, response