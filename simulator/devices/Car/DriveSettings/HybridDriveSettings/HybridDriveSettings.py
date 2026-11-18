# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..DriveSettings import DriveSettings

class HybridDriveSettings(DriveSettings):
    """
    HybridDriveSettings
    Description: Hybrid or range-extended vehicle driving settings. Adds energy-use strategy selection and queries of actual engine and electric-drive operating states, distinguishing user requests from the actual strategy under protection conditions. Instantiate only for vehicle models equipped with both fuel and electric energy systems. Range-extender generation does not imply that the engine directly drives the wheels.
    Version: 1.0.0
    Base: DriveSettings
    """

    def __init__(self, requested_energy_strategy: str = None, effective_energy_strategy: str = None, configured_energy_strategies: dict = None, protection_active: bool = None, protection_strategy: str = None, engine_operating_state: str = None, electric_drive_operating_state: str = None, **base_kwargs) -> None:
        # initialize base DriveSettings class
        super().__init__(**base_kwargs)
        # define properties
        self.requested_energy_strategy = StringProperty(
            name='requested_energy_strategy',
            description='Identifier of the most recently accepted energy-use strategy request. An empty string means no strategy has been requested.',
            default='',
            pattern='^$|^[A-Za-z0-9_-]{1,32}$',
            max_length=32
        )
        self.effective_energy_strategy = StringProperty(
            name='effective_energy_strategy',
            description='Energy-use strategy currently applied by the simulated powertrain. It may differ from requested_energy_strategy while protection_active is true.',
            default='balanced',
            mode=2,
            pattern='^[A-Za-z0-9_-]{1,32}$',
            max_length=32
        )
        self.configured_energy_strategies = DictProperty(
            name='configured_energy_strategies',
            description='Read-only vehicle-model configuration keyed by selectable energy-strategy identifier. Each record declares whether the strategy favors electric energy, balances both energy systems, or favors engine use.',
            default={'electric_priority': {'energy_bias': 'electric'}, 'balanced': {'energy_bias': 'balanced'}, 'engine_priority': {'energy_bias': 'engine'}},
            mode=2,
            schema={'type': 'object', 'minProperties': 1, 'propertyNames': {'pattern': '^[A-Za-z0-9_-]{1,32}$'}, 'additionalProperties': {'type': 'object', 'properties': {'energy_bias': {'type': 'string', 'enum': ['electric', 'balanced', 'engine']}}, 'required': ['energy_bias'], 'additionalProperties': False}}
        )
        self.protection_active = BoolProperty(
            name='protection_active',
            description='Whether a simulated powertrain protection condition currently overrides the requested energy-use strategy.',
            default=False,
            mode=2
        )
        self.protection_strategy = StringProperty(
            name='protection_strategy',
            description='Read-only configured energy strategy applied whenever protection_active is true. Its value is always a key in configured_energy_strategies.',
            default='balanced',
            mode=2,
            pattern='^[A-Za-z0-9_-]{1,32}$',
            max_length=32
        )
        self.engine_operating_state = StringProperty(
            name='engine_operating_state',
            description='Actual simulated engine operating state supplied by powertrain feedback. Generating electricity does not imply mechanical drive to the wheels.',
            default='off',
            mode=2,
            choices=['off', 'idling', 'generating_electricity', 'propelling_vehicle']
        )
        self.electric_drive_operating_state = StringProperty(
            name='electric_drive_operating_state',
            description='Actual simulated electric-drive operating state supplied by powertrain feedback, independent of the requested energy strategy.',
            default='inactive',
            mode=2,
            choices=['inactive', 'propelling_vehicle', 'regenerating']
        )

        # initialize properties
        if requested_energy_strategy is not None: code = self.requested_energy_strategy.internal_set(requested_energy_strategy)
        if effective_energy_strategy is not None: code = self.effective_energy_strategy.internal_set(effective_energy_strategy)
        if configured_energy_strategies is not None: code = self.configured_energy_strategies.internal_set(configured_energy_strategies)
        if protection_active is not None: code = self.protection_active.internal_set(protection_active)
        if protection_strategy is not None: code = self.protection_strategy.internal_set(protection_strategy)
        if engine_operating_state is not None: code = self.engine_operating_state.internal_set(engine_operating_state)
        if electric_drive_operating_state is not None: code = self.electric_drive_operating_state.internal_set(electric_drive_operating_state)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_requested_energy_strategy(self) -> tuple[str, dict]:
        """
        Return the most recently accepted energy-use strategy request without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- requested_energy_strategy: Requested configured energy-strategy identifier, or an empty string when none has been requested. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.requested_energy_strategy.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'requested_energy_strategy': value})

    def get_effective_energy_strategy(self) -> tuple[str, dict]:
        """
        Return the energy-use strategy currently applied by the simulated powertrain without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- effective_energy_strategy: Currently effective energy-strategy identifier. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.effective_energy_strategy.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'effective_energy_strategy': value})

    def get_energy_strategy_configuration(self, strategy: str) -> tuple[str, dict]:
        """
        Return the fixed configuration for one available energy-use strategy. An unknown strategy identifier is rejected without changing state.

        Args:
        - strategy:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- strategy_configuration: Fixed strategy record containing its energy_bias. (type=object)

        Error Codes:
        - PRECONDITION_FAILED: The requested energy-use strategy is not configured for this vehicle model.
        """
        if type(strategy) is not str:
            return ('[INVALID_INPUT_ERROR]', {})

        code, configured_strategies = self.configured_energy_strategies.get()
        if code != '[PASS]':
            return (code, {})

        if strategy not in configured_strategies:
            return ('[PRECONDITION_FAILED]', {})

        configuration = configured_strategies[strategy]
        return (
            '[PASS]',
            {
                'strategy_configuration': {
                    'energy_bias': configuration['energy_bias']
                }
            }
        )

    def get_protection_active(self) -> tuple[str, dict]:
        """
        Return whether a simulated powertrain protection condition is currently overriding the requested energy-use strategy.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- protection_active: Whether protection-based strategy override is active. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.protection_active.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'protection_active': value})

    def get_protection_strategy(self) -> tuple[str, dict]:
        """
        Return the configured energy-use strategy applied while protection_active is true.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- protection_strategy: Configured protection strategy identifier. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.protection_strategy.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'protection_strategy': value})

    def get_engine_operating_state(self) -> tuple[str, dict]:
        """
        Return the actual simulated engine operating state. A generating_electricity result does not establish a mechanical connection between the engine and the wheels.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- engine_operating_state: Actual engine state: off, idling, generating_electricity, or propelling_vehicle. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.engine_operating_state.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'engine_operating_state': value})

    def get_electric_drive_operating_state(self) -> tuple[str, dict]:
        """
        Return the actual simulated electric-drive operating state without inferring it from the requested energy strategy.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- electric_drive_operating_state: Actual electric-drive state: inactive, propelling_vehicle, or regenerating. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.electric_drive_operating_state.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'electric_drive_operating_state': value})

    def select_energy_strategy(self, strategy: str) -> tuple[str, dict]:
        """
        Select an energy-use strategy configured for this vehicle model. The accepted strategy is always stored in requested_energy_strategy. When protection_active is false, it also becomes effective_energy_strategy; when protection_active is true, effective_energy_strategy remains the configured protection_strategy. The operation does not infer or modify actual engine or electric-drive operating states and does not set speed or gear. Unknown identifiers are rejected before any state change.

        Args:
        - strategy:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The requested energy-use strategy is not configured for this vehicle model.
        """
        if type(strategy) is not str:
            return ('[INVALID_INPUT_ERROR]', {})

        code, configured_strategies = self.configured_energy_strategies.get()
        if code != '[PASS]':
            return (code, {})
        if strategy not in configured_strategies:
            return ('[PRECONDITION_FAILED]', {})

        code, protection_active = self.protection_active.get()
        if code != '[PASS]':
            return (code, {})

        if protection_active:
            code, effective_strategy = self.protection_strategy.get()
            if code != '[PASS]':
                return (code, {})
        else:
            effective_strategy = strategy

        code = self.requested_energy_strategy.set(strategy)
        if code != '[PASS]':
            return (code, {})

        code = self.effective_energy_strategy.internal_set(effective_strategy)
        if code != '[PASS]':
            return (code, {})

        return ('[PASS]', {})

    def report_powertrain_status(self, protection_active: bool, engine_operating_state: str, electric_drive_operating_state: str) -> tuple[str, dict]:
        """
        Atomically ingest simulated powertrain feedback. The supplied protection condition and actual engine and electric-drive operating states replace the previous feedback. When protection_active is true, effective_energy_strategy becomes protection_strategy. When protection_active is false and a requested strategy exists, that request becomes effective; when no request exists, the configured protection strategy remains the deterministic baseline. This feedback operation does not change requested_energy_strategy, select a driving mode, set vehicle speed or gear, or imply that electricity generation mechanically drives the wheels. Invalid input leaves all state unchanged.

        Args:
        - protection_active: Whether a powertrain protection condition currently overrides the requested energy-use strategy.
        - engine_operating_state:  (choices=['off', 'idling', 'generating_electricity', 'propelling_vehicle'])
        - electric_drive_operating_state:  (choices=['inactive', 'propelling_vehicle', 'regenerating'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - INVALID_INPUT_ERROR: Protection status and both operating states must use the declared types and choices; invalid feedback leaves all state unchanged.
        """
        if type(protection_active) is not bool:
            return ('[INVALID_INPUT_ERROR]', {})
        if (
            type(engine_operating_state) is not str
            or engine_operating_state not in (
                'off',
                'idling',
                'generating_electricity',
                'propelling_vehicle'
            )
        ):
            return ('[INVALID_INPUT_ERROR]', {})
        if (
            type(electric_drive_operating_state) is not str
            or electric_drive_operating_state not in (
                'inactive',
                'propelling_vehicle',
                'regenerating'
            )
        ):
            return ('[INVALID_INPUT_ERROR]', {})

        code, requested_strategy = self.requested_energy_strategy.get()
        if code != '[PASS]':
            return (code, {})

        code, protection_strategy = self.protection_strategy.get()
        if code != '[PASS]':
            return (code, {})

        if protection_active or requested_strategy == '':
            effective_strategy = protection_strategy
        else:
            effective_strategy = requested_strategy

        code = self.protection_active.internal_set(protection_active)
        if code != '[PASS]':
            return (code, {})

        code = self.engine_operating_state.internal_set(engine_operating_state)
        if code != '[PASS]':
            return (code, {})

        code = self.electric_drive_operating_state.internal_set(electric_drive_operating_state)
        if code != '[PASS]':
            return (code, {})

        code = self.effective_energy_strategy.internal_set(effective_strategy)
        if code != '[PASS]':
            return (code, {})

        return ('[PASS]', {})