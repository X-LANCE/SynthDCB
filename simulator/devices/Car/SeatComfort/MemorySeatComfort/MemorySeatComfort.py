# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..SeatComfort import SeatComfort

class MemorySeatComfort(SeatComfort):
    """
    MemorySeatComfort
    Description: Powered seat with memory. Adds saving the current actual position to a local memory slot, recalling a saved position, and canceling recall. Recall uses the existing adjustment process.
    Version: 1.0.0
    Base: SeatComfort
    """

    def __init__(self, memory_slots: dict = None, active_memory_slot: str = None, *, power: bool | None = None, _defer_power_init: bool = False, **base_kwargs) -> None:
        _power_init_value = power if power is not None else False
        # initialize base SeatComfort class
        super().__init__(power=_power_init_value, _defer_power_init=True, **base_kwargs)
        # define properties
        self.memory_slots = DictProperty(
            name='memory_slots',
            description='Local memory slots keyed by caller-supplied slot ID. Each slot contains a snapshot of the actual positions of all installed axes at the time it was saved.',
            default={},
            mode=2,
            schema={'type': 'object', 'propertyNames': {'type': 'string', 'pattern': '^(?!none$)[a-z0-9][a-z0-9_-]{0,31}$'}, 'additionalProperties': {'type': 'object', 'properties': {'positions': {'type': 'object', 'propertyNames': {'enum': ['fore_aft', 'height', 'recline', 'lumbar']}, 'additionalProperties': {'type': 'integer', 'minimum': 0, 'maximum': 100}}}, 'required': ['positions'], 'additionalProperties': False}}
        )
        self.active_memory_slot = StringProperty(
            name='active_memory_slot',
            description='Slot currently being recalled, or none when no memory recall is active. A recall remains active across its sequential axis adjustments and while paused or obstructed.',
            default='none',
            mode=2,
            pattern='^(none|[a-z0-9][a-z0-9_-]{0,31})$',
            max_length=32
        )

        # initialize properties
        if memory_slots is not None: code = self.memory_slots.internal_set(memory_slots)
        if active_memory_slot is not None: code = self.active_memory_slot.internal_set(active_memory_slot)
        self._power_managed_properties = (self.axes, self.motion_status, self.active_axis, self.progress_percent, self.obstruction_state, self.memory_slots, self.active_memory_slot,)
        self._power_initialized = False
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

        if not _defer_power_init:
            self.set_power(_power_init_value)

    def get_memory_slot(self, slot_id: str) -> tuple[str, dict]:
        """
        Return one saved memory slot, including the saved positions of all axes installed when the slot was last saved. The seat must be powered on and the slot must exist.

        Args:
        - slot_id:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- memory_slot: Saved position snapshot for the requested memory slot. (type=object)

        Error Codes:
        - POWER_OFF: Seat adjustment module must be powered on.
        - MEMORY_SLOT_NOT_FOUND: The requested memory slot does not exist.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        valid_characters = "abcdefghijklmnopqrstuvwxyz0123456789_-"
        valid_initial_characters = "abcdefghijklmnopqrstuvwxyz0123456789"
        if (
            type(slot_id) is not str
            or len(slot_id) < 1
            or len(slot_id) > 32
            or slot_id == "none"
            or slot_id[0] not in valid_initial_characters
            or any(character not in valid_characters for character in slot_id)
        ):
            return "[INVALID_INPUT_ERROR]", {}

        slots_code, slots = self.memory_slots.get()
        if slots_code != "[PASS]":
            return slots_code, {}
        if slot_id not in slots:
            return "[MEMORY_SLOT_NOT_FOUND]", {}

        slot = slots[slot_id]
        response_slot = {
            "positions": {
                axis_name: position
                for axis_name, position in slot["positions"].items()
            }
        }
        return "[PASS]", {"memory_slot": response_slot}

    def get_active_memory_slot(self) -> tuple[str, dict]:
        """
        Return the slot currently being recalled, or none when no recall is active. Requires power on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- active_memory_slot: Active memory slot ID, or none when no recall is active. (type=string)

        Error Codes:
        - POWER_OFF: Seat adjustment module must be powered on.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        code, value = self.active_memory_slot.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"active_memory_slot": value}

    def save_memory_slot(self, slot_id: str) -> tuple[str, dict]:
        """
        Save the current actual position of every installed axis under slot_id. The seat must be powered on and idle, with no active recall. If the slot already exists, only that slot is replaced; every other slot is preserved. Targets and motion state are not changed. Invalid input or a failed precondition leaves all state unchanged.

        Args:
        - slot_id:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Seat adjustment module must be powered on.
        - ADJUSTMENT_ACTIVE: A memory slot can be saved only while seat adjustment is idle.
        - RECALL_ACTIVE: A memory slot cannot be saved while a memory recall is active.
        - INVALID_INPUT_ERROR: Slot ID must contain 1 through 32 lowercase letters, digits, underscores, or hyphens, must begin with a letter or digit, and cannot be none.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        valid_characters = "abcdefghijklmnopqrstuvwxyz0123456789_-"
        valid_initial_characters = "abcdefghijklmnopqrstuvwxyz0123456789"
        if (
            type(slot_id) is not str
            or len(slot_id) < 1
            or len(slot_id) > 32
            or slot_id == "none"
            or slot_id[0] not in valid_initial_characters
            or any(character not in valid_characters for character in slot_id)
        ):
            return "[INVALID_INPUT_ERROR]", {}

        status_code, status = self.motion_status.get()
        if status_code != "[PASS]":
            return status_code, {}
        if status != "idle":
            return "[ADJUSTMENT_ACTIVE]", {}

        active_slot_code, active_slot = self.active_memory_slot.get()
        if active_slot_code != "[PASS]":
            return active_slot_code, {}
        if active_slot != "none":
            return "[RECALL_ACTIVE]", {}

        axes_code, axes_value = self.axes.get()
        if axes_code != "[PASS]":
            return axes_code, {}

        slots_code, slots = self.memory_slots.get()
        if slots_code != "[PASS]":
            return slots_code, {}

        updated_slots = {
            existing_slot_id: {
                "positions": {
                    axis_name: position
                    for axis_name, position in record["positions"].items()
                }
            }
            for existing_slot_id, record in slots.items()
        }
        updated_slots[slot_id] = {
            "positions": {
                axis_name: record["actual"]
                for axis_name, record in axes_value.items()
            }
        }

        code = self.memory_slots.internal_set(updated_slots)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def recall_memory_slot(self, slot_id: str) -> tuple[str, dict]:
        """
        Recall an existing memory slot. The seat must be powered on, idle, unobstructed, and not already recalling another slot. The first differing saved axis is selected in fore_aft, height, recline, lumbar order and starts through the inherited adjustment mechanism. Each later eligible minute tick completes the current axis and starts the next differing saved axis. If all saved positions already equal their actual positions, the call completes immediately without starting motion. Missing slots and failed preconditions leave all state unchanged.

        Args:
        - slot_id:

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: Seat adjustment module must be powered on.
        - MEMORY_SLOT_NOT_FOUND: The requested memory slot does not exist.
        - ADJUSTMENT_ACTIVE: Stop the current or interrupted adjustment before recalling a memory slot.
        - OBSTRUCTION_DETECTED: Memory recall cannot start while an obstruction is detected.
        - RECALL_ACTIVE: Cancel or stop the current memory recall before starting another.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        valid_characters = "abcdefghijklmnopqrstuvwxyz0123456789_-"
        valid_initial_characters = "abcdefghijklmnopqrstuvwxyz0123456789"
        if (
            type(slot_id) is not str
            or len(slot_id) < 1
            or len(slot_id) > 32
            or slot_id == "none"
            or slot_id[0] not in valid_initial_characters
            or any(character not in valid_characters for character in slot_id)
        ):
            return "[INVALID_INPUT_ERROR]", {}

        slots_code, slots = self.memory_slots.get()
        if slots_code != "[PASS]":
            return slots_code, {}
        if slot_id not in slots:
            return "[MEMORY_SLOT_NOT_FOUND]", {}

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

        active_slot_code, active_slot = self.active_memory_slot.get()
        if active_slot_code != "[PASS]":
            return active_slot_code, {}
        if active_slot != "none":
            return "[RECALL_ACTIVE]", {}

        axes_code, axes_value = self.axes.get()
        if axes_code != "[PASS]":
            return axes_code, {}

        saved_positions = slots[slot_id]["positions"]
        next_axis = "none"
        next_target = 0
        for axis_name in ("fore_aft", "height", "recline", "lumbar"):
            if (
                axis_name in axes_value
                and axis_name in saved_positions
                and axes_value[axis_name]["actual"] != saved_positions[axis_name]
            ):
                next_axis = axis_name
                next_target = saved_positions[axis_name]
                break

        if next_axis == "none":
            code = self.motion_status.internal_set("idle")
            if code != "[PASS]":
                return code, {}
            code = self.active_axis.internal_set("none")
            if code != "[PASS]":
                return code, {}
            code = self.progress_percent.internal_set(100)
            if code != "[PASS]":
                return code, {}
            code = self.active_memory_slot.internal_set("none")
            if code != "[PASS]":
                return code, {}
            return "[PASS]", {}

        selected_record = axes_value[next_axis]
        if (
            next_target < selected_record["minimum"]
            or next_target > selected_record["maximum"]
        ):
            return "[TARGET_OUT_OF_RANGE]", {}

        updated_axes = {
            axis_name: {
                field_name: field_value
                for field_name, field_value in record.items()
            }
            for axis_name, record in axes_value.items()
        }
        updated_axes[next_axis]["start"] = selected_record["actual"]
        updated_axes[next_axis]["requested_position"] = next_target

        code = self.axes.internal_set(updated_axes)
        if code != "[PASS]":
            return code, {}
        code = self.motion_status.internal_set("moving")
        if code != "[PASS]":
            return code, {}
        code = self.active_axis.internal_set(next_axis)
        if code != "[PASS]":
            return code, {}
        code = self.progress_percent.internal_set(0)
        if code != "[PASS]":
            return code, {}
        code = self.active_memory_slot.internal_set(slot_id)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def cancel_recall(self) -> tuple[str, dict]:
        """
        Cancel an active memory recall. If an axis is currently moving, paused, or obstructed, its target is replaced with its current actual position while its limits, unit, actual position, and start position are preserved. Motion_status becomes idle, active_axis becomes none, progress_percent becomes 100, and active_memory_slot becomes none. Obstruction feedback is preserved. Calling with no active recall succeeds without affecting an unrelated manual adjustment. Requires power on.

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

        active_slot_code, active_slot = self.active_memory_slot.get()
        if active_slot_code != "[PASS]":
            return active_slot_code, {}
        if active_slot == "none":
            return "[PASS]", {}

        active_axis_code, active_axis = self.active_axis.get()
        if active_axis_code != "[PASS]":
            return active_axis_code, {}

        updated_axes = None
        if active_axis != "none":
            axes_code, axes_value = self.axes.get()
            if axes_code != "[PASS]":
                return axes_code, {}
            if active_axis in axes_value:
                updated_axes = {
                    axis_name: {
                        field_name: field_value
                        for field_name, field_value in record.items()
                    }
                    for axis_name, record in axes_value.items()
                }
                updated_axes[active_axis]["requested_position"] = updated_axes[active_axis]["actual"]

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
        code = self.active_memory_slot.internal_set("none")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def stop_adjustment(self) -> tuple[str, dict]:
        """
        Stop a moving, paused, or obstructed adjustment and cancel any active memory recall. When an active axis exists, only that axis record's target is replaced with its current actual position; its actual, start, limits, and unit remain unchanged. Motion_status becomes idle, active_axis becomes none, progress_percent becomes 100, and active_memory_slot becomes none. Calling while already idle performs the same state cleanup idempotently. Obstruction feedback is preserved and must be cleared separately. Requires power on.

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
        code = self.active_memory_slot.internal_set("none")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        On an eligible minute tick, complete the moving active axis by setting its actual position to its target. During memory recall, then compare saved positions with current actual positions in fore_aft, height, recline, lumbar order. If another saved installed axis differs, initialize that axis through the existing adjustment state with progress at 0; otherwise finish recall, set motion_status to idle, set progress_percent to 100, and clear active_axis and active_memory_slot. For movement not owned by a recall, retain the inherited single-axis completion behavior. If obstruction is detected while moving, preserve all positions and targets, set motion_status to obstructed, and retain the active memory slot for cancellation. Unpowered, idle, paused, and obstructed states do not advance.

    Effect properties:
    - power: Determines whether pending adjustment or recall movement may advance.
    - axes: Provides actual, target, and start positions for completing and sequencing axis adjustments.
    - motion_status: Determines whether an axis is moving and records completion, continued recall, or obstruction.
    - active_axis: Selects the axis being adjusted and records the next axis selected during recall.
    - progress_percent: Records completion of the current axis or zero progress for the next recalled axis.
    - obstruction_state: Prevents movement completion and changes moving status to obstructed when detection is active.
    - memory_slots: Provides the saved axis positions for the active recall.
    - active_memory_slot: Identifies whether movement belongs to a recall and selects its saved position snapshot.
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

        active_axis_code, active_axis = self.active_axis.get()
        if active_axis_code != "[PASS]":
            return active_axis_code, []

        axes_code, axes_value = self.axes.get()
        if axes_code != "[PASS]":
            return axes_code, []
        if active_axis == "none" or active_axis not in axes_value:
            return "[PASS]", []

        active_slot_code, active_slot = self.active_memory_slot.get()
        if active_slot_code != "[PASS]":
            return active_slot_code, []

        updated_axes = {
            axis_name: {
                field_name: field_value
                for field_name, field_value in record.items()
            }
            for axis_name, record in axes_value.items()
        }
        updated_axes[active_axis]["actual"] = updated_axes[active_axis]["requested_position"]

        if active_slot == "none":
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

        slots_code, slots = self.memory_slots.get()
        if slots_code != "[PASS]":
            return slots_code, []
        if active_slot not in slots:
            return "[MEMORY_SLOT_NOT_FOUND]", []

        saved_positions = slots[active_slot]["positions"]
        next_axis = "none"
        next_target = 0
        for axis_name in ("fore_aft", "height", "recline", "lumbar"):
            if (
                axis_name in updated_axes
                and axis_name in saved_positions
                and updated_axes[axis_name]["actual"] != saved_positions[axis_name]
            ):
                next_axis = axis_name
                next_target = saved_positions[axis_name]
                break

        if next_axis != "none":
            selected_record = updated_axes[next_axis]
            if (
                next_target < selected_record["minimum"]
                or next_target > selected_record["maximum"]
            ):
                return "[TARGET_OUT_OF_RANGE]", []

            updated_axes[next_axis]["start"] = selected_record["actual"]
            updated_axes[next_axis]["requested_position"] = next_target

            code = self.axes.internal_set(updated_axes)
            if code != "[PASS]":
                return code, []
            code = self.progress_percent.internal_set(0)
            if code != "[PASS]":
                return code, []
            code = self.motion_status.internal_set("moving")
            if code != "[PASS]":
                return code, []
            code = self.active_axis.internal_set(next_axis)
            if code != "[PASS]":
                return code, []
            return "[PASS]", []

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
        code = self.active_memory_slot.internal_set("none")
        if code != "[PASS]":
            return code, []
        return "[PASS]", []