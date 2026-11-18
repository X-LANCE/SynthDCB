# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class ParkingCamera:
    """
    ParkingCamera
    Description: Parking camera module. Supports turning the image display on or off, selecting views provided by installed cameras, and querying image availability. Camera count and selectable views are fixed capabilities.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, display_active: bool = None, selected_view: str = None, camera_count: int = None, available_views: dict = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the parking camera module is powered on.',
            default=False
        )
        self.display_active = BoolProperty(
            name='display_active',
            description='Whether the image for the selected parking-camera view is currently displayed. As an auto-reset property, this resets to false when device power is turned on.',
            default=False,
            auto_reset=True
        )
        self.selected_view = StringProperty(
            name='selected_view',
            description='Identifier of the selected view from the fixed available_views collection.',
            default='rear',
            pattern='^[A-Za-z0-9_-]{1,32}$',
            max_length=32
        )
        self.camera_count = IntProperty(
            name='camera_count',
            description='Fixed number of installed physical cameras belonging to this parking-camera module. Composite views do not necessarily correspond one-to-one with physical cameras.',
            default=1,
            mode=2,
            minimum=1,
            maximum=12,
            step=1,
            step_origin=1
        )
        self.available_views = DictProperty(
            name='available_views',
            description='Read-only collection of fixed selectable views keyed by view identifier. Each record contains a display name and reports whether an image for that view is currently available.',
            default={'rear': {'display_name': 'Rear', 'image_available': True}},
            mode=2,
            schema={'type': 'object', 'minProperties': 1, 'propertyNames': {'pattern': '^[A-Za-z0-9_-]{1,32}$'}, 'additionalProperties': {'type': 'object', 'properties': {'display_name': {'type': 'string', 'minLength': 1, 'maxLength': 64}, 'image_available': {'type': 'boolean'}}, 'required': ['display_name', 'image_available'], 'additionalProperties': False}}
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if display_active is not None: code = self.display_active.internal_set(display_active)
        if selected_view is not None: code = self.selected_view.internal_set(selected_view)
        if camera_count is not None: code = self.camera_count.internal_set(camera_count)
        if available_views is not None: code = self.available_views.internal_set(available_views)
        self._power_managed_properties = (self.display_active, self.selected_view, self.camera_count, self.available_views,)
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

    def get_display_active(self) -> tuple[str, dict]:
        """
        Return whether a parking-camera image is currently displayed without changing state. The module must be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- display_active: Whether the selected parking-camera view is currently displayed. (type=boolean)

        Error Codes:
        - PRECONDITION_FAILED: The parking camera module must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[PRECONDITION_FAILED]", {}

        code, value = self.display_active.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"display_active": value}

    def set_display_active(self, value: bool) -> tuple[str, dict]:
        """
        Turn the parking-camera image display on or off while the module is powered on. Turning the display off always succeeds while powered. Turning it on succeeds only when the selected view exists and its image_available field is true; otherwise the request is rejected and state remains unchanged.

        Args:
        - value:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The parking camera module must be powered on.
        - IMAGE_UNAVAILABLE: The display cannot be activated because the selected view has no available image.
        """
        if type(value) is not bool:
            return "[INVALID_INPUT_ERROR]", {}

        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[PRECONDITION_FAILED]", {}

        if value:
            selected_code, selected = self.selected_view.get()
            if selected_code != "[PASS]":
                return selected_code, {}

            views_code, views = self.available_views.get()
            if views_code != "[PASS]":
                return views_code, {}

            if selected not in views:
                return "[IMAGE_UNAVAILABLE]", {}
            if views[selected]["image_available"] is not True:
                return "[IMAGE_UNAVAILABLE]", {}

        code = self.display_active.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_selected_view(self) -> tuple[str, dict]:
        """
        Return the identifier of the currently selected parking-camera view without changing state. The module must be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- selected_view: Identifier of the selected fixed view. (type=string)

        Error Codes:
        - PRECONDITION_FAILED: The parking camera module must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[PRECONDITION_FAILED]", {}

        code, value = self.selected_view.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"selected_view": value}

    def set_selected_view(self, view_id: str) -> tuple[str, dict]:
        """
        Select a view from the fixed available_views collection while the module is powered on. An unknown view is rejected. An unavailable view may be selected while the image display is inactive, but switching an active display to an unavailable view is rejected. Rejected requests leave all state unchanged.

        Args:
        - view_id:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The parking camera module must be powered on and the requested view must be provided by this module.
        - IMAGE_UNAVAILABLE: An unavailable view cannot be selected while the image display is active.
        """
        if type(view_id) is not str:
            return "[INVALID_INPUT_ERROR]", {}
        if len(view_id) < 1 or len(view_id) > 32:
            return "[INVALID_INPUT_ERROR]", {}
        for character in view_id:
            if not (
                "A" <= character <= "Z"
                or "a" <= character <= "z"
                or "0" <= character <= "9"
                or character == "_"
                or character == "-"
            ):
                return "[INVALID_INPUT_ERROR]", {}

        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[PRECONDITION_FAILED]", {}

        views_code, views = self.available_views.get()
        if views_code != "[PASS]":
            return views_code, {}
        if view_id not in views:
            return "[PRECONDITION_FAILED]", {}

        display_code, display_active = self.display_active.get()
        if display_code != "[PASS]":
            return display_code, {}
        if display_active and views[view_id]["image_available"] is not True:
            return "[IMAGE_UNAVAILABLE]", {}

        code = self.selected_view.set(view_id)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_camera_count(self) -> tuple[str, dict]:
        """
        Return the fixed number of installed physical cameras assigned to this module without changing state. The module must be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- camera_count: Number of installed physical parking cameras. (type=integer)

        Error Codes:
        - PRECONDITION_FAILED: The parking camera module must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[PRECONDITION_FAILED]", {}

        code, value = self.camera_count.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"camera_count": value}

    def get_available_view(self, view_id: str) -> tuple[str, dict]:
        """
        Return the fixed display name and current image availability for one selectable view while the module is powered on. An unknown view identifier is rejected without changing state.

        Args:
        - view_id:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- view: View record containing display_name and image_available fields. (type=object)

        Error Codes:
        - PRECONDITION_FAILED: The parking camera module must be powered on and the requested view must be provided by this module.
        """
        if type(view_id) is not str:
            return "[INVALID_INPUT_ERROR]", {}
        if len(view_id) < 1 or len(view_id) > 32:
            return "[INVALID_INPUT_ERROR]", {}
        for character in view_id:
            if not (
                "A" <= character <= "Z"
                or "a" <= character <= "z"
                or "0" <= character <= "9"
                or character == "_"
                or character == "-"
            ):
                return "[INVALID_INPUT_ERROR]", {}

        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[PRECONDITION_FAILED]", {}

        code, views = self.available_views.get()
        if code != "[PASS]":
            return code, {}
        if view_id not in views:
            return "[PRECONDITION_FAILED]", {}

        view = {
            "display_name": views[view_id]["display_name"],
            "image_available": views[view_id]["image_available"]
        }
        return "[PASS]", {"view": view}