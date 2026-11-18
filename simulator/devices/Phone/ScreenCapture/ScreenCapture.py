# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty


class ScreenCapture:
    """
    ScreenCapture
    Description: Screenshot and screen recording application, placed in Application and contained by System. Supports requesting simulated capture authorization, taking screenshots, starting and stopping screen recording, querying authorization and recording state, and querying or deleting screenshot and completed recording records by stable ID. Records contain only metadata such as type, time, and duration; no actual images or videos are generated. Authorization may be denied or revoked, and protected content or resource conflicts may block capture. Failures create no successful records, and repeated recording starts are rejected. Recording duration uses monotonic time. Normal stopping creates a completed record; authorization revocation or resource loss terminates recording with an explicitly marked interrupted result. Enabling microphone audio recording additionally requires Privacy authorization; screen capture authorization does not replace microphone permission.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, authorization_status: str = None, recording_state: str = None, microphone_audio_enabled: bool = None, microphone_access_granted: bool = None, capture_block_reason: str = None, captures: dict = None, recording_started_at_minute: int = None, next_capture_number: int = None) -> None:
        # define properties
        self.authorization_status = StringProperty(
            name='authorization_status',
            description='Current simulated screen capture authorization state. A granted state permits capture subject to the other interlocks. Explicit revocation interrupts an active recording.',
            default='not_requested',
            mode=2,
            choices=['not_requested', 'granted', 'denied', 'revoked']
        )
        self.recording_state = StringProperty(
            name='recording_state',
            description='Current screen recording lifecycle state. Both normal stopping and interruption return this state to idle; the resulting metadata record identifies the outcome.',
            default='idle',
            mode=2,
            choices=['idle', 'recording']
        )
        self.microphone_audio_enabled = BoolProperty(
            name='microphone_audio_enabled',
            description='Whether newly started screen recordings include simulated microphone-audio metadata. Enabling requires microphone_access_granted, and this setting cannot be changed during recording.',
            default=False
        )
        self.microphone_access_granted = BoolProperty(
            name='microphone_access_granted',
            description='Read-only microphone authorization derived exactly from the declared Privacy dependency property microphone_authorized: true maps to true and false maps to false. Screen capture authorization does not grant microphone access.',
            default=False,
            mode=2
        )
        self.capture_block_reason = StringProperty(
            name='capture_block_reason',
            description='Read-only current capture block reason derived from the declared system capture-condition dependency. protected_content_active=true maps to protected_content regardless of resource availability; otherwise capture_resource_available=false maps to resource_conflict; otherwise the value is none.',
            default='none',
            mode=2,
            choices=['none', 'protected_content', 'resource_conflict']
        )
        self.captures = DictProperty(
            name='captures',
            description='Metadata-only capture records keyed by stable IDs. A screenshot record has exactly type, capture_minute, duration_minutes, and result. A recording record has exactly type, start_minute, end_minute, duration_minutes, microphone_audio_included, result, and interruption_reason. Completed recordings use interruption_reason none; interrupted recordings use authorization_revoked, protected_content, resource_conflict, or microphone_authorization_revoked.',
            default={},
            mode=2,
            schema={
                'type': 'object',
                'propertyNames': {
                    'pattern': '^capture_[0-9]{6,}$',
                    'maxLength': 128
                },
                'additionalProperties': {
                    'oneOf': [
                        {
                            'type': 'object',
                            'properties': {
                                'type': {'const': 'screenshot'},
                                'capture_minute': {
                                    'type': 'integer',
                                    'minimum': 0
                                },
                                'duration_minutes': {'const': 0},
                                'result': {'const': 'completed'}
                            },
                            'required': [
                                'type',
                                'capture_minute',
                                'duration_minutes',
                                'result'
                            ],
                            'additionalProperties': False
                        },
                        {
                            'type': 'object',
                            'properties': {
                                'type': {'const': 'recording'},
                                'start_minute': {
                                    'type': 'integer',
                                    'minimum': 0
                                },
                                'end_minute': {
                                    'type': 'integer',
                                    'minimum': 0
                                },
                                'duration_minutes': {
                                    'type': 'integer',
                                    'minimum': 0
                                },
                                'microphone_audio_included': {
                                    'type': 'boolean'
                                },
                                'result': {'const': 'completed'},
                                'interruption_reason': {'const': 'none'}
                            },
                            'required': [
                                'type',
                                'start_minute',
                                'end_minute',
                                'duration_minutes',
                                'microphone_audio_included',
                                'result',
                                'interruption_reason'
                            ],
                            'additionalProperties': False
                        },
                        {
                            'type': 'object',
                            'properties': {
                                'type': {'const': 'recording'},
                                'start_minute': {
                                    'type': 'integer',
                                    'minimum': 0
                                },
                                'end_minute': {
                                    'type': 'integer',
                                    'minimum': 0
                                },
                                'duration_minutes': {
                                    'type': 'integer',
                                    'minimum': 0
                                },
                                'microphone_audio_included': {
                                    'type': 'boolean'
                                },
                                'result': {'const': 'interrupted'},
                                'interruption_reason': {
                                    'type': 'string',
                                    'enum': [
                                        'authorization_revoked',
                                        'protected_content',
                                        'resource_conflict',
                                        'microphone_authorization_revoked'
                                    ]
                                }
                            },
                            'required': [
                                'type',
                                'start_minute',
                                'end_minute',
                                'duration_minutes',
                                'microphone_audio_included',
                                'result',
                                'interruption_reason'
                            ],
                            'additionalProperties': False
                        }
                    ]
                }
            }
        )
        self.recording_started_at_minute = IntProperty(
            name='recording_started_at_minute',
            description='Internal monotonic elapsed simulation minute at which the active recording started, or zero when no recording is active.',
            default=0,
            mode=0,
            unit='minutes',
            minimum=0,
            step=1,
            step_origin=0
        )
        self.next_capture_number = IntProperty(
            name='next_capture_number',
            description='Internal monotonically increasing sequence number used to allocate stable capture IDs without reusing deleted IDs.',
            default=1,
            mode=0,
            minimum=1,
            step=1,
            step_origin=1
        )

        self._recording_started_at_minute_value = 0
        self._next_capture_number_value = 1

        # initialize properties
        if authorization_status is not None:
            code = self.authorization_status.internal_set(authorization_status)
        if recording_state is not None:
            code = self.recording_state.internal_set(recording_state)
        if microphone_audio_enabled is not None:
            code = self.microphone_audio_enabled.internal_set(
                microphone_audio_enabled
            )
        if microphone_access_granted is not None:
            code = self.microphone_access_granted.internal_set(
                microphone_access_granted
            )
        if capture_block_reason is not None:
            code = self.capture_block_reason.internal_set(capture_block_reason)
        if captures is not None:
            code = self.captures.internal_set(captures)
        if recording_started_at_minute is not None:
            code = self.recording_started_at_minute.internal_set(
                recording_started_at_minute
            )
            if code == '[PASS]':
                self._recording_started_at_minute_value = (
                    recording_started_at_minute
                )
        if next_capture_number is not None:
            code = self.next_capture_number.internal_set(next_capture_number)
            if code == '[PASS]':
                self._next_capture_number_value = next_capture_number
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_authorization_status(self) -> tuple[str, dict]:
        """
        Return the current simulated screen capture authorization status without changing it.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- authorization_status: Current authorization status: not_requested, granted, denied, or revoked. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.authorization_status.get()
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {'authorization_status': value}

    def request_capture_authorization(self, decision: str) -> tuple[str, dict]:
        """
        Resolve a simulated screen capture authorization request using an explicit granted or denied user decision. Requests are accepted only while recording is idle. A granted decision sets authorization_status to granted, and a denied decision sets it to denied. Invalid input or an active recording leaves all state unchanged.

        Args:
        - decision: Explicit simulated authorization decision. (choices=['granted', 'denied'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: Capture authorization cannot be requested while a screen recording is active.
        """
        if type(decision) is not str or decision not in ('granted', 'denied'):
            return '[INVALID_ARGUMENT]', {}

        code, recording_state = self.recording_state.get()
        if code != '[PASS]':
            return code, {}
        if recording_state != 'idle':
            return '[PRECONDITION_FAILED]', {}

        code = self.authorization_status.internal_set(decision)
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {}

    def revoke_capture_authorization(self) -> tuple[str, dict]:
        """
        Set authorization_status to revoked. If a recording is active, atomically terminate it, allocate one stable capture ID, and create an interrupted recording record with interruption_reason authorization_revoked. Its end_minute is the current monotonic elapsed simulation minute and duration_minutes is max(end_minute minus start_minute, 0). Revocation while idle creates no record. A successful interruption returns recording_state to idle and resets recording_started_at_minute to zero.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, recording_state = self.recording_state.get()
        if code != '[PASS]':
            return code, {}

        if recording_state == 'recording':
            start_minute = self._recording_started_at_minute_value
            next_number = self._next_capture_number_value

            code, microphone_audio = self.microphone_audio_enabled.get()
            if code != '[PASS]':
                return code, {}
            code, captures = self.captures.get()
            if code != '[PASS]':
                return code, {}

            end_minute = start_minute
            capture_id = 'capture_' + str(next_number).zfill(6)
            updated_captures = {
                key: dict(record)
                for key, record in captures.items()
            }
            updated_captures[capture_id] = {
                'type': 'recording',
                'start_minute': start_minute,
                'end_minute': end_minute,
                'duration_minutes': max(end_minute - start_minute, 0),
                'microphone_audio_included': microphone_audio,
                'result': 'interrupted',
                'interruption_reason': 'authorization_revoked'
            }

            code = self.captures.internal_set(updated_captures)
            if code != '[PASS]':
                return code, {}

            code = self.next_capture_number.internal_set(next_number + 1)
            if code != '[PASS]':
                return code, {}
            self._next_capture_number_value = next_number + 1

            code = self.recording_state.internal_set('idle')
            if code != '[PASS]':
                return code, {}

            code = self.recording_started_at_minute.internal_set(0)
            if code != '[PASS]':
                return code, {}
            self._recording_started_at_minute_value = 0

        code = self.authorization_status.internal_set('revoked')
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {}

    def get_recording_state(self) -> tuple[str, dict]:
        """
        Return whether screen recording is idle or currently recording.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- recording_state: Current recording state: idle or recording. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.recording_state.get()
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {'recording_state': value}

    def get_microphone_audio_enabled(self) -> tuple[str, dict]:
        """
        Return whether newly started screen recordings are configured to include simulated microphone audio.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- microphone_audio_enabled: Whether newly started recordings are configured to include microphone audio. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.microphone_audio_enabled.get()
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {'microphone_audio_enabled': value}

    def set_microphone_audio_enabled(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable microphone audio for newly started recordings. The setting can change only while recording is idle. Enabling additionally requires microphone_access_granted to be true; disabling does not require microphone authorization. A rejected call leaves the setting unchanged.

        Args:
        - value: Whether newly started recordings should include microphone audio.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The setting cannot change during recording, and enabling it requires microphone authorization from Privacy.
        """
        if type(value) is not bool:
            return '[INVALID_ARGUMENT]', {}

        code, recording_state = self.recording_state.get()
        if code != '[PASS]':
            return code, {}
        if recording_state != 'idle':
            return '[PRECONDITION_FAILED]', {}

        if value:
            code, microphone_access = self.microphone_access_granted.get()
            if code != '[PASS]':
                return code, {}
            if not microphone_access:
                return '[PRECONDITION_FAILED]', {}

        code = self.microphone_audio_enabled.set(value)
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {}

    def get_microphone_access_granted(self) -> tuple[str, dict]:
        """
        Return the microphone access state derived from the declared Privacy dependency property microphone_authorized.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- microphone_access_granted: Whether the declared Privacy dependency currently grants microphone access. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.microphone_access_granted.get()
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {'microphone_access_granted': value}

    def get_capture_block_reason(self) -> tuple[str, dict]:
        """
        Return the current capture block reason derived from protected-content and capture-resource conditions, or none when those conditions permit capture.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- capture_block_reason: Current capture block reason: none, protected_content, or resource_conflict. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.capture_block_reason.get()
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {'capture_block_reason': value}

    def get_captures(self) -> tuple[str, dict]:
        """
        Return all metadata-only screenshot and completed or interrupted recording records keyed by stable capture ID. This query does not create, delete, or modify records.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- captures: All stored metadata-only capture records keyed by stable capture ID. (type=object)

        Error Codes:
        (no specified error codes)
        """
        code, captures = self.captures.get()
        if code != '[PASS]':
            return code, {}
        copied = {
            capture_id: dict(record)
            for capture_id, record in captures.items()
        }
        return '[PASS]', {'captures': copied}

    def take_screenshot(self) -> tuple[str, dict]:
        """
        Create one metadata-only screenshot record. Authorization must be granted and capture_block_reason must be none. On success, allocate capture_NNNNNN from next_capture_number and store exactly type screenshot, capture_minute equal to the current monotonic elapsed simulation minute, duration_minutes 0, and result completed. Protected content, a resource conflict, or missing authorization creates no record and does not consume an ID.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- capture_id: Stable ID of the newly created screenshot metadata record. (type=string)

        Error Codes:
        - NOT_AUTHORIZED: Screen capture authorization is not granted.
        - PROTECTED_CONTENT: The current content is protected from capture.
        - RESOURCE_CONFLICT: A capture resource conflict currently blocks the screenshot.
        """
        code, authorization = self.authorization_status.get()
        if code != '[PASS]':
            return code, {}
        if authorization != 'granted':
            return '[NOT_AUTHORIZED]', {}

        code, block_reason = self.capture_block_reason.get()
        if code != '[PASS]':
            return code, {}
        if block_reason == 'protected_content':
            return '[PROTECTED_CONTENT]', {}
        if block_reason == 'resource_conflict':
            return '[RESOURCE_CONFLICT]', {}

        code, captures = self.captures.get()
        if code != '[PASS]':
            return code, {}

        next_number = self._next_capture_number_value
        capture_id = 'capture_' + str(next_number).zfill(6)
        updated_captures = {
            key: dict(record)
            for key, record in captures.items()
        }
        updated_captures[capture_id] = {
            'type': 'screenshot',
            'capture_minute': 0,
            'duration_minutes': 0,
            'result': 'completed'
        }

        code = self.captures.internal_set(updated_captures)
        if code != '[PASS]':
            return code, {}

        code = self.next_capture_number.internal_set(next_number + 1)
        if code != '[PASS]':
            return code, {}
        self._next_capture_number_value = next_number + 1

        return '[PASS]', {'capture_id': capture_id}

    def start_recording(self) -> tuple[str, dict]:
        """
        Start one screen recording and store the current monotonic elapsed simulation minute in recording_started_at_minute. Authorization must be granted, recording_state must be idle, and capture_block_reason must be none. If microphone audio is enabled, microphone_access_granted must also be true. Repeated starts and all other failed starts leave state unchanged and create no record.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - ALREADY_RECORDING: A screen recording is already active.
        - NOT_AUTHORIZED: Screen capture authorization is not granted.
        - MICROPHONE_NOT_AUTHORIZED: Microphone audio is enabled but Privacy has not granted microphone access.
        - PROTECTED_CONTENT: The current content is protected from capture.
        - RESOURCE_CONFLICT: A capture resource conflict currently blocks recording.
        """
        code, recording_state = self.recording_state.get()
        if code != '[PASS]':
            return code, {}
        if recording_state == 'recording':
            return '[ALREADY_RECORDING]', {}

        code, authorization = self.authorization_status.get()
        if code != '[PASS]':
            return code, {}
        if authorization != 'granted':
            return '[NOT_AUTHORIZED]', {}

        code, block_reason = self.capture_block_reason.get()
        if code != '[PASS]':
            return code, {}
        if block_reason == 'protected_content':
            return '[PROTECTED_CONTENT]', {}
        if block_reason == 'resource_conflict':
            return '[RESOURCE_CONFLICT]', {}

        code, microphone_enabled = self.microphone_audio_enabled.get()
        if code != '[PASS]':
            return code, {}
        if microphone_enabled:
            code, microphone_access = self.microphone_access_granted.get()
            if code != '[PASS]':
                return code, {}
            if not microphone_access:
                return '[MICROPHONE_NOT_AUTHORIZED]', {}

        code = self.recording_started_at_minute.internal_set(0)
        if code != '[PASS]':
            return code, {}
        self._recording_started_at_minute_value = 0

        code = self.recording_state.internal_set('recording')
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {}

    def stop_recording(self) -> tuple[str, dict]:
        """
        Normally stop the active screen recording. On success, allocate one stable capture ID and create a recording record with type recording, the stored start_minute, end_minute equal to the current monotonic elapsed simulation minute, duration_minutes equal to max(end_minute minus start_minute, 0), microphone_audio_included equal to the frozen microphone_audio_enabled setting, result completed, and interruption_reason none. Then set recording_state to idle and recording_started_at_minute to zero. A call while idle is rejected and creates no record.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- capture_id: Stable ID of the newly created completed recording metadata record. (type=string)

        Error Codes:
        - NOT_RECORDING: No screen recording is active.
        """
        code, recording_state = self.recording_state.get()
        if code != '[PASS]':
            return code, {}
        if recording_state != 'recording':
            return '[NOT_RECORDING]', {}

        start_minute = self._recording_started_at_minute_value
        next_number = self._next_capture_number_value

        code, microphone_audio = self.microphone_audio_enabled.get()
        if code != '[PASS]':
            return code, {}
        code, captures = self.captures.get()
        if code != '[PASS]':
            return code, {}

        end_minute = start_minute
        capture_id = 'capture_' + str(next_number).zfill(6)
        updated_captures = {
            key: dict(record)
            for key, record in captures.items()
        }
        updated_captures[capture_id] = {
            'type': 'recording',
            'start_minute': start_minute,
            'end_minute': end_minute,
            'duration_minutes': max(end_minute - start_minute, 0),
            'microphone_audio_included': microphone_audio,
            'result': 'completed',
            'interruption_reason': 'none'
        }

        code = self.captures.internal_set(updated_captures)
        if code != '[PASS]':
            return code, {}

        code = self.next_capture_number.internal_set(next_number + 1)
        if code != '[PASS]':
            return code, {}
        self._next_capture_number_value = next_number + 1

        code = self.recording_state.internal_set('idle')
        if code != '[PASS]':
            return code, {}

        code = self.recording_started_at_minute.internal_set(0)
        if code != '[PASS]':
            return code, {}
        self._recording_started_at_minute_value = 0

        return '[PASS]', {'capture_id': capture_id}

    def get_capture(self, capture_id: str) -> tuple[str, dict]:
        """
        Return one existing screenshot or completed or interrupted recording metadata record by stable ID. An unknown ID is rejected without changing the collection.

        Args:
        - capture_id: Stable ID of an existing capture metadata record.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- capture: The metadata-only screenshot or recording record stored under the requested ID. (type=object)

        Error Codes:
        - NOT_FOUND: Capture record ID does not exist.
        """
        code, captures = self.captures.get()
        if code != '[PASS]':
            return code, {}
        if type(capture_id) is not str or capture_id not in captures:
            return '[NOT_FOUND]', {}
        return '[PASS]', {'capture': dict(captures[capture_id])}

    def delete_capture(self, capture_id: str) -> tuple[str, dict]:
        """
        Delete one existing screenshot or completed or interrupted recording metadata record by stable ID while preserving every other record. Active recording state is unaffected. An unknown ID is rejected without changing the collection.

        Args:
        - capture_id: Stable ID of an existing capture metadata record to delete.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - NOT_FOUND: Capture record ID does not exist.
        """
        code, captures = self.captures.get()
        if code != '[PASS]':
            return code, {}
        if type(capture_id) is not str or capture_id not in captures:
            return '[NOT_FOUND]', {}

        updated_captures = {
            key: dict(record)
            for key, record in captures.items()
            if key != capture_id
        }
        code = self.captures.internal_set(updated_captures)
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {}

    def _on_dependency_changed(self, context: dict) -> tuple[str, list[dict]]:
        """
        When declared dependencies change, sets microphone_access_granted exactly equal to the Privacy source property microphone_authorized. It derives capture_block_reason from the system capture-condition source properties as follows: protected_content_active=true produces protected_content; otherwise capture_resource_available=false produces resource_conflict; otherwise it produces none. If recording is active after applying those mappings, an interruption is selected using this strict precedence: authorization_status other than granted produces authorization_revoked; otherwise protected_content_active=true produces protected_content; otherwise capture_resource_available=false produces resource_conflict; otherwise microphone_audio_enabled=true with microphone_authorized=false produces microphone_authorization_revoked; otherwise recording continues. A selected interruption creates exactly one recording record with result interrupted, the selected interruption_reason, the stored start minute, the current monotonic end minute, nonnegative elapsed duration, and the active microphone-audio setting, then returns recording state to idle and clears the stored start minute.

    Effect properties:
    - authorization_status: Current local capture authorization used as the highest-priority active-recording validity condition.
    - recording_state: Current recording state used to apply interruption only while a recording is active.
    - microphone_audio_enabled: Whether the active recording requires continued microphone authorization.
    - microphone_access_granted: Derived microphone access state set from the Privacy source property microphone_authorized.
    - capture_block_reason: Derived block reason set from protected_content_active and capture_resource_available with protected content taking precedence.
    - captures: Metadata collection receiving one interrupted recording record when an active recording loses a required condition.
    - recording_started_at_minute: Stored monotonic start minute used to calculate an interrupted recording's duration.
    - next_capture_number: Internal sequence used to allocate the interrupted recording record's stable ID.
        """
        code, current_microphone_access = (
            self.microphone_access_granted.get()
        )
        if code != '[PASS]':
            return code, []

        code, current_block_reason = self.capture_block_reason.get()
        if code != '[PASS]':
            return code, []

        microphone_authorized = current_microphone_access
        protected_content_active = (
            current_block_reason == 'protected_content'
        )
        capture_resource_available = (
            current_block_reason != 'resource_conflict'
        )

        for properties in context['dependencies'].values():
            if 'microphone_authorized' in properties:
                value = properties['microphone_authorized']
                if type(value) is bool:
                    microphone_authorized = value

            if 'protected_content_active' in properties:
                value = properties['protected_content_active']
                if type(value) is bool:
                    protected_content_active = value

            if 'capture_resource_available' in properties:
                value = properties['capture_resource_available']
                if type(value) is bool:
                    capture_resource_available = value

        if protected_content_active:
            block_reason = 'protected_content'
        elif not capture_resource_available:
            block_reason = 'resource_conflict'
        else:
            block_reason = 'none'

        code, authorization = self.authorization_status.get()
        if code != '[PASS]':
            return code, []

        code, recording_state = self.recording_state.get()
        if code != '[PASS]':
            return code, []

        code, microphone_audio = self.microphone_audio_enabled.get()
        if code != '[PASS]':
            return code, []

        interruption_reason = None
        if recording_state == 'recording':
            if authorization != 'granted':
                interruption_reason = 'authorization_revoked'
            elif protected_content_active:
                interruption_reason = 'protected_content'
            elif not capture_resource_available:
                interruption_reason = 'resource_conflict'
            elif microphone_audio and not microphone_authorized:
                interruption_reason = 'microphone_authorization_revoked'

        updated_captures = None
        next_number = self._next_capture_number_value

        if interruption_reason is not None:
            start_minute = self._recording_started_at_minute_value

            code, captures = self.captures.get()
            if code != '[PASS]':
                return code, []

            end_minute = context['time_state']['elapsed_minutes']
            capture_id = 'capture_' + str(next_number).zfill(6)
            updated_captures = {
                key: dict(record)
                for key, record in captures.items()
            }
            updated_captures[capture_id] = {
                'type': 'recording',
                'start_minute': start_minute,
                'end_minute': end_minute,
                'duration_minutes': max(end_minute - start_minute, 0),
                'microphone_audio_included': microphone_audio,
                'result': 'interrupted',
                'interruption_reason': interruption_reason
            }

        code = self.microphone_access_granted.internal_set(
            microphone_authorized
        )
        if code != '[PASS]':
            return code, []

        code = self.capture_block_reason.internal_set(block_reason)
        if code != '[PASS]':
            return code, []

        if interruption_reason is not None:
            code = self.captures.internal_set(updated_captures)
            if code != '[PASS]':
                return code, []

            code = self.next_capture_number.internal_set(next_number + 1)
            if code != '[PASS]':
                return code, []
            self._next_capture_number_value = next_number + 1

            code = self.recording_state.internal_set('idle')
            if code != '[PASS]':
                return code, []

            code = self.recording_started_at_minute.internal_set(0)
            if code != '[PASS]':
                return code, []
            self._recording_started_at_minute_value = 0

        return '[PASS]', []