# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class ExternalPowerSupply:
    """
    ExternalPowerSupply
    Description: Vehicle external power supply module. Supports starting and stopping output, setting a reserve battery threshold, and querying actual output power, connection state, and protection reasons. Starting requires a connected external load and sufficient energy conditions. Output stops when the reserve threshold or a protection condition is reached.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, output_active: bool = None, reserve_percent: int = None, output_power: int = None, load_connected: bool = None, battery_percent: int = None, load_power_demand: int = None, protection_reason: str = None) -> None:
        # define properties
        self.output_active = BoolProperty(
            name='output_active',
            description='Whether the module is currently supplying external power.',
            default=False,
            mode=2
        )
        self.reserve_percent = IntProperty(
            name='reserve_percent',
            description='Battery percentage reserved from external discharge. Output cannot operate when battery_percent is at or below this threshold.',
            default=20,
            unit='percent',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.output_power = IntProperty(
            name='output_power',
            description='Actual measured external output power. It equals load_power_demand while output is active and permitted, and is zero while output is stopped.',
            default=0,
            mode=2,
            unit='W',
            minimum=0,
            maximum=6000,
            step=1,
            step_origin=0
        )
        self.load_connected = BoolProperty(
            name='load_connected',
            description='Whether an external electrical load is currently connected.',
            default=False,
            mode=2
        )
        self.battery_percent = IntProperty(
            name='battery_percent',
            description='Current vehicle battery percentage used to enforce the external-discharge reserve threshold.',
            default=60,
            mode=2,
            unit='percent',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.load_power_demand = IntProperty(
            name='load_power_demand',
            description="Power requested by the connected external load, bounded by this simulated module's 6000 W rating.",
            default=0,
            mode=2,
            unit='W',
            minimum=0,
            maximum=6000,
            step=1,
            step_origin=0
        )
        self.protection_reason = StringProperty(
            name='protection_reason',
            description='Current condition that blocks or stopped external output. Reserve protection is derived from battery_percent and reserve_percent; other conditions are supplied by deterministic feedback.',
            default='none',
            mode=2,
            choices=['none', 'reserve_threshold_reached', 'insufficient_energy', 'overload', 'overtemperature', 'system_fault']
        )

        # initialize properties
        if output_active is not None: code = self.output_active.internal_set(output_active)
        if reserve_percent is not None: code = self.reserve_percent.internal_set(reserve_percent)
        if output_power is not None: code = self.output_power.internal_set(output_power)
        if load_connected is not None: code = self.load_connected.internal_set(load_connected)
        if battery_percent is not None: code = self.battery_percent.internal_set(battery_percent)
        if load_power_demand is not None: code = self.load_power_demand.internal_set(load_power_demand)
        if protection_reason is not None: code = self.protection_reason.internal_set(protection_reason)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_output_active(self) -> tuple[str, dict]:
        """
        Return whether external power is currently being supplied.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- output_active: Whether external power output is active. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.output_active.get()
        if code != '[PASS]':
            return code, {}
        return code, {'output_active': value}

    def get_reserve_percent(self) -> tuple[str, dict]:
        """
        Return the configured external-discharge battery reserve threshold.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- reserve_percent: Configured battery reserve threshold in percent. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.reserve_percent.get()
        if code != '[PASS]':
            return code, {}
        return code, {'reserve_percent': value}

    def set_reserve_percent(self, value: int) -> tuple[str, dict]:
        """
        Set the reserve threshold to an integer from 0 through 100 percent. After assignment, if battery_percent is at or below the new threshold, active output stops, output_power becomes zero, and protection_reason becomes reserve_threshold_reached unless another reported protection reason is already active. If the battery is above the new threshold and the previous reason was reserve_threshold_reached, that reason is cleared to none; output does not restart automatically. Invalid input leaves all state unchanged.

        Args:
        - value: Desired reserve threshold in percent. (min=0, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - INVALID_INPUT_ERROR: Reserve percentage must be an integer from 0 through 100.
        """
        if type(value) is not int or value < 0 or value > 100:
            return '[INVALID_INPUT_ERROR]', {}

        battery_code, battery = self.battery_percent.get()
        if battery_code != '[PASS]':
            return battery_code, {}

        reason_code, current_reason = self.protection_reason.get()
        if reason_code != '[PASS]':
            return reason_code, {}

        resulting_reason = current_reason
        must_stop = battery <= value

        if must_stop:
            if current_reason in ('none', 'reserve_threshold_reached'):
                resulting_reason = 'reserve_threshold_reached'
        elif current_reason == 'reserve_threshold_reached':
            resulting_reason = 'none'

        code = self.reserve_percent.set(value)
        if code != '[PASS]':
            return code, {}

        if resulting_reason != current_reason:
            code = self.protection_reason.internal_set(resulting_reason)
            if code != '[PASS]':
                return code, {}

        if must_stop:
            code = self.output_active.internal_set(False)
            if code != '[PASS]':
                return code, {}
            code = self.output_power.internal_set(0)
            if code != '[PASS]':
                return code, {}

        return '[PASS]', {}

    def get_output_power(self) -> tuple[str, dict]:
        """
        Return actual measured external output power in watts. Stopped output always reports zero.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- output_power: Actual external output power from 0 through 6000 W. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.output_power.get()
        if code != '[PASS]':
            return code, {}
        return code, {'output_power': value}

    def get_load_connected(self) -> tuple[str, dict]:
        """
        Return whether an external electrical load is connected.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- load_connected: Whether an external load is connected. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.load_connected.get()
        if code != '[PASS]':
            return code, {}
        return code, {'load_connected': value}

    def get_battery_percent(self) -> tuple[str, dict]:
        """
        Return the battery percentage currently used for reserve-threshold protection.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- battery_percent: Current battery percentage. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.battery_percent.get()
        if code != '[PASS]':
            return code, {}
        return code, {'battery_percent': value}

    def get_load_power_demand(self) -> tuple[str, dict]:
        """
        Return the power currently requested by the connected external load.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- load_power_demand: Connected-load power demand from 0 through 6000 W. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.load_power_demand.get()
        if code != '[PASS]':
            return code, {}
        return code, {'load_power_demand': value}

    def get_protection_reason(self) -> tuple[str, dict]:
        """
        Return the current energy or protection condition blocking external output. A value of none means no energy or protection restriction is active.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- protection_reason: Current output protection reason. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.protection_reason.get()
        if code != '[PASS]':
            return code, {}
        return code, {'protection_reason': value}

    def report_feedback(self, load_connected: bool, battery_percent: int, load_power_demand: int, protection_reason: str) -> tuple[str, dict]:
        """
        Apply one complete deterministic feedback sample. The supplied connection, battery percentage, and load demand replace their previous values. A supplied protection reason other than none takes priority; otherwise protection_reason becomes reserve_threshold_reached when battery_percent is at or below reserve_percent, or none when it is above the threshold. If output is active, it remains active with output_power equal to load_power_demand only when the load is connected and the resulting protection reason is none. Otherwise output stops and output_power becomes zero. Inactive output remains stopped with zero output power. Invalid input leaves all state unchanged.

        Args:
        - load_connected: Whether the external load is connected.
        - battery_percent: Current battery percentage. (min=0, max=100)
        - load_power_demand: Current connected-load demand in watts. (min=0, max=6000)
        - protection_reason: Reported non-reserve protection condition. (choices=['none', 'insufficient_energy', 'overload', 'overtemperature', 'system_fault'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - INVALID_INPUT_ERROR: Feedback values must satisfy their declared types and ranges.
        """
        valid_reasons = (
            'none',
            'insufficient_energy',
            'overload',
            'overtemperature',
            'system_fault'
        )
        if type(load_connected) is not bool:
            return '[INVALID_INPUT_ERROR]', {}
        if type(battery_percent) is not int or battery_percent < 0 or battery_percent > 100:
            return '[INVALID_INPUT_ERROR]', {}
        if type(load_power_demand) is not int or load_power_demand < 0 or load_power_demand > 6000:
            return '[INVALID_INPUT_ERROR]', {}
        if type(protection_reason) is not str or protection_reason not in valid_reasons:
            return '[INVALID_INPUT_ERROR]', {}

        reserve_code, reserve = self.reserve_percent.get()
        if reserve_code != '[PASS]':
            return reserve_code, {}

        active_code, currently_active = self.output_active.get()
        if active_code != '[PASS]':
            return active_code, {}

        if protection_reason != 'none':
            resulting_reason = protection_reason
        elif battery_percent <= reserve:
            resulting_reason = 'reserve_threshold_reached'
        else:
            resulting_reason = 'none'

        remains_active = (
            currently_active
            and load_connected
            and resulting_reason == 'none'
        )
        resulting_power = load_power_demand if remains_active else 0

        code = self.load_connected.internal_set(load_connected)
        if code != '[PASS]':
            return code, {}

        code = self.battery_percent.internal_set(battery_percent)
        if code != '[PASS]':
            return code, {}

        code = self.load_power_demand.internal_set(load_power_demand)
        if code != '[PASS]':
            return code, {}

        code = self.protection_reason.internal_set(resulting_reason)
        if code != '[PASS]':
            return code, {}

        code = self.output_active.internal_set(remains_active)
        if code != '[PASS]':
            return code, {}

        code = self.output_power.internal_set(resulting_power)
        if code != '[PASS]':
            return code, {}

        return '[PASS]', {}

    def start_output(self) -> tuple[str, dict]:
        """
        Start external power output. The action succeeds only while output is stopped, a load is connected, and protection_reason is none. A none protection reason establishes that the latest battery feedback is above reserve_percent and no other reported protection condition is active. On success, output_active becomes true and output_power becomes the current load_power_demand. A rejected request leaves all state unchanged.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: Output must be stopped, a load must be connected, and protection_reason must be none.
        """
        active_code, active = self.output_active.get()
        if active_code != '[PASS]':
            return active_code, {}

        connected_code, connected = self.load_connected.get()
        if connected_code != '[PASS]':
            return connected_code, {}

        reason_code, reason = self.protection_reason.get()
        if reason_code != '[PASS]':
            return reason_code, {}

        demand_code, demand = self.load_power_demand.get()
        if demand_code != '[PASS]':
            return demand_code, {}

        if active or not connected or reason != 'none':
            return '[PRECONDITION_FAILED]', {}

        code = self.output_active.internal_set(True)
        if code != '[PASS]':
            return code, {}

        code = self.output_power.internal_set(demand)
        if code != '[PASS]':
            return code, {}

        return '[PASS]', {}

    def stop_output(self) -> tuple[str, dict]:
        """
        Stop external power output from any state and set measured output power to zero. Reserve configuration and feedback states are preserved.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.output_active.internal_set(False)
        if code != '[PASS]':
            return code, {}

        code = self.output_power.internal_set(0)
        if code != '[PASS]':
            return code, {}

        return '[PASS]', {}