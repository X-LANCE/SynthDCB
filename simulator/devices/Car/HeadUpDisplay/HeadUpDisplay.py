# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class HeadUpDisplay:
    """
    HeadUpDisplay
    Description: Head-up display module, instantiated only for vehicle models equipped with the corresponding hardware. Supports enabling/disabling the display, brightness, and projection position adjustment. Displays information supplied by vehicle and navigation modules without holding a second set of speed or route state. Projection range and supported display content are fixed capabilities; augmented reality and automated driving are not implicit base capabilities.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, enabled: bool = None, brightness: int = None, projection_position: int = None, supported_content: str = None) -> None:
        # define properties
        self.enabled = BoolProperty(
            name='enabled',
            description='Whether the head-up display is enabled.',
            default=False
        )
        self.brightness = IntProperty(
            name='brightness',
            description='Normalized display brightness percentage within the hardware-supported brightness range.',
            default=50,
            unit='%',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.projection_position = IntProperty(
            name='projection_position',
            description='Normalized projection position within the hardware-supported adjustment range, where 0 is the lowest position and 100 is the highest.',
            default=50,
            unit='%',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.supported_content = StringProperty(
            name='supported_content',
            description='Fixed content capability profile indicating that the display can present information supplied by vehicle and navigation modules.',
            default='vehicle_and_navigation',
            mode=2,
            choices=['vehicle_and_navigation']
        )

        # initialize properties
        if enabled is not None: code = self.enabled.internal_set(enabled)
        if brightness is not None: code = self.brightness.internal_set(brightness)
        if projection_position is not None: code = self.projection_position.internal_set(projection_position)
        if supported_content is not None: code = self.supported_content.internal_set(supported_content)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_enabled(self) -> tuple[str, dict]:
        """
        Return whether the head-up display is enabled without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- enabled: Whether the head-up display is enabled. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.enabled.get()
        if code != '[PASS]':
            return (code, {})
        return (code, {'enabled': value})

    def set_enabled(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable the head-up display. The brightness and projection position settings are preserved when the display is disabled. Invalid input is rejected without changing state.

        Args:
        - value:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.enabled.set(value)
        if code != '[PASS]':
            return (code, {})
        return (code, {})

    def get_brightness(self) -> tuple[str, dict]:
        """
        Return the normalized head-up display brightness percentage without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- brightness: Normalized brightness percentage from 0 through 100. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.brightness.get()
        if code != '[PASS]':
            return (code, {})
        return (code, {'brightness': value})

    def set_brightness(self, value: int) -> tuple[str, dict]:
        """
        Set the normalized head-up display brightness to an integer percentage from 0 through 100. The setting may be configured while the display is disabled and takes effect when enabled. Invalid input is rejected without changing state.

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
        return (code, {})

    def get_projection_position(self) -> tuple[str, dict]:
        """
        Return the normalized projection position without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- projection_position: Normalized projection position from 0 at the lowest supported position to 100 at the highest. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.projection_position.get()
        if code != '[PASS]':
            return (code, {})
        return (code, {'projection_position': value})

    def set_projection_position(self, value: int) -> tuple[str, dict]:
        """
        Set the normalized projection position to an integer percentage from 0 through 100 within the hardware-supported adjustment range. The setting may be configured while the display is disabled. Invalid input is rejected without changing state.

        Args:
        - value:  (min=0, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - INVALID_INPUT_ERROR: Projection position must be an integer from 0 through 100.
        """
        code = self.projection_position.set(value)
        if code != '[PASS]':
            return (code, {})
        return (code, {})

    def get_supported_content(self) -> tuple[str, dict]:
        """
        Return the fixed supported-content capability profile. This reports the categories of externally supplied information the display can present and does not return or duplicate current speed, route, or navigation state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- supported_content: Fixed supported-content capability profile. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.supported_content.get()
        if code != '[PASS]':
            return (code, {})
        return (code, {'supported_content': value})