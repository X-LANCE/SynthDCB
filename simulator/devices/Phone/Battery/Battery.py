# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Battery:
    """
    Battery
    Description: Battery and power-saving settings, placed in Setting and contained by System. Supports querying battery percentage, charging state, external power connection, and battery temperature, enabling/disabling power-saving mode, and querying its effective state. Battery level, temperature, and charging state are read-only feedback that changes with simulation time and power conditions; setters cannot specify target measured values. Switching power-saving mode does not instantly change battery level. Charging is determined by external power and system protection conditions. Power-supply restrictions on power-saving mode are defined by a fixed simulation policy.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, battery_percent: float = None, charging_state: str = None, external_power_connected: bool = None, battery_temperature_celsius: float = None, power_saving_mode: bool = None, power_saving_effective: bool = None) -> None:
        # define properties
        self.battery_percent = FloatProperty(
            name='battery_percent',
            description='Read-only remaining battery charge as a percentage. Simulation ticks increase it while charging and decrease it while discharging.',
            default=80.0,
            mode=2,
            unit='percent',
            minimum=0.0,
            maximum=100.0,
            step=0.1,
            step_origin=0.0,
            precision=1
        )
        self.charging_state = StringProperty(
            name='charging_state',
            description='Read-only charging result. Discharging means external power is absent; charging means external power is present and charging is permitted; full means the externally powered battery is at 100 percent; not_charging means external power is present but temperature protection prevents charging.',
            default='discharging',
            mode=2,
            choices=['discharging', 'charging', 'full', 'not_charging']
        )
        self.external_power_connected = BoolProperty(
            name='external_power_connected',
            description='Read-only feedback indicating whether an external power supply is connected. This condition may be configured by the simulation world but cannot be changed through Battery tools.',
            default=False,
            mode=2
        )
        self.battery_temperature_celsius = FloatProperty(
            name='battery_temperature_celsius',
            description='Read-only simulated battery temperature in degrees Celsius. Temperature moves toward 35 degrees while charging and toward 25 degrees otherwise.',
            default=25.0,
            mode=2,
            unit='celsius',
            minimum=-20.0,
            maximum=60.0,
            step=0.1,
            step_origin=-20.0,
            precision=1
        )
        self.power_saving_mode = BoolProperty(
            name='power_saving_mode',
            description='User-requested power-saving mode. The request persists while external power is connected, but the fixed simulation policy prevents it from becoming effective on external power.',
            default=False
        )
        self.power_saving_effective = BoolProperty(
            name='power_saving_effective',
            description='Read-only effective power-saving state. It is true exactly when power-saving mode is requested and external power is not connected.',
            default=False,
            mode=2
        )

        # initialize properties
        if battery_percent is not None: code = self.battery_percent.internal_set(battery_percent)
        if charging_state is not None: code = self.charging_state.internal_set(charging_state)
        if external_power_connected is not None: code = self.external_power_connected.internal_set(external_power_connected)
        if battery_temperature_celsius is not None: code = self.battery_temperature_celsius.internal_set(battery_temperature_celsius)
        if power_saving_mode is not None: code = self.power_saving_mode.internal_set(power_saving_mode)
        if power_saving_effective is not None: code = self.power_saving_effective.internal_set(power_saving_effective)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_battery_percent(self) -> tuple[str, dict]:
        """
        Return the current read-only battery percentage without changing battery feedback or settings.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- battery_percent: Current battery charge from 0.0 through 100.0 percent. (type=number)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.battery_percent.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'battery_percent': value
        }
        return code, response

    def get_charging_state(self) -> tuple[str, dict]:
        """
        Return the current read-only charging result without changing any battery state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- charging_state: Current charging result: discharging, charging, full, or not_charging. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.charging_state.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'charging_state': value
        }
        return code, response

    def get_external_power_connected(self) -> tuple[str, dict]:
        """
        Return whether an external power supply is currently connected. This read-only feedback cannot be changed with Battery tools.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- external_power_connected: Whether external power is connected. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.external_power_connected.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'external_power_connected': value
        }
        return code, response

    def get_battery_temperature_celsius(self) -> tuple[str, dict]:
        """
        Return the current read-only simulated battery temperature in degrees Celsius without changing it.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- battery_temperature_celsius: Current simulated battery temperature in degrees Celsius. (type=number)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.battery_temperature_celsius.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'battery_temperature_celsius': value
        }
        return code, response

    def get_power_saving_mode(self) -> tuple[str, dict]:
        """
        Return whether power-saving mode is requested. This may differ from its effective state while external power is connected.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- power_saving_mode: Whether power-saving mode is requested. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.power_saving_mode.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'power_saving_mode': value
        }
        return code, response

    def set_power_saving_mode(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable the power-saving request. The request is accepted on or off external power, but it is effective only while external power is disconnected. After the request changes, the effective state is recomputed from the request and external power condition. This operation does not immediately change battery percentage, temperature, or charging state. Invalid input is rejected and leaves state unchanged.

        Args:
        - value: Desired power-saving request.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        if type(value) is not bool:
            return '[INVALID_ARGUMENT]', {}

        code, external_power = self.external_power_connected.get()
        if code != '[PASS]':
            return code, {}

        code = self.power_saving_mode.set(value)
        if code != '[PASS]':
            return code, {}

        effective = value and not external_power
        code = self.power_saving_effective.internal_set(effective)
        if code != '[PASS]':
            return code, {}

        return '[PASS]', {}

    def get_power_saving_effective(self) -> tuple[str, dict]:
        """
        Return whether power-saving mode is currently effective under the fixed supply policy. It is effective exactly when requested and external power is disconnected.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- power_saving_effective: Whether power-saving mode is currently effective. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.power_saving_effective.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'power_saving_effective': value
        }
        return code, response

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        For each elapsed simulation minute, first applies the fixed supply policy so power saving is effective only when requested without external power. When external power is absent, battery charge decreases by 0.1 percentage point per minute if power saving is effective and by 0.2 otherwise. When external power is present, the battery is below 100 percent, and temperature is from 0.0 through 45.0 degrees Celsius inclusive, charge increases by 0.5 percentage point per minute. External power supplies no charge outside that temperature range. Charge is clamped from 0.0 through 100.0 percent. Temperature moves by up to 0.2 degrees per minute toward 35.0 while charging and by up to 0.1 degrees per minute toward 25.0 otherwise. The final charging state is discharging without external power, full at 100 percent on external power, charging when connected and temperature permits charging, and not_charging when connected but temperature protection blocks charging.

    Effect properties:
    - battery_percent: Current charge used as the starting value for deterministic charging or discharging.
    - charging_state: Read-only charging result updated from the final supply, charge, and protection conditions.
    - external_power_connected: External supply condition that determines whether charging or discharging is possible.
    - battery_temperature_celsius: Battery temperature used by charging protection and updated toward the applicable thermal target.
    - power_saving_mode: Requested power-saving setting used to determine effective power saving.
    - power_saving_effective: Effective power-saving state used to select the disconnected discharge rate.
        """
        code, battery_percent = self.battery_percent.get()
        if code != '[PASS]':
            return code, []

        code, external_power = self.external_power_connected.get()
        if code != '[PASS]':
            return code, []

        code, temperature = self.battery_temperature_celsius.get()
        if code != '[PASS]':
            return code, []

        code, power_saving_mode = self.power_saving_mode.get()
        if code != '[PASS]':
            return code, []

        effective = power_saving_mode and not external_power
        minutes = context['minutes']

        for _ in range(minutes):
            effective = power_saving_mode and not external_power
            temperature_permits_charging = 0.0 <= temperature <= 45.0
            charging_this_minute = (
                external_power
                and battery_percent < 100.0
                and temperature_permits_charging
            )

            if charging_this_minute:
                battery_percent = min(100.0, battery_percent + 0.5)
            elif not external_power:
                discharge_rate = 0.1 if effective else 0.2
                battery_percent = max(0.0, battery_percent - discharge_rate)

            if charging_this_minute:
                if temperature < 35.0:
                    temperature = min(35.0, temperature + 0.2)
                elif temperature > 35.0:
                    temperature = max(35.0, temperature - 0.2)
            else:
                if temperature < 25.0:
                    temperature = min(25.0, temperature + 0.1)
                elif temperature > 25.0:
                    temperature = max(25.0, temperature - 0.1)

            battery_percent = round(battery_percent, 1)
            temperature = round(temperature, 1)

        if not external_power:
            final_charging_state = 'discharging'
        elif battery_percent >= 100.0:
            final_charging_state = 'full'
        elif 0.0 <= temperature <= 45.0:
            final_charging_state = 'charging'
        else:
            final_charging_state = 'not_charging'

        code = self.power_saving_effective.internal_set(effective)
        if code != '[PASS]':
            return code, []

        code = self.battery_percent.internal_set(battery_percent)
        if code != '[PASS]':
            return code, []

        code = self.battery_temperature_celsius.internal_set(temperature)
        if code != '[PASS]':
            return code, []

        code = self.charging_state.internal_set(final_charging_state)
        if code != '[PASS]':
            return code, []

        return '[PASS]', []

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        After a successful power-saving setting change, immediately recomputes the effective state under the fixed policy: power saving is effective exactly when it is requested and external power is disconnected. This recalculation does not alter battery percentage, temperature, or charging state.

    Effect properties:
    - external_power_connected: External supply condition that suppresses effective power saving while connected.
    - power_saving_mode: Requested power-saving setting.
    - power_saving_effective: Read-only effective state recalculated after the setting changes.
        """
        code, external_power = self.external_power_connected.get()
        if code != '[PASS]':
            return code, []

        code, power_saving_mode = self.power_saving_mode.get()
        if code != '[PASS]':
            return code, []

        effective = power_saving_mode and not external_power
        code = self.power_saving_effective.internal_set(effective)
        if code != '[PASS]':
            return code, []

        return '[PASS]', []