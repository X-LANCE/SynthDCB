# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..DriveSettings import DriveSettings

class ElectrifiedDriveSettings(DriveSettings):
    """
    ElectrifiedDriveSettings
    Description: Electrified vehicle driving settings. Adds selection of regenerative braking intensity or mode and feedback on the effective setting, without directly writing battery charge level. Applies only to battery-electric, hybrid, or range-extended configurations with configurable energy recovery strategies.
    Version: 1.0.0
    Base: DriveSettings
    """

    def __init__(self, configured_modes: dict = None, requested_regeneration_mode: str = None, effective_regeneration_mode: str = None, **base_kwargs) -> None:
        # initialize base DriveSettings class
        super().__init__(**base_kwargs)
        # define properties
        self.configured_modes = DictProperty(
            name='configured_modes',
            description='Read-only electrified vehicle-model configuration keyed by selectable driving-mode identifier. Each record contains the electrified powertrain types to which the mode applies and its fixed switching condition. The baseline configuration provides a standard mode applicable to electric, hybrid, and range-extended powertrains.',
            default={'standard': {'applicable_powertrain_types': ['electric', 'hybrid', 'range_extended'], 'switching_condition': 'unconditional'}},
            mode=2,
            schema={'type': 'object', 'minProperties': 1, 'propertyNames': {'pattern': '^[A-Za-z0-9_-]{1,32}$'}, 'additionalProperties': {'type': 'object', 'properties': {'applicable_powertrain_types': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': {'type': 'string', 'minLength': 1, 'maxLength': 32, 'enum': ['electric', 'hybrid', 'range_extended']}}, 'switching_condition': {'type': 'string', 'const': 'unconditional'}}, 'required': ['applicable_powertrain_types', 'switching_condition'], 'additionalProperties': False}}
        )
        self.requested_regeneration_mode = StringProperty(
            name='requested_regeneration_mode',
            description='Most recently accepted regenerative-braking strategy request.',
            default='standard',
            choices=['low', 'standard', 'high']
        )
        self.effective_regeneration_mode = StringProperty(
            name='effective_regeneration_mode',
            description='Regenerative-braking strategy currently effective in the simulated electrified powertrain.',
            default='standard',
            mode=2,
            choices=['low', 'standard', 'high']
        )

        # initialize properties
        if configured_modes is not None: code = self.configured_modes.internal_set(configured_modes)
        if requested_regeneration_mode is not None: code = self.requested_regeneration_mode.internal_set(requested_regeneration_mode)
        if effective_regeneration_mode is not None: code = self.effective_regeneration_mode.internal_set(effective_regeneration_mode)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_requested_regeneration_mode(self) -> tuple[str, dict]:
        """
        Return the most recently accepted regenerative-braking strategy request without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- requested_regeneration_mode: Requested regenerative-braking strategy: low, standard, or high. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.requested_regeneration_mode.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'requested_regeneration_mode': value})

    def get_effective_regeneration_mode(self) -> tuple[str, dict]:
        """
        Return the regenerative-braking strategy currently effective in the simulated electrified powertrain without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- effective_regeneration_mode: Effective regenerative-braking strategy: low, standard, or high. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.effective_regeneration_mode.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'effective_regeneration_mode': value})

    def select_regeneration_mode(self, mode: str) -> tuple[str, dict]:
        """
        Select low, standard, or high regenerative-braking intensity. A valid selection atomically updates both the requested and effective regenerative-braking modes. Invalid values leave all state unchanged. This preference change does not directly modify battery charge level, remaining range, vehicle speed, or gear.

        Args:
        - mode:  (choices=['low', 'standard', 'high'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        if type(mode) is not str or mode not in ('low', 'standard', 'high'):
            return ('[INVALID_INPUT_ERROR]', {})

        code = self.requested_regeneration_mode.internal_set(mode)
        if code != '[PASS]':
            return (code, {})

        code = self.effective_regeneration_mode.internal_set(mode)
        if code != '[PASS]':
            return (code, {})

        return ('[PASS]', {})