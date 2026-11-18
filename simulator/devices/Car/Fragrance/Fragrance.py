# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Fragrance:
    """
    Fragrance
    Description: Vehicle fragrance module. Supports switching on and off, release intensity, selecting an installed fragrance slot, and querying consumable availability. Slot count and contents are determined by the equipment configuration; normal release must not be reported when no usable consumable is available. Fragrance release is not air purification and does not automatically overwrite air-quality sensor readings.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, enabled: bool = None, intensity: int = None, selected_slot: str = None, consumables: dict = None) -> None:
        # define properties
        self.enabled = BoolProperty(
            name='enabled',
            description='Whether normal fragrance release is enabled. It can be enabled only when the selected slot has an available consumable.',
            default=False
        )
        self.intensity = IntProperty(
            name='intensity',
            description='Selected fragrance release intensity level.',
            default=1,
            minimum=1,
            maximum=3,
            step=1,
            step_origin=1
        )
        self.selected_slot = StringProperty(
            name='selected_slot',
            description='Identifier of the selected configured fragrance slot. An empty value means no slot is selected.',
            default='',
            pattern='^$|^[A-Za-z0-9_-]{1,32}$',
            max_length=32
        )
        self.consumables = DictProperty(
            name='consumables',
            description='Read-only equipment-configured collection of installed fragrance slots keyed by slot identifier. Each record contains the configured fragrance name and whether its consumable is available.',
            default={},
            mode=2,
            schema={'type': 'object', 'additionalProperties': {'type': 'object', 'properties': {'fragrance': {'type': 'string', 'minLength': 1, 'maxLength': 64}, 'available': {'type': 'boolean'}}, 'required': ['fragrance', 'available'], 'additionalProperties': False}}
        )

        # initialize properties
        if enabled is not None: code = self.enabled.internal_set(enabled)
        if intensity is not None: code = self.intensity.internal_set(intensity)
        if selected_slot is not None: code = self.selected_slot.internal_set(selected_slot)
        if consumables is not None: code = self.consumables.internal_set(consumables)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_enabled(self) -> tuple[str, dict]:
        """
        Return whether normal fragrance release is enabled without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- enabled: Whether normal fragrance release is enabled. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.enabled.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'enabled': value
        }
        return (code, response)

    def set_enabled(self, value: bool) -> tuple[str, dict]:
        """
        Enable or disable normal fragrance release. Disabling always succeeds. Enabling succeeds only when selected_slot identifies an installed consumable whose available field is true; otherwise the request is rejected and all state remains unchanged.

        Args:
        - value:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - CONSUMABLE_UNAVAILABLE: Fragrance release cannot be enabled because the selected slot is missing or its consumable is unavailable.
        """
        if type(value) is not bool:
            return ('[INVALID_INPUT_ERROR]', {})

        if value is True:
            slot_code, slot_id = self.selected_slot.get()
            if slot_code != '[PASS]':
                return (slot_code, {})

            consumables_code, consumables = self.consumables.get()
            if consumables_code != '[PASS]':
                return (consumables_code, {})

            if slot_id not in consumables:
                return ('[CONSUMABLE_UNAVAILABLE]', {})
            if consumables[slot_id]['available'] is not True:
                return ('[CONSUMABLE_UNAVAILABLE]', {})

        code = self.enabled.set(value)
        if code != '[PASS]':
            return (code, {})
        response = {}
        return (code, response)

    def get_intensity(self) -> tuple[str, dict]:
        """
        Return the selected fragrance release intensity level without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- intensity: Selected fragrance release intensity from 1 through 3. (type=integer)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.intensity.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'intensity': value
        }
        return (code, response)

    def set_intensity(self, value: int) -> tuple[str, dict]:
        """
        Set the fragrance release intensity to an integer from 1 through 3. The setting persists while release is disabled. Invalid input is rejected and leaves state unchanged.

        Args:
        - value:  (min=1, max=3)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - INVALID_INPUT_ERROR: Intensity must be an integer from 1 through 3.
        """
        if type(value) is not int or value < 1 or value > 3:
            return ('[INVALID_INPUT_ERROR]', {})

        code = self.intensity.set(value)
        if code != '[PASS]':
            return (code, {})
        response = {}
        return (code, response)

    def get_selected_slot(self) -> tuple[str, dict]:
        """
        Return the selected fragrance slot identifier. An empty string means no slot is selected.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- selected_slot: Identifier of the selected configured fragrance slot, or an empty string when none is selected. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.selected_slot.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'selected_slot': value
        }
        return (code, response)

    def set_selected_slot(self, slot_id: str) -> tuple[str, dict]:
        """
        Select an installed fragrance slot. The slot identifier must exist in consumables. An unavailable slot may be selected while release is disabled, but selecting an unavailable slot while release is enabled is rejected so normal release is never reported without a usable consumable. Rejected requests leave all state unchanged.

        Args:
        - slot_id:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The requested slot is not installed.
        - CONSUMABLE_UNAVAILABLE: An unavailable fragrance slot cannot be selected while fragrance release is enabled.
        """
        if type(slot_id) is not str:
            return ('[INVALID_INPUT_ERROR]', {})
        if len(slot_id) < 1 or len(slot_id) > 32:
            return ('[INVALID_INPUT_ERROR]', {})
        for character in slot_id:
            if not (
                'A' <= character <= 'Z'
                or 'a' <= character <= 'z'
                or '0' <= character <= '9'
                or character == '_'
                or character == '-'
            ):
                return ('[INVALID_INPUT_ERROR]', {})

        consumables_code, consumables = self.consumables.get()
        if consumables_code != '[PASS]':
            return (consumables_code, {})
        if slot_id not in consumables:
            return ('[PRECONDITION_FAILED]', {})

        if consumables[slot_id]['available'] is not True:
            enabled_code, enabled = self.enabled.get()
            if enabled_code != '[PASS]':
                return (enabled_code, {})
            if enabled:
                return ('[CONSUMABLE_UNAVAILABLE]', {})

        code = self.selected_slot.set(slot_id)
        if code != '[PASS]':
            return (code, {})
        response = {}
        return (code, response)

    def get_consumable(self, slot_id: str) -> tuple[str, dict]:
        """
        Return the configured fragrance name and current availability for one installed slot. An unknown slot identifier is rejected without changing state.

        Args:
        - slot_id:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- consumable: Configured slot record containing fragrance and available fields. (type=object)

        Error Codes:
        - PRECONDITION_FAILED: The requested slot is not installed.
        """
        if type(slot_id) is not str:
            return ('[INVALID_INPUT_ERROR]', {})
        if len(slot_id) < 1 or len(slot_id) > 32:
            return ('[INVALID_INPUT_ERROR]', {})
        for character in slot_id:
            if not (
                'A' <= character <= 'Z'
                or 'a' <= character <= 'z'
                or '0' <= character <= '9'
                or character == '_'
                or character == '-'
            ):
                return ('[INVALID_INPUT_ERROR]', {})

        code, consumables = self.consumables.get()
        if code != '[PASS]':
            return (code, {})
        if slot_id not in consumables:
            return ('[PRECONDITION_FAILED]', {})

        record = consumables[slot_id]
        response = {
            'consumable': {
                'fragrance': record['fragrance'],
                'available': record['available']
            }
        }
        return ('[PASS]', response)