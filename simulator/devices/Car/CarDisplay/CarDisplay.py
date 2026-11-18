# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class CarDisplay:
    """
    CarDisplay
    Description: In-vehicle display, instantiated for each actual independent center, instrument, front-passenger, or rear-seat screen. Supports brightness, light/dark theme, and display layout settings.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, brightness: int = None, theme: str = None, layout: str = None) -> None:
        # define properties
        self.brightness = IntProperty(
            name='brightness',
            description='Configured display brightness as a percentage.',
            default=50,
            unit='%',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.theme = StringProperty(
            name='theme',
            description='Selected light or dark display theme.',
            default='light',
            choices=['light', 'dark']
        )
        self.layout = StringProperty(
            name='layout',
            description='Selected display presentation layout.',
            default='standard',
            choices=['standard', 'minimal', 'split']
        )

        # initialize properties
        if brightness is not None: code = self.brightness.internal_set(brightness)
        if theme is not None: code = self.theme.internal_set(theme)
        if layout is not None: code = self.layout.internal_set(layout)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_brightness(self) -> tuple[str, dict]:
        """
        Return the configured display brightness percentage without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- brightness: Configured display brightness from 0 through 100 percent. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.brightness.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'brightness': value})

    def set_brightness(self, value: int) -> tuple[str, dict]:
        """
        Set display brightness to an integer from 0 through 100 percent. This changes only the display setting and does not claim a corresponding cabin illuminance. Invalid input is rejected and leaves state unchanged.

        Args:
        - value:  (min=0, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - INVALID_INPUT_ERROR: Brightness must be an integer from 0 through 100.
        """
        code = self.brightness.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_theme(self) -> tuple[str, dict]:
        """
        Return the selected display theme without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- theme: Selected display theme: light or dark. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.theme.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'theme': value})

    def set_theme(self, value: str) -> tuple[str, dict]:
        """
        Select the light or dark display theme. Invalid input is rejected and leaves state unchanged.

        Args:
        - value:  (choices=['light', 'dark'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - INVALID_INPUT_ERROR: Theme must be light or dark.
        """
        code = self.theme.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_layout(self) -> tuple[str, dict]:
        """
        Return the selected display layout without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- layout: Selected presentation layout: standard, minimal, or split. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.layout.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'layout': value})

    def set_layout(self, value: str) -> tuple[str, dict]:
        """
        Select the standard, minimal, or split presentation layout. The setting changes presentation only and does not alter underlying vehicle state. Invalid input is rejected and leaves state unchanged.

        Args:
        - value:  (choices=['standard', 'minimal', 'split'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - INVALID_INPUT_ERROR: Layout must be standard, minimal, or split.
        """
        code = self.layout.set(value)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})