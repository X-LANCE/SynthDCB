# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty


class Dashcam:
    """
    Dashcam
    Description: Dashcam module. Supports starting and stopping recording, saving the current segment, querying recording state and local storage availability, and managing retention or deletion of simulated clips.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, recording_state: str = None, storage_available: bool = None, clips: dict = None) -> None:
        # define properties
        self.recording_state = StringProperty(
            name='recording_state',
            description='Current dashcam recording state.',
            default='stopped',
            mode=2,
            choices=['recording', 'stopped']
        )
        self.storage_available = BoolProperty(
            name='storage_available',
            description='Whether compatible local storage is currently available for recording and saving clips.',
            default=True,
            mode=2
        )
        self.clips = DictProperty(
            name='clips',
            description='Saved simulated clips keyed by stable clip ID. Each clip records whether it is retained.',
            default={},
            mode=2,
            schema={
                'type': 'object',
                'additionalProperties': {
                    'type': 'object',
                    'properties': {
                        'retained': {
                            'type': 'boolean'
                        }
                    },
                    'required': ['retained'],
                    'additionalProperties': False
                }
            }
        )

        # initialize properties
        if recording_state is not None:
            code = self.recording_state.internal_set(recording_state)
        if storage_available is not None:
            code = self.storage_available.internal_set(storage_available)
        if clips is not None:
            code = self.clips.internal_set(clips)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_recording_state(self) -> tuple[str, dict]:
        """
        Return the current recording state without changing dashcam state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- recording_state: Current state: recording or stopped. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.recording_state.get()
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {'recording_state': value}

    def get_storage_available(self) -> tuple[str, dict]:
        """
        Return whether local storage is available without changing dashcam state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- storage_available: Whether local storage is available for recording and saving clips. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.storage_available.get()
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {'storage_available': value}

    def start_recording(self) -> tuple[str, dict]:
        """
        Start dashcam recording. The action succeeds only when recording is stopped and local storage is available; otherwise it is rejected without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: Recording must be stopped and local storage must be available.
        """
        state_code, state = self.recording_state.get()
        if state_code != '[PASS]':
            return state_code, {}

        storage_code, storage_available = self.storage_available.get()
        if storage_code != '[PASS]':
            return storage_code, {}

        if state != 'stopped' or not storage_available:
            return '[PRECONDITION_FAILED]', {}

        code = self.recording_state.internal_set('recording')
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {}

    def stop_recording(self) -> tuple[str, dict]:
        """
        Stop active dashcam recording. The action is rejected without mutation when the dashcam is already stopped.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The dashcam must be recording before it can be stopped.
        """
        state_code, state = self.recording_state.get()
        if state_code != '[PASS]':
            return state_code, {}

        if state != 'recording':
            return '[PRECONDITION_FAILED]', {}

        code = self.recording_state.internal_set('stopped')
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {}

    def save_current_segment(self) -> tuple[str, dict]:
        """
        Save the current recording segment as a new retained simulated clip and return its stable clip ID. The action succeeds only while recording and when local storage is available; failure leaves all existing clips unchanged.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- clip_id: Stable ID assigned to the newly saved clip. (type=string)

        Error Codes:
        - PRECONDITION_FAILED: A segment can be saved only while recording with local storage available.
        """
        state_code, state = self.recording_state.get()
        if state_code != '[PASS]':
            return state_code, {}

        storage_code, storage_available = self.storage_available.get()
        if storage_code != '[PASS]':
            return storage_code, {}

        if state != 'recording' or not storage_available:
            return '[PRECONDITION_FAILED]', {}

        clips_code, clips = self.clips.get()
        if clips_code != '[PASS]':
            return clips_code, {}

        clip_number = 1
        clip_id = 'clip_1'
        while clip_id in clips:
            clip_number += 1
            clip_id = 'clip_' + str(clip_number)

        updated_clips = {}
        for existing_id, existing_clip in clips.items():
            updated_clips[existing_id] = {
                'retained': existing_clip['retained']
            }
        updated_clips[clip_id] = {'retained': True}

        code = self.clips.internal_set(updated_clips)
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {'clip_id': clip_id}

    def get_clip(self, clip_id: str) -> tuple[str, dict]:
        """
        Return the simulated clip identified by clip_id. An unknown ID is rejected without changing state.

        Args:
        - clip_id:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- clip: The requested simulated clip record, including its retained flag. (type=object)

        Error Codes:
        - PRECONDITION_FAILED: No saved clip exists with the supplied clip_id.
        """
        if type(clip_id) is not str or len(clip_id) == 0:
            return '[INVALID_INPUT_ERROR]', {}

        clips_code, clips = self.clips.get()
        if clips_code != '[PASS]':
            return clips_code, {}

        if clip_id not in clips:
            return '[PRECONDITION_FAILED]', {}

        clip = {
            'retained': clips[clip_id]['retained']
        }
        return '[PASS]', {'clip': clip}

    def set_clip_retained(self, clip_id: str, retained: bool) -> tuple[str, dict]:
        """
        Set whether a saved simulated clip is retained. Only the retained field of the selected clip changes; all other clips are preserved. An unknown ID or invalid value leaves state unchanged.

        Args:
        - clip_id: 
        - retained:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: No saved clip exists with the supplied clip_id.
        """
        if type(clip_id) is not str or len(clip_id) == 0:
            return '[INVALID_INPUT_ERROR]', {}
        if type(retained) is not bool:
            return '[INVALID_INPUT_ERROR]', {}

        clips_code, clips = self.clips.get()
        if clips_code != '[PASS]':
            return clips_code, {}

        if clip_id not in clips:
            return '[PRECONDITION_FAILED]', {}

        updated_clips = {}
        for existing_id, existing_clip in clips.items():
            if existing_id == clip_id:
                updated_clips[existing_id] = {
                    'retained': retained
                }
            else:
                updated_clips[existing_id] = {
                    'retained': existing_clip['retained']
                }

        code = self.clips.internal_set(updated_clips)
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {}

    def delete_clip(self, clip_id: str) -> tuple[str, dict]:
        """
        Permanently delete the saved simulated clip identified by clip_id, whether retained or unretained. All other clips are preserved. An unknown ID is rejected without changing state.

        Args:
        - clip_id:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: No saved clip exists with the supplied clip_id.
        """
        if type(clip_id) is not str or len(clip_id) == 0:
            return '[INVALID_INPUT_ERROR]', {}

        clips_code, clips = self.clips.get()
        if clips_code != '[PASS]':
            return clips_code, {}

        if clip_id not in clips:
            return '[PRECONDITION_FAILED]', {}

        updated_clips = {}
        for existing_id, existing_clip in clips.items():
            if existing_id != clip_id:
                updated_clips[existing_id] = {
                    'retained': existing_clip['retained']
                }

        code = self.clips.internal_set(updated_clips)
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {}