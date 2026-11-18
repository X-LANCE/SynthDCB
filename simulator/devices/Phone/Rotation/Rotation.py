# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Rotation:
    """
    Rotation
    Description: Screen orientation settings, placed in Setting and contained by System. Supports enabling/disabling automatic rotation, locking a supported orientation when automatic rotation is disabled, and querying actual current orientation. Lockable orientations are read-only capabilities. With automatic rotation enabled, actual orientation is jointly determined by simulated device pose and the foreground application orientation restrictions and cannot be written directly. A lock preference does not guarantee an immediate orientation change in an application with orientation restrictions. This module does not duplicate Display brightness or screen-off settings.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, auto_rotate: bool = None, orientation_lock: str = None, lockable_orientations: dict = None, actual_orientation: str = None) -> None:
        # define properties
        self.auto_rotate = BoolProperty(
            name='auto_rotate',
            description='Whether automatic screen rotation is enabled. When enabled and the foreground application does not impose an orientation restriction, actual orientation follows simulated device pose.',
            default=True
        )
        self.orientation_lock = StringProperty(
            name='orientation_lock',
            description='The preferred orientation used when automatic rotation is disabled and the foreground application does not impose an orientation restriction. The value must identify a key in lockable_orientations. This preference does not directly overwrite actual_orientation.',
            default='portrait',
            pattern='^[a-z][a-z0-9_]*$',
            max_length=32
        )
        self.lockable_orientations = DictProperty(
            name='lockable_orientations',
            description='Read-only orientation-lock capabilities keyed by supported orientation ID. This baseline supports portrait and landscape locks.',
            default={'portrait': {'label': 'Portrait'}, 'landscape': {'label': 'Landscape'}},
            mode=2
        )
        self.actual_orientation = StringProperty(
            name='actual_orientation',
            description='Read-only current screen orientation feedback. A portrait or landscape foreground-application restriction takes precedence. Otherwise, this value follows simulated device pose when automatic rotation is enabled and the selected orientation lock when automatic rotation is disabled.',
            default='portrait',
            mode=2,
            choices=['portrait', 'landscape']
        )

        # initialize properties
        if auto_rotate is not None: code = self.auto_rotate.internal_set(auto_rotate)
        if orientation_lock is not None: code = self.orientation_lock.internal_set(orientation_lock)
        if lockable_orientations is not None: code = self.lockable_orientations.internal_set(lockable_orientations)
        if actual_orientation is not None: code = self.actual_orientation.internal_set(actual_orientation)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_auto_rotate(self) -> tuple[str, dict]:
        """
        Return whether automatic screen rotation is enabled without changing any setting or feedback.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- auto_rotate: Whether automatic screen rotation is enabled. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.auto_rotate.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'auto_rotate': value
        }
        return (code, response)

    def set_auto_rotate(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable automatic screen rotation. The existing orientation lock preference is preserved. This operation does not directly write actual_orientation because foreground application restrictions and external orientation feedback determine when the displayed orientation is resolved.

        Args:
        - value: The desired automatic rotation state.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.auto_rotate.set(value)
        if code != '[PASS]':
            return (code, {})
        response = {}
        return (code, response)

    def get_orientation_lock(self) -> tuple[str, dict]:
        """
        Return the preferred orientation lock. The preference is retained while automatic rotation is enabled but is used only when automatic rotation is disabled and the foreground application does not impose an orientation restriction.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- orientation_lock: The selected supported orientation-lock ID. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.orientation_lock.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'orientation_lock': value
        }
        return (code, response)

    def set_orientation_lock(self, orientation: str) -> tuple[str, dict]:
        """
        Select a supported orientation lock while automatic rotation is disabled. orientation must be an existing key in lockable_orientations. If automatic rotation is enabled or the orientation is unsupported, the operation fails and leaves all state unchanged. A successful preference change does not directly write actual_orientation because a foreground application restriction may prevent an immediate orientation change.

        Args:
        - orientation: An orientation ID from lockable_orientations.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - NOT_FOUND: The requested orientation is not a supported lockable orientation.
        - PRECONDITION_FAILED: Automatic rotation must be disabled before selecting an orientation lock.
        """
        code, auto_rotate = self.auto_rotate.get()
        if code != '[PASS]':
            return (code, {})
        if auto_rotate:
            return ('[PRECONDITION_FAILED]', {})

        code, lockable_orientations = self.lockable_orientations.get()
        if code != '[PASS]':
            return (code, {})
        if type(orientation) is not str or orientation not in lockable_orientations:
            return ('[NOT_FOUND]', {})

        code = self.orientation_lock.set(orientation)
        if code != '[PASS]':
            return (code, {})
        response = {}
        return (code, response)

    def get_lockable_orientations(self) -> tuple[str, dict]:
        """
        Return the fixed read-only dictionary of supported orientation-lock capabilities and their IDs.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- lockable_orientations: Supported orientation locks keyed by orientation ID. (type=object)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.lockable_orientations.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'lockable_orientations': {
                key: dict(record) for key, record in value.items()
            }
        }
        return (code, response)

    def get_actual_orientation(self) -> tuple[str, dict]:
        """
        Return the read-only current screen orientation. A foreground application restriction to portrait or landscape takes precedence. Without such a restriction, the value follows simulated device pose when automatic rotation is enabled and the selected lock preference when automatic rotation is disabled. This query does not change feedback.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- actual_orientation: The resolved current orientation, either portrait or landscape. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.actual_orientation.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'actual_orientation': value
        }
        return (code, response)

    def _on_dependency_changed(self, context: dict) -> tuple[str, list[dict]]:
        """
        When simulated device pose or foreground application orientation restrictions change, recompute actual orientation deterministically. A foreground restriction of portrait or landscape takes precedence. If the foreground application is unrestricted, use the simulated pose orientation when automatic rotation is enabled; otherwise use the selected orientation lock. Repeated updates with unchanged inputs leave the resolved orientation unchanged.

    Effect properties:
    - auto_rotate: Determines whether unrestricted orientation follows simulated device pose or the selected lock preference.
    - orientation_lock: Preferred orientation used when automatic rotation is disabled and the foreground application is unrestricted.
    - actual_orientation: Read-only orientation feedback recomputed from the dependency values and local rotation preferences.
        """
        code, auto_rotate = self.auto_rotate.get()
        if code != '[PASS]':
            return (code, [])

        code, orientation_lock = self.orientation_lock.get()
        if code != '[PASS]':
            return (code, [])

        pose_orientation = None
        orientation_restriction = None

        for dependency in context['dependencies'].values():
            if 'orientation_restriction' in dependency:
                orientation_restriction = dependency['orientation_restriction']
            elif 'foreground_orientation_restriction' in dependency:
                orientation_restriction = dependency['foreground_orientation_restriction']
            elif 'foreground_app_orientation_restriction' in dependency:
                orientation_restriction = dependency['foreground_app_orientation_restriction']

            if 'pose_orientation' in dependency:
                pose_orientation = dependency['pose_orientation']
            elif 'simulated_pose_orientation' in dependency:
                pose_orientation = dependency['simulated_pose_orientation']
            elif 'device_pose_orientation' in dependency:
                pose_orientation = dependency['device_pose_orientation']
            elif 'orientation' in dependency and 'orientation_restriction' not in dependency:
                pose_orientation = dependency['orientation']

        if orientation_restriction in ('portrait', 'landscape'):
            resolved_orientation = orientation_restriction
        elif auto_rotate:
            if pose_orientation not in ('portrait', 'landscape'):
                return ('[PRECONDITION_FAILED]', [])
            resolved_orientation = pose_orientation
        else:
            resolved_orientation = orientation_lock

        code = self.actual_orientation.internal_set(resolved_orientation)
        if code != '[PASS]':
            return (code, [])
        return ('[PASS]', [])