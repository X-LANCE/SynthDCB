# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class MediaPlayer:
    """
    MediaPlayer
    Description: Media playback application, placed in Application. Supports selecting preset tracks, querying playback state, play, pause, stop, and setting repeat and shuffle. Pause preserves the track and configuration; stop changes only playback state. The virtual Space does not hold physical properties such as sound level.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, current_track: str = None, playback_state: str = None, repeat_mode: str = None, shuffle: bool = None) -> None:
        # define properties
        self.current_track = StringProperty(
            name='current_track',
            description='The currently selected preset local track.',
            default='morning',
            choices=['morning', 'news', 'music']
        )
        self.playback_state = StringProperty(
            name='playback_state',
            description='The current playback lifecycle state. It is changed internally by play, pause, and stop.',
            default='stopped',
            mode=2,
            choices=['stopped', 'playing', 'paused']
        )
        self.repeat_mode = StringProperty(
            name='repeat_mode',
            description='The repeat policy applied to local media playback.',
            default='none',
            choices=['none', 'one', 'all']
        )
        self.shuffle = BoolProperty(
            name='shuffle',
            description='Whether shuffle is enabled for local track ordering.',
            default=False
        )

        # initialize properties
        if current_track is not None: code = self.current_track.internal_set(current_track)
        if playback_state is not None: code = self.playback_state.internal_set(playback_state)
        if repeat_mode is not None: code = self.repeat_mode.internal_set(repeat_mode)
        if shuffle is not None: code = self.shuffle.internal_set(shuffle)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_current_track(self) -> tuple[str, dict]:
        """
        Return the currently selected preset track without changing playback or configuration.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- current_track: The currently selected preset track. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.current_track.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'current_track': value
        }
        return (code, response)

    def set_current_track(self, value: str) -> tuple[str, dict]:
        """
        Select one of the preset tracks: morning, news, or music. Selection does not change playback state, repeat mode, or shuffle. Invalid values are rejected and leave all state unchanged.

        Args:
        - value:  (choices=['morning', 'news', 'music'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.current_track.set(value)
        if code != '[PASS]':
            return (code, {})
        response = {}
        return (code, response)

    def get_playback_state(self) -> tuple[str, dict]:
        """
        Return the current playback state without changing application state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- playback_state: The current playback state: stopped, playing, or paused. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.playback_state.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'playback_state': value
        }
        return (code, response)

    def get_repeat_mode(self) -> tuple[str, dict]:
        """
        Return the current repeat mode without changing playback or configuration.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- repeat_mode: The current repeat mode: none, one, or all. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.repeat_mode.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'repeat_mode': value
        }
        return (code, response)

    def set_repeat_mode(self, value: str) -> tuple[str, dict]:
        """
        Set repeat mode to none, one, or all without changing the selected track, playback state, or shuffle. Invalid values are rejected and leave all state unchanged.

        Args:
        - value:  (choices=['none', 'one', 'all'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.repeat_mode.set(value)
        if code != '[PASS]':
            return (code, {})
        response = {}
        return (code, response)

    def get_shuffle(self) -> tuple[str, dict]:
        """
        Return whether shuffle is enabled without changing playback or configuration.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- shuffle: Whether shuffle is currently enabled. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.shuffle.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'shuffle': value
        }
        return (code, response)

    def set_shuffle(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable shuffle without changing the selected track, playback state, or repeat mode.

        Args:
        - value:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.shuffle.set(value)
        if code != '[PASS]':
            return (code, {})
        response = {}
        return (code, response)

    def play(self) -> tuple[str, dict]:
        """
        Start or resume playback of the selected track by changing playback_state to playing. This action is valid only while stopped or paused. If already playing, it fails and leaves all state unchanged.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: Playback is already playing.
        """
        code, state = self.playback_state.get()
        if code != '[PASS]':
            return (code, {})
        if state == 'playing':
            return ('[PRECONDITION_FAILED]', {})
        code = self.playback_state.internal_set('playing')
        if code != '[PASS]':
            return (code, {})
        response = {}
        return (code, response)

    def pause(self) -> tuple[str, dict]:
        """
        Pause active playback by changing playback_state to paused. The selected track, repeat mode, and shuffle setting are preserved. This action fails without changing state unless playback is currently playing.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: Playback is not currently playing.
        """
        code, state = self.playback_state.get()
        if code != '[PASS]':
            return (code, {})
        if state != 'playing':
            return ('[PRECONDITION_FAILED]', {})
        code = self.playback_state.internal_set('paused')
        if code != '[PASS]':
            return (code, {})
        response = {}
        return (code, response)

    def stop(self) -> tuple[str, dict]:
        """
        Stop playback by changing only playback_state to stopped. The selected track, repeat mode, and shuffle setting are preserved. The action is idempotent when playback is already stopped.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.playback_state.internal_set('stopped')
        if code != '[PASS]':
            return (code, {})
        response = {}
        return (code, response)