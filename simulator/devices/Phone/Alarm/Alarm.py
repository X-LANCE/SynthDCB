# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty


class Alarm:
    """
    Alarm
    Description: Alarm configuration application, placed in Application. Supports adding, querying, partially updating, deleting, enabling, and disabling multiple alarms. Stores hour, minute, label, enabled state, and a list of weekdays without duplicates. An empty weekday list represents a one-time configuration. Updates preserve unspecified fields and unrelated records.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, alarms: dict = None) -> None:
        # define properties
        self.alarms = DictProperty(
            name='alarms',
            description='Alarm records keyed by stable string IDs. Each record contains an hour from 0 through 23, a minute from 0 through 59, a label, an enabled state, and unique weekdays from 1 through 7. An empty weekday list represents a one-time configuration.',
            default={'alarm_1': {'hour': 8, 'minute': 0, 'label': 'Workday', 'enabled': False, 'weekdays': [1, 2, 3, 4, 5]}, 'alarm_2': {'hour': 9, 'minute': 0, 'label': 'Weekend', 'enabled': False, 'weekdays': [6, 7]}}
        )

        # initialize properties
        if alarms is not None:
            code = self.alarms.internal_set(alarms)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def _valid_alarm_id(self, alarm_id: str) -> bool:
        if type(alarm_id) is not str:
            return False
        if len(alarm_id) < 1 or len(alarm_id) > 128:
            return False
        for character in alarm_id:
            if not (
                'A' <= character <= 'Z'
                or 'a' <= character <= 'z'
                or '0' <= character <= '9'
                or character == '_'
                or character == '-'
            ):
                return False
        return True

    def add_alarm(self, hour: int, minute: int, label: str, weekdays: list, enabled: bool = False) -> tuple[str, dict]:
        """
        Add an alarm with the supplied hour, minute, label, weekdays, and optional enabled state. The system generates and returns a new stable string ID without changing existing records. Hour must be 0 through 23, minute must be 0 through 59, the label must contain 1 through 80 characters, and weekdays must contain no duplicate values outside 1 through 7. An empty weekdays list represents a one-time configuration. Invalid arguments leave the collection unchanged.

        Args:
        - hour:  (min=0, max=23)
        - minute:  (min=0, max=59)
        - label: 
        - weekdays: 
        - enabled:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- alarm_id: The generated stable string ID of the new alarm. (type=string)

        Error Codes:
        - INVALID: One or more supplied alarm fields are invalid.
        """
        if type(hour) is not int or hour < 0 or hour > 23:
            return ('[INVALID]', {})
        if type(minute) is not int or minute < 0 or minute > 59:
            return ('[INVALID]', {})
        if type(label) is not str or len(label) < 1 or len(label) > 80:
            return ('[INVALID]', {})
        if type(weekdays) is not list:
            return ('[INVALID]', {})

        validated_weekdays = []
        for weekday in weekdays:
            if type(weekday) is not int or weekday < 1 or weekday > 7:
                return ('[INVALID]', {})
            if weekday in validated_weekdays:
                return ('[INVALID]', {})
            validated_weekdays.append(weekday)

        if type(enabled) is not bool:
            return ('[INVALID]', {})

        code, alarms = self.alarms.get()
        if code != '[PASS]':
            return (code, {})
        if type(alarms) is not dict:
            return ('[INVALID]', {})

        updated_alarms = dict(alarms)
        number = 1
        alarm_id = 'alarm_' + str(number)
        while alarm_id in updated_alarms:
            number += 1
            alarm_id = 'alarm_' + str(number)

        updated_alarms[alarm_id] = {
            'hour': hour,
            'minute': minute,
            'label': label,
            'enabled': enabled,
            'weekdays': list(validated_weekdays)
        }

        code = self.alarms.internal_set(updated_alarms)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'alarm_id': alarm_id})

    def get_alarm(self, alarm_id: str) -> tuple[str, dict]:
        """
        Return the complete alarm record identified by alarm_id without changing state. The operation fails if the alarm ID does not exist.

        Args:
        - alarm_id:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- alarm: The complete requested alarm record. (type=object)

        Error Codes:
        - NOT_FOUND: The specified alarm ID does not exist.
        """
        if not self._valid_alarm_id(alarm_id):
            return ('[NOT_FOUND]', {})

        code, alarms = self.alarms.get()
        if code != '[PASS]':
            return (code, {})
        if type(alarms) is not dict or alarm_id not in alarms:
            return ('[NOT_FOUND]', {})

        record = alarms[alarm_id]
        if type(record) is not dict:
            return ('[NOT_FOUND]', {})

        alarm = dict(record)
        if 'weekdays' in alarm and type(alarm['weekdays']) is list:
            alarm['weekdays'] = list(alarm['weekdays'])
        return ('[PASS]', {'alarm': alarm})

    def update_alarm(self, alarm_id: str, hour: int = None, minute: int = None, label: str = None, weekdays: list = None) -> tuple[str, dict]:
        """
        Partially update an existing alarm. At least one of hour, minute, label, or weekdays must be supplied in addition to alarm_id. Omitted fields retain their previous values, enabled state is unchanged, and unrelated records are preserved. An empty weekdays list represents a one-time configuration. An unknown ID or any invalid supplied value leaves the collection unchanged.

        Args:
        - alarm_id: 
        - hour:  (min=0, max=23)
        - minute:  (min=0, max=59)
        - label: 
        - weekdays:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- updated_alarm: The complete alarm record after applying the supplied updates. (type=object)

        Error Codes:
        - INVALID: No update field was supplied or a supplied value is invalid.
        - NOT_FOUND: The specified alarm ID does not exist.
        """
        if not self._valid_alarm_id(alarm_id):
            return ('[NOT_FOUND]', {})
        if hour is None and minute is None and label is None and weekdays is None:
            return ('[INVALID]', {})
        if hour is not None and (type(hour) is not int or hour < 0 or hour > 23):
            return ('[INVALID]', {})
        if minute is not None and (type(minute) is not int or minute < 0 or minute > 59):
            return ('[INVALID]', {})
        if label is not None and (type(label) is not str or len(label) < 1 or len(label) > 80):
            return ('[INVALID]', {})

        validated_weekdays = None
        if weekdays is not None:
            if type(weekdays) is not list:
                return ('[INVALID]', {})
            validated_weekdays = []
            for weekday in weekdays:
                if type(weekday) is not int or weekday < 1 or weekday > 7:
                    return ('[INVALID]', {})
                if weekday in validated_weekdays:
                    return ('[INVALID]', {})
                validated_weekdays.append(weekday)

        code, alarms = self.alarms.get()
        if code != '[PASS]':
            return (code, {})
        if type(alarms) is not dict or alarm_id not in alarms:
            return ('[NOT_FOUND]', {})

        current = alarms[alarm_id]
        if type(current) is not dict:
            return ('[NOT_FOUND]', {})

        updated_record = dict(current)
        if hour is not None:
            updated_record['hour'] = hour
        if minute is not None:
            updated_record['minute'] = minute
        if label is not None:
            updated_record['label'] = label
        if validated_weekdays is not None:
            updated_record['weekdays'] = list(validated_weekdays)

        updated_alarms = dict(alarms)
        updated_alarms[alarm_id] = updated_record

        code = self.alarms.internal_set(updated_alarms)
        if code != '[PASS]':
            return (code, {})

        response_record = dict(updated_record)
        if 'weekdays' in response_record and type(response_record['weekdays']) is list:
            response_record['weekdays'] = list(response_record['weekdays'])
        return ('[PASS]', {'updated_alarm': response_record})

    def remove_alarm(self, alarm_id: str) -> tuple[str, dict]:
        """
        Delete the alarm identified by alarm_id while preserving every unrelated alarm record. An unknown ID causes the operation to fail without changing the collection.

        Args:
        - alarm_id:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- removed_alarm_id: The ID of the deleted alarm. (type=string)

        Error Codes:
        - NOT_FOUND: The specified alarm ID does not exist.
        """
        if not self._valid_alarm_id(alarm_id):
            return ('[NOT_FOUND]', {})

        code, alarms = self.alarms.get()
        if code != '[PASS]':
            return (code, {})
        if type(alarms) is not dict or alarm_id not in alarms:
            return ('[NOT_FOUND]', {})

        updated_alarms = dict(alarms)
        del updated_alarms[alarm_id]

        code = self.alarms.internal_set(updated_alarms)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'removed_alarm_id': alarm_id})

    def enable_alarm(self, alarm_id: str) -> tuple[str, dict]:
        """
        Set enabled to true for the alarm identified by alarm_id. All other fields and unrelated records remain unchanged. An unknown ID leaves the collection unchanged.

        Args:
        - alarm_id:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- enabled_alarm: The complete alarm record with enabled set to true. (type=object)

        Error Codes:
        - NOT_FOUND: The specified alarm ID does not exist.
        """
        if not self._valid_alarm_id(alarm_id):
            return ('[NOT_FOUND]', {})

        code, alarms = self.alarms.get()
        if code != '[PASS]':
            return (code, {})
        if type(alarms) is not dict or alarm_id not in alarms:
            return ('[NOT_FOUND]', {})

        current = alarms[alarm_id]
        if type(current) is not dict:
            return ('[NOT_FOUND]', {})

        enabled_record = dict(current)
        enabled_record['enabled'] = True

        updated_alarms = dict(alarms)
        updated_alarms[alarm_id] = enabled_record

        code = self.alarms.internal_set(updated_alarms)
        if code != '[PASS]':
            return (code, {})

        response_record = dict(enabled_record)
        if 'weekdays' in response_record and type(response_record['weekdays']) is list:
            response_record['weekdays'] = list(response_record['weekdays'])
        return ('[PASS]', {'enabled_alarm': response_record})

    def disable_alarm(self, alarm_id: str) -> tuple[str, dict]:
        """
        Set enabled to false for the alarm identified by alarm_id. All other fields and unrelated records remain unchanged. An unknown ID leaves the collection unchanged.

        Args:
        - alarm_id:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- disabled_alarm: The complete alarm record with enabled set to false. (type=object)

        Error Codes:
        - NOT_FOUND: The specified alarm ID does not exist.
        """
        if not self._valid_alarm_id(alarm_id):
            return ('[NOT_FOUND]', {})

        code, alarms = self.alarms.get()
        if code != '[PASS]':
            return (code, {})
        if type(alarms) is not dict or alarm_id not in alarms:
            return ('[NOT_FOUND]', {})

        current = alarms[alarm_id]
        if type(current) is not dict:
            return ('[NOT_FOUND]', {})

        disabled_record = dict(current)
        disabled_record['enabled'] = False

        updated_alarms = dict(alarms)
        updated_alarms[alarm_id] = disabled_record

        code = self.alarms.internal_set(updated_alarms)
        if code != '[PASS]':
            return (code, {})

        response_record = dict(disabled_record)
        if 'weekdays' in response_record and type(response_record['weekdays']) is list:
            response_record['weekdays'] = list(response_record['weekdays'])
        return ('[PASS]', {'disabled_alarm': response_record})