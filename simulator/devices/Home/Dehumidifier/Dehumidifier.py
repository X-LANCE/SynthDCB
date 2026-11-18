# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty


class Dehumidifier:
    """
    Dehumidifier
    Description: Dehumidifier. Users can query and set target humidity, dehumidification intensity, and fan speed, and can query the full-tank and continuous-drainage states. While running and when space humidity is above the target, the device gradually lowers space humidity; it stops dehumidifying when the target is reached or the tank is full. The amount of water in the tank changes with dehumidification intensity and remains unchanged in continuous-drainage mode. A powered empty_tank action resets the tank amount and full interlock, allowing dehumidification to resume.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, target_humidity: int = None, dehumidification_intensity: str = None, fan_speed: str = None, tank_full: bool = None, continuous_drainage: bool = None, tank_fill_units: int = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        self.power = BoolProperty(
            name='power',
            description='Whether the dehumidifier is powered.',
            default=False
        )
        self.target_humidity = IntProperty(
            name='target_humidity',
            description='Desired room relative humidity target.',
            default=50,
            unit='%RH',
            minimum=20,
            maximum=80,
            step=1,
            step_origin=20
        )
        self.dehumidification_intensity = StringProperty(
            name='dehumidification_intensity',
            description='Dehumidification intensity used while operating.',
            default='medium',
            choices=['low', 'medium', 'high']
        )
        self.fan_speed = StringProperty(
            name='fan_speed',
            description='Fan speed used while operating.',
            default='medium',
            choices=['low', 'medium', 'high']
        )
        self.tank_full = BoolProperty(
            name='tank_full',
            description='Whether the water collection tank is full. A full tank prevents dehumidification.',
            default=False,
            mode=2
        )
        self.continuous_drainage = BoolProperty(
            name='continuous_drainage',
            description='Whether collected water is continuously drained instead of accumulating in the tank.',
            default=False
        )
        self.tank_fill_units = IntProperty(
            name='tank_fill_units',
            description='Accumulated moisture-removal units in the tank, 0 through 60; one unit equals one percentage point of room humidity actually removed.',
            default=0,
            mode=2,
            minimum=0,
            maximum=60,
            step=1,
            step_origin=0
        )
        code = self.power.internal_set(_power_init_value)

        if target_humidity is not None:
            code = self.target_humidity.internal_set(target_humidity)
        if dehumidification_intensity is not None:
            code = self.dehumidification_intensity.internal_set(dehumidification_intensity)
        if fan_speed is not None:
            code = self.fan_speed.internal_set(fan_speed)
        if tank_full is not None:
            code = self.tank_full.internal_set(tank_full)
        if continuous_drainage is not None:
            code = self.continuous_drainage.internal_set(continuous_drainage)
        if tank_fill_units is not None:
            code = self.tank_fill_units.internal_set(tank_fill_units)
        self._power_managed_properties = (
            self.target_humidity,
            self.dehumidification_intensity,
            self.fan_speed,
            self.tank_full,
            self.continuous_drainage,
            self.tank_fill_units,
        )
        self._power_initialized = False
        self._disabled = {'properties': [], 'functions': [], 'events': []}

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

    def get_target_humidity(self) -> tuple[str, dict]:
        code, value = self.target_humidity.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"target_humidity": value}

    def set_target_humidity(self, value: int) -> tuple[str, dict]:
        code = self.target_humidity.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_dehumidification_intensity(self) -> tuple[str, dict]:
        code, value = self.dehumidification_intensity.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"dehumidification_intensity": value}

    def set_dehumidification_intensity(self, value: str) -> tuple[str, dict]:
        code = self.dehumidification_intensity.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_fan_speed(self) -> tuple[str, dict]:
        code, value = self.fan_speed.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"fan_speed": value}

    def set_fan_speed(self, value: str) -> tuple[str, dict]:
        code = self.fan_speed.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_tank_full(self) -> tuple[str, dict]:
        code, value = self.tank_full.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"tank_full": value}

    def get_continuous_drainage(self) -> tuple[str, dict]:
        code, value = self.continuous_drainage.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"continuous_drainage": value}

    def set_continuous_drainage(self, value: bool) -> tuple[str, dict]:
        code = self.continuous_drainage.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_tank_fill_units(self) -> tuple[str, dict]:
        code, value = self.tank_fill_units.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"tank_fill_units": value}

    def empty_tank(self) -> tuple[str, dict]:
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if powered is not True:
            return "[NO_ACTION] Device is powered off.", {}

        code = self.tank_fill_units.internal_set(0)
        if code != "[PASS]":
            return code, {}

        code = self.tank_full.internal_set(False)
        if code != "[PASS]":
            return code, {}

        return "[PASS]", {}

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, []
        if powered is not True:
            return "[PASS]", []

        code, target_humidity = self.target_humidity.get()
        if code != "[PASS]":
            return code, []
        code, intensity = self.dehumidification_intensity.get()
        if code != "[PASS]":
            return code, []
        code, fan_speed = self.fan_speed.get()
        if code != "[PASS]":
            return code, []
        code, tank_full = self.tank_full.get()
        if code != "[PASS]":
            return code, []
        code, drainage = self.continuous_drainage.get()
        if code != "[PASS]":
            return code, []
        code, fill = self.tank_fill_units.get()
        if code != "[PASS]":
            return code, []

        humidity = context["space_state"]["humidity"]
        if tank_full is True or humidity <= target_humidity:
            return "[PASS]", []

        base_rate = {
            "low": 1,
            "medium": 2,
            "high": 3,
        }[intensity]
        fan_multiplier = {
            "low": 1,
            "medium": 1.5,
            "high": 2,
        }[fan_speed]

        rate = max(1, int(base_rate * fan_multiplier))
        removal = min(int(humidity - target_humidity), rate)

        if drainage is not True:
            new_fill = min(60, fill + removal)
            code = self.tank_fill_units.internal_set(new_fill)
            if code != "[PASS]":
                return code, []

            if new_fill >= 60:
                code = self.tank_full.internal_set(True)
                if code != "[PASS]":
                    return code, []

        return "[PASS]", [{
            "trigger": "tick",
            "source": context["object_id"],
            "target": context["space_id"],
            "function": "delta",
            "parameters": {
                "property": "humidity",
                "value": -removal,
                "unit": "%RH"
            }
        }]