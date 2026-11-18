# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Oven:
    """
    Oven
    Description: Oven. Users can query and set the cooking mode, heating temperature, and cooking time. Cooking modes other than manual mode preset the temperature and time.
    Version: 1.0.0
    Base: -
    """

    PROCESS = {'mode_property': 'cooking_mode', 'start_function': 'start_cooking', 'pause_function': 'pause_cooking', 'resume_function': 'resume_cooking', 'modes': {'manual': [{'phase': 'cooking', 'minutes': {'property': 'cooking_time'}}], 'bake': [{'phase': 'cooking', 'minutes': 30}], 'roast': [{'phase': 'cooking', 'minutes': 60}], 'broil': [{'phase': 'cooking', 'minutes': 15}]}}

    def __init__(self, power: bool = None, cooking_mode: str = None, heating_temperature: int = None, cooking_time: int = None, status: str = None, phase: str = None, remaining_minutes: int = None, started_at_minute: int = None, progress_minutes: int = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Device-wide electrical power state. Turning the oven off preserves its configuration and pauses a running cooking process.',
            default=False
        )
        self.cooking_mode = StringProperty(
            name='cooking_mode',
            description='Selected cooking mode. Manual mode uses the configured temperature and time. Bake presets 180 degrees Celsius for 30 minutes, roast presets 200 degrees Celsius for 60 minutes, and broil presets 230 degrees Celsius for 15 minutes.',
            default='manual',
            choices=['manual', 'bake', 'roast', 'broil']
        )
        self.heating_temperature = IntProperty(
            name='heating_temperature',
            description='Configured oven heating temperature. It can be directly changed only in manual mode while no cooking process is running or paused.',
            default=180,
            unit='degC',
            minimum=50,
            maximum=250,
            step=5,
            step_origin=50
        )
        self.cooking_time = IntProperty(
            name='cooking_time',
            description='Configured cooking duration. It can be directly changed only in manual mode while no cooking process is running or paused.',
            default=30,
            unit='min',
            minimum=1,
            maximum=240,
            step=1,
            step_origin=1
        )
        self.status = StringProperty(
            name='status',
            description='Current cooking-process status.',
            default='idle',
            mode=2,
            choices=['idle', 'running', 'paused', 'completed']
        )
        self.phase = StringProperty(
            name='phase',
            description='Current cooking-process phase.',
            default='idle',
            mode=2,
            choices=['idle', 'cooking', 'completed']
        )
        self.remaining_minutes = IntProperty(
            name='remaining_minutes',
            description='Whole minutes remaining in the current cooking process.',
            default=0,
            mode=2,
            unit='min',
            minimum=0,
            maximum=240,
            step=1,
            step_origin=0
        )
        self.started_at_minute = IntProperty(
            name='started_at_minute',
            description='Elapsed world minute at which the current running-time origin was established.',
            default=0,
            mode=2,
            unit='min',
            minimum=0,
            maximum=2147483647,
            step=1,
            step_origin=0
        )
        self.progress_minutes = IntProperty(
            name='progress_minutes',
            description='Whole cooking minutes completed since the beginning of the current process.',
            default=0,
            mode=2,
            unit='min',
            minimum=0,
            maximum=240,
            step=1,
            step_origin=0
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if cooking_mode is not None: code = self.cooking_mode.internal_set(cooking_mode)
        if heating_temperature is not None: code = self.heating_temperature.internal_set(heating_temperature)
        if cooking_time is not None: code = self.cooking_time.internal_set(cooking_time)
        if status is not None: code = self.status.internal_set(status)
        if phase is not None: code = self.phase.internal_set(phase)
        if remaining_minutes is not None: code = self.remaining_minutes.internal_set(remaining_minutes)
        if started_at_minute is not None: code = self.started_at_minute.internal_set(started_at_minute)
        if progress_minutes is not None: code = self.progress_minutes.internal_set(progress_minutes)
        self._power_managed_properties = (self.cooking_mode, self.heating_temperature, self.cooking_time, self.status, self.phase, self.remaining_minutes, self.started_at_minute, self.progress_minutes,)
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

    def get_cooking_mode(self) -> tuple[str, dict]:
        """
        Get the selected cooking mode. The operation fails without changing state while the oven is powered off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- cooking_mode: Selected cooking mode: manual, bake, roast, or broil. (type=string)

        Error Codes:
        - POWER_OFF: Cooking mode is inaccessible while the oven is powered off.
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
        Set the cooking mode while powered and while the process is idle or completed. Selecting manual preserves the current heating temperature and cooking time. Bake sets 180 degrees Celsius and 30 minutes, roast sets 200 degrees Celsius and 60 minutes, and broil sets 230 degrees Celsius and 15 minutes. Invalid input or an unavailable process state leaves all properties unchanged.

        Args:
        - mode: Cooking mode to select. (choices=['manual', 'bake', 'roast', 'broil'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Cooking mode cannot be changed while the oven is powered off.
        - PROCESS_ACTIVE: Cooking mode cannot be changed while cooking is running or paused.
        - INVALID_MODE: Cooking mode must be manual, bake, roast, or broil.
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

        if type(mode) is not str or mode not in ("manual", "bake", "roast", "broil"):
            return "[INVALID_MODE]", {}

        if mode == "bake":
            temperature = 180
            duration = 30
        elif mode == "roast":
            temperature = 200
            duration = 60
        elif mode == "broil":
            temperature = 230
            duration = 15
        else:
            temperature = None
            duration = None

        code = self.cooking_mode.set(mode)
        if code != "[PASS]":
            return code, {}

        if temperature is not None:
            code = self.heating_temperature.set(temperature)
            if code != "[PASS]":
                return code, {}
            code = self.cooking_time.set(duration)
            if code != "[PASS]":
                return code, {}

        return "[PASS]", {}

    def get_heating_temperature(self) -> tuple[str, dict]:
        """
        Get the configured heating temperature. The operation fails without changing state while the oven is powered off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- heating_temperature: Configured heating temperature in degrees Celsius. (type=integer)

        Error Codes:
        - POWER_OFF: Heating temperature is inaccessible while the oven is powered off.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.heating_temperature.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"heating_temperature": value}

    def set_heating_temperature(self, value: int) -> tuple[str, dict]:
        """
        Set the heating temperature from 50 through 250 degrees Celsius in 5-degree increments. This operation is available only while powered, in manual mode, and while the process is idle or completed. Invalid input or a failed precondition leaves all state unchanged.

        Args:
        - value: Desired heating temperature in degrees Celsius. (min=50, max=250)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Heating temperature cannot be changed while the oven is powered off.
        - INVALID_MODE: Heating temperature can be directly changed only in manual mode.
        - PROCESS_ACTIVE: Heating temperature cannot be changed while cooking is running or paused.
        - INVALID_TEMPERATURE: Heating temperature must be from 50 through 250 degrees Celsius in 5-degree increments.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        mode_code, mode = self.cooking_mode.get()
        if mode_code != "[PASS]":
            return mode_code, {}
        if mode != "manual":
            return "[INVALID_MODE]", {}

        status_code, status = self.status.get()
        if status_code != "[PASS]":
            return status_code, {}
        if status not in ("idle", "completed"):
            return "[PROCESS_ACTIVE]", {}

        if type(value) is not int or value < 50 or value > 250 or (value - 50) % 5 != 0:
            return "[INVALID_TEMPERATURE]", {}

        code = self.heating_temperature.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_cooking_time(self) -> tuple[str, dict]:
        """
        Get the configured cooking time. The operation fails without changing state while the oven is powered off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- cooking_time: Configured cooking duration in minutes. (type=integer)

        Error Codes:
        - POWER_OFF: Cooking time is inaccessible while the oven is powered off.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.cooking_time.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"cooking_time": value}

    def set_cooking_time(self, value: int) -> tuple[str, dict]:
        """
        Set the cooking time from 1 through 240 minutes. This operation is available only while powered, in manual mode, and while the process is idle or completed. Invalid input or a failed precondition leaves all state unchanged.

        Args:
        - value: Desired cooking duration in whole minutes. (min=1, max=240)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Cooking time cannot be changed while the oven is powered off.
        - INVALID_MODE: Cooking time can be directly changed only in manual mode.
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
        if mode != "manual":
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

    def get_status(self) -> tuple[str, dict]:
        """
        Get the current cooking-process status without changing progress. The operation fails while the oven is powered off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- status: Current process status: idle, running, paused, or completed. (type=string)

        Error Codes:
        - POWER_OFF: Process status is inaccessible while the oven is powered off.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.status.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"status": value}

    def get_phase(self) -> tuple[str, dict]:
        """
        Get the current cooking-process phase without changing progress. The operation fails while the oven is powered off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- phase: Current process phase: idle, cooking, or completed. (type=string)

        Error Codes:
        - POWER_OFF: Process phase is inaccessible while the oven is powered off.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.phase.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"phase": value}

    def get_remaining_minutes(self) -> tuple[str, dict]:
        """
        Get the number of whole minutes remaining in the cooking process without changing progress. The operation fails while the oven is powered off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- remaining_minutes: Whole minutes remaining in the cooking process. (type=integer)

        Error Codes:
        - POWER_OFF: Remaining cooking time is inaccessible while the oven is powered off.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.remaining_minutes.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"remaining_minutes": value}

    def get_started_at_minute(self) -> tuple[str, dict]:
        """
        Get the elapsed world minute used as the current running-time origin. Reading it does not change process state. The operation fails while the oven is powered off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- started_at_minute: Elapsed world minute at which the current running-time origin was established. (type=integer)

        Error Codes:
        - POWER_OFF: The process time origin is inaccessible while the oven is powered off.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.started_at_minute.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"started_at_minute": value}

    def get_progress_minutes(self) -> tuple[str, dict]:
        """
        Get the number of whole cooking minutes already completed without changing process state. The operation fails while the oven is powered off.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- progress_minutes: Whole cooking minutes completed. (type=integer)

        Error Codes:
        - POWER_OFF: Cooking progress is inaccessible while the oven is powered off.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}
        code, value = self.progress_minutes.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"progress_minutes": value}

    def start_cooking(self, mode: str) -> tuple[str, dict]:
        """
        Start a new cooking process in the requested mode while powered and while the previous process is idle or completed. Manual mode uses the current temperature and cooking time. Bake applies 180 degrees Celsius and 30 minutes, roast applies 200 degrees Celsius and 60 minutes, and broil applies 230 degrees Celsius and 15 minutes before initializing the process. Starting resets progress to zero, selects the cooking phase, and freezes the resulting configuration until completion or an explicit stop.

        Args:
        - mode: Cooking mode to start. (choices=['manual', 'bake', 'roast', 'broil'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Cooking cannot start while the oven is powered off.
        - PROCESS_ACTIVE: A new cooking process can start only while the previous process is idle or completed.
        - INVALID_MODE: Cooking mode must be manual, bake, roast, or broil.
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

        if type(mode) is not str or mode not in ("manual", "bake", "roast", "broil"):
            return "[INVALID_MODE]", {}

        if mode == "bake":
            temperature = 180
            duration = 30
        elif mode == "roast":
            temperature = 200
            duration = 60
        elif mode == "broil":
            temperature = 230
            duration = 15
        else:
            temperature_code, temperature = self.heating_temperature.get()
            if temperature_code != "[PASS]":
                return temperature_code, {}
            duration_code, duration = self.cooking_time.get()
            if duration_code != "[PASS]":
                return duration_code, {}

        code = self.cooking_mode.set(mode)
        if code != "[PASS]":
            return code, {}

        if mode != "manual":
            code = self.heating_temperature.set(temperature)
            if code != "[PASS]":
                return code, {}
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
        Pause a running cooking process while powered. Progress and remaining time are synchronized to the current elapsed minute before status becomes paused. The selected mode, temperature, duration, phase, and running-time origin are retained. The operation fails without changing state unless the process is running.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Cooking cannot be paused while the oven is powered off.
        - NOT_RUNNING: Only a running cooking process can be paused.
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

    def resume_cooking(self) -> tuple[str, dict]:
        """
        Resume a paused cooking process while powered. Existing configuration, phase, remaining time, and progress are retained. Status becomes running and started_at_minute is re-established from the retained progress. The operation fails without changing state unless the process is paused.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Cooking cannot be resumed while the oven is powered off.
        - NOT_PAUSED: Only a paused cooking process can be resumed.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        status_code, status = self.status.get()
        if status_code != "[PASS]":
            return status_code, {}
        if status != "paused":
            return "[NOT_PAUSED]", {}

        code = self.status.internal_set("running")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def stop_cooking(self) -> tuple[str, dict]:
        """
        Stop and abandon a running or paused cooking process while powered. The operation resets status and phase to idle and resets remaining time, elapsed progress, and the running-time origin to zero. The configured cooking mode, heating temperature, and cooking time are preserved so they may be changed or used for a new process. A failed precondition leaves all state unchanged.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Cooking cannot be stopped while the oven is powered off.
        - NOT_ACTIVE: Only a running or paused cooking process can be stopped.
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
        Each minute, advance a powered and running cooking process using elapsed time from started_at_minute. The single cooking phase lasts exactly the frozen cooking_time. Clamp progress to the configured duration and remaining time to zero; at the exact duration boundary set both status and phase to completed. Paused, idle, completed, or unpowered processes do not advance. For each minute that begins with the oven powered and running, increase the containing space temperature by 0.1 degrees Celsius when heating_temperature is from 50 through 145 degrees, by 0.2 degrees when it is from 150 through 195 degrees, or by 0.3 degrees when it is from 200 through 250 degrees.

    Effect properties:
    - power: Determines whether cooking may advance and whether the oven releases heat.
    - heating_temperature: Determines the per-minute temperature increase produced while the oven is cooking.
    - cooking_time: Provides the exact duration of the cooking phase.
    - status: Determines whether the process advances and whether the oven releases heat.
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

        temperature_code, temperature = self.heating_temperature.get()
        if temperature_code != "[PASS]":
            return temperature_code, []
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

        if temperature <= 145:
            increase = 0.1
        elif temperature <= 195:
            increase = 0.2
        else:
            increase = 0.3

        effect = {
            "trigger": "tick",
            "source": context["object_id"],
            "target": context["space_id"],
            "function": "delta",
            "parameters": {
                "property": "temperature",
                "value": increase,
                "unit": "degC"
            }
        }
        return "[PASS]", [effect]

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        When a cooking process transitions into running, establish started_at_minute as the current elapsed world minute minus retained progress_minutes. When power changes from on to off during a running process, change status to paused while retaining the current process configuration and progress. Restoring power does not resume cooking. This event emits no space effect.

    Effect properties:
    - power: Determines whether loss of power must pause a running process.
    - status: Identifies transitions into running and records an automatic pause after power loss.
    - progress_minutes: Provides retained progress when establishing the running-time origin.
    - started_at_minute: Stores the internally established elapsed-minute origin when the process transitions into running.
        """
        pre_properties = context["pre_state"]["objects"][context["object_id"]]["properties"]
        previous_power = pre_properties["power"]
        previous_status = pre_properties["status"]
        elapsed = context["time_state"]["elapsed_minutes"]

        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, []

        if powered is not True:
            if previous_power is True and previous_status == "running":
                code = self.status.internal_set("paused")
                if code != "[PASS]":
                    return code, []
            return "[PASS]", []

        status_code, status = self.status.get()
        if status_code != "[PASS]":
            return status_code, []

        if previous_status == "running" and status == "paused":
            origin_code, origin = self.started_at_minute.get()
            if origin_code != "[PASS]":
                return origin_code, []
            duration_code, duration = self.cooking_time.get()
            if duration_code != "[PASS]":
                return duration_code, []

            progress = max(elapsed - origin, 0)
            progress = min(progress, duration)
            remaining = max(duration - progress, 0)

            code = self.progress_minutes.internal_set(progress)
            if code != "[PASS]":
                return code, []
            code = self.remaining_minutes.internal_set(remaining)
            if code != "[PASS]":
                return code, []
            return "[PASS]", []

        if status == "running" and (
            previous_status != "running" or previous_power is not True
        ):
            progress_code, progress = self.progress_minutes.get()
            if progress_code != "[PASS]":
                return progress_code, []
            origin = elapsed - progress
            code = self.started_at_minute.internal_set(origin)
            if code != "[PASS]":
                return code, []

        return "[PASS]", []