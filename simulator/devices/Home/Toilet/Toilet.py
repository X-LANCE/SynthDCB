# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Toilet:
    """
    Toilet
    Description: Toilet. Users can query and set seat heating, wash-water temperature and pressure, feminine-wash or rear-wash mode, drying, deodorization, and automatic lid-opening states.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, seat_heating: int = None, wash_water_temperature: int = None, wash_pressure: int = None, wash_mode: str = None, drying: bool = None, deodorization: bool = None, automatic_lid_opening: bool = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the toilet is powered.',
            default=False
        )
        self.seat_heating = IntProperty(
            name='seat_heating',
            description='Seat heating level.',
            default=0,
            minimum=0,
            maximum=3,
            step=1,
            step_origin=0
        )
        self.wash_water_temperature = IntProperty(
            name='wash_water_temperature',
            description='Wash-water temperature in degrees Celsius.',
            default=35,
            unit='degC',
            minimum=30,
            maximum=40,
            step=1,
            step_origin=30
        )
        self.wash_pressure = IntProperty(
            name='wash_pressure',
            description='Wash-water pressure level.',
            default=1,
            minimum=1,
            maximum=3,
            step=1,
            step_origin=1
        )
        self.wash_mode = StringProperty(
            name='wash_mode',
            description='Selected wash mode.',
            default='rear',
            choices=['rear', 'feminine']
        )
        self.drying = BoolProperty(
            name='drying',
            description='Whether the drying function is enabled.',
            default=False
        )
        self.deodorization = BoolProperty(
            name='deodorization',
            description='Whether deodorization is enabled.',
            default=False
        )
        self.automatic_lid_opening = BoolProperty(
            name='automatic_lid_opening',
            description='Whether the automatic lid-opening function is enabled.',
            default=False
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if seat_heating is not None: code = self.seat_heating.internal_set(seat_heating)
        if wash_water_temperature is not None: code = self.wash_water_temperature.internal_set(wash_water_temperature)
        if wash_pressure is not None: code = self.wash_pressure.internal_set(wash_pressure)
        if wash_mode is not None: code = self.wash_mode.internal_set(wash_mode)
        if drying is not None: code = self.drying.internal_set(drying)
        if deodorization is not None: code = self.deodorization.internal_set(deodorization)
        if automatic_lid_opening is not None: code = self.automatic_lid_opening.internal_set(automatic_lid_opening)
        self._power_managed_properties = (self.seat_heating, self.wash_water_temperature, self.wash_pressure, self.wash_mode, self.drying, self.deodorization, self.automatic_lid_opening,)
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

    def get_seat_heating(self) -> tuple[str, dict]:
        """
        Return the seat heating level. The toilet must be powered.
        """
        code, value = self.seat_heating.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"seat_heating": value}

    def set_seat_heating(self, value: int) -> tuple[str, dict]:
        """
        Set the seat heating level while powered.
        """
        code = self.seat_heating.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_wash_water_temperature(self) -> tuple[str, dict]:
        """
        Return the wash-water temperature while powered.
        """
        code, value = self.wash_water_temperature.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"wash_water_temperature": value}

    def set_wash_water_temperature(self, value: int) -> tuple[str, dict]:
        """
        Set the wash-water temperature while powered.
        """
        code = self.wash_water_temperature.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_wash_pressure(self) -> tuple[str, dict]:
        """
        Return the wash-water pressure level while powered.
        """
        code, value = self.wash_pressure.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"wash_pressure": value}

    def set_wash_pressure(self, value: int) -> tuple[str, dict]:
        """
        Set the wash-water pressure level while powered.
        """
        code = self.wash_pressure.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_wash_mode(self) -> tuple[str, dict]:
        """
        Return the selected wash mode while powered.
        """
        code, value = self.wash_mode.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"wash_mode": value}

    def set_wash_mode(self, value: str) -> tuple[str, dict]:
        """
        Select rear or feminine wash mode while powered.
        """
        code = self.wash_mode.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_drying(self) -> tuple[str, dict]:
        """
        Return whether drying is enabled while powered.
        """
        code, value = self.drying.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"drying": value}

    def set_drying(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable drying while powered.
        """
        code = self.drying.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_deodorization(self) -> tuple[str, dict]:
        """
        Return whether deodorization is enabled while powered.
        """
        code, value = self.deodorization.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"deodorization": value}

    def set_deodorization(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable deodorization while powered.
        """
        code = self.deodorization.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_automatic_lid_opening(self) -> tuple[str, dict]:
        """
        Return whether automatic lid opening is enabled while powered.
        """
        code, value = self.automatic_lid_opening.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"automatic_lid_opening": value}

    def set_automatic_lid_opening(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable automatic lid opening while powered.
        """
        code = self.automatic_lid_opening.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}