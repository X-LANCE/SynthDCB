# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty

class SeatComfort:
    """
    SeatComfort
    Description: Powered seat position adjustment module, instantiated for each actual seat. Supports querying and adjusting the powered position axes of that seat and stopping adjustment. Available axes and travel ranges are fixed capabilities; axes that are not installed offer no control. Target and actual positions are separate, with progress and obstruction state available during motion.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, axes: dict = None, motion_status: str = None, active_axis: str = None, progress_percent: int = None, obstruction_state: str = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether powered seat adjustment is available.',
            default=False
        )
        self.axes = DictProperty(
            name='axes',
            description='Installed position axes keyed by axis name. Each record contains immutable normalized travel limits and unit together with internally updated actual, target, and motion-start positions. Axes absent from this dictionary are not installed and cannot be controlled.',
            default={'fore_aft': {'minimum': 0, 'maximum': 100, 'unit': '%', 'actual': 50, 'requested_position': 50, 'start': 50}, 'height': {'minimum': 0, 'maximum': 100, 'unit': '%', 'actual': 50, 'requested_position': 50, 'start': 50}, 'recline': {'minimum': 0, 'maximum': 100, 'unit': '%', 'actual': 50, 'requested_position': 50, 'start': 50}, 'lumbar': {'minimum': 0, 'maximum': 100, 'unit': '%', 'actual': 50, 'requested_position': 50, 'start': 50}},
            mode=2,
            schema={'type': 'object', 'propertyNames': {'enum': ['fore_aft', 'height', 'recline', 'lumbar']}, 'additionalProperties': {'type': 'object', 'properties': {'minimum': {'type': 'integer', 'minimum': 0, 'maximum': 100}, 'maximum': {'type': 'integer', 'minimum': 0, 'maximum': 100}, 'unit': {'type': 'string', 'const': '%'}, 'actual': {'type': 'integer', 'minimum': 0, 'maximum': 100}, 'requested_position': {'type': 'integer', 'minimum': 0, 'maximum': 100}, 'start': {'type': 'integer', 'minimum': 0, 'maximum': 100}}, 'required': ['minimum', 'maximum', 'unit', 'actual', 'requested_position', 'start'], 'additionalProperties': False}}
        )
        self.motion_status = StringProperty(
            name='motion_status',
            description='Current adjustment state. Paused indicates that power was removed during motion; obstructed indicates that motion stopped after obstruction detection.',
            default='idle',
            mode=2,
            choices=['idle', 'moving', 'paused', 'obstructed']
        )
        self.active_axis = StringProperty(
            name='active_axis',
            description='Axis associated with the current or interrupted adjustment, or none when no adjustment is pending.',
            default='none',
            mode=2,
            choices=['none', 'fore_aft', 'height', 'recline', 'lumbar']
        )
        self.progress_percent = IntProperty(
            name='progress_percent',
            description='Integer progress of the active adjustment from its recorded start position to its target. It is 0 while a newly requested movement is pending and 100 when no adjustment is pending or the target has been reached.',
            default=100,
            mode=2,
            unit='%',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.obstruction_state = StringProperty(
            name='obstruction_state',
            description='Seat adjustment obstruction feedback supplied by the simulated seat mechanism through the obstruction reporting actions.',
            default='clear',
            mode=2,
            choices=['clear', 'detected']
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if axes is not None: code = self.axes.internal_set(axes)
        if motion_status is not None: code = self.motion_status.internal_set(motion_status)
        if active_axis is not None: code = self.active_axis.internal_set(active_axis)
        if progress_percent is not None: code = self.progress_percent.internal_set(progress_percent)
        if obstruction_state is not None: code = self.obstruction_state.internal_set(obstruction_state)
        self._power_managed_properties = (self.axes, self.motion_status, self.active_axis, self.progress_percent, self.obstruction_state,)
        self._power_initialized = False
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

        if not _defer_power_init:
            self.set_power(_power_init_value)

    def get_power(self) -> tuple[str, dict]:
        """
        Get the current power state.
        """
        code, value = self.power.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"power": value}

    def set_power(self, value: bool) -> tuple[str, dict]:
        """
        Set power and update access for active dependent properties.
        """
        if self._power_initialized:
            current_code, current_value = self.power.get()
            if current_code != "[PASS]":
                return current_code, {}
            if type(value) is bool and current_value == value:
                return "[PASS]", {}
        code = self.power.set(value)
        if code != "[PASS]":
            return code, {}
        for prop in self._power_managed_properties:
            switch_code = prop.handle_power_switch(value)
            if switch_code != "[PASS]" and not switch_code.startswith("[NO_ACTION]"):
                return switch_code, {}
        self._power_initialized = True
        return "[PASS]", {}

    def get_axes(self) -> tuple[str, dict]:
        """
        Return all installed axes with their fixed limits, units, actual positions, target positions, and motion-start positions. Requires power on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- axes: Installed axis capability and position records keyed by axis name. (type=object)

        Error Codes:
        - POWER_OFF: Seat adjustment module must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        code, value = self.axes.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"axes": value}

    def get_motion_status(self) -> tuple[str, dict]:
        """
        Return the current adjustment state. Requires power on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- motion_status: Current state: idle, moving, paused, or obstructed. (type=string)

        Error Codes:
        - POWER_OFF: Seat adjustment module must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        code, value = self.motion_status.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"motion_status": value}

    def get_active_axis(self) -> tuple[str, dict]:
        """
        Return the axis associated with the current or interrupted adjustment. Requires power on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- active_axis: Active axis name, or none when no adjustment is pending. (type=string)

        Error Codes:
        - POWER_OFF: Seat adjustment module must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        code, value = self.active_axis.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"active_axis": value}

    def get_progress_percent(self) -> tuple[str, dict]:
        """
        Return adjustment progress as an integer from 0 through 100 percent. A newly requested movement reports 0 until the first eligible minute tick completes it, after which it reports 100. Requires power on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- progress_percent: Current adjustment progress percentage. (type=integer)

        Error Codes:
        - POWER_OFF: Seat adjustment module must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        code, value = self.progress_percent.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"progress_percent": value}

    def get_obstruction_state(self) -> tuple[str, dict]:
        """
        Return the current seat mechanism obstruction feedback. Requires power on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- obstruction_state: Current obstruction feedback: clear or detected. (type=string)

        Error Codes:
        - POWER_OFF: Seat adjustment module must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        code, value = self.obstruction_state.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"obstruction_state": value}

    def adjust_position(self, axis: str, target: int) -> tuple[str, dict]:
        """
        Begin moving one installed axis toward target, expressed as an integer percentage of that axis's normalized travel. The target must fall within the selected axis record's fixed minimum and maximum. The action is allowed only while powered, idle, and unobstructed. An absent axis, an out-of-range target, or a failed precondition leaves all state unchanged. On a successful unequal-target request, only the selected axis record is changed: start is set to its current actual value and target is set to the requested target; actual remains unchanged, motion_status becomes moving, active_axis becomes the selected axis, and progress_percent becomes 0. The movement completes on the first eligible minute tick. On a successful equal-target request, the selected record's start and target are both set to its current actual value, actual remains unchanged, motion_status remains idle, active_axis becomes none, and progress_percent becomes 100. Every unselected axis record remains unchanged.

        Args:
        - axis:  (choices=['fore_aft', 'height', 'recline', 'lumbar'])
        - target:  (min=0, max=100)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Seat adjustment module must be powered on.
        - AXIS_NOT_INSTALLED: The requested axis is not installed on this seat.
        - TARGET_OUT_OF_RANGE: Target must be within the selected axis's fixed minimum and maximum.
        - ADJUSTMENT_ACTIVE: Stop the current or interrupted adjustment before starting another.
        - OBSTRUCTION_DETECTED: Adjustment cannot start while an obstruction is detected.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        if type(axis) is not str or type(target) is not int:
            return "[INVALID_INPUT_ERROR]", {}

        axes_code, axes_value = self.axes.get()
        if axes_code != "[PASS]":
            return axes_code, {}
        if axis not in axes_value:
            return "[AXIS_NOT_INSTALLED]", {}

        selected_record = axes_value[axis]
        if target < selected_record["minimum"] or target > selected_record["maximum"]:
            return "[TARGET_OUT_OF_RANGE]", {}

        status_code, status = self.motion_status.get()
        if status_code != "[PASS]":
            return status_code, {}
        if status != "idle":
            return "[ADJUSTMENT_ACTIVE]", {}

        obstruction_code, obstruction = self.obstruction_state.get()
        if obstruction_code != "[PASS]":
            return obstruction_code, {}
        if obstruction == "detected":
            return "[OBSTRUCTION_DETECTED]", {}

        actual = selected_record["actual"]
        updated_axes = {
            axis_name: {
                field_name: field_value
                for field_name, field_value in record.items()
            }
            for axis_name, record in axes_value.items()
        }
        updated_axes[axis]["start"] = actual
        updated_axes[axis]["requested_position"] = target

        next_status = "moving" if target != actual else "idle"
        next_active_axis = axis if target != actual else "none"
        next_progress = 0 if target != actual else 100

        code = self.axes.internal_set(updated_axes)
        if code != "[PASS]":
            return code, {}
        code = self.motion_status.internal_set(next_status)
        if code != "[PASS]":
            return code, {}
        code = self.active_axis.internal_set(next_active_axis)
        if code != "[PASS]":
            return code, {}
        code = self.progress_percent.internal_set(next_progress)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def stop_adjustment(self) -> tuple[str, dict]:
        """
        Stop a moving, paused, or obstructed adjustment. When an active axis exists, only that axis record's target is replaced with its current actual position; its actual, start, limits, and unit remain unchanged. Motion_status becomes idle, active_axis becomes none, and progress_percent becomes 100. Calling while already idle leaves the axis records unchanged and idempotently sets the same idle state. Obstruction feedback is preserved and must be cleared separately. Requires power on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Seat adjustment module must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        active_code, active = self.active_axis.get()
        if active_code != "[PASS]":
            return active_code, {}

        updated_axes = None
        if active != "none":
            axes_code, axes_value = self.axes.get()
            if axes_code != "[PASS]":
                return axes_code, {}
            if active in axes_value:
                updated_axes = {
                    axis_name: {
                        field_name: field_value
                        for field_name, field_value in record.items()
                    }
                    for axis_name, record in axes_value.items()
                }
                updated_axes[active]["requested_position"] = updated_axes[active]["actual"]

        if updated_axes is not None:
            code = self.axes.internal_set(updated_axes)
            if code != "[PASS]":
                return code, {}
        code = self.motion_status.internal_set("idle")
        if code != "[PASS]":
            return code, {}
        code = self.active_axis.internal_set("none")
        if code != "[PASS]":
            return code, {}
        code = self.progress_percent.internal_set(100)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def report_obstruction(self) -> tuple[str, dict]:
        """
        Report that the simulated seat mechanism has detected an obstruction. Obstruction_state becomes detected. If adjustment is moving, it stops without changing the active axis's actual or target position and motion_status becomes obstructed. Reporting an already detected obstruction succeeds idempotently. Requires power on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Seat adjustment module must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        status_code, status = self.motion_status.get()
        if status_code != "[PASS]":
            return status_code, {}

        if status == "moving":
            code = self.motion_status.internal_set("obstructed")
            if code != "[PASS]":
                return code, {}
        code = self.obstruction_state.internal_set("detected")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def clear_obstruction(self) -> tuple[str, dict]:
        """
        Report that the simulated seat mechanism is no longer obstructed. Obstruction_state becomes clear. Clearing feedback does not resume or cancel a paused or obstructed adjustment; stop_adjustment must be used before a new adjustment can start. Clearing an already clear state succeeds idempotently. Requires power on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Seat adjustment module must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        code = self.obstruction_state.internal_set("clear")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        """
        When power changes from on to off while motion_status is moving, preserve all axis positions and targets and change motion_status to paused. Restoring power does not resume movement.

    Effect properties:
    - power: Determines whether moving adjustment must be paused after power removal.
    - motion_status: Identifies movement that must transition to paused after power removal.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, []

        previous_properties = context["pre_state"]["objects"][context["object_id"]]["properties"]
        previous_power = previous_properties["power"]
        previous_status = previous_properties["motion_status"]

        if previous_power is True and powered is False and previous_status == "moving":
            code = self.motion_status.internal_set("paused")
            if code != "[PASS]":
                return code, []

        return "[PASS]", []

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        On the first minute tick while powered with motion_status moving and obstruction_state clear, set the active axis's actual position to its target without changing that record's fixed limits, unit, start, or target. Then set progress_percent to 100, motion_status to idle, and active_axis to none. If obstruction_state is detected while status is moving, do not change any axis position and set motion_status to obstructed. Idle, paused, obstructed, and unpowered states do not advance.

    Effect properties:
    - power: Determines whether a pending adjustment may complete.
    - axes: Provides the active axis target and receives the completed actual-position update.
    - motion_status: Determines whether adjustment is moving and records completion or obstruction.
    - active_axis: Selects the installed axis record being adjusted and is cleared on completion.
    - progress_percent: Records 100 percent progress when the requested movement completes.
    - obstruction_state: Prevents completion and changes moving status to obstructed when detection is active.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, []
        if powered is not True:
            return "[PASS]", []

        status_code, status = self.motion_status.get()
        if status_code != "[PASS]":
            return status_code, []
        if status != "moving":
            return "[PASS]", []

        obstruction_code, obstruction = self.obstruction_state.get()
        if obstruction_code != "[PASS]":
            return obstruction_code, []
        if obstruction == "detected":
            code = self.motion_status.internal_set("obstructed")
            if code != "[PASS]":
                return code, []
            return "[PASS]", []

        active_code, active = self.active_axis.get()
        if active_code != "[PASS]":
            return active_code, []

        axes_code, axes_value = self.axes.get()
        if axes_code != "[PASS]":
            return axes_code, []
        if active == "none" or active not in axes_value:
            return "[PASS]", []

        updated_axes = {
            axis_name: {
                field_name: field_value
                for field_name, field_value in record.items()
            }
            for axis_name, record in axes_value.items()
        }
        updated_axes[active]["actual"] = updated_axes[active]["requested_position"]

        code = self.axes.internal_set(updated_axes)
        if code != "[PASS]":
            return code, []
        code = self.progress_percent.internal_set(100)
        if code != "[PASS]":
            return code, []
        code = self.motion_status.internal_set("idle")
        if code != "[PASS]":
            return code, []
        code = self.active_axis.internal_set("none")
        if code != "[PASS]":
            return code, []
        return "[PASS]", []