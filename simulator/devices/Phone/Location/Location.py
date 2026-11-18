# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Location:
    """
    Location
    Description: Location settings, placed in Setting and contained by System. Supports querying and changing the system-wide location switch, querying application location permissions and effective location availability, and requesting the current synthetic location when conditions are satisfied. Per-application foreground, background, and precision authorizations are owned and modified by Privacy; this module only references them. Position, accuracy, and sample time are read-only feedback. Even when the system-wide switch is enabled, application authorization, running state, and simulated location-source availability must be satisfied. Failures must not fabricate successful locations. Disabling the switch stops new location acquisition.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, enabled: bool = None, source_available: bool = None, application_access: dict = None, last_location: dict = None) -> None:
        # define properties
        self.enabled = BoolProperty(
            name='enabled',
            description='Whether the system-wide location switch is enabled. Enabling the switch does not itself grant application authorization or guarantee source availability.',
            default=False
        )
        self.source_available = BoolProperty(
            name='source_available',
            description='Read-only feedback indicating whether the synthetic location source is currently available.',
            default=True,
            mode=2
        )
        self.application_access = DictProperty(
            name='application_access',
            description='Read-only referenced application records keyed by application ID. Each record contains foreground_authorized, background_authorized, precise_authorized, and running_state. Authorization values are owned by Privacy, while running state is supplied by the corresponding application-state dependency.',
            default={'maps': {'foreground_authorized': True, 'background_authorized': False, 'precise_authorized': True, 'running_state': 'foreground'}, 'fitness': {'foreground_authorized': True, 'background_authorized': True, 'precise_authorized': False, 'running_state': 'background'}},
            mode=2
        )
        self.last_location = DictProperty(
            name='last_location',
            description='Read-only feedback for the last successful synthetic location acquisition. has_sample is false until a request succeeds; latitude, longitude, accuracy_meters, and sample_time_minute are then populated. sample_time_minute uses monotonic elapsed simulation minutes.',
            default={'has_sample': False, 'application_id': '', 'latitude': None, 'longitude': None, 'accuracy_meters': None, 'sample_time_minute': None},
            mode=2
        )

        # initialize properties
        if enabled is not None: code = self.enabled.internal_set(enabled)
        if source_available is not None: code = self.source_available.internal_set(source_available)
        if application_access is not None: code = self.application_access.internal_set(application_access)
        if last_location is not None: code = self.last_location.internal_set(last_location)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_enabled(self) -> tuple[str, dict]:
        """
        Return whether the system-wide location switch is enabled without changing any state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- enabled: Whether the system-wide location switch is enabled. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.enabled.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'enabled': value
        }
        return code, response

    def set_enabled(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable the system-wide location switch. Disabling immediately prevents new location acquisitions but retains the last successful sample as historical feedback. Enabling does not grant permissions or make an unavailable source available.

        Args:
        - value: The desired system-wide location switch state.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.enabled.set(value)
        if code != '[PASS]':
            return code, {}
        response = {}
        return code, response

    def get_source_available(self) -> tuple[str, dict]:
        """
        Return whether the deterministic synthetic location source is currently available.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- source_available: Whether the synthetic location source is currently available. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.source_available.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'source_available': value
        }
        return code, response

    def get_application_location_access(self, application_id: str) -> tuple[str, dict]:
        """
        Return the referenced location authorization and running-state record for an existing application ID. This operation does not modify permissions; Privacy remains authoritative for authorization.

        Args:
        - application_id: An existing application ID in application_access.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- application_location_access: The application's referenced foreground, background, and precision authorizations together with its current running state. (type=object)

        Error Codes:
        - NOT_FOUND: The application ID does not exist in application_access.
        """
        code, application_access = self.application_access.get()
        if code != '[PASS]':
            return code, {}
        if type(application_id) is not str or application_id not in application_access:
            return '[NOT_FOUND]', {}
        record = application_access[application_id]
        response = {
            'application_location_access': dict(record)
        }
        return '[PASS]', response

    def get_effective_location_availability(self, application_id: str) -> tuple[str, dict]:
        """
        Determine effective location availability for an existing application without acquiring a sample. Availability is true only when the system switch is enabled, the source is available, and the application is running in an authorized state: foreground requires foreground authorization, background requires background authorization, and stopped is never available. Precision authorization affects result accuracy but not basic availability.

        Args:
        - application_id: An existing application ID in application_access.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- available: Whether the application can currently acquire a synthetic location. (type=boolean)

        Error Codes:
        - NOT_FOUND: The application ID does not exist in application_access.
        """
        code, application_access = self.application_access.get()
        if code != '[PASS]':
            return code, {}
        if type(application_id) is not str or application_id not in application_access:
            return '[NOT_FOUND]', {}

        code, enabled = self.enabled.get()
        if code != '[PASS]':
            return code, {}
        code, source_available = self.source_available.get()
        if code != '[PASS]':
            return code, {}

        record = application_access[application_id]
        running_state = record['running_state']
        authorized = False
        if running_state == 'foreground':
            authorized = record['foreground_authorized']
        elif running_state == 'background':
            authorized = record['background_authorized']

        response = {
            'available': enabled and source_available and authorized
        }
        return '[PASS]', response

    def get_last_location(self) -> tuple[str, dict]:
        """
        Return the last successful synthetic location sample. Before the first success, has_sample is false and the position, accuracy, and sample time fields are null.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- last_location: The last successful location sample and its originating application ID, or an empty sample record when no request has succeeded. (type=object)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.last_location.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'last_location': dict(value)
        }
        return code, response

    def request_current_location(self, application_id: str) -> tuple[str, dict]:
        """
        Request a current deterministic synthetic location for an existing application. The request succeeds only when the system switch is enabled, the source is available, and the application's running state has the required referenced authorization. A foreground application requires foreground authorization; a background application requires background authorization; a stopped application is rejected. Precise authorization produces latitude 35.1234, longitude -120.5678, and 10-meter accuracy. Otherwise a permitted request produces latitude 35.12, longitude -120.57, and 1000-meter accuracy. A successful request records the current elapsed simulation minute. Any failure leaves last_location unchanged.

        Args:
        - application_id: An existing application ID requesting location.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- location: The newly acquired synthetic position, accuracy, requesting application ID, and elapsed simulation sample minute. (type=object)

        Error Codes:
        - NOT_FOUND: The application ID does not exist in application_access.
        - LOCATION_DISABLED: The system-wide location switch is disabled.
        - SOURCE_UNAVAILABLE: The synthetic location source is unavailable.
        - APPLICATION_NOT_RUNNING: The application running state is stopped or otherwise unsupported.
        - PERMISSION_DENIED: The application's referenced authorization does not permit location access in its current running state.
        """
        code, application_access = self.application_access.get()
        if code != '[PASS]':
            return code, {}
        if type(application_id) is not str or application_id not in application_access:
            return '[NOT_FOUND]', {}

        code, enabled = self.enabled.get()
        if code != '[PASS]':
            return code, {}
        if not enabled:
            return '[LOCATION_DISABLED]', {}

        code, source_available = self.source_available.get()
        if code != '[PASS]':
            return code, {}
        if not source_available:
            return '[SOURCE_UNAVAILABLE]', {}

        record = application_access[application_id]
        running_state = record['running_state']
        if running_state not in ('foreground', 'background'):
            return '[APPLICATION_NOT_RUNNING]', {}

        if running_state == 'foreground':
            authorized = record['foreground_authorized']
        else:
            authorized = record['background_authorized']
        if not authorized:
            return '[PERMISSION_DENIED]', {}

        if record['precise_authorized']:
            latitude = 35.1234
            longitude = -120.5678
            accuracy_meters = 10
        else:
            latitude = 35.12
            longitude = -120.57
            accuracy_meters = 1000

        code, previous_location = self.last_location.get()
        if code != '[PASS]':
            return code, {}
        previous_sample_time = previous_location['sample_time_minute']
        if previous_sample_time is None:
            sample_time_minute = 0
        else:
            sample_time_minute = previous_sample_time

        location = {
            'has_sample': True,
            'application_id': application_id,
            'latitude': latitude,
            'longitude': longitude,
            'accuracy_meters': accuracy_meters,
            'sample_time_minute': sample_time_minute
        }
        code = self.last_location.internal_set(location)
        if code != '[PASS]':
            return code, {}

        response = {
            'location': dict(location)
        }
        return '[PASS]', response

    def _on_dependency_changed(self, context: dict) -> tuple[str, list[dict]]:
        """
        When declared Privacy, application-state, or location-source dependencies change, refreshes the read-only application authorization and running-state references and the synthetic source-availability feedback. It does not acquire or fabricate a location sample.

    Effect properties:
    - source_available: Read-only synthetic location-source availability refreshed from its declared dependency.
    - application_access: Read-only application authorization and running-state references refreshed from declared dependencies.
        """
        code, current_source_available = self.source_available.get()
        if code != '[PASS]':
            return code, []
        code, current_application_access = self.application_access.get()
        if code != '[PASS]':
            return code, []

        new_source_available = current_source_available
        new_application_access = {
            application_id: dict(record)
            for application_id, record in current_application_access.items()
        }

        for properties in context['dependencies'].values():
            if 'source_available' in properties:
                source_value = properties['source_available']
                if type(source_value) is bool:
                    new_source_available = source_value

            if 'application_access' in properties:
                dependency_access = properties['application_access']
                if type(dependency_access) is dict:
                    for application_id, dependency_record in dependency_access.items():
                        if type(application_id) is not str or type(dependency_record) is not dict:
                            continue
                        if application_id in new_application_access:
                            record = dict(new_application_access[application_id])
                        else:
                            record = {
                                'foreground_authorized': False,
                                'background_authorized': False,
                                'precise_authorized': False,
                                'running_state': 'stopped'
                            }
                        if (
                            'foreground_authorized' in dependency_record
                            and type(dependency_record['foreground_authorized']) is bool
                        ):
                            record['foreground_authorized'] = dependency_record['foreground_authorized']
                        if (
                            'background_authorized' in dependency_record
                            and type(dependency_record['background_authorized']) is bool
                        ):
                            record['background_authorized'] = dependency_record['background_authorized']
                        if (
                            'precise_authorized' in dependency_record
                            and type(dependency_record['precise_authorized']) is bool
                        ):
                            record['precise_authorized'] = dependency_record['precise_authorized']
                        if (
                            'running_state' in dependency_record
                            and dependency_record['running_state'] in ('foreground', 'background', 'stopped')
                        ):
                            record['running_state'] = dependency_record['running_state']
                        new_application_access[application_id] = record

            if 'application_permissions' in properties:
                dependency_permissions = properties['application_permissions']
                if type(dependency_permissions) is dict:
                    for application_id, permission_record in dependency_permissions.items():
                        if type(application_id) is not str or type(permission_record) is not dict:
                            continue
                        if application_id in new_application_access:
                            record = dict(new_application_access[application_id])
                        else:
                            record = {
                                'foreground_authorized': False,
                                'background_authorized': False,
                                'precise_authorized': False,
                                'running_state': 'stopped'
                            }
                        if (
                            'foreground_authorized' in permission_record
                            and type(permission_record['foreground_authorized']) is bool
                        ):
                            record['foreground_authorized'] = permission_record['foreground_authorized']
                        if (
                            'background_authorized' in permission_record
                            and type(permission_record['background_authorized']) is bool
                        ):
                            record['background_authorized'] = permission_record['background_authorized']
                        if (
                            'precise_authorized' in permission_record
                            and type(permission_record['precise_authorized']) is bool
                        ):
                            record['precise_authorized'] = permission_record['precise_authorized']
                        new_application_access[application_id] = record

            if 'application_states' in properties:
                dependency_states = properties['application_states']
                if type(dependency_states) is dict:
                    for application_id, state_record in dependency_states.items():
                        if type(application_id) is not str:
                            continue
                        if application_id in new_application_access:
                            record = dict(new_application_access[application_id])
                        else:
                            record = {
                                'foreground_authorized': False,
                                'background_authorized': False,
                                'precise_authorized': False,
                                'running_state': 'stopped'
                            }
                        if type(state_record) is str:
                            running_state = state_record
                        elif type(state_record) is dict and 'running_state' in state_record:
                            running_state = state_record['running_state']
                        else:
                            running_state = None
                        if running_state in ('foreground', 'background', 'stopped'):
                            record['running_state'] = running_state
                        new_application_access[application_id] = record

            if 'running_states' in properties:
                dependency_states = properties['running_states']
                if type(dependency_states) is dict:
                    for application_id, running_state in dependency_states.items():
                        if type(application_id) is not str:
                            continue
                        if type(running_state) is dict and 'running_state' in running_state:
                            running_state = running_state['running_state']
                        if running_state not in ('foreground', 'background', 'stopped'):
                            continue
                        if application_id in new_application_access:
                            record = dict(new_application_access[application_id])
                        else:
                            record = {
                                'foreground_authorized': False,
                                'background_authorized': False,
                                'precise_authorized': False,
                                'running_state': 'stopped'
                            }
                        record['running_state'] = running_state
                        new_application_access[application_id] = record

        code = self.source_available.internal_set(new_source_available)
        if code != '[PASS]':
            return code, []
        code = self.application_access.internal_set(new_application_access)
        if code != '[PASS]':
            return code, []

        return '[PASS]', []