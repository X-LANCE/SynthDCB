# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Accessibility:
    """
    Accessibility
    Description: Accessibility and readability settings, placed in Setting and contained by System. Supports adjusting font scaling, enabling/disabling captions and reduced-motion preferences, querying installed and enabled assistive services, and requesting activation or deactivation of a specified service through simulated authorization. Font levels and assistive-service capabilities are read-only configuration. Normalized scales must state their mapping to platform levels; synthetic increments are not native cross-platform constraints. Denied authorization leaves service activation unchanged. Screen-reading capability depends on the services actually enabled; setting a preference alone must not imply that all content can be read aloud. Uses system-settings simulation; querying service state does not mean an ordinary application has permission to enable it.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, font_scale_level: str = None, font_levels: dict = None, captions_enabled: bool = None, reduced_motion: bool = None, installed_services: dict = None, enabled_services: dict = None, screen_reading_available: bool = None) -> None:
        # define properties
        self.font_scale_level = StringProperty(
            name='font_scale_level',
            description='Selected normalized font scale level. Each value refers to an entry in font_levels rather than to a native cross-platform platform constant.',
            default='default',
            choices=['small', 'default', 'large', 'extra_large']
        )
        self.font_levels = DictProperty(
            name='font_levels',
            description='Read-only font-level configuration keyed by level ID. Normalized percentages are synthetic simulation values: small is 85%, default is 100%, large is 115%, and extra_large is 130%. Platform adapters map these values to the nearest supported Android, HarmonyOS, or OpenHarmony level; the increments are not native cross-platform constraints.',
            default={'small': {'normalized_percent': 85, 'platform_mapping': 'nearest_supported_level'}, 'default': {'normalized_percent': 100, 'platform_mapping': 'nearest_supported_level'}, 'large': {'normalized_percent': 115, 'platform_mapping': 'nearest_supported_level'}, 'extra_large': {'normalized_percent': 130, 'platform_mapping': 'nearest_supported_level'}},
            mode=2
        )
        self.captions_enabled = BoolProperty(
            name='captions_enabled',
            description='Whether the system caption preference is enabled. Availability and coverage of captions still depend on the content and application.',
            default=False
        )
        self.reduced_motion = BoolProperty(
            name='reduced_motion',
            description='Whether reduced motion is preferred. Applications may interpret this preference according to their own supported behavior.',
            default=False
        )
        self.installed_services = DictProperty(
            name='installed_services',
            description='Read-only synthetic assistive-service catalog keyed by stable service ID. Each record contains a display name and immutable capability list.',
            default={'screen_reader': {'name': 'Synthetic Screen Reader', 'capabilities': ['screen_reading', 'spoken_feedback']}, 'switch_access': {'name': 'Synthetic Switch Access', 'capabilities': ['switch_navigation']}},
            mode=2
        )
        self.enabled_services = DictProperty(
            name='enabled_services',
            description='Currently enabled assistive services keyed by installed service ID. Every value has the exact fixed record structure {"enabled": true}, with no copied name, capabilities, or additional fields. Authorized activation inserts that exact record under the selected service ID, and authorized deactivation removes the selected key. Installed service metadata and capabilities remain owned by installed_services.',
            default={},
            mode=2
        )
        self.screen_reading_available = BoolProperty(
            name='screen_reading_available',
            description='Whether at least one key in enabled_services identifies an installed service whose immutable capabilities include screen_reading. This does not guarantee that every application or item of content can be read aloud.',
            default=False,
            mode=2
        )

        # initialize properties
        if font_scale_level is not None: code = self.font_scale_level.internal_set(font_scale_level)
        if font_levels is not None: code = self.font_levels.internal_set(font_levels)
        if captions_enabled is not None: code = self.captions_enabled.internal_set(captions_enabled)
        if reduced_motion is not None: code = self.reduced_motion.internal_set(reduced_motion)
        if installed_services is not None: code = self.installed_services.internal_set(installed_services)
        if enabled_services is not None: code = self.enabled_services.internal_set(enabled_services)
        if screen_reading_available is not None: code = self.screen_reading_available.internal_set(screen_reading_available)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_font_scale_level(self) -> tuple[str, dict]:
        """
        Return the selected normalized font scale level without changing any accessibility setting.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- font_scale_level: The selected normalized font scale level ID. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.font_scale_level.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'font_scale_level': value})

    def set_font_scale_level(self, level: str) -> tuple[str, dict]:
        """
        Select an existing normalized font level. The level must be a key in the read-only font_levels catalog. Its synthetic normalized percentage is mapped to the nearest level supported by the simulated platform and is not treated as a native cross-platform increment. Invalid level IDs leave the selection unchanged.

        Args:
        - level:  (choices=['small', 'default', 'large', 'extra_large'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - NOT_FOUND: The requested font level does not exist in the read-only font_levels catalog.
        """
        if type(level) is not str:
            code = self.font_scale_level.set(level)
            return (code, {})
        code, levels = self.font_levels.get()
        if code != '[PASS]':
            return (code, {})
        if level not in levels:
            return ('[NOT_FOUND]', {})
        code = self.font_scale_level.set(level)
        return (code, {})

    def get_font_levels(self) -> tuple[str, dict]:
        """
        Return the read-only normalized font-level catalog and its nearest-supported-platform mapping policy.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- font_levels: Read-only font levels keyed by level ID, including synthetic normalized percentages and platform mapping information. (type=object)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.font_levels.get()
        if code != '[PASS]':
            return (code, {})
        copied_levels = {
            key: dict(record)
            for key, record in value.items()
        }
        return ('[PASS]', {'font_levels': copied_levels})

    def get_captions_enabled(self) -> tuple[str, dict]:
        """
        Return whether the system caption preference is enabled. This reports the preference, not whether particular content supplies captions.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- captions_enabled: Whether the system caption preference is enabled. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.captions_enabled.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'captions_enabled': value})

    def set_captions_enabled(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable the system caption preference. This does not create captions for content that does not provide them.

        Args:
        - value:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.captions_enabled.set(value)
        return (code, {})

    def get_reduced_motion(self) -> tuple[str, dict]:
        """
        Return whether reduced motion is preferred without changing the preference.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- reduced_motion: Whether reduced motion is preferred. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.reduced_motion.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'reduced_motion': value})

    def set_reduced_motion(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable the reduced-motion preference. The setting expresses a preference and does not guarantee that every application suppresses all animation.

        Args:
        - value:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.reduced_motion.set(value)
        return (code, {})

    def get_installed_services(self) -> tuple[str, dict]:
        """
        Return all installed synthetic assistive services and their read-only capabilities. Reading this catalog does not grant an ordinary application permission to enable a service.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- installed_services: Installed assistive services keyed by stable service ID with names and immutable capability lists. (type=object)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.installed_services.get()
        if code != '[PASS]':
            return (code, {})
        copied_services = {
            key: {
                'name': record['name'],
                'capabilities': list(record['capabilities'])
            }
            for key, record in value.items()
        }
        return ('[PASS]', {'installed_services': copied_services})

    def get_enabled_services(self) -> tuple[str, dict]:
        """
        Return all currently enabled assistive services. Each returned dictionary value is exactly {"enabled": true}; service names and capabilities are available separately from installed_services. This is a system-settings simulation query and does not imply that an ordinary application can change the returned state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- enabled_services: Enabled assistive services keyed by installed service ID, with every value exactly equal to {"enabled": true}. (type=object)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.enabled_services.get()
        if code != '[PASS]':
            return (code, {})
        copied_services = {
            key: dict(record)
            for key, record in value.items()
        }
        return ('[PASS]', {'enabled_services': copied_services})

    def get_screen_reading_available(self) -> tuple[str, dict]:
        """
        Return whether an enabled assistive service currently declares screen-reading capability. A true result does not guarantee that every application or item of content is readable.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- screen_reading_available: Whether at least one enabled service declares screen_reading capability. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.screen_reading_available.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'screen_reading_available': value})

    def request_service_state(self, service_id: str, activate: bool, authorization_granted: bool) -> tuple[str, dict]:
        """
        Request activation or deactivation of an installed assistive service through a resolved simulated authorization decision. The service ID must be a key in installed_services. If authorization_granted is false, enabled_services and screen_reading_available remain unchanged. If authorization is granted and activate is true, the operation inserts or retains enabled_services[service_id] with the exact value {"enabled": true}; no installed-service fields are copied into that record. If authorization is granted and activate is false, the operation removes service_id from enabled_services. Activation and deactivation are idempotent when the service is already in the requested state. After an authorized request, screen_reading_available is recomputed as true exactly when at least one remaining enabled-service key identifies an installed service whose capabilities list contains screen_reading; otherwise it is false. Invalid input or an unknown service ID causes no mutation. This unified system-settings simulation does not represent a generally available ordinary-application API.

        Args:
        - service_id: Stable ID of an installed assistive service.
        - activate: True to request activation or false to request deactivation.
        - authorization_granted: Resolved simulated authorization result. False represents denial and guarantees that service activation state remains unchanged.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- authorization_granted: The resolved simulated authorization result supplied for the request. (type=boolean)
        	- service_id: The installed service ID addressed by the request. (type=string)
        	- enabled: Whether the specified service is enabled after resolving the request. (type=boolean)
        	- changed: Whether the authorized request changed the specified service's enabled state. (type=boolean)
        	- screen_reading_available: Whether any enabled service declares screen-reading capability after resolving the request. (type=boolean)

        Error Codes:
        - NOT_FOUND: The specified service ID does not exist in installed_services.
        - AUTHORIZATION_DENIED: Simulated authorization was denied; enabled_services and screen_reading_available remain unchanged.
        """
        if type(service_id) is not str:
            return ('[NOT_FOUND]', {})
        if type(activate) is not bool or type(authorization_granted) is not bool:
            return ('[INVALID_ARGUMENT]', {})

        code, installed = self.installed_services.get()
        if code != '[PASS]':
            return (code, {})
        if service_id not in installed:
            return ('[NOT_FOUND]', {})

        code, enabled_services = self.enabled_services.get()
        if code != '[PASS]':
            return (code, {})
        code, screen_reading_available = self.screen_reading_available.get()
        if code != '[PASS]':
            return (code, {})

        currently_enabled = service_id in enabled_services

        if not authorization_granted:
            return (
                '[AUTHORIZATION_DENIED]',
                {
                    'authorization_granted': False,
                    'service_id': service_id,
                    'enabled': currently_enabled,
                    'changed': False,
                    'screen_reading_available': screen_reading_available
                }
            )

        changed = currently_enabled != activate
        updated_services = {
            key: dict(record)
            for key, record in enabled_services.items()
        }

        if activate:
            updated_services[service_id] = {'enabled': True}
        elif service_id in updated_services:
            del updated_services[service_id]

        reading_available = False
        for enabled_service_id in updated_services:
            if enabled_service_id in installed:
                record = installed[enabled_service_id]
                if (
                    type(record) is dict
                    and 'capabilities' in record
                    and type(record['capabilities']) is list
                    and 'screen_reading' in record['capabilities']
                ):
                    reading_available = True
                    break

        code = self.enabled_services.internal_set(updated_services)
        if code != '[PASS]':
            return (code, {})
        code = self.screen_reading_available.internal_set(reading_available)
        if code != '[PASS]':
            return (code, {})

        return (
            '[PASS]',
            {
                'authorization_granted': True,
                'service_id': service_id,
                'enabled': activate,
                'changed': changed,
                'screen_reading_available': reading_available
            }
        )