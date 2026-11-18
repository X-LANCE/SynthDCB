# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class PetWaterDispenser:
    """
    PetWaterDispenser
    Description: Pet water dispenser. Users can query and set the dispensing or circulation mode, and can query the water level, filter state, and low-water state. Circulation mode filters and circulates drinking water; when the water level is too low, dispensing or circulation stops.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, operation_mode: str = None, water_level: int = None, filter_state: str = None, low_water: bool = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the dispenser is powered.',
            default=False
        )
        self.operation_mode = StringProperty(
            name='operation_mode',
            description='Retained selected dispensing/circulation mode. Low water or power-off blocks physical operation without changing this setting; its observable operation effect is the containing Space noise contribution.',
            default='circulation',
            choices=['dispensing', 'circulation']
        )
        self.water_level = IntProperty(
            name='water_level',
            description='Current water level as a percentage of the dispenser reservoir capacity.',
            default=100,
            mode=2,
            unit='%',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.filter_state = StringProperty(
            name='filter_state',
            description='Condition of the water filter.',
            default='good',
            mode=2,
            choices=['good', 'replace']
        )
        self.low_water = BoolProperty(
            name='low_water',
            description='Derived low-water flag: true exactly when water_level is less than 10 percent; false at 10 percent and above.',
            default=False,
            mode=2
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if operation_mode is not None: code = self.operation_mode.internal_set(operation_mode)
        if water_level is not None: code = self.water_level.internal_set(water_level)
        if filter_state is not None: code = self.filter_state.internal_set(filter_state)
        if low_water is not None: code = self.low_water.internal_set(low_water)
        self._power_managed_properties = (self.operation_mode, self.water_level, self.filter_state, self.low_water,)
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

    def get_operation_mode(self) -> tuple[str, dict]:
        """
        Return the selected dispensing or circulation mode. This function is available only while the dispenser is powered.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.operation_mode.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"operation_mode": value}

    def set_operation_mode(self, value: str) -> tuple[str, dict]:
        """
        Set the dispensing or circulation mode. The mode is changed only while powered and valid values are dispensing or circulation.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        if value not in ("dispensing", "circulation"):
            return "[INVALID_VALUE]", {}
        code = self.operation_mode.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_water_level(self) -> tuple[str, dict]:
        """
        Return the current reservoir water level percentage. This function is available only while the dispenser is powered.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.water_level.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"water_level": value}

    def get_filter_state(self) -> tuple[str, dict]:
        """
        Return the current filter state. This function is available only while the dispenser is powered.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.filter_state.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"filter_state": value}

    def get_low_water(self) -> tuple[str, dict]:
        """
        Return whether the reservoir is in the low-water state. This function is available only while the dispenser is powered.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.low_water.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"low_water": value}

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        After each successful action, internally set low_water to (water_level < 10). Set the containing Space noise contribution to 20 dBA for dispensing or 10 dBA for circulation when power is true and low_water is false; otherwise set it to zero. Keep operation_mode unchanged while blocked. water_level is a read-only externally supplied sensor state restored from World initialization; no water-depletion or refill process is declared.

        Effect properties:
        - power: Whether the dispenser is powered.
        - operation_mode: The selected dispensing or circulation mode.
        - low_water: Whether low water blocks operation.
        - water_level: Read to update the derived low_water flag.
        """
        water_level = self.water_level.value

        low_water = water_level < 10
        low_code = self.low_water.internal_set(low_water)
        if low_code != "[PASS]":
            return low_code, []

        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, []

        mode = self.operation_mode.value

        contribution = 0
        if powered is True and low_water is False:
            contribution = 20 if mode == "dispensing" else 10

        effect = {
            "trigger": "after_action",
            "source": context["object_id"],
            "target": context["space_id"],
            "function": "set_contribution",
            "parameters": {
                "property": "noise",
                "value": contribution,
                "unit": "dBA"
            }
        }
        return "[PASS]", [effect]