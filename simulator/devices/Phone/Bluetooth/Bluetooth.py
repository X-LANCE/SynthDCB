# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Bluetooth:
    """
    Bluetooth
    Description: Bluetooth settings, placed in Setting and contained by System. Supports enabling/disabling Bluetooth, scanning simulated nearby devices, querying devices, requesting pairing, unpairing, connecting, and disconnecting, with separate queries for pairing records, active connections, and profiles such as audio. Devices use stable IDs. Scanning, pairing, and connecting require Bluetooth to be enabled and comply with airplane-mode policy. Pairing confirmation may be denied, and a paired device is not guaranteed to connect. Disabling Bluetooth ends active connections but preserves pairing records. Unpairing removes the specified record and ends its connection without affecting other records. Connection capacity and supported profiles are read-only simulation capabilities.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, enabled: bool = None, radio_allowed: bool = None, nearby_devices: dict = None, paired_devices: dict = None, active_connections: dict = None, supported_profiles: dict = None, connection_capacity: int = None) -> None:
        # define properties
        self.enabled = BoolProperty(
            name='enabled',
            description='Whether Bluetooth is enabled. Enabling does not scan, pair, or connect automatically.',
            default=False
        )
        self.radio_allowed = BoolProperty(
            name='radio_allowed',
            description='Whether the current phone airplane-mode policy permits Bluetooth radio use. A false value prevents enabling, scanning, pairing, and connecting.',
            default=True,
            mode=2
        )
        self.nearby_devices = DictProperty(
            name='nearby_devices',
            description='Deterministic simulated nearby devices keyed by stable device ID. Each record contains a display name, supported profile IDs, and a pairing confirmation outcome.',
            default={'headphones_1': {'name': 'Simulated Headphones', 'supported_profiles': ['audio'], 'pairing_confirmation': 'accepted'}, 'keyboard_1': {'name': 'Simulated Keyboard', 'supported_profiles': ['input'], 'pairing_confirmation': 'accepted'}, 'speaker_denied': {'name': 'Confirmation-Denied Speaker', 'supported_profiles': ['audio'], 'pairing_confirmation': 'denied'}},
            mode=2
        )
        self.paired_devices = DictProperty(
            name='paired_devices',
            description='Persistent pairing records keyed by stable device ID. Each record retains the simulated device name and supported profiles.',
            default={},
            mode=2
        )
        self.active_connections = DictProperty(
            name='active_connections',
            description='Active Bluetooth connections keyed by paired device ID. Each record identifies the connected profile. Records are cleared when Bluetooth is disabled or blocked by airplane-mode policy.',
            default={},
            mode=2
        )
        self.supported_profiles = DictProperty(
            name='supported_profiles',
            description='Read-only Bluetooth profiles supported by this simulated phone, keyed by profile ID.',
            default={'audio': {'name': 'Audio'}, 'input': {'name': 'Input'}},
            mode=2
        )
        self.connection_capacity = IntProperty(
            name='connection_capacity',
            description='Maximum number of simultaneously connected device records supported by this simulation.',
            default=1,
            mode=2,
            unit='devices',
            minimum=1,
            maximum=1,
            step=1,
            step_origin=1
        )

        # initialize properties
        if enabled is not None: code = self.enabled.internal_set(enabled)
        if radio_allowed is not None: code = self.radio_allowed.internal_set(radio_allowed)
        if nearby_devices is not None: code = self.nearby_devices.internal_set(nearby_devices)
        if paired_devices is not None: code = self.paired_devices.internal_set(paired_devices)
        if active_connections is not None: code = self.active_connections.internal_set(active_connections)
        if supported_profiles is not None: code = self.supported_profiles.internal_set(supported_profiles)
        if connection_capacity is not None: code = self.connection_capacity.internal_set(connection_capacity)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_enabled(self) -> tuple[str, dict]:
        """
        Return whether Bluetooth is currently enabled.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- enabled: The current Bluetooth enabled state. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.enabled.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'enabled': value
        }
        return (code, response)

    def set_enabled(self, enabled: bool) -> tuple[str, dict]:
        """
        Enable or disable Bluetooth. Enabling is rejected when radio_allowed is false. Disabling immediately removes every active connection while preserving all pairing records. Invalid or blocked requests leave all state unchanged.

        Args:
        - enabled: The desired Bluetooth enabled state.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: Bluetooth cannot be enabled while the effective airplane-mode radio policy blocks it.
        """
        if type(enabled) is bool and enabled:
            code, allowed = self.radio_allowed.get()
            if code != '[PASS]':
                return (code, {})
            if not allowed:
                return ('[PRECONDITION_FAILED]', {})

        code = self.enabled.set(enabled)
        if code != '[PASS]':
            return (code, {})

        if not enabled:
            code = self.active_connections.internal_set({})
            if code != '[PASS]':
                return (code, {})

        return ('[PASS]', {})

    def get_radio_allowed(self) -> tuple[str, dict]:
        """
        Return whether the effective airplane-mode policy currently permits Bluetooth radio use.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- radio_allowed: Whether current phone policy permits Bluetooth radio use. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.radio_allowed.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'radio_allowed': value
        }
        return (code, response)

    def scan(self) -> tuple[str, dict]:
        """
        Return the deterministic simulated nearby-device dictionary. Bluetooth must be enabled and permitted by airplane-mode policy. Scanning does not pair or connect any device and does not change state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- nearby_devices: Nearby simulated devices keyed by stable device ID. (type=object)

        Error Codes:
        - PRECONDITION_FAILED: Bluetooth is disabled or blocked by airplane-mode policy.
        """
        code, enabled = self.enabled.get()
        if code != '[PASS]':
            return (code, {})

        code, allowed = self.radio_allowed.get()
        if code != '[PASS]':
            return (code, {})

        if not enabled or not allowed:
            return ('[PRECONDITION_FAILED]', {})

        code, devices = self.nearby_devices.get()
        if code != '[PASS]':
            return (code, {})

        response_devices = {}
        for device_id, record in devices.items():
            copied_record = dict(record)
            if 'supported_profiles' in copied_record:
                copied_record['supported_profiles'] = list(copied_record['supported_profiles'])
            response_devices[device_id] = copied_record

        return ('[PASS]', {'nearby_devices': response_devices})

    def get_paired_devices(self) -> tuple[str, dict]:
        """
        Return all persistent Bluetooth pairing records keyed by stable device ID. Pairing records remain available when Bluetooth is disabled.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- paired_devices: Persistent pairing records keyed by stable device ID. (type=object)

        Error Codes:
        (no specified error codes)
        """
        code, devices = self.paired_devices.get()
        if code != '[PASS]':
            return (code, {})

        response_devices = {}
        for device_id, record in devices.items():
            copied_record = dict(record)
            if 'supported_profiles' in copied_record:
                copied_record['supported_profiles'] = list(copied_record['supported_profiles'])
            response_devices[device_id] = copied_record

        return ('[PASS]', {'paired_devices': response_devices})

    def get_active_connections(self) -> tuple[str, dict]:
        """
        Return all active Bluetooth connection records keyed by paired device ID.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- active_connections: Active connection records keyed by paired device ID. (type=object)

        Error Codes:
        (no specified error codes)
        """
        code, connections = self.active_connections.get()
        if code != '[PASS]':
            return (code, {})

        return (
            '[PASS]',
            {
                'active_connections': {
                    device_id: dict(record)
                    for device_id, record in connections.items()
                }
            }
        )

    def get_supported_profiles(self) -> tuple[str, dict]:
        """
        Return the read-only dictionary of Bluetooth profiles supported by this simulated phone.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- supported_profiles: Supported Bluetooth profiles keyed by profile ID. (type=object)

        Error Codes:
        (no specified error codes)
        """
        code, profiles = self.supported_profiles.get()
        if code != '[PASS]':
            return (code, {})

        return (
            '[PASS]',
            {
                'supported_profiles': {
                    profile_id: dict(record)
                    for profile_id, record in profiles.items()
                }
            }
        )

    def get_connection_capacity(self) -> tuple[str, dict]:
        """
        Return the read-only maximum number of simultaneous connected device records supported by this simulation.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- connection_capacity: Maximum simultaneous connected-device count. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.connection_capacity.get()
        if code != '[PASS]':
            return (code, {})

        return ('[PASS]', {'connection_capacity': value})

    def request_pairing(self, device_id: str) -> tuple[str, dict]:
        """
        Request pairing with a simulated nearby device. Bluetooth must be enabled and permitted, and device_id must identify a nearby device. A record whose pairing_confirmation is denied causes a deterministic rejection and no state change. An accepted request creates or preserves the pairing under the same stable device ID without connecting it or changing unrelated records.

        Args:
        - device_id: Stable ID of an existing simulated nearby device.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- device_id: Stable ID of the successfully paired device. (type=string)

        Error Codes:
        - NOT_FOUND: The nearby device ID does not exist.
        - PRECONDITION_FAILED: Bluetooth is disabled or blocked by airplane-mode policy.
        - PAIRING_DENIED: The simulated device denied pairing confirmation.
        """
        code, enabled = self.enabled.get()
        if code != '[PASS]':
            return (code, {})

        code, allowed = self.radio_allowed.get()
        if code != '[PASS]':
            return (code, {})

        if not enabled or not allowed:
            return ('[PRECONDITION_FAILED]', {})

        code, nearby = self.nearby_devices.get()
        if code != '[PASS]':
            return (code, {})

        if type(device_id) is not str or device_id not in nearby:
            return ('[NOT_FOUND]', {})

        nearby_record = nearby[device_id]
        if nearby_record['pairing_confirmation'] == 'denied':
            return ('[PAIRING_DENIED]', {})

        code, paired = self.paired_devices.get()
        if code != '[PASS]':
            return (code, {})

        if device_id not in paired:
            updated_paired = dict(paired)
            updated_paired[device_id] = {
                'name': nearby_record['name'],
                'supported_profiles': list(nearby_record['supported_profiles'])
            }
            code = self.paired_devices.internal_set(updated_paired)
            if code != '[PASS]':
                return (code, {})

        return ('[PASS]', {'device_id': device_id})

    def unpair(self, device_id: str) -> tuple[str, dict]:
        """
        Remove one existing pairing record by stable device ID and remove that device's active connection if present. Every unrelated pairing and connection record is preserved. An unknown ID is rejected without changing state.

        Args:
        - device_id: Stable ID of an existing paired device.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - NOT_FOUND: The paired device ID does not exist.
        """
        code, paired = self.paired_devices.get()
        if code != '[PASS]':
            return (code, {})

        if type(device_id) is not str or device_id not in paired:
            return ('[NOT_FOUND]', {})

        code, connections = self.active_connections.get()
        if code != '[PASS]':
            return (code, {})

        updated_paired = dict(paired)
        del updated_paired[device_id]

        updated_connections = dict(connections)
        if device_id in updated_connections:
            del updated_connections[device_id]

        code = self.paired_devices.internal_set(updated_paired)
        if code != '[PASS]':
            return (code, {})

        code = self.active_connections.internal_set(updated_connections)
        if code != '[PASS]':
            return (code, {})

        return ('[PASS]', {})

    def connect(self, device_id: str, profile: str) -> tuple[str, dict]:
        """
        Connect one paired device using a supported profile. Bluetooth must be enabled and permitted. The device must be paired, the profile must be supported by both the phone and that device, and the active connected-device count must remain within connection_capacity. Repeating the same device and profile is idempotent. A failed request leaves every connection unchanged.

        Args:
        - device_id: Stable ID of an existing paired device.
        - profile: Bluetooth profile to activate for the connection. (choices=['audio', 'input'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- device_id: Stable ID of the connected device. (type=string)
        	- profile: Profile used by the active connection. (type=string)

        Error Codes:
        - NOT_FOUND: The paired device ID or phone profile ID does not exist.
        - PRECONDITION_FAILED: Bluetooth is disabled or blocked by airplane-mode policy.
        - UNSUPPORTED_PROFILE: The paired device does not support the requested profile.
        - CAPACITY_REACHED: Connecting the device would exceed the simulation connection capacity.
        """
        code, enabled = self.enabled.get()
        if code != '[PASS]':
            return (code, {})

        code, allowed = self.radio_allowed.get()
        if code != '[PASS]':
            return (code, {})

        if not enabled or not allowed:
            return ('[PRECONDITION_FAILED]', {})

        code, paired = self.paired_devices.get()
        if code != '[PASS]':
            return (code, {})

        if type(device_id) is not str or device_id not in paired:
            return ('[NOT_FOUND]', {})

        code, phone_profiles = self.supported_profiles.get()
        if code != '[PASS]':
            return (code, {})

        if type(profile) is not str or profile not in phone_profiles:
            return ('[NOT_FOUND]', {})

        paired_record = paired[device_id]
        if profile not in paired_record['supported_profiles']:
            return ('[UNSUPPORTED_PROFILE]', {})

        code, connections = self.active_connections.get()
        if code != '[PASS]':
            return (code, {})

        if (
            device_id in connections
            and connections[device_id].get('profile') == profile
        ):
            return (
                '[PASS]',
                {
                    'device_id': device_id,
                    'profile': profile
                }
            )

        code, capacity = self.connection_capacity.get()
        if code != '[PASS]':
            return (code, {})

        if device_id not in connections and len(connections) >= capacity:
            return ('[CAPACITY_REACHED]', {})

        updated_connections = dict(connections)
        updated_connections[device_id] = {
            'profile': profile
        }

        code = self.active_connections.internal_set(updated_connections)
        if code != '[PASS]':
            return (code, {})

        return (
            '[PASS]',
            {
                'device_id': device_id,
                'profile': profile
            }
        )

    def disconnect(self, device_id: str) -> tuple[str, dict]:
        """
        Disconnect one actively connected device by stable device ID. The pairing record and every unrelated connection are preserved. An unknown active connection ID is rejected without changing state.

        Args:
        - device_id: Stable ID of an actively connected device.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - NOT_FOUND: The active connection ID does not exist.
        """
        code, connections = self.active_connections.get()
        if code != '[PASS]':
            return (code, {})

        if type(device_id) is not str or device_id not in connections:
            return ('[NOT_FOUND]', {})

        updated_connections = dict(connections)
        del updated_connections[device_id]

        code = self.active_connections.internal_set(updated_connections)
        if code != '[PASS]':
            return (code, {})

        return ('[PASS]', {})

    def _on_dependency_changed(self, context: dict) -> tuple[str, list[dict]]:
        """
        When the effective phone airplane-mode policy changes, updates radio_allowed. If the policy becomes blocking, Bluetooth is disabled and all active connections are ended while pairing records are preserved. A later permitted policy does not automatically re-enable or reconnect Bluetooth.

    Effect properties:
    - radio_allowed: Effective phone policy determining whether Bluetooth radio use is permitted.
    - enabled: Bluetooth enabled state, which is cleared when radio use becomes blocked.
    - active_connections: Active connections, which are cleared when radio use becomes blocked.
        """
        dependency_states = list(context['dependencies'].values())
        airplane_mode = dependency_states[0]['airplane_mode']
        allowed = not airplane_mode

        code = self.radio_allowed.internal_set(allowed)
        if code != '[PASS]':
            return (code, [])

        if not allowed:
            code = self.enabled.internal_set(False)
            if code != '[PASS]':
                return (code, [])

            code = self.active_connections.internal_set({})
            if code != '[PASS]':
                return (code, [])

        return ('[PASS]', [])