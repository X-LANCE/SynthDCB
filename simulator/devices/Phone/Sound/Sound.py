# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty


class Sound:
    """
    Sound
    Description: Sound settings, placed in Setting and contained by System. Supports separate media, ringtone, notification, and alarm volumes, switching among normal, vibrate, and silent modes, setting incoming-call vibration preferences, and selecting ringtones and notification sounds from local synthetic resources. Volumes are represented uniformly as 0–100%, with native-level mappings declared. Fixed platform rules linking volume streams must be explicit; all streams cannot be treated as one master volume. Supports querying the current audio output route and selecting among connected, available outputs. Bluetooth device connections are owned by Bluetooth. Focus affects interruption permission only and does not overwrite stored volumes. The virtual Space does not hold physical sound properties.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, media_volume: int = None, ringtone_volume: int = None, notification_volume: int = None, alarm_volume: int = None, ringer_mode: str = None, incoming_call_vibration: str = None, ringtone: str = None, notification_sound: str = None, available_outputs: dict = None, output_route: str = None) -> None:
        # define properties
        self.media_volume = IntProperty(
            name='media_volume',
            description='Independent media-stream volume from 0 through 100 percent. It maps to synthetic native levels 0 through 25 using floor((percentage * 25 + 50) / 100).',
            default=50,
            unit='percent',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.ringtone_volume = IntProperty(
            name='ringtone_volume',
            description='Independent ringtone-stream volume from 0 through 100 percent. It maps to synthetic native levels 0 through 7 using floor((percentage * 7 + 50) / 100). Changing it does not change notification volume.',
            default=70,
            unit='percent',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.notification_volume = IntProperty(
            name='notification_volume',
            description='Independent notification-stream volume from 0 through 100 percent. It maps to synthetic native levels 0 through 7 using floor((percentage * 7 + 50) / 100). Changing it does not change ringtone volume.',
            default=70,
            unit='percent',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.alarm_volume = IntProperty(
            name='alarm_volume',
            description='Independent alarm-stream volume from 0 through 100 percent. It maps to synthetic native levels 0 through 15 using floor((percentage * 15 + 50) / 100).',
            default=80,
            unit='percent',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.ringer_mode = StringProperty(
            name='ringer_mode',
            description='Current incoming-call audible-alert policy. Normal permits the configured ringtone, vibrate suppresses the ringtone in favor of vibration when allowed by the vibration preference, and silent suppresses ringtone and incoming-call vibration. Changing mode preserves every stored stream volume.',
            default='normal',
            choices=['normal', 'vibrate', 'silent']
        )
        self.incoming_call_vibration = StringProperty(
            name='incoming_call_vibration',
            description='Incoming-call vibration preference. Never disables call vibration; vibrate_mode permits it only in vibrate ringer mode; always permits it in normal and vibrate modes. Silent mode still suppresses incoming-call vibration. This preference does not change ringer mode or volumes.',
            default='vibrate_mode',
            choices=['never', 'vibrate_mode', 'always']
        )
        self.ringtone = StringProperty(
            name='ringtone',
            description='Selected local synthetic ringtone resource. None represents no ringtone resource and does not alter ringtone volume.',
            default='classic_ring',
            choices=['classic_ring', 'digital_ring', 'gentle_ring', 'none']
        )
        self.notification_sound = StringProperty(
            name='notification_sound',
            description='Selected local synthetic notification-sound resource. None represents no notification sound and does not alter notification volume.',
            default='chime',
            choices=['chime', 'pop', 'soft_bell', 'none']
        )
        self.available_outputs = DictProperty(
            name='available_outputs',
            description='Read-only collection of currently connected and available audio outputs keyed by route ID. Each record has label and kind fields. The deterministic standalone model contains the always-available built-in speaker and earpiece. Sound does not create Bluetooth connections.',
            default={
                'speaker': {
                    'label': 'Built-in speaker',
                    'kind': 'speaker'
                },
                'earpiece': {
                    'label': 'Built-in earpiece',
                    'kind': 'earpiece'
                }
            },
            mode=2
        )
        self.output_route = StringProperty(
            name='output_route',
            description='ID of the currently selected connected, available audio output.',
            default='speaker',
            mode=2,
            pattern='^[A-Za-z0-9_-]+$',
            max_length=128
        )

        # initialize properties
        if media_volume is not None:
            code = self.media_volume.internal_set(media_volume)
        if ringtone_volume is not None:
            code = self.ringtone_volume.internal_set(ringtone_volume)
        if notification_volume is not None:
            code = self.notification_volume.internal_set(notification_volume)
        if alarm_volume is not None:
            code = self.alarm_volume.internal_set(alarm_volume)
        if ringer_mode is not None:
            code = self.ringer_mode.internal_set(ringer_mode)
        if incoming_call_vibration is not None:
            code = self.incoming_call_vibration.internal_set(incoming_call_vibration)
        if ringtone is not None:
            code = self.ringtone.internal_set(ringtone)
        if notification_sound is not None:
            code = self.notification_sound.internal_set(notification_sound)
        if available_outputs is not None:
            code = self.available_outputs.internal_set(available_outputs)
        if output_route is not None:
            code = self.output_route.internal_set(output_route)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_media_volume(self) -> tuple[str, dict]:
        """
        Return the independent media volume percentage.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- media_volume: Current media volume percentage. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.media_volume.get()
        if code != '[PASS]':
            return (code, {})
        return (code, {'media_volume': value})

    def set_media_volume(self, value: int) -> tuple[str, dict]:
        """
        Set media volume to a whole percentage from 0 through 100. No other volume stream changes. Invalid values leave all state unchanged.

        Args:
        - value:  (min=0, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.media_volume.set(value)
        return (code, {})

    def get_ringtone_volume(self) -> tuple[str, dict]:
        """
        Return the independent ringtone volume percentage.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- ringtone_volume: Current ringtone volume percentage. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.ringtone_volume.get()
        if code != '[PASS]':
            return (code, {})
        return (code, {'ringtone_volume': value})

    def set_ringtone_volume(self, value: int) -> tuple[str, dict]:
        """
        Set ringtone volume to a whole percentage from 0 through 100. Notification, media, and alarm volumes remain unchanged. Invalid values leave all state unchanged.

        Args:
        - value:  (min=0, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.ringtone_volume.set(value)
        return (code, {})

    def get_notification_volume(self) -> tuple[str, dict]:
        """
        Return the independent notification volume percentage.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- notification_volume: Current notification volume percentage. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.notification_volume.get()
        if code != '[PASS]':
            return (code, {})
        return (code, {'notification_volume': value})

    def set_notification_volume(self, value: int) -> tuple[str, dict]:
        """
        Set notification volume to a whole percentage from 0 through 100. Ringtone, media, and alarm volumes remain unchanged. Invalid values leave all state unchanged.

        Args:
        - value:  (min=0, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.notification_volume.set(value)
        return (code, {})

    def get_alarm_volume(self) -> tuple[str, dict]:
        """
        Return the independent alarm volume percentage.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- alarm_volume: Current alarm volume percentage. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.alarm_volume.get()
        if code != '[PASS]':
            return (code, {})
        return (code, {'alarm_volume': value})

    def set_alarm_volume(self, value: int) -> tuple[str, dict]:
        """
        Set alarm volume to a whole percentage from 0 through 100. Media, ringtone, and notification volumes remain unchanged. Invalid values leave all state unchanged.

        Args:
        - value:  (min=0, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.alarm_volume.set(value)
        return (code, {})

    def get_ringer_mode(self) -> tuple[str, dict]:
        """
        Return the current ringer mode without changing stored stream volumes.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- ringer_mode: Current mode: normal, vibrate, or silent. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.ringer_mode.get()
        if code != '[PASS]':
            return (code, {})
        return (code, {'ringer_mode': value})

    def set_ringer_mode(self, value: str) -> tuple[str, dict]:
        """
        Set ringer mode to normal, vibrate, or silent. The operation preserves all stream volumes, sound selections, and the incoming-call vibration preference. Invalid modes leave state unchanged.

        Args:
        - value:  (choices=['normal', 'vibrate', 'silent'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.ringer_mode.set(value)
        return (code, {})

    def get_incoming_call_vibration(self) -> tuple[str, dict]:
        """
        Return the current incoming-call vibration preference.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- incoming_call_vibration: Current preference: never, vibrate_mode, or always. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.incoming_call_vibration.get()
        if code != '[PASS]':
            return (code, {})
        return (code, {'incoming_call_vibration': value})

    def set_incoming_call_vibration(self, value: str) -> tuple[str, dict]:
        """
        Set the incoming-call vibration preference to never, vibrate_mode, or always. This does not change ringer mode or any volume. Invalid values leave state unchanged.

        Args:
        - value:  (choices=['never', 'vibrate_mode', 'always'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.incoming_call_vibration.set(value)
        return (code, {})

    def get_ringtone(self) -> tuple[str, dict]:
        """
        Return the selected local synthetic ringtone resource.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- ringtone: Selected synthetic ringtone resource ID. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.ringtone.get()
        if code != '[PASS]':
            return (code, {})
        return (code, {'ringtone': value})

    def set_ringtone(self, value: str) -> tuple[str, dict]:
        """
        Select classic_ring, digital_ring, gentle_ring, or none as the local synthetic ringtone. The operation does not change ringtone volume or ringer mode. Invalid values leave state unchanged.

        Args:
        - value:  (choices=['classic_ring', 'digital_ring', 'gentle_ring', 'none'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.ringtone.set(value)
        return (code, {})

    def get_notification_sound(self) -> tuple[str, dict]:
        """
        Return the selected local synthetic notification-sound resource.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- notification_sound: Selected synthetic notification-sound resource ID. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.notification_sound.get()
        if code != '[PASS]':
            return (code, {})
        return (code, {'notification_sound': value})

    def set_notification_sound(self, value: str) -> tuple[str, dict]:
        """
        Select chime, pop, soft_bell, or none as the local synthetic notification sound. The operation does not change notification volume. Invalid values leave state unchanged.

        Args:
        - value:  (choices=['chime', 'pop', 'soft_bell', 'none'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.notification_sound.set(value)
        return (code, {})

    def get_available_output(self, output_id: str) -> tuple[str, dict]:
        """
        Return one currently connected, available audio-output record by route ID. Unknown or unavailable IDs are rejected without changing state.

        Args:
        - output_id:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- output: The available output record containing its label and kind. (type=object)

        Error Codes:
        - NOT_FOUND: The output ID is not currently connected and available.
        """
        if type(output_id) is not str:
            return ('[INVALID_ARGUMENT]', {})
        if len(output_id) == 0 or len(output_id) > 128:
            return ('[INVALID_ARGUMENT]', {})
        for character in output_id:
            if not (
                'A' <= character <= 'Z'
                or 'a' <= character <= 'z'
                or '0' <= character <= '9'
                or character == '_'
                or character == '-'
            ):
                return ('[INVALID_ARGUMENT]', {})

        code, outputs = self.available_outputs.get()
        if code != '[PASS]':
            return (code, {})
        if output_id not in outputs:
            return ('[NOT_FOUND]', {})

        record = outputs[output_id]
        if type(record) is not dict:
            return ('[NOT_FOUND]', {})
        return ('[PASS]', {'output': dict(record)})

    def get_output_route(self) -> tuple[str, dict]:
        """
        Return the ID of the currently selected audio output route.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- output_route: Currently selected connected, available output ID. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.output_route.get()
        if code != '[PASS]':
            return (code, {})
        return (code, {'output_route': value})

    def select_output_route(self, output_id: str) -> tuple[str, dict]:
        """
        Select an output route that is present in available_outputs. This resolves routing immediately but does not connect or disconnect any Bluetooth or other external device. Unknown or unavailable IDs leave the current route unchanged.

        Args:
        - output_id:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - NOT_FOUND: The output ID is not currently connected and available.
        """
        code, outputs = self.available_outputs.get()
        if code != '[PASS]':
            return (code, {})
        if type(output_id) is not str or output_id not in outputs:
            return ('[NOT_FOUND]', {})
        code = self.output_route.internal_set(output_id)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})