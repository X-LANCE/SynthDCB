# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..Monitor import Monitor

class Projector(Monitor):
    """
    Projector
    Description: A projector variant. It adds projection focus, keystone correction, and projected-image size controls to the base display capabilities. Focus and keystone correction affect only the clarity and geometry of the projected image.
    Version: 1.0.0
    Base: Monitor
    """

    def __init__(self, focus: int = None, keystone: int = None, image_size: int = None, *, power: bool | None = None, _defer_power_init: bool = False, **base_kwargs) -> None:
        _power_init_value = power if power is not None else False
        # initialize base Monitor class
        super().__init__(power=_power_init_value, _defer_power_init=True, **base_kwargs)
        # define properties
        self.focus = IntProperty(
            name='focus',
            description='Manual focus position on a normalized scale from 0 to 100. Higher values move focus toward the far end of its adjustment range, not necessarily toward greater clarity. Changes affect only projected-image clarity.',
            default=50,
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.keystone = IntProperty(
            name='keystone',
            description='Signed vertical keystone correction angle in degrees. Zero applies no correction; positive values narrow the top of the projected image and negative values narrow the bottom. Changes affect only projected-image geometry.',
            default=0,
            unit='degrees',
            minimum=-40,
            maximum=40,
            step=1,
            step_origin=0
        )
        self.image_size = IntProperty(
            name='image_size',
            description='Projected-image diagonal size in inches. Adjusting this setting changes only the projected-image dimensions without changing focus, keystone, or inherited display settings.',
            default=100,
            unit='inches',
            minimum=30,
            maximum=300,
            step=1,
            step_origin=0
        )

        # initialize properties
        if focus is not None: code = self.focus.internal_set(focus)
        if keystone is not None: code = self.keystone.internal_set(keystone)
        if image_size is not None: code = self.image_size.internal_set(image_size)
        self._power_managed_properties = (self.input_source, self.volume, self.mute, self.picture_mode, self.brightness, self.focus, self.keystone, self.image_size,)
        self._power_initialized = False
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

        if not _defer_power_init:
            self.set_power(_power_init_value)

    def get_focus(self) -> tuple[str, dict]:
        """
        Return the manual focus position under focus. Available only while powered on; otherwise fail without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- focus: The manual focus position from 0 through 100. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.focus.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"focus": value}

    def set_focus(self, value: int) -> tuple[str, dict]:
        """
        Set the manual focus position to an integer from 0 through 100 inclusive. This affects only projected-image clarity and does not automatically find optimal focus. Available only while powered on. Invalid arguments or a failed power precondition leave all state unchanged. Success returns no data fields.

        Args:
        - value: Desired manual focus position. (min=0, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        if type(value) is not int or isinstance(value, bool) or value < 0 or value > 100:
            return "[INVALID_INPUT_ERROR]", {}
        code = self.focus.set(value)
        return code, {}

    def get_keystone(self) -> tuple[str, dict]:
        """
        Return the signed vertical keystone correction angle in degrees under keystone. Available only while powered on; otherwise fail without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- keystone: Vertical keystone correction from -40 through 40 degrees. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.keystone.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"keystone": value}

    def set_keystone(self, value: int) -> tuple[str, dict]:
        """
        Set vertical keystone correction to an integer from -40 through 40 degrees inclusive. Zero removes correction; positive values narrow the image top and negative values narrow the bottom. This affects only projected-image geometry. Available only while powered on. Invalid arguments or a failed power precondition leave all state unchanged. Success returns no data fields.

        Args:
        - value: Desired signed vertical keystone correction in degrees. (min=-40, max=40)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        if type(value) is not int or isinstance(value, bool) or value < -40 or value > 40:
            return "[INVALID_INPUT_ERROR]", {}
        code = self.keystone.set(value)
        return code, {}

    def get_image_size(self) -> tuple[str, dict]:
        """
        Return the projected-image diagonal in inches under image_size. Available only while powered on; otherwise fail without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- image_size: The projected-image diagonal from 30 through 300 inches. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.image_size.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"image_size": value}

    def set_image_size(self, value: int) -> tuple[str, dict]:
        """
        Set the projected-image diagonal to an integer from 30 through 300 inches inclusive, changing only image dimensions. Available only while powered on. Invalid arguments or a failed power precondition leave all state unchanged. Success returns no data fields.

        Args:
        - value: Desired projected-image diagonal in inches. (min=30, max=300)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        if type(value) is not int or isinstance(value, bool) or value < 30 or value > 300:
            return "[INVALID_INPUT_ERROR]", {}
        code = self.image_size.set(value)
        return code, {}