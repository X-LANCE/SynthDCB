# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..Oven import Oven

class Microwave(Oven):
    """
    Microwave
    Description: Microwave oven. Users can query and set microwave power. Defrost mode is added to the available modes. Heating temperature is not supported.
    Version: 1.0.0
    Base: Oven
    """

    PROCESS = {'mode_property': 'cooking_mode', 'start_function': 'start_cooking', 'pause_function': 'pause_cooking', 'resume_function': 'resume_cooking', 'modes': {'manual': [{'phase': 'cooking', 'minutes': {'property': 'cooking_time'}}], 'bake': [{'phase': 'cooking', 'minutes': 30}], 'roast': [{'phase': 'cooking', 'minutes': 60}], 'broil': [{'phase': 'cooking', 'minutes': 15}], 'defrost': [{'phase': 'cooking', 'minutes': {'property': 'cooking_time'}}]}}

    def __init__(self, cooking_mode: str = None, cooking_time: int = None, microwave_power: int = None, *, power: bool | None = None, _defer_power_init: bool = False, **base_kwargs) -> None:
        _power_init_value = power if power is not None else False
        # initialize base Oven class
        super().__init__(power=_power_init_value, _defer_power_init=True, **base_kwargs)
        # define properties
        self.cooking_mode = StringProperty(
            name='cooking_mode',
            description='Selected microwave cooking mode. Manual and defrost modes preserve the configured cooking time when selected. Bake presets 30 minutes, roast presets 60 minutes, and broil presets 15 minutes. Microwave power remains independently configurable in every mode.',
            default='manual',
            choices=['manual', 'bake', 'roast', 'broil', 'defrost']
        )
        self.cooking_time = IntProperty(
            name='cooking_time',
            description='Configured microwave cooking duration. It can be directly changed in manual or defrost mode while no cooking process is running or paused.',
            default=30,
            unit='min',
            minimum=1,
            maximum=240,
            step=1,
            step_origin=1
        )
        self.microwave_power = IntProperty(
            name='microwave_power',
            description='Configured microwave output power. It can be changed while the microwave is powered and the cooking process is idle or completed, and it remains fixed while a process is running or paused.',
            default=800,
            unit='W',
            minimum=100,
            maximum=1000,
            step=100,
            step_origin=100
        )

        # initialize properties
        if cooking_mode is not None: code = self.cooking_mode.internal_set(cooking_mode)
        if cooking_time is not None: code = self.cooking_time.internal_set(cooking_time)
        if microwave_power is not None: code = self.microwave_power.internal_set(microwave_power)

        # disable inherited properties
        self.heating_temperature.chmod(0)
        self._power_managed_properties = (self.cooking_mode, self.cooking_time, self.status, self.phase, self.remaining_minutes, self.started_at_minute, self.progress_minutes, self.microwave_power,)
        self._power_initialized = False
        self._disabled = {
            'properties': ['heating_temperature'],
            'functions': ['get_heating_temperature', 'set_heating_temperature'],
            'events': []
        }

        if not _defer_power_init:
            self.set_power(_power_init_value)

    def get_cooking_mode(self) -> tuple[str, dict]:
        """
        Get the selected microwave cooking mode. The operation fails without changing state while the microwave is powered off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- cooking_mode: Selected cooking mode: manual, bake, roast, broil, or defrost. (type=string)

        Error Codes:
        - POWER_OFF: Cooking mode is inaccessible while the microwave is powered off.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        code, value = self.cooking_mode.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"cooking_mode": value}

    def set_cooking_mode(self, mode: str) -> tuple[str, dict]:
        """
        Set the cooking mode while powered and while the process is idle or completed. Selecting manual or defrost preserves the current cooking time. Bake sets 30 minutes, roast sets 60 minutes, and broil sets 15 minutes. Every mode preserves the configured microwave power. Invalid input or an unavailable process state leaves all properties unchanged.

        Args:
        - mode: Microwave cooking mode to select. (choices=['manual', 'bake', 'roast', 'broil', 'defrost'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Cooking mode cannot be changed while the microwave is powered off.
        - PROCESS_ACTIVE: Cooking mode cannot be changed while cooking is running or paused.
        - INVALID_MODE: Cooking mode must be manual, bake, roast, broil, or defrost.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        status_code, status = self.status.get()
        if status_code != "[PASS]":
            return status_code, {}
        if status not in ("idle", "completed"):
            return "[PROCESS_ACTIVE]", {}

        if type(mode) is not str or mode not in (
            "manual",
            "bake",
            "roast",
            "broil",
            "defrost",
        ):
            return "[INVALID_MODE]", {}

        if mode == "bake":
            duration = 30
        elif mode == "roast":
            duration = 60
        elif mode == "broil":
            duration = 15
        else:
            duration = None

        code = self.cooking_mode.set(mode)
        if code != "[PASS]":
            return code, {}

        if duration is not None:
            code = self.cooking_time.set(duration)
            if code != "[PASS]":
                return code, {}

        return "[PASS]", {}

    def set_cooking_time(self, value: int) -> tuple[str, dict]:
        """
        Set the cooking time from 1 through 240 minutes. This operation is available only while powered, in manual or defrost mode, and while the process is idle or completed. Invalid input or a failed precondition leaves all state unchanged.

        Args:
        - value: Desired cooking duration in whole minutes. (min=1, max=240)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Cooking time cannot be changed while the microwave is powered off.
        - INVALID_MODE: Cooking time can be directly changed only in manual or defrost mode.
        - PROCESS_ACTIVE: Cooking time cannot be changed while cooking is running or paused.
        - INVALID_TIME: Cooking time must be an integer from 1 through 240 minutes.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        mode_code, mode = self.cooking_mode.get()
        if mode_code != "[PASS]":
            return mode_code, {}
        if mode not in ("manual", "defrost"):
            return "[INVALID_MODE]", {}

        status_code, status = self.status.get()
        if status_code != "[PASS]":
            return status_code, {}
        if status not in ("idle", "completed"):
            return "[PROCESS_ACTIVE]", {}

        if type(value) is not int or value < 1 or value > 240:
            return "[INVALID_TIME]", {}

        code = self.cooking_time.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_microwave_power(self) -> tuple[str, dict]:
        """
        Get the configured microwave output power. The operation fails without changing state while the microwave is powered off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- microwave_power: Configured microwave output power in watts, from 100 through 1000 in 100-watt increments. (type=integer)

        Error Codes:
        - POWER_OFF: Microwave power is inaccessible while the microwave is powered off.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        code, value = self.microwave_power.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"microwave_power": value}

    def set_microwave_power(self, value: int) -> tuple[str, dict]:
        """
        Set microwave output power from 100 through 1000 watts in 100-watt increments. This operation is available only while powered and while the cooking process is idle or completed. Invalid input or a failed precondition leaves all state unchanged.

        Args:
        - value: Desired microwave output power in watts. (min=100, max=1000)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Microwave power cannot be changed while the microwave is powered off.
        - PROCESS_ACTIVE: Microwave power cannot be changed while cooking is running or paused.
        - INVALID_POWER: Microwave power must be from 100 through 1000 watts in 100-watt increments.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        status_code, status = self.status.get()
        if status_code != "[PASS]":
            return status_code, {}
        if status not in ("idle", "completed"):
            return "[PROCESS_ACTIVE]", {}

        if (
            type(value) is not int
            or value < 100
            or value > 1000
            or (value - 100) % 100 != 0
        ):
            return "[INVALID_POWER]", {}

        code = self.microwave_power.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def start_cooking(self, mode: str) -> tuple[str, dict]:
        """
        Start a new microwave cooking process in the requested mode while powered and while the previous process is idle or completed. Manual and defrost use the current cooking time. Bake applies 30 minutes, roast applies 60 minutes, and broil applies 15 minutes before initializing the process. The configured microwave power is preserved and cannot be changed through its setter while cooking is running or paused. Starting resets progress to zero, selects the cooking phase, and freezes the resulting duration until completion or an explicit stop.

        Args:
        - mode: Microwave cooking mode to start. (choices=['manual', 'bake', 'roast', 'broil', 'defrost'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Cooking cannot start while the microwave is powered off.
        - PROCESS_ACTIVE: A new cooking process can start only while the previous process is idle or completed.
        - INVALID_MODE: Cooking mode must be manual, bake, roast, broil, or defrost.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        status_code, status = self.status.get()
        if status_code != "[PASS]":
            return status_code, {}
        if status not in ("idle", "completed"):
            return "[PROCESS_ACTIVE]", {}

        if type(mode) is not str or mode not in (
            "manual",
            "bake",
            "roast",
            "broil",
            "defrost",
        ):
            return "[INVALID_MODE]", {}

        if mode == "bake":
            duration = 30
        elif mode == "roast":
            duration = 60
        elif mode == "broil":
            duration = 15
        else:
            duration_code, duration = self.cooking_time.get()
            if duration_code != "[PASS]":
                return duration_code, {}

        code = self.cooking_mode.set(mode)
        if code != "[PASS]":
            return code, {}

        if mode in ("bake", "roast", "broil"):
            code = self.cooking_time.set(duration)
            if code != "[PASS]":
                return code, {}

        code = self.status.internal_set("running")
        if code != "[PASS]":
            return code, {}

        code = self.phase.internal_set("cooking")
        if code != "[PASS]":
            return code, {}

        code = self.remaining_minutes.internal_set(duration)
        if code != "[PASS]":
            return code, {}

        code = self.started_at_minute.internal_set(0)
        if code != "[PASS]":
            return code, {}

        code = self.progress_minutes.internal_set(0)
        if code != "[PASS]":
            return code, {}

        return "[PASS]", {}

    def pause_cooking(self) -> tuple[str, dict]:
        """
        Pause a running microwave cooking process while powered. Progress and remaining time are synchronized to the current elapsed minute before status becomes paused. The selected mode, cooking duration, microwave-power setting, phase, and running-time origin remain unchanged. The operation fails without changing state unless the process is running.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Cooking cannot be paused while the microwave is powered off.
        - NOT_RUNNING: Only a running microwave cooking process can be paused.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        status_code, status = self.status.get()
        if status_code != "[PASS]":
            return status_code, {}
        if status != "running":
            return "[NOT_RUNNING]", {}

        code = self.status.internal_set("paused")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def stop_cooking(self) -> tuple[str, dict]:
        """
        Stop and abandon a running or paused microwave cooking process while powered. The operation resets status and phase to idle and resets remaining time, elapsed progress, and the running-time origin to zero. The configured cooking mode, cooking time, and microwave-power setting remain unchanged so they may be changed or used for a new process. A failed precondition leaves all state unchanged.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Cooking cannot be stopped while the microwave is powered off.
        - NOT_ACTIVE: Only a running or paused microwave cooking process can be stopped.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        status_code, status = self.status.get()
        if status_code != "[PASS]":
            return status_code, {}
        if status not in ("running", "paused"):
            return "[NOT_ACTIVE]", {}

        code = self.status.internal_set("idle")
        if code != "[PASS]":
            return code, {}

        code = self.phase.internal_set("idle")
        if code != "[PASS]":
            return code, {}

        code = self.remaining_minutes.internal_set(0)
        if code != "[PASS]":
            return code, {}

        code = self.started_at_minute.internal_set(0)
        if code != "[PASS]":
            return code, {}

        code = self.progress_minutes.internal_set(0)
        if code != "[PASS]":
            return code, {}

        return "[PASS]", {}

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        Each minute, advance a powered and running microwave cooking process using elapsed time from started_at_minute. The single cooking phase lasts exactly the frozen cooking_time. Clamp progress to the configured duration and remaining time to zero; at the exact duration boundary set both status and phase to completed. Paused, idle, completed, or unpowered processes do not advance. The microwave emits no direct Space effect.

    Effect properties:
    - power: Determines whether the cooking process may advance.
    - cooking_time: Provides the exact duration of the cooking phase.
    - status: Determines whether the cooking process advances.
    - phase: Tracks the active cooking phase and is set to completed when the configured duration elapses.
    - remaining_minutes: Stores the internally updated number of whole minutes remaining in the cooking process.
    - started_at_minute: Provides the elapsed-minute origin used to calculate process progress.
    - progress_minutes: Stores the internally updated number of completed cooking minutes.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, []
        if powered is not True:
            return "[PASS]", []

        status_code, status = self.status.get()
        if status_code != "[PASS]":
            return status_code, []
        if status != "running":
            return "[PASS]", []

        duration_code, duration = self.cooking_time.get()
        if duration_code != "[PASS]":
            return duration_code, []

        origin_code, origin = self.started_at_minute.get()
        if origin_code != "[PASS]":
            return origin_code, []

        elapsed = context["time_state"]["elapsed_minutes"]
        progress = max(elapsed - origin, 0)
        progress = min(progress, duration)
        remaining = max(duration - progress, 0)

        if progress >= duration:
            code = self.progress_minutes.internal_set(duration)
            if code != "[PASS]":
                return code, []

            code = self.remaining_minutes.internal_set(0)
            if code != "[PASS]":
                return code, []

            code = self.phase.internal_set("completed")
            if code != "[PASS]":
                return code, []

            code = self.status.internal_set("completed")
            if code != "[PASS]":
                return code, []
        else:
            code = self.progress_minutes.internal_set(progress)
            if code != "[PASS]":
                return code, []

            code = self.remaining_minutes.internal_set(remaining)
            if code != "[PASS]":
                return code, []

            code = self.phase.internal_set("cooking")
            if code != "[PASS]":
                return code, []

        return "[PASS]", []

    def get_heating_temperature(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'get_heating_temperature' is disabled in Microwave.", {}

    def set_heating_temperature(self, *args, **kwargs):
        """
        Disabled function (overrides base implementation if any).
        """
        return "[DISABLED_FUNCTION] Function 'set_heating_temperature' is disabled in Microwave.", {}