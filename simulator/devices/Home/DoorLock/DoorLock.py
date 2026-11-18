# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class DoorLock:
    """
    DoorLock
    Description: Smart door lock. Users can query the lock's open or closed state and perform lock and unlock actions. The device provides multiple identity-verification methods and allows individual methods to be enabled or disabled.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, lock_state: str = None, verification_methods: dict = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the door lock is powered and available for public operation.',
            default=False
        )
        self.lock_state = StringProperty(
            name='lock_state',
            description='Current lock state.',
            default='locked',
            mode=2,
            choices=['locked', 'unlocked']
        )
        self.verification_methods = DictProperty(
            name='verification_methods',
            description='Identity-verification methods and whether each method is enabled.',
            default={'fingerprint': {'enabled': True}, 'pin': {'enabled': True}, 'card': {'enabled': True}, 'mobile_credential': {'enabled': True}},
            mode=2
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if lock_state is not None: code = self.lock_state.internal_set(lock_state)
        if verification_methods is not None: code = self.verification_methods.internal_set(verification_methods)
        self._power_managed_properties = (self.lock_state, self.verification_methods,)
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

    def get_lock_state(self) -> tuple[str, dict]:
        """
        Return the current lock state. This operation fails while the door lock is powered off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- lock_state: The current lock state, either locked or unlocked. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.lock_state.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"lock_state": value}

    def lock(self) -> tuple[str, dict]:
        """
        Lock the door. If it is already locked, the operation succeeds without changing state. This operation fails while powered off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- lock_state: The resulting lock state. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, current_state = self.lock_state.get()
        if code != "[PASS]":
            return code, {}
        if current_state == "locked":
            return "[PASS]", {"lock_state": current_state}
        code = self.lock_state.internal_set("locked")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"lock_state": "locked"}

    def unlock(self) -> tuple[str, dict]:
        """
        Unlock the door. If it is already unlocked, the operation succeeds without changing state. This operation fails while powered off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- lock_state: The resulting lock state. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, current_state = self.lock_state.get()
        if code != "[PASS]":
            return code, {}
        if current_state == "unlocked":
            return "[PASS]", {"lock_state": current_state}
        code = self.lock_state.internal_set("unlocked")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"lock_state": "unlocked"}

    def get_verification_methods(self) -> tuple[str, dict]:
        """
        Return all configured identity-verification methods and their enabled states. This operation fails while powered off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- verification_methods: Mapping of verification method identifiers to records containing an enabled boolean. (type=object)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.verification_methods.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"verification_methods": value}

    def set_verification_method_enabled(self, method_id: str, enabled: bool) -> tuple[str, dict]:
        """
        Enable or disable one existing identity-verification method. Unknown method identifiers fail without changing state. This operation fails while powered off.

        Args:
        - method_id: Existing verification method identifier, such as fingerprint, pin, card, or mobile_credential.
        - enabled: Whether the selected verification method should be enabled.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- method_id: The updated verification method identifier. (type=string)
        	- enabled: The resulting enabled state. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        if type(method_id) is not str or type(enabled) is not bool:
            return "[ERROR] Invalid argument.", {}
        code, methods = self.verification_methods.get()
        if code != "[PASS]":
            return code, {}
        if method_id not in methods:
            return "[ERROR] Unknown verification method.", {}
        updated_methods = dict(methods)
        updated_record = dict(methods[method_id])
        updated_record["enabled"] = enabled
        updated_methods[method_id] = updated_record
        code = self.verification_methods.internal_set(updated_methods)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"method_id": method_id, "enabled": enabled}