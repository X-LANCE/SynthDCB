# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..Speaker import Speaker


class BluetoothSpeaker(Speaker):
    """
    BluetoothSpeaker
    Description: Bluetooth speaker. It supports querying the battery level.
    Version: 1.0.0
    Base: Speaker
    """

    def __init__(
        self,
        battery_level: int = None,
        *,
        power: bool | None = None,
        _defer_power_init: bool = False,
        **base_kwargs,
    ) -> None:
        _power_init_value = power if power is not None else False
        super().__init__(
            power=_power_init_value,
            _defer_power_init=True,
            **base_kwargs,
        )

        self.battery_level = IntProperty(
            name="battery_level",
            description="The speaker battery level as a percentage.",
            default=100,
            unit="%",
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0,
        )

        if battery_level is not None:
            code = self.battery_level.internal_set(battery_level)

        self._power_managed_properties = (
            self.playback_state,
            self.volume,
            self.content,
            self.playback_mode,
            self.battery_level,
        )
        self._power_initialized = False
        self._disabled = {
            "properties": [],
            "functions": [],
            "events": [],
        }

        if not _defer_power_init:
            self.set_power(_power_init_value)

    def get_battery_level(self) -> tuple[str, dict]:
        """
        Returns the speaker battery level as an integer percentage from 0 through 100. Fails when the speaker is powered off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- battery_level: The speaker battery level percentage. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, powered = self._powered()
        if code != "[PASS]":
            return code, {}

        code, value = self.battery_level.get()
        if code != "[PASS]":
            return code, {}

        return "[PASS]", {"battery_level": value}