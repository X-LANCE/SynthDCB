# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class Notifications:
    """
    Notifications
    Description: Notification management settings, placed in Setting and contained by System. Supports querying and setting notification permission, alert behavior, and lock-screen content display preferences for each application and its notification channels, querying current synthetic notifications, and dismissing eligible items by ID. Applications, channels, and notifications use stable IDs; partial updates preserve other configuration. Nonexistent IDs and notifications that cannot be dismissed must return explicit failures. Overall application permission, channel configuration, privacy display preferences, and Focus policy jointly determine actual presentation and alerts; allowing notifications does not guarantee immediate sound. Notification-sending authorization is centrally owned by Privacy. This module neither duplicates permission records nor changes Sound volumes.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, application_settings: dict = None, channel_settings: dict = None, current_notifications: dict = None) -> None:
        # define properties
        self.application_settings = DictProperty(
            name='application_settings',
            description="Notification presentation preferences keyed by stable application ID. The notifications_enabled field is the application's local notification enablement preference and is distinct from notification-sending authorization owned by Privacy.",
            default={'Chat': {'name': 'Chat', 'notifications_enabled': True, 'alert_behavior': 'alert', 'lock_screen_display': 'show_content'}, 'Calendar': {'name': 'Calendar', 'notifications_enabled': True, 'alert_behavior': 'alert', 'lock_screen_display': 'hide_content'}},
            mode=2,
            schema={'type': 'object', 'propertyNames': {'pattern': '^[A-Za-z0-9_-]+$', 'maxLength': 128}, 'additionalProperties': {'type': 'object', 'properties': {'name': {'type': 'string', 'minLength': 1, 'maxLength': 128}, 'notifications_enabled': {'type': 'boolean'}, 'alert_behavior': {'type': 'string', 'enum': ['alert', 'silent']}, 'lock_screen_display': {'type': 'string', 'enum': ['show_content', 'hide_content', 'do_not_show']}}, 'required': ['name', 'notifications_enabled', 'alert_behavior', 'lock_screen_display'], 'additionalProperties': False}}
        )
        self.channel_settings = DictProperty(
            name='channel_settings',
            description='Notification channel preferences keyed by stable channel ID. Each channel belongs to one application. Channel settings refine but do not override a disabled application preference or external Privacy and Focus restrictions.',
            default={'chat_messages': {'app_id': 'Chat', 'name': 'Messages', 'notifications_enabled': True, 'alert_behavior': 'alert', 'lock_screen_display': 'show_content'}, 'chat_updates': {'app_id': 'Chat', 'name': 'Updates', 'notifications_enabled': True, 'alert_behavior': 'silent', 'lock_screen_display': 'hide_content'}, 'calendar_reminders': {'app_id': 'Calendar', 'name': 'Reminders', 'notifications_enabled': True, 'alert_behavior': 'alert', 'lock_screen_display': 'hide_content'}},
            mode=2,
            schema={'type': 'object', 'propertyNames': {'pattern': '^[A-Za-z0-9_-]+$', 'maxLength': 128}, 'additionalProperties': {'type': 'object', 'properties': {'app_id': {'type': 'string', 'pattern': '^[A-Za-z0-9_-]+$', 'maxLength': 128}, 'name': {'type': 'string', 'minLength': 1, 'maxLength': 128}, 'notifications_enabled': {'type': 'boolean'}, 'alert_behavior': {'type': 'string', 'enum': ['alert', 'silent']}, 'lock_screen_display': {'type': 'string', 'enum': ['show_content', 'hide_content', 'do_not_show']}}, 'required': ['app_id', 'name', 'notifications_enabled', 'alert_behavior', 'lock_screen_display'], 'additionalProperties': False}}
        )
        self.current_notifications = DictProperty(
            name='current_notifications',
            description='Currently posted synthetic notifications keyed by stable notification ID. Records contain metadata only and do not represent content obtained from a real application or network service.',
            default={'chat_001': {'app_id': 'Chat', 'channel_id': 'chat_messages', 'title': 'Alice', 'content': 'Lunch at noon?', 'dismissible': True}, 'calendar_001': {'app_id': 'Calendar', 'channel_id': 'calendar_reminders', 'title': 'Calendar reminder', 'content': 'Team meeting in 10 minutes', 'dismissible': False}},
            mode=2,
            schema={'type': 'object', 'propertyNames': {'pattern': '^[A-Za-z0-9_-]+$', 'maxLength': 128}, 'additionalProperties': {'type': 'object', 'properties': {'app_id': {'type': 'string', 'pattern': '^[A-Za-z0-9_-]+$', 'maxLength': 128}, 'channel_id': {'type': 'string', 'pattern': '^[A-Za-z0-9_-]+$', 'maxLength': 128}, 'title': {'type': 'string', 'maxLength': 256}, 'content': {'type': 'string', 'maxLength': 1024}, 'dismissible': {'type': 'boolean'}}, 'required': ['app_id', 'channel_id', 'title', 'content', 'dismissible'], 'additionalProperties': False}}
        )

        # initialize properties
        if application_settings is not None: code = self.application_settings.internal_set(application_settings)
        if channel_settings is not None: code = self.channel_settings.internal_set(channel_settings)
        if current_notifications is not None: code = self.current_notifications.internal_set(current_notifications)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_application_setting(self, app_id: str) -> tuple[str, dict]:
        """
        Return the notification presentation preferences for one existing application ID. This reports local notification settings and does not report or modify the separate notification-sending authorization owned by Privacy.

        Args:
        - app_id: An existing stable application ID.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- application_setting: The selected application's notification presentation preferences. (type=object)

        Error Codes:
        - NOT_FOUND: Application ID does not exist.
        """
        code, settings = self.application_settings.get()
        if code != '[PASS]':
            return (code, {})
        if type(app_id) is not str or app_id not in settings:
            return ('[NOT_FOUND]', {})
        response = {
            'application_setting': dict(settings[app_id])
        }
        return ('[PASS]', response)

    def update_application_setting(self, app_id: str, notifications_enabled: bool = None, alert_behavior: str = None, lock_screen_display: str = None) -> tuple[str, dict]:
        """
        Partially update an existing application's notification presentation preferences. Omitted fields remain unchanged, the application name remains unchanged, and all other application records are preserved. notifications_enabled controls this module's application-level notification preference but does not grant Privacy authorization or guarantee that a notification will be shown or make a sound.

        Args:
        - app_id: An existing stable application ID.
        - notifications_enabled: Optional application-level notification enablement preference.
        - alert_behavior: Optional application alert preference. (choices=['alert', 'silent'])
        - lock_screen_display: Optional application lock-screen content preference. (choices=['show_content', 'hide_content', 'do_not_show'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - NOT_FOUND: Application ID does not exist.
        - INVALID_ARGUMENT: No preference field was supplied or a supplied value is unsupported.
        """
        code, settings = self.application_settings.get()
        if code != '[PASS]':
            return (code, {})
        if type(app_id) is not str or app_id not in settings:
            return ('[NOT_FOUND]', {})
        if notifications_enabled is None and alert_behavior is None and lock_screen_display is None:
            return ('[INVALID_ARGUMENT]', {})
        if notifications_enabled is not None and type(notifications_enabled) is not bool:
            return ('[INVALID_ARGUMENT]', {})
        if alert_behavior is not None and (
            type(alert_behavior) is not str
            or alert_behavior not in ('alert', 'silent')
        ):
            return ('[INVALID_ARGUMENT]', {})
        if lock_screen_display is not None and (
            type(lock_screen_display) is not str
            or lock_screen_display not in ('show_content', 'hide_content', 'do_not_show')
        ):
            return ('[INVALID_ARGUMENT]', {})

        updated_settings = dict(settings)
        updated_record = dict(settings[app_id])
        if notifications_enabled is not None:
            updated_record['notifications_enabled'] = notifications_enabled
        if alert_behavior is not None:
            updated_record['alert_behavior'] = alert_behavior
        if lock_screen_display is not None:
            updated_record['lock_screen_display'] = lock_screen_display
        updated_settings[app_id] = updated_record

        code = self.application_settings.internal_set(updated_settings)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_channel_setting(self, channel_id: str) -> tuple[str, dict]:
        """
        Return the notification preferences for one existing channel ID, including the stable ID of its owning application.

        Args:
        - channel_id: An existing stable notification channel ID.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- channel_setting: The selected notification channel's preferences and owning application ID. (type=object)

        Error Codes:
        - NOT_FOUND: Channel ID does not exist.
        """
        code, settings = self.channel_settings.get()
        if code != '[PASS]':
            return (code, {})
        if type(channel_id) is not str or channel_id not in settings:
            return ('[NOT_FOUND]', {})
        response = {
            'channel_setting': dict(settings[channel_id])
        }
        return ('[PASS]', response)

    def update_channel_setting(self, channel_id: str, notifications_enabled: bool = None, alert_behavior: str = None, lock_screen_display: str = None) -> tuple[str, dict]:
        """
        Partially update an existing notification channel. Omitted fields remain unchanged, ownership and channel name remain unchanged, and all other channel records are preserved. Enabling a channel does not override a disabled application preference, Privacy authorization, Focus policy, or Sound state.

        Args:
        - channel_id: An existing stable notification channel ID.
        - notifications_enabled: Optional channel-level notification enablement preference.
        - alert_behavior: Optional channel alert preference. (choices=['alert', 'silent'])
        - lock_screen_display: Optional channel lock-screen content preference. (choices=['show_content', 'hide_content', 'do_not_show'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - NOT_FOUND: Channel ID does not exist.
        - INVALID_ARGUMENT: No preference field was supplied or a supplied value is unsupported.
        """
        code, settings = self.channel_settings.get()
        if code != '[PASS]':
            return (code, {})
        if type(channel_id) is not str or channel_id not in settings:
            return ('[NOT_FOUND]', {})
        if notifications_enabled is None and alert_behavior is None and lock_screen_display is None:
            return ('[INVALID_ARGUMENT]', {})
        if notifications_enabled is not None and type(notifications_enabled) is not bool:
            return ('[INVALID_ARGUMENT]', {})
        if alert_behavior is not None and (
            type(alert_behavior) is not str
            or alert_behavior not in ('alert', 'silent')
        ):
            return ('[INVALID_ARGUMENT]', {})
        if lock_screen_display is not None and (
            type(lock_screen_display) is not str
            or lock_screen_display not in ('show_content', 'hide_content', 'do_not_show')
        ):
            return ('[INVALID_ARGUMENT]', {})

        updated_settings = dict(settings)
        updated_record = dict(settings[channel_id])
        if notifications_enabled is not None:
            updated_record['notifications_enabled'] = notifications_enabled
        if alert_behavior is not None:
            updated_record['alert_behavior'] = alert_behavior
        if lock_screen_display is not None:
            updated_record['lock_screen_display'] = lock_screen_display
        updated_settings[channel_id] = updated_record

        code = self.channel_settings.internal_set(updated_settings)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})

    def get_current_notifications(self) -> tuple[str, dict]:
        """
        Return all currently posted synthetic notifications keyed by stable notification ID. The records are local simulation metadata and querying them does not dismiss or otherwise change them.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- current_notifications: Dictionary of currently posted synthetic notifications keyed by notification ID. (type=object)

        Error Codes:
        (no specified error codes)
        """
        code, notifications = self.current_notifications.get()
        if code != '[PASS]':
            return (code, {})
        response = {
            'current_notifications': {
                notification_id: dict(record)
                for notification_id, record in notifications.items()
            }
        }
        return ('[PASS]', response)

    def get_notification(self, notification_id: str) -> tuple[str, dict]:
        """
        Return one currently posted synthetic notification by its stable ID without changing it.

        Args:
        - notification_id: An existing stable notification ID.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- notification: The selected synthetic notification record. (type=object)

        Error Codes:
        - NOT_FOUND: Notification ID does not exist.
        """
        code, notifications = self.current_notifications.get()
        if code != '[PASS]':
            return (code, {})
        if type(notification_id) is not str or notification_id not in notifications:
            return ('[NOT_FOUND]', {})
        response = {
            'notification': dict(notifications[notification_id])
        }
        return ('[PASS]', response)

    def dismiss_notification(self, notification_id: str) -> tuple[str, dict]:
        """
        Dismiss an existing synthetic notification by deleting only its record. The notification must have dismissible set to true. A nonexistent ID or a nondismissible notification causes an explicit failure and leaves every notification unchanged.

        Args:
        - notification_id: The stable ID of an existing dismissible notification.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - NOT_FOUND: Notification ID does not exist.
        - NOT_DISMISSIBLE: The selected notification is marked nondismissible.
        """
        code, notifications = self.current_notifications.get()
        if code != '[PASS]':
            return (code, {})
        if type(notification_id) is not str or notification_id not in notifications:
            return ('[NOT_FOUND]', {})
        if not notifications[notification_id]['dismissible']:
            return ('[NOT_DISMISSIBLE]', {})

        updated_notifications = dict(notifications)
        del updated_notifications[notification_id]
        code = self.current_notifications.internal_set(updated_notifications)
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {})