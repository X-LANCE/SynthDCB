# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class SystemSettings:
    """
    SystemSettings
    Description: System preference settings, placed in Setting and contained by System. Supports querying and setting the system language and specified application languages, toggling automatic date/time and automatic time zone, setting manual date/time or time zone, and querying and changing default application roles. Available languages, application-supported languages, and role candidates are read-only configuration. An application language may follow the system. Changing a role requires candidate eligibility checks and simulated user confirmation; denial preserves the original setting. Manual wall-clock changes are prohibited while automatic time is enabled, and manual time-zone selection is prohibited while automatic time zone is enabled. Automatic synchronization uses only a local simulated time source without network access. Adjustments affect the phone wall-clock offset and time zone, not the world monotonic clock, and must not move Timer or Stopwatch backward.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, available_languages: dict = None, system_language: str = None, application_supported_languages: dict = None, application_languages: dict = None, automatic_time: bool = None, wall_clock_offset_minutes: int = None, automatic_time_zone: bool = None, time_zone: str = None, role_candidates: dict = None, default_application_roles: dict = None) -> None:
        # define properties
        self.available_languages = DictProperty(
            name='available_languages',
            description='Read-only language configuration keyed by supported language identifier.',
            default={'en-US': {'name': 'English (United States)'}, 'es-ES': {'name': 'Spanish (Spain)'}, 'zh-CN': {'name': 'Chinese (Simplified)'}},
            mode=2
        )
        self.system_language = StringProperty(
            name='system_language',
            description='The language identifier used by the phone system and by applications configured to follow the system language.',
            default='en-US',
            choices=['en-US', 'es-ES', 'zh-CN']
        )
        self.application_supported_languages = DictProperty(
            name='application_supported_languages',
            description='Read-only application language capabilities keyed by application ID. Each record lists the explicit language identifiers supported by that application.',
            default={'browser': {'languages': ['en-US', 'es-ES', 'zh-CN']}, 'maps': {'languages': ['en-US', 'es-ES']}},
            mode=2
        )
        self.application_languages = DictProperty(
            name='application_languages',
            description='Application language preferences keyed by application ID. A language value of system means that the application dynamically follows system_language.',
            default={'browser': {'language': 'system'}, 'maps': {'language': 'system'}},
            mode=2
        )
        self.automatic_time = BoolProperty(
            name='automatic_time',
            description='Whether phone wall-clock date and time are synchronized to the local simulated time source.',
            default=True
        )
        self.wall_clock_offset_minutes = IntProperty(
            name='wall_clock_offset_minutes',
            description='Manual phone wall-clock adjustment in whole minutes relative to the local simulated time source. Zero represents synchronized date and time. This offset never changes the world monotonic clock.',
            default=0,
            unit='minutes',
            minimum=-525600,
            maximum=525600,
            step=1,
            step_origin=0
        )
        self.automatic_time_zone = BoolProperty(
            name='automatic_time_zone',
            description='Whether the phone time zone follows the deterministic local simulated time-zone source.',
            default=True
        )
        self.time_zone = StringProperty(
            name='time_zone',
            description='The phone time-zone identifier used to interpret its wall clock. The local simulated automatic time-zone source resolves to UTC.',
            default='UTC',
            choices=['UTC', 'America/New_York', 'Europe/Madrid', 'Asia/Shanghai']
        )
        self.role_candidates = DictProperty(
            name='role_candidates',
            description='Read-only eligible application candidates keyed by default-role ID.',
            default={'browser': {'applications': ['browser_alpha', 'browser_beta']}, 'maps': {'applications': ['maps_standard', 'maps_offline']}},
            mode=2
        )
        self.default_application_roles = DictProperty(
            name='default_application_roles',
            description='Current default application selections keyed by role ID.',
            default={'browser': {'application_id': 'browser_alpha'}, 'maps': {'application_id': 'maps_standard'}},
            mode=2
        )

        # initialize properties
        if available_languages is not None: code = self.available_languages.internal_set(available_languages)
        if system_language is not None: code = self.system_language.internal_set(system_language)
        if application_supported_languages is not None: code = self.application_supported_languages.internal_set(application_supported_languages)
        if application_languages is not None: code = self.application_languages.internal_set(application_languages)
        if automatic_time is not None: code = self.automatic_time.internal_set(automatic_time)
        if wall_clock_offset_minutes is not None: code = self.wall_clock_offset_minutes.internal_set(wall_clock_offset_minutes)
        if automatic_time_zone is not None: code = self.automatic_time_zone.internal_set(automatic_time_zone)
        if time_zone is not None: code = self.time_zone.internal_set(time_zone)
        if role_candidates is not None: code = self.role_candidates.internal_set(role_candidates)
        if default_application_roles is not None: code = self.default_application_roles.internal_set(default_application_roles)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_available_language(self, language: str) -> tuple[str, dict]:
        """
        Return the read-only configuration record for an available language. An unknown language identifier is rejected without changing state.

        Args:
        - language:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- language: The selected available-language configuration record. (type=object)

        Error Codes:
        - NOT_FOUND: The language identifier is not available.
        """
        code, languages = self.available_languages.get()
        if code != '[PASS]':
            return code, {}
        if type(language) is not str or language not in languages:
            return '[NOT_FOUND]', {}
        response = {
            'language': dict(languages[language])
        }
        return '[PASS]', response

    def get_system_language(self) -> tuple[str, dict]:
        """
        Return the current system language identifier without changing any preference.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- system_language: The current system language identifier. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.system_language.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'system_language': value
        }
        return code, response

    def set_system_language(self, language: str) -> tuple[str, dict]:
        """
        Set the system language to an identifier in available_languages. Applications whose language preference is system follow the new value without rewriting their records. Unsupported identifiers are rejected and leave all preferences unchanged.

        Args:
        - language:  (choices=['en-US', 'es-ES', 'zh-CN'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - NOT_FOUND: The requested system language is not available.
        """
        code, languages = self.available_languages.get()
        if code != '[PASS]':
            return code, {}
        if type(language) is not str or language not in languages:
            return '[NOT_FOUND]', {}
        code = self.system_language.set(language)
        return code, {}

    def get_application_supported_languages(self, application_id: str) -> tuple[str, dict]:
        """
        Return the read-only supported-language record for a specified application. An unknown application ID is rejected without changing state.

        Args:
        - application_id:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- supported_languages: The selected application's supported-language configuration record. (type=object)

        Error Codes:
        - NOT_FOUND: The application ID has no language capability record.
        """
        code, supported = self.application_supported_languages.get()
        if code != '[PASS]':
            return code, {}
        if type(application_id) is not str or application_id not in supported:
            return '[NOT_FOUND]', {}
        record = supported[application_id]
        copied_record = {
            key: list(value) if type(value) is list else value
            for key, value in record.items()
        }
        response = {
            'supported_languages': copied_record
        }
        return '[PASS]', response

    def get_application_language(self, application_id: str) -> tuple[str, dict]:
        """
        Return the language preference record for a specified application. A stored value of system means the application follows system_language.

        Args:
        - application_id:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- application_language: The selected application's language preference record. (type=object)

        Error Codes:
        - NOT_FOUND: The application ID has no language preference record.
        """
        code, preferences = self.application_languages.get()
        if code != '[PASS]':
            return code, {}
        if type(application_id) is not str or application_id not in preferences:
            return '[NOT_FOUND]', {}
        response = {
            'application_language': dict(preferences[application_id])
        }
        return '[PASS]', response

    def set_application_language(self, application_id: str, language: str) -> tuple[str, dict]:
        """
        Set one existing application's language preference while preserving every other application record. The value system makes the application follow system_language. Any explicit language must appear in that application's application_supported_languages record. Unknown applications or unsupported explicit languages are rejected before any state change.

        Args:
        - application_id: 
        - language:  (choices=['system', 'en-US', 'es-ES', 'zh-CN'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - NOT_FOUND: The application ID has no language preference record.
        - UNSUPPORTED_LANGUAGE: The explicit language is not supported by the selected application.
        """
        code, preferences = self.application_languages.get()
        if code != '[PASS]':
            return code, {}
        if type(application_id) is not str or application_id not in preferences:
            return '[NOT_FOUND]', {}

        code, supported = self.application_supported_languages.get()
        if code != '[PASS]':
            return code, {}
        if application_id not in supported:
            return '[NOT_FOUND]', {}

        if type(language) is not str:
            return '[UNSUPPORTED_LANGUAGE]', {}
        if language != 'system':
            supported_languages = supported[application_id].get('languages', [])
            if language not in supported_languages:
                return '[UNSUPPORTED_LANGUAGE]', {}

        updated_preferences = {
            key: dict(record)
            for key, record in preferences.items()
        }
        updated_preferences[application_id]['language'] = language
        code = self.application_languages.internal_set(updated_preferences)
        return code, {}

    def get_automatic_time(self) -> tuple[str, dict]:
        """
        Return whether phone date and time are synchronized to the local simulated time source.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- automatic_time: Whether automatic date and time synchronization is enabled. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.automatic_time.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'automatic_time': value
        }
        return code, response

    def set_automatic_time(self, enabled: bool) -> tuple[str, dict]:
        """
        Enable or disable automatic date and time synchronization. Enabling uses the local simulated time source and resets wall_clock_offset_minutes to zero. Disabling preserves the current offset. No network access occurs, and the world monotonic clock is never changed.

        Args:
        - enabled:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        if type(enabled) is not bool:
            code = self.automatic_time.set(enabled)
            return code, {}

        if enabled:
            code = self.wall_clock_offset_minutes.internal_set(0)
            if code != '[PASS]':
                return code, {}

        code = self.automatic_time.set(enabled)
        return code, {}

    def get_wall_clock_offset_minutes(self) -> tuple[str, dict]:
        """
        Return the phone wall-clock adjustment in whole minutes relative to the local simulated time source. This value does not affect monotonic Timer or Stopwatch progress.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- wall_clock_offset_minutes: The current phone wall-clock offset in whole minutes. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.wall_clock_offset_minutes.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'wall_clock_offset_minutes': value
        }
        return code, response

    def set_manual_datetime(self, wall_clock_offset_minutes: int) -> tuple[str, dict]:
        """
        Set the phone's manual date and time as a whole-minute offset from the local simulated time source. The offset must be between -525600 and 525600 minutes, and automatic_time must be disabled. Invalid input or an enabled automatic-time setting leaves all state unchanged. This operation never modifies the world monotonic clock.

        Args:
        - wall_clock_offset_minutes:  (min=-525600, max=525600)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: Manual date and time cannot be changed while automatic time is enabled.
        """
        code, automatic = self.automatic_time.get()
        if code != '[PASS]':
            return code, {}
        if automatic:
            return '[PRECONDITION_FAILED]', {}
        code = self.wall_clock_offset_minutes.set(wall_clock_offset_minutes)
        return code, {}

    def get_automatic_time_zone(self) -> tuple[str, dict]:
        """
        Return whether the phone time zone follows the local simulated time-zone source.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- automatic_time_zone: Whether automatic time-zone selection is enabled. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.automatic_time_zone.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'automatic_time_zone': value
        }
        return code, response

    def set_automatic_time_zone(self, enabled: bool) -> tuple[str, dict]:
        """
        Enable or disable automatic time-zone selection. Enabling selects UTC from the deterministic local simulated source. Disabling preserves the current time zone. No network access occurs.

        Args:
        - enabled:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        if type(enabled) is not bool:
            code = self.automatic_time_zone.set(enabled)
            return code, {}

        if enabled:
            code = self.time_zone.internal_set('UTC')
            if code != '[PASS]':
                return code, {}

        code = self.automatic_time_zone.set(enabled)
        return code, {}

    def get_time_zone(self) -> tuple[str, dict]:
        """
        Return the phone time-zone identifier without changing its wall clock or monotonic time.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- time_zone: The current phone time-zone identifier. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.time_zone.get()
        if code != '[PASS]':
            return code, {}
        response = {
            'time_zone': value
        }
        return code, response

    def set_manual_time_zone(self, time_zone: str) -> tuple[str, dict]:
        """
        Set the phone time zone to one of UTC, America/New_York, Europe/Madrid, or Asia/Shanghai. Automatic time-zone selection must be disabled. Invalid identifiers or an enabled automatic-time-zone setting leave all state unchanged. The change affects wall-clock interpretation only and never changes monotonic time.

        Args:
        - time_zone:  (choices=['UTC', 'America/New_York', 'Europe/Madrid', 'Asia/Shanghai'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: A manual time zone cannot be selected while automatic time zone is enabled.
        """
        code, automatic = self.automatic_time_zone.get()
        if code != '[PASS]':
            return code, {}
        if automatic:
            return '[PRECONDITION_FAILED]', {}
        code = self.time_zone.set(time_zone)
        return code, {}

    def get_role_candidates(self, role_id: str) -> tuple[str, dict]:
        """
        Return the read-only eligible application candidates for a specified default role. An unknown role ID is rejected without changing state.

        Args:
        - role_id:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- role_candidates: The selected role's eligible-application configuration record. (type=object)

        Error Codes:
        - NOT_FOUND: The default-role ID does not exist.
        """
        code, candidates = self.role_candidates.get()
        if code != '[PASS]':
            return code, {}
        if type(role_id) is not str or role_id not in candidates:
            return '[NOT_FOUND]', {}
        record = candidates[role_id]
        copied_record = {
            key: list(value) if type(value) is list else value
            for key, value in record.items()
        }
        response = {
            'role_candidates': copied_record
        }
        return '[PASS]', response

    def get_default_application_role(self, role_id: str) -> tuple[str, dict]:
        """
        Return the current default application record for a specified role. An unknown role ID is rejected without changing state.

        Args:
        - role_id:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- default_application_role: The selected role's current default-application record. (type=object)

        Error Codes:
        - NOT_FOUND: The default-role ID does not exist.
        """
        code, roles = self.default_application_roles.get()
        if code != '[PASS]':
            return code, {}
        if type(role_id) is not str or role_id not in roles:
            return '[NOT_FOUND]', {}
        response = {
            'default_application_role': dict(roles[role_id])
        }
        return '[PASS]', response

    def change_default_application_role(self, role_id: str, application_id: str, user_confirmed: bool) -> tuple[str, dict]:
        """
        Resolve a simulated request to change one default application role. The role must exist and application_id must be listed in that role's read-only candidate record. When user_confirmed is true, only that role's application_id is changed and all other role records are preserved. When user_confirmed is false, the request is treated as denied and the original role setting is preserved. Invalid role or candidate input is rejected before any state change.

        Args:
        - role_id: 
        - application_id: 
        - user_confirmed: The deterministic result of simulated user confirmation.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- changed: Whether confirmation was granted and the selected role was changed. (type=boolean)
        	- application_id: The application ID that remains selected for the role after the request is resolved. (type=string)

        Error Codes:
        - NOT_FOUND: The default-role ID does not exist.
        - INELIGIBLE_CANDIDATE: The requested application is not an eligible candidate for the selected role.
        """
        code, candidates = self.role_candidates.get()
        if code != '[PASS]':
            return code, {}
        code, roles = self.default_application_roles.get()
        if code != '[PASS]':
            return code, {}

        if type(role_id) is not str or role_id not in candidates or role_id not in roles:
            return '[NOT_FOUND]', {}

        eligible_applications = candidates[role_id].get('applications', [])
        if type(application_id) is not str or application_id not in eligible_applications:
            return '[INELIGIBLE_CANDIDATE]', {}

        if type(user_confirmed) is not bool:
            return '[INVALID_TYPE]', {}

        current_application_id = roles[role_id]['application_id']
        if not user_confirmed:
            response = {
                'changed': False,
                'application_id': current_application_id
            }
            return '[PASS]', response

        updated_roles = {
            key: dict(record)
            for key, record in roles.items()
        }
        updated_roles[role_id]['application_id'] = application_id
        code = self.default_application_roles.internal_set(updated_roles)
        if code != '[PASS]':
            return code, {}

        response = {
            'changed': True,
            'application_id': application_id
        }
        return '[PASS]', response