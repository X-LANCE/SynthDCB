# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..AirConditioner import AirConditioner

class CoolingOnlyAirConditioner(AirConditioner):
    """
    CoolingOnlyAirConditioner
    Description: A cooling-only air-conditioner subclass. It inherits the base air conditioner's cooling, fan, dehumidification, and automatic-mode capabilities but does not provide heating, auxiliary heating, or related operations. The device produces no heating effect in its space.
    Version: 1.0.0
    Base: AirConditioner
    """

    def __init__(self, operating_mode: str = None, target_temperature: float = None, *, power: bool | None = None, _defer_power_init: bool = False, **base_kwargs) -> None:
        _power_init_value = power if power is not None else False
        # initialize base AirConditioner class
        super().__init__(power=_power_init_value, _defer_power_init=True, **base_kwargs)
        # define properties
        self.operating_mode = StringProperty(
            name='operating_mode',
            description='The operating mode. Cooling regulates temperature, dehumidification reduces humidity, fan circulates air without directly changing temperature or humidity, and automatic operation cools when the room is above the target without providing heating.',
            default='cool',
            choices=['cool', 'fan', 'dry', 'auto']
        )
        self.target_temperature = FloatProperty(
            name='target_temperature',
            description='The desired room temperature in degrees Celsius. It is used by cooling and automatic modes and cannot be changed in dry or fan mode.',
            default=22.0,
            unit='degC',
            minimum=16.0,
            maximum=30.0,
            step=0.5,
            step_origin=16.0,
            precision=1
        )

        # initialize properties
        if operating_mode is not None: code = self.operating_mode.internal_set(operating_mode)
        if target_temperature is not None: code = self.target_temperature.internal_set(target_temperature)

        # disable inherited properties
        self.auxiliary_heating.chmod(0)
        self._power_managed_properties = (self.operating_mode, self.target_temperature, self.fan_speed, self.swing_direction, self.sleep_mode,)
        self._power_initialized = False
        self._disabled = {
            'properties': ['auxiliary_heating'],
            'functions': ['get_auxiliary_heating', 'set_auxiliary_heating'],
            'events': ['after_action']
        }

        if not _defer_power_init:
            self.set_power(_power_init_value)

    def set_operating_mode(self, value: str) -> tuple[str, dict]:
        """
        Set the operating mode while powered. Supported modes are cool, fan, dry, and auto. Automatic operation never provides heating.

        Args:
        - value: Operating mode. (choices=['cool', 'fan', 'dry', 'auto'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing the return code and response data (type=dict)
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        if value not in ("cool", "fan", "dry", "auto"):
            return "[ERROR] INVALID_MODE", {}
        code = self.operating_mode.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_target_temperature(self) -> tuple[str, dict]:
        """
        Return the target temperature while powered and in cool or auto mode.
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        code, mode = self.operating_mode.get()
        if code != "[PASS]":
            return code, {}
        if mode not in ("cool", "auto"):
            return "[ERROR] INVALID_MODE", {}
        code, value = self.target_temperature.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"target_temperature": value}

    def set_target_temperature(self, value: float) -> tuple[str, dict]:
        """
        Set the target temperature while powered in cool or auto mode. It cannot be set in dry or fan mode.
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        code, mode = self.operating_mode.get()
        if code != "[PASS]":
            return code, {}
        if mode not in ("cool", "auto"):
            return "[ERROR] INVALID_MODE", {}
        code = self.target_temperature.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def increase_target_temperature(self) -> tuple[str, dict]:
        """
        Increase the target temperature by 0.5 degrees Celsius while powered in cool or auto mode, without exceeding 30 degrees Celsius.
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        code, mode = self.operating_mode.get()
        if code != "[PASS]":
            return code, {}
        if mode not in ("cool", "auto"):
            return "[ERROR] INVALID_MODE", {}
        code, value = self.target_temperature.get()
        if code != "[PASS]":
            return code, {}
        code = self.target_temperature.set(min(30.0, value + 0.5))
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def decrease_target_temperature(self) -> tuple[str, dict]:
        """
        Decrease the target temperature by 0.5 degrees Celsius while powered in cool or auto mode, without going below 16 degrees Celsius.
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        code, mode = self.operating_mode.get()
        if code != "[PASS]":
            return code, {}
        if mode not in ("cool", "auto"):
            return "[ERROR] INVALID_MODE", {}
        code, value = self.target_temperature.get()
        if code != "[PASS]":
            return code, {}
        code = self.target_temperature.set(max(16.0, value - 0.5))
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        While powered, cool the room toward the target in cool mode and in automatic operation when the room is above the target, or reduce room humidity in dry operation. Automatic operation never heats the room. Fan operation does not directly change temperature or humidity. When unpowered, emit zero contributions.

        Effect properties:
        - power: Whether the air conditioner is powered.
        - operating_mode: Current operating mode.
        - target_temperature: Desired room temperature for cooling operation.
        - fan_speed: Current fan speed.
        """
        code, power = self.power.get()
        if code != "[PASS]":
            return code, []
        if power is not True:
            return "[PASS]", []

        code, mode = self.operating_mode.get()
        if code != "[PASS]":
            return code, []
        code, target_temperature = self.target_temperature.get()
        if code != "[PASS]":
            return code, []
        code, fan_speed = self.fan_speed.get()
        if code != "[PASS]":
            return code, []

        if mode == "fan":
            return "[PASS]", []

        if mode == "dry":
            if context["space_state"]["humidity"] <= 50:
                return "[PASS]", []
            return "[PASS]", [{
                "trigger": "tick",
                "source": context["object_id"],
                "target": context["space_id"],
                "function": "approach",
                "parameters": {
                    "property": "humidity",
                    "value": 50,
                    "rate_per_minute": 2,
                    "unit": "%RH"
                }
            }]

        room_temperature = context["space_state"]["temperature"]
        if room_temperature <= target_temperature:
            return "[PASS]", []

        rate = {
            "low": 0.2,
            "medium": 0.4,
            "high": 0.6,
            "auto": 0.4
        }[fan_speed]

        return "[PASS]", [{
            "trigger": "tick",
            "source": context["object_id"],
            "target": context["space_id"],
            "function": "approach",
            "parameters": {
                "property": "temperature",
                "value": target_temperature,
                "rate_per_minute": rate,
                "unit": "degC"
            }
        }]

    def get_auxiliary_heating(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'get_auxiliary_heating' is disabled in CoolingOnlyAirConditioner.", {}

    def set_auxiliary_heating(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'set_auxiliary_heating' is disabled in CoolingOnlyAirConditioner.", {}

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        Disabled event for this device class.
        """
        return "[DISABLED_EVENT]", []