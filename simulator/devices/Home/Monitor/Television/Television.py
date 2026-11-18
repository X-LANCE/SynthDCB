# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..Monitor import Monitor

class Television(Monitor):
    """
    Television
    Description: A television variant. It adds channel selection, program playback, and casting states to the base display capabilities, and users can query and set the current channel or media content.
    Version: 1.0.0
    Base: Monitor
    """

    def __init__(self, channel: int = None, media_content: str = None, casting: bool = None, *, power: bool | None = None, _defer_power_init: bool = False, **base_kwargs) -> None:
        _power_init_value = power if power is not None else False
        # initialize base Monitor class
        super().__init__(power=_power_init_value, _defer_power_init=True, **base_kwargs)
        # define properties
        self.channel = IntProperty(
            name='channel',
            description='The currently selected television channel.',
            default=1,
            minimum=1,
            maximum=999,
            step=1,
            step_origin=1
        )
        self.media_content = StringProperty(
            name='media_content',
            description='The program or media content currently selected for playback.',
            default='',
            max_length=256
        )
        self.casting = BoolProperty(
            name='casting',
            description='Whether the television is currently displaying cast content.',
            default=False
        )

        # initialize properties
        if channel is not None: code = self.channel.internal_set(channel)
        if media_content is not None: code = self.media_content.internal_set(media_content)
        if casting is not None: code = self.casting.internal_set(casting)
        self._power_managed_properties = (self.input_source, self.volume, self.mute, self.picture_mode, self.brightness, self.channel, self.media_content, self.casting,)
        self._power_initialized = False
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

        if not _defer_power_init:
            self.set_power(_power_init_value)

    def get_channel(self) -> tuple[str, dict]:
        """
        Return the currently selected television channel. Available only while the television is powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- channel: The selected television channel. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.channel.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"channel": value}

    def set_channel(self, value: int) -> tuple[str, dict]:
        """
        Select a television channel from 1 through 999. Available only while the television is powered on.

        Args:
        - value: The television channel to select. (min=1, max=999)

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
        if type(value) is not int or isinstance(value, bool) or value < 1 or value > 999:
            return "[INVALID_INPUT_ERROR]", {}
        code = self.channel.set(value)
        return code, {}

    def get_media_content(self) -> tuple[str, dict]:
        """
        Return the program or media content currently selected for playback. Available only while the television is powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- media_content: The selected program or media content. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.media_content.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"media_content": value}

    def set_media_content(self, value: str) -> tuple[str, dict]:
        """
        Set the program or media content selected for playback. The value may be an empty string to clear the selection. Available only while the television is powered on.

        Args:
        - value: The program or media content to select.

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
        if type(value) is not str or len(value) > 256:
            return "[INVALID_INPUT_ERROR]", {}
        code = self.media_content.set(value)
        return code, {}

    def get_casting(self) -> tuple[str, dict]:
        """
        Return whether the television is currently displaying cast content. Available only while the television is powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- casting: Whether cast content is being displayed. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.casting.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"casting": value}

    def set_casting(self, value: bool) -> tuple[str, dict]:
        """
        Set whether the television is displaying cast content. Available only while the television is powered on.

        Args:
        - value: Whether cast content should be displayed.

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
        code = self.casting.set(value)
        return code, {}