# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class DriveSettings:
    """
    DriveSettings
    Description: Vehicle driving preference module. Supports selecting a driving mode configured for the vehicle model and querying the requested and effective modes. Available modes, applicable powertrain types, and switching conditions are fixed configuration. Driving modes change powertrain response strategies without directly setting speed or gear or completing a driving task.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, requested_mode: str = None, effective_mode: str = None, configured_modes: dict = None) -> None:
        # define properties
        self.requested_mode = StringProperty(
            name='requested_mode',
            description='Identifier of the most recently accepted driving-mode request. An empty string means no mode has been requested.',
            default='',
            pattern='^$|^[A-Za-z0-9_-]{1,32}$',
            max_length=32
        )
        self.effective_mode = StringProperty(
            name='effective_mode',
            description='Identifier of the driving mode currently effective in the simulated powertrain strategy. An empty string means no configured mode is effective.',
            default='',
            mode=2,
            pattern='^$|^[A-Za-z0-9_-]{1,32}$',
            max_length=32
        )
        self.configured_modes = DictProperty(
            name='configured_modes',
            description='Read-only vehicle-model configuration keyed by selectable driving-mode identifier. Each record contains the powertrain types to which the mode applies and its fixed switching condition. The baseline configuration provides a standard mode applicable to electric, hybrid, and internal-combustion powertrains.',
            default={'standard': {'applicable_powertrain_types': ['electric', 'hybrid', 'internal_combustion'], 'switching_condition': 'unconditional'}},
            mode=2,
            schema={'type': 'object', 'minProperties': 1, 'propertyNames': {'pattern': '^[A-Za-z0-9_-]{1,32}$'}, 'additionalProperties': {'type': 'object', 'properties': {'applicable_powertrain_types': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': {'type': 'string', 'minLength': 1, 'maxLength': 32}}, 'switching_condition': {'type': 'string', 'const': 'unconditional'}}, 'required': ['applicable_powertrain_types', 'switching_condition'], 'additionalProperties': False}}
        )

        # initialize properties
        if requested_mode is not None: code = self.requested_mode.internal_set(requested_mode)
        if effective_mode is not None: code = self.effective_mode.internal_set(effective_mode)
        if configured_modes is not None: code = self.configured_modes.internal_set(configured_modes)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_requested_mode(self) -> tuple[str, dict]:
        """
        Return the most recently accepted driving-mode request without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- requested_mode: Requested configured mode identifier, or an empty string when none has been requested. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.requested_mode.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'requested_mode': value})

    def get_effective_mode(self) -> tuple[str, dict]:
        """
        Return the driving mode currently effective in the simulated powertrain strategy without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- effective_mode: Effective configured mode identifier, or an empty string when no mode is effective. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.effective_mode.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'effective_mode': value})

    def get_mode_configuration(self, mode: str) -> tuple[str, dict]:
        """
        Return the fixed configuration for one available driving mode, including its applicable powertrain types and switching condition. An unknown mode identifier is rejected without changing state.

        Args:
        - mode:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- mode_configuration: Fixed mode record containing applicable_powertrain_types and switching_condition. (type=object)

        Error Codes:
        - PRECONDITION_FAILED: The requested driving mode is not configured for this vehicle model.
        """
        if type(mode) is not str:
            return ('[INVALID_INPUT_ERROR]', {})

        code, configured_modes = self.configured_modes.get()
        if code != '[PASS]':
            return (code, {})

        if mode not in configured_modes:
            return ('[PRECONDITION_FAILED]', {})

        configuration = configured_modes[mode]
        response = {
            'mode_configuration': {
                'applicable_powertrain_types': list(configuration['applicable_powertrain_types']),
                'switching_condition': configuration['switching_condition']
            }
        }
        return ('[PASS]', response)

    def select_drive_mode(self, mode: str) -> tuple[str, dict]:
        """
        Select a driving mode configured for this vehicle model. Under the fixed unconditional switching policy, a valid selection atomically updates both requested_mode and effective_mode. Unknown mode identifiers are rejected and leave all state unchanged. This action changes only driving preferences and does not set vehicle speed or gear.

        Args:
        - mode:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The requested driving mode is not configured for this vehicle model.
        """
        if type(mode) is not str:
            return ('[INVALID_INPUT_ERROR]', {})

        code, configured_modes = self.configured_modes.get()
        if code != '[PASS]':
            return (code, {})

        if mode not in configured_modes:
            return ('[PRECONDITION_FAILED]', {})

        code = self.requested_mode.internal_set(mode)
        if code != '[PASS]':
            return (code, {})

        code = self.effective_mode.internal_set(mode)
        if code != '[PASS]':
            return (code, {})

        return ('[PASS]', {})