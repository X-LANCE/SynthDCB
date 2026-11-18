# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class VehicleSecurity:
    """
    VehicleSecurity
    Description: Vehicle anti-theft and parked security module. Supports arming, disarming, and querying security state and the current trigger reason. Triggers arise from configured local sensor events. Dismissing an alarm requires authorization; door lock state is still read from Door, and arming does not mean the doors are locked. Recording requests are delegated to Dashcam; an alarm trigger does not mean a recording has been saved.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, security_state: str = None, trigger_reason: str = None, dismissal_authorized: bool = None) -> None:
        # define properties
        self.security_state = StringProperty(
            name='security_state',
            description='Current anti-theft state. Alarm indicates that a configured local sensor triggered while the system was armed.',
            default='disarmed',
            mode=2,
            choices=['disarmed', 'armed', 'alarm']
        )
        self.trigger_reason = StringProperty(
            name='trigger_reason',
            description='Reason for the current alarm. It is none unless security_state is alarm.',
            default='none',
            mode=2,
            choices=['none', 'door_opened', 'glass_break', 'interior_motion', 'vehicle_tampering']
        )
        self.dismissal_authorized = BoolProperty(
            name='dismissal_authorized',
            description='Whether the configured local authorization source currently permits dismissal of an active alarm. This module records only the authorization result and does not validate credentials.',
            default=False,
            mode=2
        )

        # initialize properties
        if security_state is not None: code = self.security_state.internal_set(security_state)
        if trigger_reason is not None: code = self.trigger_reason.internal_set(trigger_reason)
        if dismissal_authorized is not None: code = self.dismissal_authorized.internal_set(dismissal_authorized)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    def get_security_state(self) -> tuple[str, dict]:
        """
        Return the current security state without changing it. The result does not report or imply any Door lock state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- security_state: Current state: disarmed, armed, or alarm. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.security_state.get()
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {'security_state': value}

    def get_trigger_reason(self) -> tuple[str, dict]:
        """
        Return the current alarm trigger reason without changing state. The result is none when no alarm is active.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- trigger_reason: Current trigger reason, or none when no alarm is active. (type=string)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.trigger_reason.get()
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {'trigger_reason': value}

    def get_dismissal_authorized(self) -> tuple[str, dict]:
        """
        Return whether the configured local authorization source currently permits dismissal of an active alarm. This query does not perform authentication or change authorization.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- dismissal_authorized: Whether alarm dismissal is currently authorized. (type=boolean)

        Error Codes:
        (no specified error codes)
        """
        code, value = self.dismissal_authorized.get()
        if code != '[PASS]':
            return code, {}
        return '[PASS]', {'dismissal_authorized': value}

    def arm(self) -> tuple[str, dict]:
        """
        Arm the anti-theft system while it is disarmed. This action clears any stale trigger reason, does not change Door lock state, and does not request Dashcam recording. A request made from armed or alarm state is rejected without changing state.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: The security system can be armed only while disarmed.
        """
        state_code, state = self.security_state.get()
        if state_code != '[PASS]':
            return state_code, {}
        if state != 'disarmed':
            return '[PRECONDITION_FAILED]', {}

        reason_code = self.trigger_reason.internal_set('none')
        if reason_code != '[PASS]':
            return reason_code, {}

        state_code = self.security_state.internal_set('armed')
        if state_code != '[PASS]':
            return state_code, {}
        return '[PASS]', {}

    def disarm(self) -> tuple[str, dict]:
        """
        Disarm an armed system that has not triggered and clear the trigger reason. An active alarm must instead be dismissed with dismiss_alarm, which requires authorization. Rejected requests leave state unchanged.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: Ordinary disarming is allowed only from armed state; an active alarm requires authorized dismissal.
        """
        state_code, state = self.security_state.get()
        if state_code != '[PASS]':
            return state_code, {}
        if state != 'armed':
            return '[PRECONDITION_FAILED]', {}

        reason_code = self.trigger_reason.internal_set('none')
        if reason_code != '[PASS]':
            return reason_code, {}

        state_code = self.security_state.internal_set('disarmed')
        if state_code != '[PASS]':
            return state_code, {}
        return '[PASS]', {}

    def dismiss_alarm(self) -> tuple[str, dict]:
        """
        Dismiss an active alarm and return the system to disarmed state, clearing the trigger reason. The action succeeds only while an alarm is active and dismissal_authorized is true. Authorization is supplied by the configured local authorization source; this action does not accept or validate credentials. Failure leaves all state unchanged.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - PRECONDITION_FAILED: Alarm dismissal requires an active alarm and current authorization from the configured local authorization source.
        """
        state_code, state = self.security_state.get()
        if state_code != '[PASS]':
            return state_code, {}

        authorization_code, authorized = self.dismissal_authorized.get()
        if authorization_code != '[PASS]':
            return authorization_code, {}

        if state != 'alarm' or not authorized:
            return '[PRECONDITION_FAILED]', {}

        reason_code = self.trigger_reason.internal_set('none')
        if reason_code != '[PASS]':
            return reason_code, {}

        state_code = self.security_state.internal_set('disarmed')
        if state_code != '[PASS]':
            return state_code, {}
        return '[PASS]', {}

    def _on_dependency_changed(self, context: dict) -> tuple[str, list[dict]]:
        """
        Mirror the configured local authorization decision into dismissal_authorized. While security_state is armed, an active configured security sensor changes security_state to alarm and records its reported reason. If multiple sensor reasons become active together, select the first by this fixed precedence: door_opened, glass_break, interior_motion, vehicle_tampering. Sensor activity is ignored while disarmed, and an existing alarm preserves its recorded trigger reason until dismissed.

    Effect properties:
    - security_state: Determines whether configured sensor activity can trigger an alarm or whether an existing alarm must be preserved.
    - trigger_reason: Preserves the reason already recorded for an active alarm.
    - dismissal_authorized: Stores the current authorization result supplied by the configured local authorization source.
        """
        state_code, state = self.security_state.get()
        if state_code != '[PASS]':
            return state_code, []

        reason_code, current_reason = self.trigger_reason.get()
        if reason_code != '[PASS]':
            return reason_code, []

        authorization_code, current_authorization = self.dismissal_authorized.get()
        if authorization_code != '[PASS]':
            return authorization_code, []

        authorization_value = current_authorization
        active_reasons = {
            'door_opened': False,
            'glass_break': False,
            'interior_motion': False,
            'vehicle_tampering': False
        }

        for dependency in context['dependencies'].values():
            if 'dismissal_authorized' in dependency:
                authorization_value = dependency['dismissal_authorized']
            elif 'authorization_granted' in dependency:
                authorization_value = dependency['authorization_granted']
            elif 'authorized' in dependency:
                authorization_value = dependency['authorized']

            sensor_active = False
            if 'active' in dependency:
                sensor_active = dependency['active']
            elif 'trigger_active' in dependency:
                sensor_active = dependency['trigger_active']

            reported_reason = 'none'
            if 'trigger_reason' in dependency:
                reported_reason = dependency['trigger_reason']
            elif 'reason' in dependency:
                reported_reason = dependency['reason']

            if sensor_active and reported_reason in active_reasons:
                active_reasons[reported_reason] = True

            for reason in active_reasons:
                if reason in dependency and dependency[reason] is True:
                    active_reasons[reason] = True

        if type(authorization_value) is not bool:
            return '[INVALID_INPUT_ERROR]', []

        authorization_code = self.dismissal_authorized.internal_set(authorization_value)
        if authorization_code != '[PASS]':
            return authorization_code, []

        if state != 'armed':
            return '[PASS]', []

        selected_reason = 'none'
        for reason in ('door_opened', 'glass_break', 'interior_motion', 'vehicle_tampering'):
            if active_reasons[reason]:
                selected_reason = reason
                break

        if selected_reason == 'none':
            return '[PASS]', []

        reason_code = self.trigger_reason.internal_set(selected_reason)
        if reason_code != '[PASS]':
            return reason_code, []

        state_code = self.security_state.internal_set('alarm')
        if state_code != '[PASS]':
            return state_code, []

        return '[PASS]', []