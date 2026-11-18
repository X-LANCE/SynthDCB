# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Connectivity:
    """
    Connectivity
    Description: Cellular data and network availability settings, placed in Setting and contained by System. Supports querying SIM and cellular service state, enabling/disabling mobile data, setting data roaming permission, and querying the current upstream network and internet availability. SIM slot count is a read-only capability; signal strength, link state, and internet availability are read-only feedback. Effective mobile data availability requires a valid SIM, service coverage, and satisfied airplane-mode dependencies. Enabling the switch does not guarantee connection, and allowing roaming does not mean the device is currently roaming. Wi-Fi connection state is owned by WiFi; this module only references it in its aggregated view.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, sim_slot_count: int=None, sim_state: str=None, service_state: str=None, mobile_data_enabled: bool=None, data_roaming_enabled: bool=None, signal_strength_percent: int=None, cellular_link_state: str=None, upstream_network: str=None, internet_available: bool=None) -> None:
        self.sim_slot_count = IntProperty(name='sim_slot_count', description='Fixed number of cellular SIM slots supported by this simulated phone.', default=1, mode=2, unit='slots', minimum=1, maximum=1, step=1, step_origin=1)
        self.sim_state = StringProperty(name='sim_state', description='Read-only state of the SIM used for cellular data. Ready indicates a valid usable SIM, absent indicates no SIM, and invalid indicates a present but unusable SIM.', default='ready', mode=2, choices=['absent', 'invalid', 'ready'])
        self.service_state = StringProperty(name='service_state', description='Read-only cellular service feedback. Home and roaming indicate coverage, while unavailable indicates that cellular service cannot currently be used.', default='home', mode=2, choices=['unavailable', 'home', 'roaming'])
        self.mobile_data_enabled = BoolProperty(name='mobile_data_enabled', description='Whether use of cellular mobile data is requested. Enabling this setting does not by itself guarantee a cellular connection or internet access.', default=False)
        self.data_roaming_enabled = BoolProperty(name='data_roaming_enabled', description='Whether cellular data use is permitted while roaming. This permission does not indicate that the phone is currently roaming.', default=False)
        self.signal_strength_percent = IntProperty(name='signal_strength_percent', description='Read-only normalized cellular signal strength from 0 through 100 percent. This synthetic percentage is feedback and does not by itself establish connectivity.', default=75, mode=2, unit='percent', minimum=0, maximum=100, step=1, step_origin=0)
        self.cellular_link_state = StringProperty(name='cellular_link_state', description='Read-only cellular data link feedback derived from the mobile-data setting, SIM state, service state, signal strength, roaming permission, and airplane-mode dependency.', default='disconnected', mode=2, choices=['disconnected', 'connected'])
        self.upstream_network = StringProperty(name='upstream_network', description='Read-only aggregated upstream network selected by the simulation. An active Wi-Fi connection has priority over an eligible connected cellular link. Wi-Fi state remains owned by WiFi.', default='none', mode=2, choices=['none', 'cellular', 'wifi'])
        self.internet_available = BoolProperty(name='internet_available', description='Read-only deterministic internet-availability feedback for the selected upstream. It is true when dependency recomputation selects an active Wi-Fi connection or an eligible connected cellular link, and false when no upstream is selected.', default=False, mode=2)
        if sim_slot_count is not None:
            code = self.sim_slot_count.internal_set(sim_slot_count)
        if sim_state is not None:
            code = self.sim_state.internal_set(sim_state)
        if service_state is not None:
            code = self.service_state.internal_set(service_state)
        if mobile_data_enabled is not None:
            code = self.mobile_data_enabled.internal_set(mobile_data_enabled)
        if data_roaming_enabled is not None:
            code = self.data_roaming_enabled.internal_set(data_roaming_enabled)
        if signal_strength_percent is not None:
            code = self.signal_strength_percent.internal_set(signal_strength_percent)
        if cellular_link_state is not None:
            code = self.cellular_link_state.internal_set(cellular_link_state)
        if upstream_network is not None:
            code = self.upstream_network.internal_set(upstream_network)
        if internet_available is not None:
            code = self.internet_available.internal_set(internet_available)
        self._disabled = {'properties': [], 'functions': [], 'events': []}

    def get_sim_slot_count(self) -> tuple[str, dict]:
        """
        Return the fixed number of cellular SIM slots supported by this simulated phone.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- sim_slot_count: Number of supported SIM slots. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.sim_slot_count.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'sim_slot_count': value})

    def get_sim_state(self) -> tuple[str, dict]:
        """
        Return whether the cellular-data SIM is absent, invalid, or ready without changing its state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- sim_state: Current cellular-data SIM state. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.sim_state.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'sim_state': value})

    def get_service_state(self) -> tuple[str, dict]:
        """
        Return the current cellular service feedback as unavailable, home, or roaming. This does not change roaming permission.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- service_state: Current cellular service state. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.service_state.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'service_state': value})

    def get_mobile_data_enabled(self) -> tuple[str, dict]:
        """
        Return whether cellular mobile data is enabled as a user setting. The result does not by itself assert that a cellular link or internet access is available.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- mobile_data_enabled: Current mobile-data enabled setting. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.mobile_data_enabled.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'mobile_data_enabled': value})

    def set_mobile_data_enabled(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable the mobile-data setting. Disabling immediately makes an existing cellular link ineligible and clears cellular-derived upstream and internet feedback while preserving any Wi-Fi upstream. Enabling does not manufacture a connection; full derived feedback is recomputed when network dependencies are evaluated. Invalid input is rejected and leaves all state unchanged.

        Args:
        - value: Desired mobile-data enabled setting.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        if not isinstance(value, bool):
            return ('[FAIL] Invalid value', {})
        code, sim_state = self.sim_state.get()
        if code != '[PASS]':
            return (code, {})
        code, service_state = self.service_state.get()
        if code != '[PASS]':
            return (code, {})
        code, current_mobile_data_enabled = self.mobile_data_enabled.get()
        if code != '[PASS]':
            return (code, {})
        code, roaming_enabled = self.data_roaming_enabled.get()
        if code != '[PASS]':
            return (code, {})
        code, signal_strength = self.signal_strength_percent.get()
        if code != '[PASS]':
            return (code, {})
        code, upstream = self.upstream_network.get()
        if code != '[PASS]':
            return (code, {})
        locally_eligible = value and sim_state == 'ready' and (service_state != 'unavailable') and (signal_strength > 0) and (service_state != 'roaming' or roaming_enabled)
        code = self.mobile_data_enabled.set(value)
        if code != '[PASS]':
            return (code, {})
        if not locally_eligible:
            code = self.cellular_link_state.internal_set('disconnected')
            if code != '[PASS]':
                return (code, {})
            if upstream == 'cellular':
                code = self.upstream_network.internal_set('none')
                if code != '[PASS]':
                    return (code, {})
                code = self.internet_available.internal_set(False)
                if code != '[PASS]':
                    return (code, {})
            elif upstream == 'none':
                code = self.internet_available.internal_set(False)
                if code != '[PASS]':
                    return (code, {})
        return ('[PASS]', {})

    def get_data_roaming_enabled(self) -> tuple[str, dict]:
        """
        Return whether cellular data use is permitted while roaming. This permission is independent of the current service state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- data_roaming_enabled: Current data-roaming permission. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.data_roaming_enabled.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'data_roaming_enabled': value})

    def set_data_roaming_enabled(self, value: bool) -> tuple[str, dict]:
        """
        Permit or deny cellular data use while roaming. If service is currently roaming, denying permission immediately disconnects an existing cellular link and clears cellular-derived upstream and internet feedback while preserving any Wi-Fi upstream. This setting does not make the phone enter or leave roaming service. Invalid input is rejected and leaves all state unchanged.

        Args:
        - value: Whether cellular data should be permitted while roaming.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        if not isinstance(value, bool):
            return ('[FAIL] Invalid value', {})
        code, sim_state = self.sim_state.get()
        if code != '[PASS]':
            return (code, {})
        code, service_state = self.service_state.get()
        if code != '[PASS]':
            return (code, {})
        code, mobile_data_enabled = self.mobile_data_enabled.get()
        if code != '[PASS]':
            return (code, {})
        code, current_roaming_enabled = self.data_roaming_enabled.get()
        if code != '[PASS]':
            return (code, {})
        code, signal_strength = self.signal_strength_percent.get()
        if code != '[PASS]':
            return (code, {})
        code, upstream = self.upstream_network.get()
        if code != '[PASS]':
            return (code, {})
        locally_eligible = mobile_data_enabled and sim_state == 'ready' and (service_state != 'unavailable') and (signal_strength > 0) and (service_state != 'roaming' or value)
        code = self.data_roaming_enabled.set(value)
        if code != '[PASS]':
            return (code, {})
        if not locally_eligible:
            code = self.cellular_link_state.internal_set('disconnected')
            if code != '[PASS]':
                return (code, {})
            if upstream == 'cellular':
                code = self.upstream_network.internal_set('none')
                if code != '[PASS]':
                    return (code, {})
                code = self.internet_available.internal_set(False)
                if code != '[PASS]':
                    return (code, {})
            elif upstream == 'none':
                code = self.internet_available.internal_set(False)
                if code != '[PASS]':
                    return (code, {})
        return ('[PASS]', {})

    def get_signal_strength_percent(self) -> tuple[str, dict]:
        """
        Return the current normalized cellular signal-strength feedback from 0 through 100 percent without changing connectivity.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- signal_strength_percent: Current normalized cellular signal strength percentage. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.signal_strength_percent.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'signal_strength_percent': value})

    def get_cellular_link_state(self) -> tuple[str, dict]:
        """
        Return the current read-only cellular data link state. This feedback is distinct from the mobile-data switch.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- cellular_link_state: Current cellular link state. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.cellular_link_state.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'cellular_link_state': value})

    def get_upstream_network(self) -> tuple[str, dict]:
        """
        Return the phone's current aggregated upstream selection as none, cellular, or wifi. This query does not modify Wi-Fi or cellular state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- upstream_network: Current aggregated upstream network selection. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.upstream_network.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'upstream_network': value})

    def get_internet_available(self) -> tuple[str, dict]:
        """
        Return whether internet access is currently available through the deterministically selected upstream network.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- internet_available: Whether internet access is currently available through the selected upstream. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.internet_available.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'internet_available': value})

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        After a successful setting change, immediately disconnects cellular feedback whenever local cellular requirements are no longer satisfied. Disabling mobile data always disconnects cellular service. Denying roaming while service is roaming also disconnects cellular service. If the removed link was the cellular upstream, the upstream becomes none and internet availability becomes false; an existing Wi-Fi upstream is preserved.

    Effect properties:
    - sim_state: SIM usability used to determine whether cellular service remains locally eligible.
    - service_state: Coverage and roaming state used to determine whether cellular service remains locally eligible.
    - mobile_data_enabled: Mobile-data request whose disabled state invalidates a cellular link.
    - data_roaming_enabled: Roaming permission required when cellular service is roaming.
    - signal_strength_percent: Cellular signal feedback whose zero value makes the cellular link locally ineligible.
    - cellular_link_state: Derived cellular link feedback cleared when local requirements fail.
    - upstream_network: Aggregated upstream selection cleared only when its invalidated source is cellular.
    - internet_available: Internet feedback cleared when no valid upstream remains.
        """
        code, sim_state = self.sim_state.get()
        if code != '[PASS]':
            return (code, [])
        code, service_state = self.service_state.get()
        if code != '[PASS]':
            return (code, [])
        code, mobile_data_enabled = self.mobile_data_enabled.get()
        if code != '[PASS]':
            return (code, [])
        code, roaming_enabled = self.data_roaming_enabled.get()
        if code != '[PASS]':
            return (code, [])
        code, signal_strength = self.signal_strength_percent.get()
        if code != '[PASS]':
            return (code, [])
        code, cellular_link_state = self.cellular_link_state.get()
        if code != '[PASS]':
            return (code, [])
        code, upstream = self.upstream_network.get()
        if code != '[PASS]':
            return (code, [])
        code, internet_available = self.internet_available.get()
        if code != '[PASS]':
            return (code, [])
        locally_eligible = mobile_data_enabled and sim_state == 'ready' and (service_state != 'unavailable') and (signal_strength > 0) and (service_state != 'roaming' or roaming_enabled)
        if not locally_eligible:
            if cellular_link_state != 'disconnected':
                code = self.cellular_link_state.internal_set('disconnected')
                if code != '[PASS]':
                    return (code, [])
            if upstream == 'cellular':
                code = self.upstream_network.internal_set('none')
                if code != '[PASS]':
                    return (code, [])
                if internet_available:
                    code = self.internet_available.internal_set(False)
                    if code != '[PASS]':
                        return (code, [])
            elif upstream == 'none' and internet_available:
                code = self.internet_available.internal_set(False)
                if code != '[PASS]':
                    return (code, [])
        return ('[PASS]', [])

    def _on_dependency_changed(self, context: dict) -> tuple[str, list[dict]]:
        """
        When airplane-mode or Wi-Fi connection dependencies change, deterministically recomputes all derived connectivity feedback. Cellular is connected only when mobile data is enabled, the SIM is ready, service is available, signal strength is positive, roaming is permitted when required, and airplane mode is disabled. An enabled Wi-Fi connection is selected before cellular; otherwise eligible cellular is selected, and no eligible link produces no upstream. Internet availability is true exactly when this recomputation selects an upstream.

    Effect properties:
    - sim_state: SIM usability required for an eligible cellular link.
    - service_state: Cellular coverage and roaming state used in cellular eligibility.
    - mobile_data_enabled: Requested mobile-data state used in cellular eligibility.
    - data_roaming_enabled: Permission required for cellular eligibility while roaming.
    - signal_strength_percent: Normalized signal feedback required to be positive for cellular eligibility.
    - cellular_link_state: Derived cellular link state recomputed from cellular settings and dependencies.
    - upstream_network: Derived aggregate upstream selected from Wi-Fi and cellular availability.
    - internet_available: Derived availability indicating whether the recomputation selected an upstream.
        """
        code, sim_state = self.sim_state.get()
        if code != '[PASS]':
            return (code, [])
        code, service_state = self.service_state.get()
        if code != '[PASS]':
            return (code, [])
        code, mobile_data_enabled = self.mobile_data_enabled.get()
        if code != '[PASS]':
            return (code, [])
        code, roaming_enabled = self.data_roaming_enabled.get()
        if code != '[PASS]':
            return (code, [])
        code, signal_strength = self.signal_strength_percent.get()
        if code != '[PASS]':
            return (code, [])
        code, current_cellular_link_state = self.cellular_link_state.get()
        if code != '[PASS]':
            return (code, [])
        code, current_upstream = self.upstream_network.get()
        if code != '[PASS]':
            return (code, [])
        code, current_internet_available = self.internet_available.get()
        if code != '[PASS]':
            return (code, [])
        airplane_mode_enabled = False
        wifi_connected = False
        dependencies = context['dependencies']
        for dependency in dependencies.values():
            has_wifi_state = 'connection_state' in dependency or 'wifi_connection_state' in dependency or 'connected' in dependency
            if 'airplane_mode_enabled' in dependency:
                airplane_mode_enabled = airplane_mode_enabled or dependency['airplane_mode_enabled'] is True
            elif 'airplane_mode' in dependency:
                airplane_mode_enabled = airplane_mode_enabled or dependency['airplane_mode'] is True
            elif 'enabled' in dependency and (not has_wifi_state):
                airplane_mode_enabled = airplane_mode_enabled or dependency['enabled'] is True
            if has_wifi_state:
                wifi_enabled = True
                if 'wifi_enabled' in dependency:
                    wifi_enabled = dependency['wifi_enabled'] is True
                elif 'enabled' in dependency:
                    wifi_enabled = dependency['enabled'] is True
                connection_active = False
                if 'connection_state' in dependency:
                    connection_active = dependency['connection_state'] == 'connected'
                elif 'wifi_connection_state' in dependency:
                    connection_active = dependency['wifi_connection_state'] == 'connected'
                elif 'connected' in dependency:
                    connection_active = dependency['connected'] is True
                if wifi_enabled and connection_active:
                    wifi_connected = True
        cellular_eligible = mobile_data_enabled and sim_state == 'ready' and (service_state != 'unavailable') and (signal_strength > 0) and (service_state != 'roaming' or roaming_enabled) and (not airplane_mode_enabled)
        new_cellular_link_state = 'connected' if cellular_eligible else 'disconnected'
        if wifi_connected:
            new_upstream = 'wifi'
        elif cellular_eligible:
            new_upstream = 'cellular'
        else:
            new_upstream = 'none'
        new_internet_available = new_upstream != 'none'
        if current_cellular_link_state != new_cellular_link_state:
            code = self.cellular_link_state.internal_set(new_cellular_link_state)
            if code != '[PASS]':
                return (code, [])
        if current_upstream != new_upstream:
            code = self.upstream_network.internal_set(new_upstream)
            if code != '[PASS]':
                return (code, [])
        if current_internet_available != new_internet_available:
            code = self.internet_available.internal_set(new_internet_available)
            if code != '[PASS]':
                return (code, [])
        return ('[PASS]', [])
