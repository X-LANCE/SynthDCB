# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Humidifier:
    """
    Humidifier
    Description: Humidifier. Users can query and set power, sleep mode, target humidity, and humidification intensity. When the device is on and the humidity of its space is below the target, it gradually increases humidity according to the humidification intensity; it produces no further humidification effect when turned off or when the space has reached the target humidity. Current space humidity is provided by the containing space.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, sleep_mode: bool = None, target_humidity: int = None, humidification_intensity: str = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the humidifier is powered.',
            default=False
        )
        self.sleep_mode = BoolProperty(
            name='sleep_mode',
            description='Whether sleep mode is enabled.',
            default=False
        )
        self.target_humidity = IntProperty(
            name='target_humidity',
            description='Desired humidity for the containing space.',
            default=50,
            unit='%RH',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.humidification_intensity = StringProperty(
            name='humidification_intensity',
            description='Humidification output intensity.',
            default='medium',
            choices=['low', 'medium', 'high']
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if sleep_mode is not None: code = self.sleep_mode.internal_set(sleep_mode)
        if target_humidity is not None: code = self.target_humidity.internal_set(target_humidity)
        if humidification_intensity is not None: code = self.humidification_intensity.internal_set(humidification_intensity)
        self._power_managed_properties = (self.sleep_mode, self.target_humidity, self.humidification_intensity,)
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

    def get_sleep_mode(self) -> tuple[str, dict]:
        """
        Return the sleep mode setting while the humidifier is powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- sleep_mode: Whether sleep mode is enabled. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.sleep_mode.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"sleep_mode": value}

    def set_sleep_mode(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable sleep mode while the humidifier is powered.

        Args:
        - value: Requested sleep mode setting.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        if type(value) is not bool:
            return "[ERROR] INVALID_TYPE", {}
        code = self.sleep_mode.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_target_humidity(self) -> tuple[str, dict]:
        """
        Return the target humidity while the humidifier is powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- target_humidity: Configured target humidity in percent relative humidity. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.target_humidity.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"target_humidity": value}

    def set_target_humidity(self, value: int) -> tuple[str, dict]:
        """
        Set the target humidity to an integer from 0 through 100 while the humidifier is powered.

        Args:
        - value: Target humidity in percent relative humidity. (min=0, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        if type(value) is not int:
            return "[ERROR] INVALID_TYPE", {}
        if value < 0 or value > 100:
            return "[ERROR] OUT_OF_RANGE", {}
        code = self.target_humidity.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_humidification_intensity(self) -> tuple[str, dict]:
        """
        Return the humidification intensity while the humidifier is powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- humidification_intensity: Current humidification intensity. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.humidification_intensity.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"humidification_intensity": value}

    def set_humidification_intensity(self, value: str) -> tuple[str, dict]:
        """
        Set humidification intensity to low, medium, or high while the humidifier is powered.

        Args:
        - value: Requested humidification intensity. (choices=['low', 'medium', 'high'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        if type(value) is not str:
            return "[ERROR] INVALID_TYPE", {}
        if value not in ("low", "medium", "high"):
            return "[ERROR] INVALID_VALUE", {}
        code = self.humidification_intensity.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        On each tick, while powered, increase the containing space's humidity by a deterministic contribution when its current humidity is below target_humidity. The contribution is 1 percentage point at low intensity, 2 at medium intensity, and 3 at high intensity; sleep mode halves the contribution using integer reduction, with a minimum contribution of 1 while humidification is needed. Emit no humidity contribution when unpowered or when current humidity is at least target_humidity.

        Effect properties:
        - power: Whether the humidifier is powered.
        - sleep_mode: Whether sleep mode is enabled.
        - target_humidity: Desired humidity for the containing space.
        - humidification_intensity: Configured humidification output intensity.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, []
        if powered is not True:
            return "[PASS]", []

        space_state = context["space_state"]
        humidity = space_state["humidity"]

        code, target_humidity = self.target_humidity.get()
        if code != "[PASS]":
            return code, []
        if humidity >= target_humidity:
            return "[PASS]", []

        code, intensity = self.humidification_intensity.get()
        if code != "[PASS]":
            return code, []

        if intensity == "low":
            contribution = 1
        elif intensity == "medium":
            contribution = 2
        else:
            contribution = 3

        code, sleeping = self.sleep_mode.get()
        if code != "[PASS]":
            return code, []
        if sleeping is True:
            contribution = max(contribution // 2, 1)

        return "[PASS]", [{
            "trigger": "tick",
            "source": context["object_id"],
            "target": context["space_id"],
            "function": "delta",
            "parameters": {
                "property": "humidity",
                "value": contribution,
                "unit": "%RH"
            }
        }]