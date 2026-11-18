# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Focus:
    """
    Focus
    Description: Do-not-disturb and focus settings, placed in Setting and contained by System. Supports adding, querying, partially updating, and deleting rules by stable ID, manually enabling/disabling rules, configuring applications, notification categories, contacts, and repeat-call exceptions allowed to interrupt, and configuring time windows with time zones and repeat days. Rule names are user data; personal, work, and sleep are not fixed cross-platform enumerations. Supports querying the effective policy and its source. Schedules advance with wall-clock time; manual overrides take priority over schedules. Exiting an override reevaluates the current time window, and conflicts between multiple rules are resolved by an explicit fixed priority.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, rules: dict = None, manual_override_rule_id: str = None, effective_rule_id: str = None, effective_source: str = None, effective_policy: dict = None) -> None:
        # define properties
        self.rules = DictProperty(
            name='rules',
            description='Focus rules keyed by stable synthetic rule ID. Each record contains a user-defined name, eligibility setting, immutable conflict priority, interruption exceptions, and one repeating wall-clock time window. A window starts inclusively and ends exclusively; an equal start and end denotes a full local day. For an overnight window, repeat_days refers to the local day on which the window starts.',
            default={},
            mode=2,
            schema={'type': 'object', 'additionalProperties': {'type': 'object', 'properties': {'name': {'type': 'string', 'minLength': 1, 'maxLength': 80}, 'enabled': {'type': 'boolean'}, 'priority': {'type': 'integer', 'minimum': 0, 'maximum': 100}, 'allowed_applications': {'type': 'array', 'items': {'type': 'string', 'minLength': 1, 'maxLength': 128}, 'uniqueItems': True, 'maxItems': 64}, 'allowed_categories': {'type': 'array', 'items': {'type': 'string', 'minLength': 1, 'maxLength': 64}, 'uniqueItems': True, 'maxItems': 32}, 'allowed_contacts': {'type': 'array', 'items': {'type': 'string', 'minLength': 1, 'maxLength': 128}, 'uniqueItems': True, 'maxItems': 64}, 'allow_repeat_callers': {'type': 'boolean'}, 'schedule_enabled': {'type': 'boolean'}, 'start_time': {'type': 'string', 'pattern': '^(?:[01][0-9]|2[0-3]):[0-5][0-9]$'}, 'end_time': {'type': 'string', 'pattern': '^(?:[01][0-9]|2[0-3]):[0-5][0-9]$'}, 'timezone': {'type': 'string', 'minLength': 1, 'maxLength': 64}, 'repeat_days': {'type': 'array', 'items': {'type': 'string', 'enum': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']}, 'minItems': 1, 'maxItems': 7, 'uniqueItems': True}}, 'required': ['name', 'enabled', 'priority', 'allowed_applications', 'allowed_categories', 'allowed_contacts', 'allow_repeat_callers', 'schedule_enabled', 'start_time', 'end_time', 'timezone', 'repeat_days'], 'additionalProperties': False}}
        )
        self.manual_override_rule_id = StringProperty(
            name='manual_override_rule_id',
            description='Stable ID of the manually active rule, or an empty string when schedules determine the effective policy. A missing or disabled referenced rule is cleared during reevaluation.',
            default='',
            mode=2,
            pattern='^[A-Za-z0-9_-]*$',
            max_length=128
        )
        self.effective_rule_id = StringProperty(
            name='effective_rule_id',
            description='Stable ID of the rule currently supplying the effective focus policy, or an empty string when no focus rule is active.',
            default='',
            mode=2,
            pattern='^[A-Za-z0-9_-]*$',
            max_length=128
        )
        self.effective_source = StringProperty(
            name='effective_source',
            description='Source that selected the effective policy: manual for a valid manual override, schedule for a matching time window, or none when no rule is active.',
            default='none',
            mode=2,
            choices=['none', 'manual', 'schedule']
        )
        self.effective_policy = DictProperty(
            name='effective_policy',
            description='Resolved interruption policy copied from the effective rule. An empty dictionary means no focus policy is active.',
            default={},
            mode=2,
            schema={'oneOf': [{'type': 'object', 'maxProperties': 0, 'additionalProperties': False}, {'type': 'object', 'properties': {'allowed_applications': {'type': 'array', 'items': {'type': 'string'}, 'uniqueItems': True}, 'allowed_categories': {'type': 'array', 'items': {'type': 'string'}, 'uniqueItems': True}, 'allowed_contacts': {'type': 'array', 'items': {'type': 'string'}, 'uniqueItems': True}, 'allow_repeat_callers': {'type': 'boolean'}}, 'required': ['allowed_applications', 'allowed_categories', 'allowed_contacts', 'allow_repeat_callers'], 'additionalProperties': False}]}
        )

        # initialize properties
        if rules is not None: code = self.rules.internal_set(rules)
        if manual_override_rule_id is not None: code = self.manual_override_rule_id.internal_set(manual_override_rule_id)
        if effective_rule_id is not None: code = self.effective_rule_id.internal_set(effective_rule_id)
        if effective_source is not None: code = self.effective_source.internal_set(effective_source)
        if effective_policy is not None: code = self.effective_policy.internal_set(effective_policy)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def add_rule(self, name: str, enabled: bool, priority: int, allowed_applications: list, allowed_categories: list, allowed_contacts: list, allow_repeat_callers: bool, schedule_enabled: bool, start_time: str, end_time: str, timezone: str, repeat_days: list) -> tuple[str, dict]:
        """
        Add a focus rule and return its new stable synthetic ID. The name is user data. Priority is fixed for the lifetime of the rule and is used only to resolve simultaneous scheduled rules. Timezone must be a valid IANA time-zone identifier available to the simulation. Invalid input creates no record. After insertion, the effective policy is immediately reevaluated.

        Args:
        - name: 
        - enabled: Whether the rule is eligible for manual activation and scheduled selection.
        - priority: Immutable conflict priority; larger values win. (min=0, max=100)
        - allowed_applications: 
        - allowed_categories: 
        - allowed_contacts: 
        - allow_repeat_callers: 
        - schedule_enabled: 
        - start_time: 
        - end_time: 
        - timezone: 
        - repeat_days:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- rule_id: New stable synthetic rule ID. (type=string)

        Error Codes:
        - INVALID_TIMEZONE: The supplied timezone is not a valid supported IANA time-zone identifier.
        - INVALID_ARGUMENT: One or more rule fields are invalid.
        """
        supported_timezones = (
            'UTC', 'Etc/UTC', 'GMT', 'Etc/GMT',
            'America/New_York', 'America/Chicago', 'America/Denver',
            'America/Los_Angeles', 'America/Phoenix', 'America/Anchorage',
            'Pacific/Honolulu',
            'Europe/London', 'Europe/Paris', 'Europe/Berlin',
            'Europe/Madrid', 'Europe/Rome', 'Europe/Amsterdam',
            'Europe/Moscow',
            'Asia/Dubai', 'Asia/Kolkata', 'Asia/Colombo',
            'Asia/Dhaka', 'Asia/Bangkok', 'Asia/Jakarta',
            'Asia/Singapore', 'Asia/Kuala_Lumpur', 'Asia/Shanghai',
            'Asia/Hong_Kong', 'Asia/Taipei', 'Asia/Seoul', 'Asia/Tokyo',
            'Australia/Perth', 'Australia/Adelaide', 'Australia/Sydney',
            'Pacific/Auckland'
        )
        days = (
            'monday', 'tuesday', 'wednesday', 'thursday',
            'friday', 'saturday', 'sunday'
        )

        def valid_time(value: object) -> bool:
            if type(value) is not str or len(value) != 5 or value[2] != ':':
                return False
            if not value[:2].isdigit() or not value[3:].isdigit():
                return False
            hour = int(value[:2])
            minute = int(value[3:])
            return 0 <= hour <= 23 and 0 <= minute <= 59

        def valid_string_list(value: object, maximum: int, max_length: int) -> bool:
            if type(value) is not list or len(value) > maximum:
                return False
            seen = set()
            for item in value:
                if type(item) is not str or len(item) < 1 or len(item) > max_length:
                    return False
                if item in seen:
                    return False
                seen.add(item)
            return True

        if type(timezone) is not str or timezone not in supported_timezones:
            return '[INVALID_TIMEZONE]', {}

        valid = (
            type(name) is str and 1 <= len(name) <= 80
            and type(enabled) is bool
            and type(priority) is int and 0 <= priority <= 100
            and valid_string_list(allowed_applications, 64, 128)
            and valid_string_list(allowed_categories, 32, 64)
            and valid_string_list(allowed_contacts, 64, 128)
            and type(allow_repeat_callers) is bool
            and type(schedule_enabled) is bool
            and valid_time(start_time)
            and valid_time(end_time)
            and type(repeat_days) is list
            and 1 <= len(repeat_days) <= 7
        )
        if valid:
            seen_days = set()
            for day in repeat_days:
                if type(day) is not str or day not in days or day in seen_days:
                    valid = False
                    break
                seen_days.add(day)
        if not valid:
            return '[INVALID_ARGUMENT]', {}

        code, rules = self.rules.get()
        if code != '[PASS]':
            return code, {}

        rule_number = 1
        rule_id = 'rule_' + str(rule_number)
        while rule_id in rules:
            rule_number += 1
            rule_id = 'rule_' + str(rule_number)

        updated_rules = {
            key: dict(record)
            for key, record in rules.items()
        }
        updated_rules[rule_id] = {
            'name': name,
            'enabled': enabled,
            'priority': priority,
            'allowed_applications': list(allowed_applications),
            'allowed_categories': list(allowed_categories),
            'allowed_contacts': list(allowed_contacts),
            'allow_repeat_callers': allow_repeat_callers,
            'schedule_enabled': schedule_enabled,
            'start_time': start_time,
            'end_time': end_time,
            'timezone': timezone,
            'repeat_days': list(repeat_days)
        }

        code = self.rules.internal_set(updated_rules)
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {'rule_id': rule_id}

    def get_rule(self, rule_id: str) -> tuple[str, dict]:
        """
        Return one focus rule by stable ID without changing focus state. An unknown ID is rejected.

        Args:
        - rule_id:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- rule: The complete stored focus rule. (type=object)

        Error Codes:
        - NOT_FOUND: The requested rule ID does not exist.
        """
        code, rules = self.rules.get()
        if code != '[PASS]':
            return code, {}
        if type(rule_id) is not str or rule_id not in rules:
            return '[NOT_FOUND]', {}

        stored = rules[rule_id]
        rule = {
            'name': stored['name'],
            'enabled': stored['enabled'],
            'priority': stored['priority'],
            'allowed_applications': list(stored['allowed_applications']),
            'allowed_categories': list(stored['allowed_categories']),
            'allowed_contacts': list(stored['allowed_contacts']),
            'allow_repeat_callers': stored['allow_repeat_callers'],
            'schedule_enabled': stored['schedule_enabled'],
            'start_time': stored['start_time'],
            'end_time': stored['end_time'],
            'timezone': stored['timezone'],
            'repeat_days': list(stored['repeat_days'])
        }
        return '[PASS]', {'rule': rule}

    def update_rule(self, rule_id: str, name: str = None, enabled: bool = None, allowed_applications: list = None, allowed_categories: list = None, allowed_contacts: list = None, allow_repeat_callers: bool = None, schedule_enabled: bool = None, start_time: str = None, end_time: str = None, timezone: str = None, repeat_days: list = None) -> tuple[str, dict]:
        """
        Partially update an existing focus rule. Omitted fields remain unchanged, and immutable priority cannot be changed. Disabling the manually selected rule causes immediate reevaluation to clear that override and select the current scheduled rule, if any. Timezone must be a valid supported IANA identifier. Invalid input or an unknown ID leaves all state unchanged.

        Args:
        - rule_id: 
        - name: 
        - enabled: 
        - allowed_applications: 
        - allowed_categories: 
        - allowed_contacts: 
        - allow_repeat_callers: 
        - schedule_enabled: 
        - start_time: 
        - end_time: 
        - timezone: 
        - repeat_days:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - NOT_FOUND: The requested rule ID does not exist.
        - INVALID_TIMEZONE: The supplied timezone is not a valid supported IANA time-zone identifier.
        - INVALID_ARGUMENT: One or more supplied fields are invalid.
        """
        code, rules = self.rules.get()
        if code != '[PASS]':
            return code, {}
        if type(rule_id) is not str or rule_id not in rules:
            return '[NOT_FOUND]', {}

        supported_timezones = (
            'UTC', 'Etc/UTC', 'GMT', 'Etc/GMT',
            'America/New_York', 'America/Chicago', 'America/Denver',
            'America/Los_Angeles', 'America/Phoenix', 'America/Anchorage',
            'Pacific/Honolulu',
            'Europe/London', 'Europe/Paris', 'Europe/Berlin',
            'Europe/Madrid', 'Europe/Rome', 'Europe/Amsterdam',
            'Europe/Moscow',
            'Asia/Dubai', 'Asia/Kolkata', 'Asia/Colombo',
            'Asia/Dhaka', 'Asia/Bangkok', 'Asia/Jakarta',
            'Asia/Singapore', 'Asia/Kuala_Lumpur', 'Asia/Shanghai',
            'Asia/Hong_Kong', 'Asia/Taipei', 'Asia/Seoul', 'Asia/Tokyo',
            'Australia/Perth', 'Australia/Adelaide', 'Australia/Sydney',
            'Pacific/Auckland'
        )
        days = (
            'monday', 'tuesday', 'wednesday', 'thursday',
            'friday', 'saturday', 'sunday'
        )

        def valid_time(value: object) -> bool:
            if type(value) is not str or len(value) != 5 or value[2] != ':':
                return False
            if not value[:2].isdigit() or not value[3:].isdigit():
                return False
            hour = int(value[:2])
            minute = int(value[3:])
            return 0 <= hour <= 23 and 0 <= minute <= 59

        def valid_string_list(value: object, maximum: int, max_length: int) -> bool:
            if type(value) is not list or len(value) > maximum:
                return False
            seen = set()
            for item in value:
                if type(item) is not str or len(item) < 1 or len(item) > max_length:
                    return False
                if item in seen:
                    return False
                seen.add(item)
            return True

        if timezone is not None:
            if type(timezone) is not str or timezone not in supported_timezones:
                return '[INVALID_TIMEZONE]', {}

        valid = True
        if name is not None and (type(name) is not str or not 1 <= len(name) <= 80):
            valid = False
        if enabled is not None and type(enabled) is not bool:
            valid = False
        if allowed_applications is not None and not valid_string_list(allowed_applications, 64, 128):
            valid = False
        if allowed_categories is not None and not valid_string_list(allowed_categories, 32, 64):
            valid = False
        if allowed_contacts is not None and not valid_string_list(allowed_contacts, 64, 128):
            valid = False
        if allow_repeat_callers is not None and type(allow_repeat_callers) is not bool:
            valid = False
        if schedule_enabled is not None and type(schedule_enabled) is not bool:
            valid = False
        if start_time is not None and not valid_time(start_time):
            valid = False
        if end_time is not None and not valid_time(end_time):
            valid = False
        if repeat_days is not None:
            if type(repeat_days) is not list or not 1 <= len(repeat_days) <= 7:
                valid = False
            else:
                seen_days = set()
                for day in repeat_days:
                    if type(day) is not str or day not in days or day in seen_days:
                        valid = False
                        break
                    seen_days.add(day)
        if not valid:
            return '[INVALID_ARGUMENT]', {}

        old_record = rules[rule_id]
        record = {
            'name': old_record['name'],
            'enabled': old_record['enabled'],
            'priority': old_record['priority'],
            'allowed_applications': list(old_record['allowed_applications']),
            'allowed_categories': list(old_record['allowed_categories']),
            'allowed_contacts': list(old_record['allowed_contacts']),
            'allow_repeat_callers': old_record['allow_repeat_callers'],
            'schedule_enabled': old_record['schedule_enabled'],
            'start_time': old_record['start_time'],
            'end_time': old_record['end_time'],
            'timezone': old_record['timezone'],
            'repeat_days': list(old_record['repeat_days'])
        }

        if name is not None:
            record['name'] = name
        if enabled is not None:
            record['enabled'] = enabled
        if allowed_applications is not None:
            record['allowed_applications'] = list(allowed_applications)
        if allowed_categories is not None:
            record['allowed_categories'] = list(allowed_categories)
        if allowed_contacts is not None:
            record['allowed_contacts'] = list(allowed_contacts)
        if allow_repeat_callers is not None:
            record['allow_repeat_callers'] = allow_repeat_callers
        if schedule_enabled is not None:
            record['schedule_enabled'] = schedule_enabled
        if start_time is not None:
            record['start_time'] = start_time
        if end_time is not None:
            record['end_time'] = end_time
        if timezone is not None:
            record['timezone'] = timezone
        if repeat_days is not None:
            record['repeat_days'] = list(repeat_days)

        updated_rules = {
            key: dict(value)
            for key, value in rules.items()
        }
        updated_rules[rule_id] = record

        code = self.rules.internal_set(updated_rules)
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {}

    def delete_rule(self, rule_id: str) -> tuple[str, dict]:
        """
        Delete an existing focus rule while preserving every other rule. If the deleted rule supplied the manual override or effective policy, immediate reevaluation clears that reference and selects the current scheduled winner, if any.

        Args:
        - rule_id:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - NOT_FOUND: The requested rule ID does not exist.
        """
        code, rules = self.rules.get()
        if code != '[PASS]':
            return code, {}
        if type(rule_id) is not str or rule_id not in rules:
            return '[NOT_FOUND]', {}

        updated_rules = {
            key: dict(record)
            for key, record in rules.items()
            if key != rule_id
        }
        code = self.rules.internal_set(updated_rules)
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {}

    def activate_rule_manually(self, rule_id: str) -> tuple[str, dict]:
        """
        Manually activate an existing enabled rule. The selected rule immediately overrides every scheduled rule until the override is cleared. An unknown or disabled rule is rejected and leaves all state unchanged.

        Args:
        - rule_id:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - NOT_FOUND: The requested rule ID does not exist.
        - PRECONDITION_FAILED: The requested rule is disabled and cannot be manually activated.
        """
        code, rules = self.rules.get()
        if code != '[PASS]':
            return code, {}
        if type(rule_id) is not str or rule_id not in rules:
            return '[NOT_FOUND]', {}
        if not rules[rule_id]['enabled']:
            return '[PRECONDITION_FAILED]', {}

        code = self.manual_override_rule_id.internal_set(rule_id)
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {}

    def clear_manual_override(self) -> tuple[str, dict]:
        """
        End the current manual override by clearing its rule ID. The operation is idempotent when no override exists, and the effective policy is immediately reevaluated from the current wall-clock schedules.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        (no specified error codes)
        """
        code = self.manual_override_rule_id.internal_set('')
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {}

    def get_manual_override_rule_id(self) -> tuple[str, dict]:
        """
        Return the stable ID selected as the manual override, or an empty string when no manual override exists.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- manual_override_rule_id: Current manual override rule ID, or an empty string. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.manual_override_rule_id.get()
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {'manual_override_rule_id': value}

    def get_effective_rule_id(self) -> tuple[str, dict]:
        """
        Return the stable ID of the rule currently supplying the effective policy, or an empty string if no rule is active.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- effective_rule_id: Effective rule ID, or an empty string when focus is inactive. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.effective_rule_id.get()
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {'effective_rule_id': value}

    def get_effective_source(self) -> tuple[str, dict]:
        """
        Return whether the effective focus policy comes from a manual override, a schedule, or no active rule.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- effective_source: One of manual, schedule, or none. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.effective_source.get()
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {'effective_source': value}

    def get_effective_policy(self) -> tuple[str, dict]:
        """
        Return the currently resolved interruption exceptions. The returned dictionary is empty when no focus rule is active.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- effective_policy: Resolved allowed applications, categories, contacts, and repeat-caller setting, or an empty dictionary. (type=object)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.effective_policy.get()
        if code != '[PASS]':
            return code, {}

        if not value:
            policy = {}
        else:
            policy = {
                'allowed_applications': list(value['allowed_applications']),
                'allowed_categories': list(value['allowed_categories']),
                'allowed_contacts': list(value['allowed_contacts']),
                'allow_repeat_callers': value['allow_repeat_callers']
            }
        return '[PASS]', {'effective_policy': policy}

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        Each simulated minute, reevaluates rule windows using wall-clock time in each rule's configured time zone. A valid enabled manual override remains authoritative. Otherwise, enabled scheduled rules whose windows currently match compete by immutable priority, with larger values winning and the lexicographically smallest stable rule ID breaking equal-priority ties. The selected rule's interruption exceptions become effective; if no rule matches, the effective rule ID and policy are cleared and the source becomes none.

    Effect properties:
    - rules: Stored rules containing eligibility, priorities, policies, time zones, repeat days, and time windows.
    - manual_override_rule_id: Manual selection that takes precedence over scheduled rules.
    - effective_rule_id: Currently resolved rule ID updated by reevaluation.
    - effective_source: Currently resolved policy source updated by reevaluation.
    - effective_policy: Currently resolved interruption policy updated by reevaluation.
        """
        code, rules = self.rules.get()
        if code != '[PASS]':
            return code, []

        code, manual_rule_id = self.manual_override_rule_id.get()
        if code != '[PASS]':
            return code, []

        selected_rule_id = ''
        selected_source = 'none'

        if (
            manual_rule_id
            and manual_rule_id in rules
            and rules[manual_rule_id]['enabled']
        ):
            selected_rule_id = manual_rule_id
            selected_source = 'manual'
        else:
            if manual_rule_id:
                code = self.manual_override_rule_id.internal_set('')
                if code != '[PASS]':
                    return code, []

            day_names = (
                'monday', 'tuesday', 'wednesday', 'thursday',
                'friday', 'saturday', 'sunday'
            )

            fixed_offsets = {
                'UTC': 0,
                'Etc/UTC': 0,
                'GMT': 0,
                'Etc/GMT': 0,
                'America/Phoenix': -420,
                'Pacific/Honolulu': -600,
                'Europe/Moscow': 180,
                'Asia/Dubai': 240,
                'Asia/Kolkata': 330,
                'Asia/Colombo': 330,
                'Asia/Dhaka': 360,
                'Asia/Bangkok': 420,
                'Asia/Jakarta': 420,
                'Asia/Singapore': 480,
                'Asia/Kuala_Lumpur': 480,
                'Asia/Shanghai': 480,
                'Asia/Hong_Kong': 480,
                'Asia/Taipei': 480,
                'Asia/Seoul': 540,
                'Asia/Tokyo': 540,
                'Australia/Perth': 480,
                'Australia/Adelaide': 570,
                'Pacific/Auckland': 720
            }
            standard_offsets = {
                'America/New_York': -300,
                'America/Chicago': -360,
                'America/Denver': -420,
                'America/Los_Angeles': -480,
                'America/Anchorage': -540,
                'Europe/London': 0,
                'Europe/Paris': 60,
                'Europe/Berlin': 60,
                'Europe/Madrid': 60,
                'Europe/Rome': 60,
                'Europe/Amsterdam': 60,
                'Australia/Sydney': 600
            }

            def leap_year(year: int) -> bool:
                return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

            def month_length(year: int, month: int) -> int:
                if month == 2:
                    return 29 if leap_year(year) else 28
                if month in (4, 6, 9, 11):
                    return 30
                return 31

            def weekday_index(year: int, month: int, day: int) -> int:
                adjusted_year = year
                adjusted_month = month
                if adjusted_month < 3:
                    adjusted_month += 12
                    adjusted_year -= 1
                century = adjusted_year // 100
                year_in_century = adjusted_year % 100
                h = (
                    day
                    + (13 * (adjusted_month + 1)) // 5
                    + year_in_century
                    + year_in_century // 4
                    + century // 4
                    + 5 * century
                ) % 7
                return (h + 5) % 7

            def nth_sunday(year: int, month: int, occurrence: int) -> int:
                first_weekday = weekday_index(year, month, 1)
                first_sunday = 1 + ((6 - first_weekday) % 7)
                return first_sunday + (occurrence - 1) * 7

            def last_sunday(year: int, month: int) -> int:
                last_day = month_length(year, month)
                last_weekday = weekday_index(year, month, last_day)
                return last_day - ((last_weekday - 6) % 7)

            def offset_for_local(
                timezone: str,
                year: int,
                month: int,
                day: int,
                hour: int
            ) -> int:
                if timezone in fixed_offsets:
                    return fixed_offsets[timezone]

                standard = standard_offsets[timezone]

                if timezone.startswith('America/'):
                    start_day = nth_sunday(year, 3, 2)
                    end_day = nth_sunday(year, 11, 1)
                    after_start = (
                        month > 3
                        or (month == 3 and (day > start_day or (day == start_day and hour >= 2)))
                    )
                    before_end = (
                        month < 11
                        or (month == 11 and (day < end_day or (day == end_day and hour < 2)))
                    )
                    if after_start and before_end:
                        return standard + 60
                    return standard

                if timezone.startswith('Europe/'):
                    start_day = last_sunday(year, 3)
                    end_day = last_sunday(year, 10)
                    after_start = (
                        month > 3
                        or (month == 3 and (day > start_day or (day == start_day and hour >= 1)))
                    )
                    before_end = (
                        month < 10
                        or (month == 10 and (day < end_day or (day == end_day and hour < 2)))
                    )
                    if after_start and before_end:
                        return standard + 60
                    return standard

                if timezone == 'Australia/Sydney':
                    end_day = nth_sunday(year, 4, 1)
                    start_day = nth_sunday(year, 10, 1)
                    daylight = (
                        month < 4
                        or month > 10
                        or (month == 4 and (day < end_day or (day == end_day and hour < 3)))
                        or (month == 10 and (day > start_day or (day == start_day and hour >= 2)))
                    )
                    return standard + 60 if daylight else standard

                return standard

            def shift_local(
                year: int,
                month: int,
                day: int,
                minute_of_day: int,
                delta_minutes: int
            ) -> tuple[int, int, int, int]:
                total_minutes = minute_of_day + delta_minutes
                while total_minutes < 0:
                    total_minutes += 1440
                    day -= 1
                    if day < 1:
                        month -= 1
                        if month < 1:
                            month = 12
                            year -= 1
                        day = month_length(year, month)
                while total_minutes >= 1440:
                    total_minutes -= 1440
                    day += 1
                    if day > month_length(year, month):
                        day = 1
                        month += 1
                        if month > 12:
                            month = 1
                            year += 1
                return year, month, day, total_minutes

            date_value = context['time_state']['date']
            clock_value = context['time_state']['clock']
            world_timezone = context['time_state']['timezone']

            date_parts = date_value.split('-')
            world_year = int(date_parts[0])
            world_month = int(date_parts[1])
            world_day = int(date_parts[2])
            world_hour = int(clock_value[:2])
            world_minute = int(clock_value[3:5])
            world_minute_of_day = world_hour * 60 + world_minute

            world_offset = offset_for_local(
                world_timezone,
                world_year,
                world_month,
                world_day,
                world_hour
            )
            utc_year, utc_month, utc_day, utc_minute_of_day = shift_local(
                world_year,
                world_month,
                world_day,
                world_minute_of_day,
                -world_offset
            )

            candidates = []
            for rule_id, rule in rules.items():
                if not rule['enabled'] or not rule['schedule_enabled']:
                    continue

                rule_timezone = rule['timezone']
                if rule_timezone == world_timezone:
                    local_year = world_year
                    local_month = world_month
                    local_day = world_day
                    local_minute = world_minute_of_day
                else:
                    provisional_offset = offset_for_local(
                        rule_timezone,
                        utc_year,
                        utc_month,
                        utc_day,
                        utc_minute_of_day // 60
                    )
                    local_year, local_month, local_day, local_minute = shift_local(
                        utc_year,
                        utc_month,
                        utc_day,
                        utc_minute_of_day,
                        provisional_offset
                    )
                    corrected_offset = offset_for_local(
                        rule_timezone,
                        local_year,
                        local_month,
                        local_day,
                        local_minute // 60
                    )
                    if corrected_offset != provisional_offset:
                        local_year, local_month, local_day, local_minute = shift_local(
                            utc_year,
                            utc_month,
                            utc_day,
                            utc_minute_of_day,
                            corrected_offset
                        )

                current_weekday = weekday_index(
                    local_year,
                    local_month,
                    local_day
                )
                previous_weekday = (current_weekday - 1) % 7

                start_minute = (
                    int(rule['start_time'][:2]) * 60
                    + int(rule['start_time'][3:])
                )
                end_minute = (
                    int(rule['end_time'][:2]) * 60
                    + int(rule['end_time'][3:])
                )

                matches = False
                if start_minute == end_minute:
                    matches = day_names[current_weekday] in rule['repeat_days']
                elif start_minute < end_minute:
                    matches = (
                        day_names[current_weekday] in rule['repeat_days']
                        and start_minute <= local_minute < end_minute
                    )
                elif local_minute >= start_minute:
                    matches = day_names[current_weekday] in rule['repeat_days']
                elif local_minute < end_minute:
                    matches = day_names[previous_weekday] in rule['repeat_days']

                if matches:
                    candidates.append((
                        -rule['priority'],
                        rule_id
                    ))

            if candidates:
                candidates.sort()
                selected_rule_id = candidates[0][1]
                selected_source = 'schedule'

        if selected_rule_id:
            selected_rule = rules[selected_rule_id]
            selected_policy = {
                'allowed_applications': list(selected_rule['allowed_applications']),
                'allowed_categories': list(selected_rule['allowed_categories']),
                'allowed_contacts': list(selected_rule['allowed_contacts']),
                'allow_repeat_callers': selected_rule['allow_repeat_callers']
            }
        else:
            selected_policy = {}

        code = self.effective_rule_id.internal_set(selected_rule_id)
        if code != '[PASS]':
            return code, []

        code = self.effective_source.internal_set(selected_source)
        if code != '[PASS]':
            return code, []

        code = self.effective_policy.internal_set(selected_policy)
        if code != '[PASS]':
            return code, []

        return '[PASS]', []

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        After a successful state-changing action, immediately reevaluates the effective policy. A deleted, missing, or disabled manual rule clears the manual override. A valid manual rule wins; otherwise the current time windows, immutable priorities, and stable-ID tie-break determine the scheduled winner. This makes rule edits, deletion, manual activation, and override exit observable without waiting for the next minute.

    Effect properties:
    - rules: Stored rules used to validate manual selection and resolve current schedules.
    - manual_override_rule_id: Manual selection to validate, retain, or clear.
    - effective_rule_id: Currently resolved rule ID updated after actions.
    - effective_source: Currently resolved policy source updated after actions.
    - effective_policy: Currently resolved interruption policy updated after actions.
        """
        return self._on_tick(context)