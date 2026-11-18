# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Navigation:
    """
    Navigation
    Description: Local vehicle navigation module. Supports setting a destination, selecting a local simulated route, starting or canceling guidance, setting route preferences, and querying route state, remaining distance, and estimated time. Route calculation, position updates, and arrival events use an explicit local execution model without accessing real map services. Starting guidance does not mean the vehicle has moved or arrived. Navigation prompts affect the shared cabin sound field through the media output chain.
    Version: 1.0.0
    Base: -
    """

    PROCESS = {'mode_property': 'selected_route', 'start_function': 'start_guidance', 'pause_function': 'pause_guidance', 'resume_function': 'resume_guidance', 'modes': {'fastest': [{'phase': 'guidance', 'minutes': 12}], 'shortest': [{'phase': 'guidance', 'minutes': 15}], 'scenic': [{'phase': 'guidance', 'minutes': 20}]}}

    def __init__(self, power: bool = None, destination: str = None, route_preference: str = None, selected_route: str = None, status: str = None, phase: str = None, remaining_minutes: int = None, started_at_minute: int = None, progress_minutes: int = None, remaining_distance: int = None, voice_guidance: bool = None, guidance_volume: int = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the local navigation module is powered.',
            default=False
        )
        self.destination = StringProperty(
            name='destination',
            description='Selected local simulated destination.',
            default='none',
            choices=['none', 'city_center', 'airport', 'charging_station']
        )
        self.route_preference = StringProperty(
            name='route_preference',
            description='Stored route calculation preference. It is retained for future route selection but does not change an already selected synthetic route.',
            default='balanced',
            choices=['balanced', 'avoid_tolls', 'avoid_highways']
        )
        self.selected_route = StringProperty(
            name='selected_route',
            description='Selected deterministic local route profile and navigation process mode.',
            default='none',
            mode=2,
            choices=['none', 'fastest', 'shortest', 'scenic']
        )
        self.status = StringProperty(
            name='status',
            description='Navigation process state. Running means guidance is active, paused means progress is suspended, and completed means the simulated destination has been reached.',
            default='idle',
            mode=2,
            choices=['idle', 'running', 'paused', 'completed']
        )
        self.phase = StringProperty(
            name='phase',
            description='Current navigation process phase.',
            default='idle',
            mode=2,
            choices=['idle', 'guidance', 'completed']
        )
        self.remaining_minutes = IntProperty(
            name='remaining_minutes',
            description='Estimated whole minutes remaining in the selected synthetic route.',
            default=0,
            mode=2,
            unit='min',
            minimum=0,
            maximum=20,
            step=1,
            step_origin=0
        )
        self.started_at_minute = IntProperty(
            name='started_at_minute',
            description='Simulation elapsed-minute timestamp from which current guidance progress is measured.',
            default=0,
            mode=2,
            unit='min',
            minimum=0,
            step=1,
            step_origin=0
        )
        self.progress_minutes = IntProperty(
            name='progress_minutes',
            description='Whole elapsed minutes of progress in the current synthetic route.',
            default=0,
            mode=2,
            unit='min',
            minimum=0,
            maximum=20,
            step=1,
            step_origin=0
        )
        self.remaining_distance = IntProperty(
            name='remaining_distance',
            description='Estimated whole kilometers remaining in the selected synthetic route.',
            default=0,
            mode=2,
            unit='km',
            minimum=0,
            maximum=18,
            step=1,
            step_origin=0
        )
        self.voice_guidance = BoolProperty(
            name='voice_guidance',
            description='Whether simulated navigation voice prompts are enabled.',
            default=True
        )
        self.guidance_volume = IntProperty(
            name='guidance_volume',
            description='Audio level contributed by active simulated navigation prompts.',
            default=40,
            unit='dBA',
            minimum=0,
            maximum=120,
            step=1,
            step_origin=0
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if destination is not None: code = self.destination.internal_set(destination)
        if route_preference is not None: code = self.route_preference.internal_set(route_preference)
        if selected_route is not None: code = self.selected_route.internal_set(selected_route)
        if status is not None: code = self.status.internal_set(status)
        if phase is not None: code = self.phase.internal_set(phase)
        if remaining_minutes is not None: code = self.remaining_minutes.internal_set(remaining_minutes)
        if started_at_minute is not None: code = self.started_at_minute.internal_set(started_at_minute)
        if progress_minutes is not None: code = self.progress_minutes.internal_set(progress_minutes)
        if remaining_distance is not None: code = self.remaining_distance.internal_set(remaining_distance)
        if voice_guidance is not None: code = self.voice_guidance.internal_set(voice_guidance)
        if guidance_volume is not None: code = self.guidance_volume.internal_set(guidance_volume)
        self._power_managed_properties = (self.destination, self.route_preference, self.selected_route, self.status, self.phase, self.remaining_minutes, self.started_at_minute, self.progress_minutes, self.remaining_distance, self.voice_guidance, self.guidance_volume,)
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

    def get_destination(self) -> tuple[str, dict]:
        """
        Return the selected local simulated destination. The module must be powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- destination: Selected destination: none, city_center, airport, or charging_station. (type=string)

        Error Codes:
        - PRECONDITION_FAILED: The navigation module must be powered.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[PRECONDITION_FAILED]', {})
        code, value = self.destination.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'destination': value})

    def set_destination(self, destination: str) -> tuple[str, dict]:
        """
        Select a local simulated destination while powered and while guidance is idle or completed. This clears the previous route selection and resets route progress and metrics. Invalid input or a failed precondition leaves state unchanged.

        Args:
        - destination:  (choices=['city_center', 'airport', 'charging_station'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The module must be powered and guidance must be idle or completed.
        - INVALID_INPUT_ERROR: Destination must be city_center, airport, or charging_station.
        """
        if type(destination) is not str or destination not in ('city_center', 'airport', 'charging_station'):
            return ('[INVALID_INPUT_ERROR]', {})
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[PRECONDITION_FAILED]', {})
        status_code, status = self.status.get()
        if status_code != '[PASS]':
            return (status_code, {})
        if status not in ('idle', 'completed'):
            return ('[PRECONDITION_FAILED]', {})

        code = self.destination.set(destination)
        if code != '[PASS]':
            return (code, {})
        code = self.selected_route.internal_set('none')
        if code != '[PASS]':
            return (code, {})
        code = self.status.internal_set('idle')
        if code != '[PASS]':
            return (code, {})
        code = self.phase.internal_set('idle')
        if code != '[PASS]':
            return (code, {})
        code = self.remaining_minutes.internal_set(0)
        if code != '[PASS]':
            return (code, {})
        code = self.started_at_minute.internal_set(0)
        if code != '[PASS]':
            return (code, {})
        code = self.progress_minutes.internal_set(0)
        if code != '[PASS]':
            return (code, {})
        code = self.remaining_distance.internal_set(0)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_route_preference(self) -> tuple[str, dict]:
        """
        Return the stored route preference. The module must be powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- route_preference: Stored preference: balanced, avoid_tolls, or avoid_highways. (type=string)

        Error Codes:
        - PRECONDITION_FAILED: The navigation module must be powered.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[PRECONDITION_FAILED]', {})
        code, value = self.route_preference.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'route_preference': value})

    def set_route_preference(self, preference: str) -> tuple[str, dict]:
        """
        Store the route calculation preference while powered. The setting does not alter a route that is already selected or running. Invalid input leaves state unchanged.

        Args:
        - preference:  (choices=['balanced', 'avoid_tolls', 'avoid_highways'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The navigation module must be powered.
        - INVALID_INPUT_ERROR: Preference must be balanced, avoid_tolls, or avoid_highways.
        """
        if type(preference) is not str or preference not in ('balanced', 'avoid_tolls', 'avoid_highways'):
            return ('[INVALID_INPUT_ERROR]', {})
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[PRECONDITION_FAILED]', {})
        code = self.route_preference.set(preference)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_selected_route(self) -> tuple[str, dict]:
        """
        Return the selected synthetic route profile. The module must be powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- selected_route: Selected route: none, fastest, shortest, or scenic. (type=string)

        Error Codes:
        - PRECONDITION_FAILED: The navigation module must be powered.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[PRECONDITION_FAILED]', {})
        code, value = self.selected_route.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'selected_route': value})

    def select_route(self, route: str) -> tuple[str, dict]:
        """
        Select a deterministic local route while powered, with a destination set, and while guidance is idle or completed. Fastest initializes 12 km and 12 minutes, shortest initializes 10 km and 15 minutes, and scenic initializes 18 km and 20 minutes. Progress is reset to zero. Invalid input or a failed precondition leaves state unchanged.

        Args:
        - route:  (choices=['fastest', 'shortest', 'scenic'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The module must be powered, a destination must be set, and guidance must be idle or completed.
        - INVALID_INPUT_ERROR: Route must be fastest, shortest, or scenic.
        """
        if type(route) is not str or route not in ('fastest', 'shortest', 'scenic'):
            return ('[INVALID_INPUT_ERROR]', {})
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[PRECONDITION_FAILED]', {})
        destination_code, destination = self.destination.get()
        if destination_code != '[PASS]':
            return (destination_code, {})
        status_code, status = self.status.get()
        if status_code != '[PASS]':
            return (status_code, {})
        if destination == 'none' or status not in ('idle', 'completed'):
            return ('[PRECONDITION_FAILED]', {})

        if route == 'fastest':
            duration = 12
            distance = 12
        elif route == 'shortest':
            duration = 15
            distance = 10
        else:
            duration = 20
            distance = 18

        code = self.selected_route.internal_set(route)
        if code != '[PASS]':
            return (code, {})
        code = self.status.internal_set('idle')
        if code != '[PASS]':
            return (code, {})
        code = self.phase.internal_set('idle')
        if code != '[PASS]':
            return (code, {})
        code = self.remaining_minutes.internal_set(duration)
        if code != '[PASS]':
            return (code, {})
        code = self.started_at_minute.internal_set(0)
        if code != '[PASS]':
            return (code, {})
        code = self.progress_minutes.internal_set(0)
        if code != '[PASS]':
            return (code, {})
        code = self.remaining_distance.internal_set(distance)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_status(self) -> tuple[str, dict]:
        """
        Return the navigation process state. The module must be powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- status: Navigation state: idle, running, paused, or completed. (type=string)

        Error Codes:
        - PRECONDITION_FAILED: The navigation module must be powered.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[PRECONDITION_FAILED]', {})
        code, value = self.status.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'status': value})

    def get_phase(self) -> tuple[str, dict]:
        """
        Return the current navigation process phase. The module must be powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- phase: Current phase: idle, guidance, or completed. (type=string)

        Error Codes:
        - PRECONDITION_FAILED: The navigation module must be powered.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[PRECONDITION_FAILED]', {})
        code, value = self.phase.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'phase': value})

    def get_estimated_time(self) -> tuple[str, dict]:
        """
        Return the estimated whole minutes remaining in the current synthetic route. The module must be powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- estimated_time: Estimated whole minutes remaining. (type=integer)

        Error Codes:
        - PRECONDITION_FAILED: The navigation module must be powered.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[PRECONDITION_FAILED]', {})
        code, value = self.remaining_minutes.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'estimated_time': value})

    def get_started_at_minute(self) -> tuple[str, dict]:
        """
        Return the simulation elapsed-minute timestamp used as the guidance progress origin. The module must be powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- started_at_minute: Guidance progress origin in simulation elapsed minutes. (type=integer)

        Error Codes:
        - PRECONDITION_FAILED: The navigation module must be powered.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[PRECONDITION_FAILED]', {})
        code, value = self.started_at_minute.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'started_at_minute': value})

    def get_progress_minutes(self) -> tuple[str, dict]:
        """
        Return the whole minutes of simulated route progress. The module must be powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- progress_minutes: Whole elapsed guidance minutes. (type=integer)

        Error Codes:
        - PRECONDITION_FAILED: The navigation module must be powered.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[PRECONDITION_FAILED]', {})
        code, value = self.progress_minutes.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'progress_minutes': value})

    def get_remaining_distance(self) -> tuple[str, dict]:
        """
        Return the estimated whole kilometers remaining in the selected synthetic route. The module must be powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- remaining_distance: Estimated whole kilometers remaining. (type=integer)

        Error Codes:
        - PRECONDITION_FAILED: The navigation module must be powered.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[PRECONDITION_FAILED]', {})
        code, value = self.remaining_distance.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'remaining_distance': value})

    def get_voice_guidance(self) -> tuple[str, dict]:
        """
        Return whether simulated voice guidance is enabled. The module must be powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- voice_guidance: Whether navigation voice prompts are enabled. (type=boolean)

        Error Codes:
        - PRECONDITION_FAILED: The navigation module must be powered.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[PRECONDITION_FAILED]', {})
        code, value = self.voice_guidance.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'voice_guidance': value})

    def set_voice_guidance(self, enabled: bool) -> tuple[str, dict]:
        """
        Enable or disable simulated navigation voice prompts while powered. Invalid input leaves state unchanged.

        Args:
        - enabled:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The navigation module must be powered.
        """
        if type(enabled) is not bool:
            return ('[INVALID_INPUT_ERROR]', {})
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[PRECONDITION_FAILED]', {})
        code = self.voice_guidance.set(enabled)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_guidance_volume(self) -> tuple[str, dict]:
        """
        Return the configured navigation prompt audio level. The module must be powered.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- guidance_volume: Configured navigation prompt audio level in dBA. (type=integer)

        Error Codes:
        - PRECONDITION_FAILED: The navigation module must be powered.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[PRECONDITION_FAILED]', {})
        code, value = self.guidance_volume.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'guidance_volume': value})

    def set_guidance_volume(self, volume: int) -> tuple[str, dict]:
        """
        Set the simulated navigation prompt audio level from 0 through 120 dBA while powered. Invalid input leaves state unchanged.

        Args:
        - volume:  (min=0, max=120)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The navigation module must be powered.
        - INVALID_INPUT_ERROR: Volume must be an integer from 0 through 120.
        """
        if type(volume) is not int or volume < 0 or volume > 120:
            return ('[INVALID_INPUT_ERROR]', {})
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[PRECONDITION_FAILED]', {})
        code = self.guidance_volume.set(volume)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def start_guidance(self, route: str) -> tuple[str, dict]:
        """
        Start deterministic guidance while powered using the supplied route profile. A destination must already be set and the process must be idle or completed. Fastest starts at 12 km for 12 minutes, shortest at 10 km for 15 minutes, and scenic at 18 km for 20 minutes. Progress starts at zero, so successful start does not itself represent movement or arrival.

        Args:
        - route:  (choices=['fastest', 'shortest', 'scenic'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The module must be powered, a destination must be set, and guidance must be idle or completed.
        - INVALID_INPUT_ERROR: Route must be fastest, shortest, or scenic.
        """
        if type(route) is not str or route not in ('fastest', 'shortest', 'scenic'):
            return ('[INVALID_INPUT_ERROR]', {})
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[PRECONDITION_FAILED]', {})
        destination_code, destination = self.destination.get()
        if destination_code != '[PASS]':
            return (destination_code, {})
        status_code, status = self.status.get()
        if status_code != '[PASS]':
            return (status_code, {})
        if destination == 'none' or status not in ('idle', 'completed'):
            return ('[PRECONDITION_FAILED]', {})

        if route == 'fastest':
            duration = 12
            distance = 12
        elif route == 'shortest':
            duration = 15
            distance = 10
        else:
            duration = 20
            distance = 18

        code = self.selected_route.internal_set(route)
        if code != '[PASS]':
            return (code, {})
        code = self.status.internal_set('running')
        if code != '[PASS]':
            return (code, {})
        code = self.phase.internal_set('guidance')
        if code != '[PASS]':
            return (code, {})
        code = self.remaining_minutes.internal_set(duration)
        if code != '[PASS]':
            return (code, {})
        code = self.started_at_minute.internal_set(0)
        if code != '[PASS]':
            return (code, {})
        code = self.progress_minutes.internal_set(0)
        if code != '[PASS]':
            return (code, {})
        code = self.remaining_distance.internal_set(distance)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def pause_guidance(self) -> tuple[str, dict]:
        """
        Pause running guidance while powered. Current progress, remaining time, and remaining distance are retained. Calling this action unless guidance is running is rejected without mutation.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The module must be powered and guidance must be running.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[PRECONDITION_FAILED]', {})
        status_code, status = self.status.get()
        if status_code != '[PASS]':
            return (status_code, {})
        if status != 'running':
            return ('[PRECONDITION_FAILED]', {})
        code = self.status.internal_set('paused')
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def resume_guidance(self) -> tuple[str, dict]:
        """
        Resume paused guidance while powered without resetting progress. The timing origin is recalculated from the retained progress. Calling this action unless guidance is paused is rejected without mutation.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The module must be powered and guidance must be paused.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[PRECONDITION_FAILED]', {})
        status_code, status = self.status.get()
        if status_code != '[PASS]':
            return (status_code, {})
        if status != 'paused':
            return ('[PRECONDITION_FAILED]', {})
        code = self.status.internal_set('running')
        if code != '[PASS]':
            return (code, {})
        code = self.phase.internal_set('guidance')
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def cancel_guidance(self) -> tuple[str, dict]:
        """
        Cancel running or paused guidance while powered and return the process to idle. The destination and selected route are preserved, while progress is reset and the selected route's full preview distance and time are restored. Calling this action in any other state is rejected without mutation.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The module must be powered and guidance must be running or paused.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, {})
        if not powered:
            return ('[PRECONDITION_FAILED]', {})
        status_code, status = self.status.get()
        if status_code != '[PASS]':
            return (status_code, {})
        route_code, route = self.selected_route.get()
        if route_code != '[PASS]':
            return (route_code, {})
        if status not in ('running', 'paused') or route not in ('fastest', 'shortest', 'scenic'):
            return ('[PRECONDITION_FAILED]', {})

        if route == 'fastest':
            duration = 12
            distance = 12
        elif route == 'shortest':
            duration = 15
            distance = 10
        else:
            duration = 20
            distance = 18

        code = self.status.internal_set('idle')
        if code != '[PASS]':
            return (code, {})
        code = self.phase.internal_set('idle')
        if code != '[PASS]':
            return (code, {})
        code = self.remaining_minutes.internal_set(duration)
        if code != '[PASS]':
            return (code, {})
        code = self.started_at_minute.internal_set(0)
        if code != '[PASS]':
            return (code, {})
        code = self.progress_minutes.internal_set(0)
        if code != '[PASS]':
            return (code, {})
        code = self.remaining_distance.internal_set(distance)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        While powered and running, advance guidance progress from its recorded start minute. Remaining time is the route duration minus progress. Remaining distance is the route's initial distance multiplied by the fraction of route time remaining and rounded up to the next whole kilometer. At the exact route-duration boundary, set remaining time and distance to zero and mark status and phase completed. Contribute guidance_volume to cabin audio_level only while powered, running, and enabled for voice guidance; otherwise contribute zero.

    Effect properties:
    - power: Determines whether guidance may advance and whether prompt audio may be emitted.
    - selected_route: Determines the fixed route duration and initial distance.
    - status: Determines whether route progress and prompt audio are active.
    - phase: Tracks the active or completed navigation phase.
    - remaining_minutes: Stores the route's estimated remaining time.
    - started_at_minute: Provides the elapsed-minute origin for deterministic progress.
    - progress_minutes: Stores elapsed route progress.
    - remaining_distance: Stores the proportionally calculated whole kilometers remaining.
    - voice_guidance: Determines whether navigation prompts contribute audio.
    - guidance_volume: Sets the active navigation prompt audio contribution.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, [])

        contribution = 0

        if powered:
            status_code, status = self.status.get()
            if status_code != '[PASS]':
                return (status_code, [])

            if status == 'running':
                route_code, route = self.selected_route.get()
                if route_code != '[PASS]':
                    return (route_code, [])
                phase_code, phase = self.phase.get()
                if phase_code != '[PASS]':
                    return (phase_code, [])
                remaining_code, old_remaining = self.remaining_minutes.get()
                if remaining_code != '[PASS]':
                    return (remaining_code, [])
                started_code, started = self.started_at_minute.get()
                if started_code != '[PASS]':
                    return (started_code, [])
                progress_code, old_progress = self.progress_minutes.get()
                if progress_code != '[PASS]':
                    return (progress_code, [])
                distance_code, old_distance = self.remaining_distance.get()
                if distance_code != '[PASS]':
                    return (distance_code, [])
                voice_code, voice_enabled = self.voice_guidance.get()
                if voice_code != '[PASS]':
                    return (voice_code, [])
                volume_code, volume = self.guidance_volume.get()
                if volume_code != '[PASS]':
                    return (volume_code, [])

                if route == 'fastest':
                    duration = 12
                    initial_distance = 12
                elif route == 'shortest':
                    duration = 15
                    initial_distance = 10
                elif route == 'scenic':
                    duration = 20
                    initial_distance = 18
                else:
                    return ('[INVALID_STATE_ERROR]', [])

                elapsed_minute = context['time_state']['elapsed_minutes']
                progress = elapsed_minute - started
                if progress < 0:
                    progress = 0
                if progress > duration:
                    progress = duration

                remaining = duration - progress
                if remaining == 0:
                    distance = 0
                else:
                    distance = (
                        initial_distance * remaining + duration - 1
                    ) // duration

                if progress != old_progress:
                    code = self.progress_minutes.internal_set(progress)
                    if code != '[PASS]':
                        return (code, [])
                if remaining != old_remaining:
                    code = self.remaining_minutes.internal_set(remaining)
                    if code != '[PASS]':
                        return (code, [])
                if distance != old_distance:
                    code = self.remaining_distance.internal_set(distance)
                    if code != '[PASS]':
                        return (code, [])

                if progress >= duration:
                    if status != 'completed':
                        code = self.status.internal_set('completed')
                        if code != '[PASS]':
                            return (code, [])
                    if phase != 'completed':
                        code = self.phase.internal_set('completed')
                        if code != '[PASS]':
                            return (code, [])
                    contribution = 0
                elif voice_enabled:
                    contribution = volume

        cabin_id = next(
            space_id
            for space_id, space in context['pre_state']['spaces'].items()
            if space['type'] == 'cabin'
        )
        effect = {
            'trigger': 'tick',
            'source': context['object_id'],
            'target': cabin_id,
            'function': 'set_contribution',
            'parameters': {
                'property': 'audio_level',
                'value': contribution,
                'unit': 'dBA'
            }
        }
        return ('[PASS]', [effect])

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        When a successful action transitions guidance into the running state, establish the timing origin from retained progress. If power becomes false while guidance is running, change the process state to paused without discarding progress. This event emits no cabin sound effect; sustained prompt audio is handled only by the tick event.

    Effect properties:
    - power: Determines whether running guidance must be paused.
    - status: Identifies transitions into running and running guidance interrupted by power loss.
    - progress_minutes: Preserves existing progress when calculating the process timing origin.
    - started_at_minute: Stores the elapsed-minute origin used by subsequent guidance ticks.
        """
        power_code, powered = self.power.get()
        if power_code != '[PASS]':
            return (power_code, [])

        previous_properties = context['pre_state']['objects'][context['object_id']]['properties']
        previous_power = previous_properties['power']
        previous_status = previous_properties['status']

        if previous_power is True and powered is False and previous_status == 'running':
            code = self.status.internal_set('paused')
            if code != '[PASS]':
                return (code, [])
            return ('[PASS]', [])

        if powered:
            status_code, status = self.status.get()
            if status_code != '[PASS]':
                return (status_code, [])
            if status == 'running' and previous_status != 'running':
                progress_code, progress = self.progress_minutes.get()
                if progress_code != '[PASS]':
                    return (progress_code, [])
                origin = context['time_state']['elapsed_minutes'] - progress
                code = self.started_at_minute.internal_set(origin)
                if code != '[PASS]':
                    return (code, [])

        return ('[PASS]', [])