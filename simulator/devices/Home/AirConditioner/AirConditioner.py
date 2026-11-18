# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty


class AirConditioner:
    """
    AirConditioner
    Description: Air conditioner. It supports cooling, heating, fan, dehumidification, and automatic modes. Users can query and set the operating mode, target temperature, fan speed, swing direction, sleep mode, and auxiliary-heating state, and can incrementally raise or lower the target temperature. Target temperature is available only in operating modes that regulate temperature; temperature cannot be set in dehumidification mode; auxiliary heating is available only in modes that require heating and turns off after the room reaches the target temperature. While running, the device adjusts the temperature or humidity of its space according to the current operating mode; fan-only operation does not directly change temperature or humidity.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, operating_mode: str = None, target_temperature: float = None, fan_speed: str = None, swing_direction: str = None, sleep_mode: bool = None, auxiliary_heating: bool = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        self.power = BoolProperty(
            name='power',
            description='Whether the air conditioner is powered.',
            default=False
        )
        self.operating_mode = StringProperty(
            name='operating_mode',
            description='The operating mode. Cooling and heating regulate temperature, dehumidification reduces humidity, fan circulates air without directly changing temperature or humidity, and automatic operation selects heating or cooling based on room conditions.',
            default='cool',
            choices=['cool', 'heat', 'fan', 'dry', 'auto']
        )
        self.target_temperature = FloatProperty(
            name='target_temperature',
            description='The desired room temperature in degrees Celsius. It is used by cooling, heating, and automatic modes and cannot be changed in dry mode.',
            default=22.0,
            unit='degC',
            minimum=16.0,
            maximum=30.0,
            step=0.5,
            step_origin=16.0,
            precision=1
        )
        self.fan_speed = StringProperty(
            name='fan_speed',
            description='The indoor fan speed.',
            default='auto',
            choices=['auto', 'low', 'medium', 'high']
        )
        self.swing_direction = StringProperty(
            name='swing_direction',
            description='The airflow swing direction.',
            default='fixed',
            choices=['fixed', 'vertical', 'horizontal', 'both']
        )
        self.sleep_mode = BoolProperty(
            name='sleep_mode',
            description='Whether sleep operation is enabled.',
            default=False
        )
        self.auxiliary_heating = BoolProperty(
            name='auxiliary_heating',
            description='Whether auxiliary heating is enabled. It is available only in heat and auto modes and is turned off when the room reaches the target temperature.',
            default=False
        )
        code = self.power.internal_set(_power_init_value)

        if operating_mode is not None: code = self.operating_mode.internal_set(operating_mode)
        if target_temperature is not None: code = self.target_temperature.internal_set(target_temperature)
        if fan_speed is not None: code = self.fan_speed.internal_set(fan_speed)
        if swing_direction is not None: code = self.swing_direction.internal_set(swing_direction)
        if sleep_mode is not None: code = self.sleep_mode.internal_set(sleep_mode)
        if auxiliary_heating is not None: code = self.auxiliary_heating.internal_set(auxiliary_heating)
        self._power_managed_properties = (self.operating_mode, self.target_temperature, self.fan_speed, self.swing_direction, self.sleep_mode, self.auxiliary_heating,)
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

    def _read(self, prop, key):
        code, value = prop.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {key: value}

    def _powered_mode(self):
        code, power = self.power.get()
        if code != "[PASS]":
            return code, None, None
        if power is not True:
            return "[ERROR] POWER_OFF", None, None
        code, mode = self.operating_mode.get()
        return code, mode, power

    def get_operating_mode(self) -> tuple[str, dict]:
        return self._read(self.operating_mode, "operating_mode")

    def set_operating_mode(self, value: str) -> tuple[str, dict]:
        code, power = self.power.get()
        if code != "[PASS]":
            return code, {}
        if power is not True:
            return "[ERROR] POWER_OFF", {}
        if value not in ("cool", "heat", "fan", "dry", "auto"):
            return "[ERROR] INVALID_MODE", {}
        code = self.operating_mode.set(value)
        if code != "[PASS]":
            return code, {}
        if value in ("cool", "fan", "dry"):
            code = self.auxiliary_heating.internal_set(False)
            if code != "[PASS]":
                return code, {}
        return "[PASS]", {}

    def get_target_temperature(self) -> tuple[str, dict]:
        code, mode, _ = self._powered_mode()
        if code != "[PASS]":
            return code, {}
        if mode not in ("cool", "heat", "auto"):
            return "[ERROR] INVALID_MODE", {}
        return self._read(self.target_temperature, "target_temperature")

    def set_target_temperature(self, value: float) -> tuple[str, dict]:
        code, mode, _ = self._powered_mode()
        if code != "[PASS]":
            return code, {}
        if mode not in ("cool", "heat", "auto"):
            return "[ERROR] INVALID_MODE", {}
        code = self.target_temperature.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def increase_target_temperature(self) -> tuple[str, dict]:
        code, mode, _ = self._powered_mode()
        if code != "[PASS]":
            return code, {}
        if mode not in ("cool", "heat", "auto"):
            return "[ERROR] INVALID_MODE", {}
        code, value = self.target_temperature.get()
        if code != "[PASS]":
            return code, {}
        code = self.target_temperature.set(min(30.0, value + 0.5))
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def decrease_target_temperature(self) -> tuple[str, dict]:
        code, mode, _ = self._powered_mode()
        if code != "[PASS]":
            return code, {}
        if mode not in ("cool", "heat", "auto"):
            return "[ERROR] INVALID_MODE", {}
        code, value = self.target_temperature.get()
        if code != "[PASS]":
            return code, {}
        code = self.target_temperature.set(max(16.0, value - 0.5))
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_fan_speed(self) -> tuple[str, dict]:
        return self._read(self.fan_speed, "fan_speed")

    def set_fan_speed(self, value: str) -> tuple[str, dict]:
        code = self.fan_speed.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_swing_direction(self) -> tuple[str, dict]:
        return self._read(self.swing_direction, "swing_direction")

    def set_swing_direction(self, value: str) -> tuple[str, dict]:
        code = self.swing_direction.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_sleep_mode(self) -> tuple[str, dict]:
        return self._read(self.sleep_mode, "sleep_mode")

    def set_sleep_mode(self, value: bool) -> tuple[str, dict]:
        code = self.sleep_mode.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_auxiliary_heating(self) -> tuple[str, dict]:
        code, mode, _ = self._powered_mode()
        if code != "[PASS]":
            return code, {}
        if mode not in ("heat", "auto"):
            return "[ERROR] INVALID_MODE", {}
        return self._read(self.auxiliary_heating, "auxiliary_heating")

    def set_auxiliary_heating(self, value: bool) -> tuple[str, dict]:
        code, mode, _ = self._powered_mode()
        if code != "[PASS]":
            return code, {}
        if mode not in ("heat", "auto"):
            return "[ERROR] INVALID_MODE", {}
        code = self.auxiliary_heating.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        code, power = self.power.get()
        if code != "[PASS]":
            return code, []
        if power is not True:
            return "[PASS]", []

        code, mode = self.operating_mode.get()
        if code != "[PASS]":
            return code, []
        code, target = self.target_temperature.get()
        if code != "[PASS]":
            return code, []
        code, fan = self.fan_speed.get()
        if code != "[PASS]":
            return code, []
        code, auxiliary = self.auxiliary_heating.get()
        if code != "[PASS]":
            return code, []

        room = context["space_state"]

        if mode == "fan":
            return "[PASS]", []

        if mode == "dry":
            if room["humidity"] <= 50:
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
                    "unit": "%RH",
                },
            }]

        rate = {"low": 0.2, "medium": 0.4, "high": 0.6, "auto": 0.4}[fan]

        if mode == "cool" or (mode == "auto" and room["temperature"] > target):
            if room["temperature"] <= target:
                return "[PASS]", []
            return "[PASS]", [{
                "trigger": "tick",
                "source": context["object_id"],
                "target": context["space_id"],
                "function": "approach",
                "parameters": {
                    "property": "temperature",
                    "value": target,
                    "rate_per_minute": rate,
                    "unit": "degC",
                },
            }]

        if mode in ("heat", "auto") and room["temperature"] < target:
            if auxiliary:
                rate += 0.4
            return "[PASS]", [{
                "trigger": "tick",
                "source": context["object_id"],
                "target": context["space_id"],
                "function": "approach",
                "parameters": {
                    "property": "temperature",
                    "value": target,
                    "rate_per_minute": rate,
                    "unit": "degC",
                },
            }]

        if auxiliary and room["temperature"] >= target:
            code = self.auxiliary_heating.internal_set(False)
            if code != "[PASS]":
                return code, []

        return "[PASS]", []

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        mode = self.operating_mode.value
        if mode in ("cool", "fan", "dry"):
            code = self.auxiliary_heating.internal_set(False)
            if code != "[PASS]":
                return code, []
        return "[PASS]", []