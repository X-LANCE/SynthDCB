# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class CatLitterBox:
    """
    CatLitterBox
    Description: Cat litter box. Users can query and set the cleaning mode and can perform cleaning and litter-replacement actions.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, cleaning_mode: str = None, operation_status: str = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the cat litter box is powered.',
            default=False
        )
        self.cleaning_mode = StringProperty(
            name='cleaning_mode',
            description='Cleaning mode used when a cleaning action is started.',
            default='automatic',
            choices=['automatic', 'manual']
        )
        self.operation_status = StringProperty(
            name='operation_status',
            description='Current litter box operation status. This status persists while the device is powered off; the active operation is paused while powered off and remains in the same status when power is restored.',
            default='idle',
            mode=2,
            choices=['idle', 'cleaning', 'replacing_litter']
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if cleaning_mode is not None: code = self.cleaning_mode.internal_set(cleaning_mode)
        if operation_status is not None: code = self.operation_status.internal_set(operation_status)
        self._power_managed_properties = (self.cleaning_mode, self.operation_status,)
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

    def get_cleaning_mode(self) -> tuple[str, dict]:
        """
        Return the configured cleaning mode. The device must be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- cleaning_mode: Configured cleaning mode. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.cleaning_mode.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"cleaning_mode": value}

    def set_cleaning_mode(self, value: str) -> tuple[str, dict]:
        """
        Set the cleaning mode to automatic or manual. The device must be powered on. Invalid input leaves the setting unchanged.

        Args:
        - value: Cleaning mode to configure. (choices=['automatic', 'manual'])

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
        if type(value) is not str or value not in ("automatic", "manual"):
            return "[INVALID_MODE]", {}
        code = self.cleaning_mode.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_operation_status(self) -> tuple[str, dict]:
        """
        Return the current cleaning or litter-replacement status. The device must be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- operation_status: Current operation status. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.operation_status.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"operation_status": value}

    def start_cleaning(self) -> tuple[str, dict]:
        """
        Start a cleaning operation using the configured cleaning mode. The device must be powered on and idle.

        Args:
        (no arguments required)

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
        code, status = self.operation_status.get()
        if code != "[PASS]":
            return code, {}
        if status != "idle":
            return "[BUSY]", {}
        code = self.operation_status.internal_set("cleaning")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def replace_litter(self) -> tuple[str, dict]:
        """
        Start a litter-replacement operation. The device must be powered on and idle.

        Args:
        - (no arguments required)

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
        code, status = self.operation_status.get()
        if code != "[PASS]":
            return code, {}
        if status != "idle":
            return "[BUSY]", {}
        code = self.operation_status.internal_set("replacing_litter")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def stop_operation(self) -> tuple[str, dict]:
        """
        Stop the active cleaning or litter-replacement operation and return the device to idle. The device must be powered on.

        Args:
        (no arguments required)

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
        code, status = self.operation_status.get()
        if code != "[PASS]":
            return code, {}
        if status == "idle":
            return "[NOT_RUNNING]", {}
        code = self.operation_status.internal_set("idle")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}