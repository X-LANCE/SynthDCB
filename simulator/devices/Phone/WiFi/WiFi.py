# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class WiFi:
    """
    WiFi
    Description: Wireless network settings, placed in Setting. Supports enabling/disabling Wi-Fi, querying saved networks, connecting, disconnecting, and forgetting networks. Connection requires Wi-Fi to be enabled and the network to be saved. Disabling Wi-Fi or forgetting the current network immediately disconnects it. Other network records are preserved, and re-enabling Wi-Fi does not automatically reconnect.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, enabled: bool = None, saved_networks: dict = None, connected_network_id: str = None) -> None:
        # define properties
        self.enabled = BoolProperty(
            name='enabled',
            description='Whether Wi-Fi is enabled. Enabling Wi-Fi does not automatically establish a connection.',
            default=False
        )
        self.saved_networks = DictProperty(
            name='saved_networks',
            description="Saved wireless networks keyed by stable network ID. Each record contains the network's display name and no credentials.",
            default={'Home': {'name': 'Home'}, 'Office': {'name': 'Office'}},
            mode=2
        )
        self.connected_network_id = StringProperty(
            name='connected_network_id',
            description='The ID of the currently connected saved network, or an empty string when disconnected.',
            default='',
            mode=2,
            pattern='^[A-Za-z0-9_-]*$',
            max_length=128
        )

        # initialize properties
        if enabled is not None: code = self.enabled.internal_set(enabled)
        if saved_networks is not None: code = self.saved_networks.internal_set(saved_networks)
        if connected_network_id is not None: code = self.connected_network_id.internal_set(connected_network_id)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_enabled(self) -> tuple[str, dict]:
        """
        Return whether Wi-Fi is currently enabled without changing any state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- enabled: Whether Wi-Fi is enabled. (type=boolean)

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
        Enable or disable Wi-Fi. Disabling immediately sets connected_network_id to an empty string while preserving every saved network. Enabling preserves saved networks and does not automatically reconnect. Invalid arguments leave all state unchanged.

        Args:
        - enabled: The desired Wi-Fi enabled state.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.enabled.set(enabled)
        if code != '[PASS]':
            return (code, {})
        if not enabled:
            code = self.connected_network_id.internal_set('')
            if code != '[PASS]':
                return (code, {})
        response = {}
        return ('[PASS]', response)

    def get_saved_networks(self) -> tuple[str, dict]:
        """
        Return all saved network records keyed by their stable network IDs without changing any state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- saved_networks: The complete dictionary of saved network records keyed by network ID. (type=object)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.saved_networks.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'saved_networks': {
                key: dict(record)
                for key, record in value.items()
            }
        }
        return (code, response)

    def get_connected_network_id(self) -> tuple[str, dict]:
        """
        Return the ID of the currently connected saved network, or an empty string when Wi-Fi is disconnected.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- connected_network_id: The connected saved network ID, or an empty string when disconnected. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.connected_network_id.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'connected_network_id': value
        }
        return (code, response)

    def connect(self, network_id: str) -> tuple[str, dict]:
        """
        Connect to a saved network by ID. Wi-Fi must be enabled and network_id must identify an existing record in saved_networks. A successful call replaces any current connection with the selected network. No real network access or internet availability is implied. Invalid input or an unmet precondition leaves state unchanged.

        Args:
        - network_id: The stable ID of an existing saved network.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - NOT_FOUND: The supplied network ID is not present in saved_networks.
        - PRECONDITION_FAILED: Wi-Fi is disabled.
        """
        if type(network_id) is not str:
            return ('[NOT_FOUND]', {})
        if (
            len(network_id) == 0
            or len(network_id) > 128
            or any(
                character not in
                'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-'
                for character in network_id
            )
        ):
            return ('[INVALID_ARGUMENT]', {})

        code, enabled = self.enabled.get()
        if code != '[PASS]':
            return (code, {})
        if not enabled:
            return ('[PRECONDITION_FAILED]', {})

        code, networks = self.saved_networks.get()
        if code != '[PASS]':
            return (code, {})
        if network_id not in networks:
            return ('[NOT_FOUND]', {})

        code = self.connected_network_id.internal_set(network_id)
        if code != '[PASS]':
            return (code, {})
        response = {}
        return ('[PASS]', response)

    def disconnect(self) -> tuple[str, dict]:
        """
        Disconnect Wi-Fi by setting connected_network_id to an empty string. Saved networks and the enabled setting are preserved. The operation is idempotent when already disconnected.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.connected_network_id.internal_set('')
        if code != '[PASS]':
            return (code, {})
        response = {}
        return ('[PASS]', response)

    def forget_network(self, network_id: str) -> tuple[str, dict]:
        """
        Forget an existing saved network by ID. Only the selected record is removed and all unrelated records are preserved. If the forgotten network is currently connected, connected_network_id is immediately cleared; otherwise the current connection is preserved. An unknown ID or invalid input leaves all state unchanged.

        Args:
        - network_id: The stable ID of the saved network to forget.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - NOT_FOUND: The supplied network ID is not present in saved_networks.
        """
        if type(network_id) is not str:
            return ('[NOT_FOUND]', {})
        if (
            len(network_id) == 0
            or len(network_id) > 128
            or any(
                character not in
                'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-'
                for character in network_id
            )
        ):
            return ('[INVALID_ARGUMENT]', {})

        code, networks = self.saved_networks.get()
        if code != '[PASS]':
            return (code, {})
        if network_id not in networks:
            return ('[NOT_FOUND]', {})

        code, connected_network_id = self.connected_network_id.get()
        if code != '[PASS]':
            return (code, {})

        updated_networks = dict(networks)
        del updated_networks[network_id]

        code = self.saved_networks.internal_set(updated_networks)
        if code != '[PASS]':
            return (code, {})

        if connected_network_id == network_id:
            code = self.connected_network_id.internal_set('')
            if code != '[PASS]':
                return (code, {})

        response = {}
        return ('[PASS]', response)