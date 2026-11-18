# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..Flashlight import Flashlight

class DimmableFlashlight(Flashlight):
    """
    DimmableFlashlight
    Description: Adds flashlight brightness-level control. Supported levels and the maximum level are read-only capabilities. Brightness can be adjusted only while the light is on and the resource is available. Out-of-range levels or unavailable resources cause rejection. Arbitrary percentages are not treated as natively supported brightness precision.
    Version: 1.0.0
    Base: Flashlight
    """

    def __init__(self, brightness_level: int = None, supported_levels: dict = None, maximum_level: int = None, **base_kwargs) -> None:
        # initialize base Flashlight class
        super().__init__(**base_kwargs)
        # define properties
        self.brightness_level = IntProperty(
            name='brightness_level',
            description='Currently selected native flashlight brightness level. This simulated device supports each whole level from 1 through 5, and the selection persists when the flashlight is turned off.',
            default=5,
            unit='level',
            minimum=1,
            maximum=5,
            step=1,
            step_origin=1
        )
        self.supported_levels = DictProperty(
            name='supported_levels',
            description='Read-only capability records for the native discrete brightness levels supported by this simulated flashlight, keyed by level ID.',
            default={'1': {'level': 1}, '2': {'level': 2}, '3': {'level': 3}, '4': {'level': 4}, '5': {'level': 5}},
            mode=2,
            schema={'type': 'object', 'additionalProperties': {'type': 'object', 'properties': {'level': {'type': 'integer', 'minimum': 1, 'maximum': 5}}, 'required': ['level'], 'additionalProperties': False}}
        )
        self.maximum_level = IntProperty(
            name='maximum_level',
            description='Read-only maximum native brightness level supported by this simulated flashlight.',
            default=5,
            mode=2,
            unit='level',
            minimum=5,
            maximum=5,
            step=1,
            step_origin=5
        )

        # initialize properties
        if brightness_level is not None: code = self.brightness_level.internal_set(brightness_level)
        if supported_levels is not None: code = self.supported_levels.internal_set(supported_levels)
        if maximum_level is not None: code = self.maximum_level.internal_set(maximum_level)

        # disable inherited properties
        self.brightness_percent.chmod(0)
        self._disabled = {
            'properties': ['brightness_percent'],
            'functions': ['get_brightness_percent'],
            'events': []
        }

    def get_brightness_level(self) -> tuple[str, dict]:
        """
        Return the currently selected native flashlight brightness level without changing it.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- brightness_level: The currently selected native brightness level from 1 through 5. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.brightness_level.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'brightness_level': value
        }
        return code, response

    def set_brightness_level(self, level: int) -> tuple[str, dict]:
        """
        Set the flashlight to a supported native brightness level from 1 through 5. Adjustment is allowed only while the flashlight is actually on and the resource remains available and authorized. Unsupported or out-of-range levels and failed preconditions are rejected before any state change; arbitrary percentages are not accepted.

        Args:
        - level:  (choices=[1, 2, 3, 4, 5])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: Brightness can be adjusted only while the flashlight is on and its resource is available and authorized.
        - INVALID_ARGUMENT: The requested level is not one of the supported native brightness levels 1 through 5.
        """
        if type(level) is not int:
            return '[INVALID_ARGUMENT]', {}

        code, supported_levels = self.supported_levels.get()
        if code != '[PASS]':
            return code, {}
        level_id = str(level)
        if level_id not in supported_levels:
            return '[INVALID_ARGUMENT]', {}
        if supported_levels[level_id]['level'] != level:
            return '[INVALID_ARGUMENT]', {}

        code, light_on = self.light_on.get()
        if code != '[PASS]':
            return code, {}
        code, available = self.available.get()
        if code != '[PASS]':
            return code, {}
        code, authorized = self.authorized.get()
        if code != '[PASS]':
            return code, {}
        if not light_on or not available or not authorized:
            return '[PRECONDITION_FAILED]', {}

        code = self.brightness_level.set(level)
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {}

    def get_supported_levels(self) -> tuple[str, dict]:
        """
        Return the read-only dictionary of native discrete brightness levels supported by this simulated flashlight.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- supported_levels: Read-only capability records keyed by supported brightness-level ID. (type=object)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.supported_levels.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'supported_levels': {
                key: dict(record) for key, record in value.items()
            }
        }
        return code, response

    def get_maximum_level(self) -> tuple[str, dict]:
        """
        Return the read-only maximum native brightness level supported by this simulated flashlight.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- maximum_level: The maximum supported native brightness level. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.maximum_level.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'maximum_level': value
        }
        return code, response

    def turn_on(self) -> tuple[str, dict]:
        """
        Turn on the flashlight at its currently selected native brightness level. The operation succeeds only when the light resource is available and system authorization is granted. A failed precondition leaves the actual light state unchanged and is not reported as successful.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The flashlight resource is unavailable or system authorization is not granted.
        """
        code, available = self.available.get()
        if code != '[PASS]':
            return code, {}
        code, authorized = self.authorized.get()
        if code != '[PASS]':
            return code, {}
        if not available or not authorized:
            return '[PRECONDITION_FAILED]', {}

        code = self.light_on.internal_set(True)
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {}

    def get_brightness_percent(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'get_brightness_percent' is disabled in DimmableFlashlight.", {}