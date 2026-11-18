# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..Oven import Oven

class AirFryer(Oven):
    """
    AirFryer
    Description: Air fryer. It has the same settings as the oven.
    Version: 1.0.0
    Base: Oven
    """

    PROCESS = {'mode_property': 'cooking_mode', 'start_function': 'start_cooking', 'pause_function': 'pause_cooking', 'resume_function': 'resume_cooking', 'modes': {'manual': [{'phase': 'cooking', 'minutes': {'property': 'cooking_time'}}], 'bake': [{'phase': 'cooking', 'minutes': 30}], 'roast': [{'phase': 'cooking', 'minutes': 60}], 'broil': [{'phase': 'cooking', 'minutes': 15}]}}

    def __init__(self, *, power: bool | None = None, _defer_power_init: bool = False, **base_kwargs) -> None:
        _power_init_value = power if power is not None else False
        # initialize base Oven class
        super().__init__(power=_power_init_value, _defer_power_init=True, **base_kwargs)
        # define properties
        self._power_managed_properties = (self.cooking_mode, self.heating_temperature, self.cooking_time, self.status, self.phase, self.remaining_minutes, self.started_at_minute, self.progress_minutes,)
        self._power_initialized = False
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

        if not _defer_power_init:
            self.set_power(_power_init_value)

    pass