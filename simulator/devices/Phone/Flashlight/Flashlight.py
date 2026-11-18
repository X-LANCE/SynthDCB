# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Flashlight:
    """
    Flashlight
    Description: Flashlight control, placed in Setting and contained by System. Supports turning the light on and off and querying actual light state and current availability. The base class provides fixed brightness. Activation requires an available light resource and system authorization. When camera use or system resource restrictions make it unavailable, activation must not be reported as successful. If the resource is revoked during operation, the actual light turns off. Stores only light controls and feedback, without changing virtual Space illuminance.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, light_on: bool = None, available: bool = None, authorized: bool = None, brightness_percent: int = None) -> None:
        # define properties
        self.light_on = BoolProperty(
            name='light_on',
            description='Whether the flashlight is actually emitting light. This becomes false if availability or authorization is revoked.',
            default=False,
            mode=2
        )
        self.available = BoolProperty(
            name='available',
            description='Whether the flashlight hardware resource is currently available. Camera use or system resource restrictions can make it unavailable.',
            default=True,
            mode=2
        )
        self.authorized = BoolProperty(
            name='authorized',
            description='Whether the system currently authorizes use of the flashlight resource.',
            default=True,
            mode=2
        )
        self.brightness_percent = IntProperty(
            name='brightness_percent',
            description='Fixed flashlight brightness provided by this base class. The value is read-only and cannot be adjusted.',
            default=100,
            mode=2,
            unit='percent',
            minimum=100,
            maximum=100,
            step=1,
            step_origin=100
        )

        # initialize properties
        if light_on is not None: code = self.light_on.internal_set(light_on)
        if available is not None: code = self.available.internal_set(available)
        if authorized is not None: code = self.authorized.internal_set(authorized)
        if brightness_percent is not None: code = self.brightness_percent.internal_set(brightness_percent)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_light_on(self) -> tuple[str, dict]:
        """
        Return whether the flashlight is actually emitting light without changing its state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- light_on: Whether the flashlight is actually emitting light. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.light_on.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'light_on': value
        }
        return code, response

    def get_available(self) -> tuple[str, dict]:
        """
        Return whether the flashlight hardware resource is currently available.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- available: Whether the flashlight hardware resource is currently available. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.available.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'available': value
        }
        return code, response

    def get_authorized(self) -> tuple[str, dict]:
        """
        Return whether the system currently authorizes flashlight use.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- authorized: Whether system authorization for flashlight use is currently granted. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.authorized.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'authorized': value
        }
        return code, response

    def get_brightness_percent(self) -> tuple[str, dict]:
        """
        Return the fixed flashlight brightness percentage. This base class does not support brightness adjustment.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- brightness_percent: The fixed flashlight brightness percentage. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.brightness_percent.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'brightness_percent': value
        }
        return code, response

    def turn_on(self) -> tuple[str, dict]:
        """
        Turn on the flashlight at its fixed brightness. The operation succeeds only when the light resource is available and system authorization is granted. A failed precondition leaves the actual light state unchanged and is not reported as successful.

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

    def turn_off(self) -> tuple[str, dict]:
        """
        Turn off the flashlight by setting its actual light state to false. The operation is idempotent when the light is already off and does not require the resource to remain available.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.light_on.internal_set(False)
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {}

    def _on_dependency_changed(self, context: dict) -> tuple[str, list[dict]]:
        """
        When camera use, system resource restrictions, or system authorization changes, recomputes the corresponding availability and authorization feedback. If either prerequisite is revoked while the flashlight is on, the actual light turns off. Restoring a prerequisite does not automatically turn the light back on.

    Effect properties:
    - available: Current hardware resource availability determined by camera and system resource conditions.
    - authorized: Current system authorization for flashlight use.
    - light_on: Actual light state, which is cleared when availability or authorization is revoked.
        """
        code, current_available = self.available.get()
        if code != '[PASS]':
            return code, []
        code, current_authorized = self.authorized.get()
        if code != '[PASS]':
            return code, []

        availability_present = False
        authorization_present = False
        computed_available = True
        computed_authorized = True

        for properties in context['dependencies'].values():
            if 'available' in properties:
                availability_present = True
                computed_available = computed_available and properties['available']
            if 'resource_available' in properties:
                availability_present = True
                computed_available = computed_available and properties['resource_available']
            if 'flashlight_available' in properties:
                availability_present = True
                computed_available = computed_available and properties['flashlight_available']
            if 'camera_in_use' in properties:
                availability_present = True
                computed_available = computed_available and not properties['camera_in_use']
            if 'resource_restricted' in properties:
                availability_present = True
                computed_available = computed_available and not properties['resource_restricted']
            if 'flashlight_resource_restricted' in properties:
                availability_present = True
                computed_available = computed_available and not properties['flashlight_resource_restricted']

            if 'authorized' in properties:
                authorization_present = True
                computed_authorized = computed_authorized and properties['authorized']
            if 'flashlight_authorized' in properties:
                authorization_present = True
                computed_authorized = computed_authorized and properties['flashlight_authorized']

        new_available = computed_available if availability_present else current_available
        new_authorized = computed_authorized if authorization_present else current_authorized

        code = self.available.internal_set(new_available)
        if code != '[PASS]':
            return code, []
        code = self.authorized.internal_set(new_authorized)
        if code != '[PASS]':
            return code, []
        if not new_available or not new_authorized:
            code = self.light_on.internal_set(False)
            if code != '[PASS]':
                return code, []

        return '[PASS]', []