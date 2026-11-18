# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Monitor:
    """
    Monitor
    Description: Display device. Users can query and set display power, input source, volume, mute, picture mode, and brightness. When the display device is on, it presents content from the current input source; switching the input source changes the displayed content.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, input_source: str = None, volume: int = None, mute: bool = None, picture_mode: str = None, brightness: int = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the display device is powered on.',
            default=False
        )
        self.input_source = StringProperty(
            name='input_source',
            description='The currently selected display input source.',
            default='hdmi_1',
            choices=['hdmi_1', 'hdmi_2', 'displayport', 'usb_c']
        )
        self.volume = IntProperty(
            name='volume',
            description='The display device volume level.',
            default=50,
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.mute = BoolProperty(
            name='mute',
            description='Whether audio output from the display device is muted.',
            default=False
        )
        self.picture_mode = StringProperty(
            name='picture_mode',
            description='The active picture preset.',
            default='standard',
            choices=['standard', 'cinema', 'game', 'vivid']
        )
        self.brightness = IntProperty(
            name='brightness',
            description='The display brightness level.',
            default=50,
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if input_source is not None: code = self.input_source.internal_set(input_source)
        if volume is not None: code = self.volume.internal_set(volume)
        if mute is not None: code = self.mute.internal_set(mute)
        if picture_mode is not None: code = self.picture_mode.internal_set(picture_mode)
        if brightness is not None: code = self.brightness.internal_set(brightness)
        self._power_managed_properties = (self.input_source, self.volume, self.mute, self.picture_mode, self.brightness,)
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

    def get_input_source(self) -> tuple[str, dict]:
        """
        Return the currently selected input source. This function is available only while the display device is powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- input_source: The selected input source. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.input_source.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"input_source": value}

    def set_input_source(self, value: str) -> tuple[str, dict]:
        """
        Select the input source presented by the display. This changes displayed content selection without changing the external source's playback state. Available only while powered on.

        Args:
        - value: The input source to select. (choices=['hdmi_1', 'hdmi_2', 'displayport', 'usb_c'])

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
        if type(value) is not str or value not in ("hdmi_1", "hdmi_2", "displayport", "usb_c"):
            return "[INVALID_INPUT_ERROR]", {}
        code = self.input_source.set(value)
        return code, {}

    def get_volume(self) -> tuple[str, dict]:
        """
        Return the display device volume level. Available only while powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- volume: The volume level from 0 to 100. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.volume.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"volume": value}

    def set_volume(self, value: int) -> tuple[str, dict]:
        """
        Set the display device volume from 0 through 100. Available only while powered on.

        Args:
        - value: The desired volume level. (min=0, max=100)

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
        code = self.volume.set(value)
        return code, {}

    def get_mute(self) -> tuple[str, dict]:
        """
        Return whether display audio is muted. Available only while powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- mute: Whether audio is muted. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.mute.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"mute": value}

    def set_mute(self, value: bool) -> tuple[str, dict]:
        """
        Set whether display audio is muted. Available only while powered on.

        Args:
        - value: Whether to mute audio.

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
        if type(value) is not bool:
            return "[INVALID_INPUT_ERROR]", {}
        code = self.mute.set(value)
        return code, {}

    def get_picture_mode(self) -> tuple[str, dict]:
        """
        Return the active picture preset. Available only while powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- picture_mode: The active picture preset. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.picture_mode.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"picture_mode": value}

    def set_picture_mode(self, value: str) -> tuple[str, dict]:
        """
        Set the active picture preset. Available only while powered on.

        Args:
        - value: The picture preset to use. (choices=['standard', 'cinema', 'game', 'vivid'])

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
        if type(value) is not str or value not in ("standard", "cinema", "game", "vivid"):
            return "[INVALID_INPUT_ERROR]", {}
        code = self.picture_mode.set(value)
        return code, {}

    def get_brightness(self) -> tuple[str, dict]:
        """
        Return the display brightness level. Available only while powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- brightness: The brightness level from 0 to 100. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.brightness.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"brightness": value}

    def set_brightness(self, value: int) -> tuple[str, dict]:
        """
        Set the display brightness from 0 through 100. Available only while powered on.

        Args:
        - value: The desired brightness level. (min=0, max=100)

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
        code = self.brightness.set(value)
        return code, {}