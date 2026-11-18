# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..AmbientLight import AmbientLight

class DynamicAmbientLight(AmbientLight):
    """
    DynamicAmbientLight
    Description: Dynamic ambient light. Adds selecting, starting, and stopping local dynamic lighting effects and querying the current effect state. Dynamic effects and static color mode are mutually exclusive.
    Version: 1.0.0
    Base: AmbientLight
    """

    def __init__(self, effect: str = None, effect_state: str = None, *, power: bool | None = None, _defer_power_init: bool = False, **base_kwargs) -> None:
        _power_init_value = power if power is not None else False
        # initialize base AmbientLight class
        super().__init__(power=_power_init_value, _defer_power_init=True, **base_kwargs)
        # define properties
        self.effect = StringProperty(
            name='effect',
            description='Selected local dynamic lighting effect. Selection persists when the effect is stopped or the light is powered off.',
            default='pulse',
            choices=['pulse', 'wave', 'rainbow']
        )
        self.effect_state = StringProperty(
            name='effect_state',
            description='Current dynamic effect state. Stopped means the light uses its inherited static color setting; running means the selected dynamic effect is active while powered.',
            default='stopped',
            mode=2,
            choices=['stopped', 'running']
        )

        # initialize properties
        if effect is not None: code = self.effect.internal_set(effect)
        if effect_state is not None: code = self.effect_state.internal_set(effect_state)
        self._power_managed_properties = (self.brightness, self.color, self.effect, self.effect_state,)
        self._power_initialized = False
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

        if not _defer_power_init:
            self.set_power(_power_init_value)

    def set_color(self, value: str) -> tuple[str, dict]:
        """
        Set the static color using the fixed 24-bit sRGB hexadecimal format #RRGGBB and stop any running dynamic effect. Requires the ambient light to be powered on. Invalid input or a failed power precondition leaves all state unchanged.

        Args:
        - value: Desired static 24-bit sRGB color in #RRGGBB format.

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The ambient light must be powered on.
        - INVALID_INPUT_ERROR: Color must use the 24-bit sRGB hexadecimal format #RRGGBB.
        """
        if (
            type(value) is not str
            or len(value) != 7
            or value[0] != "#"
            or any(character not in "0123456789ABCDEFabcdef" for character in value[1:])
        ):
            return "[INVALID_INPUT_ERROR]", {}

        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        color_code = self.color.set(value)
        if color_code != "[PASS]":
            return color_code, {}

        state_code = self.effect_state.internal_set("stopped")
        if state_code != "[PASS]":
            return state_code, {}

        return "[PASS]", {}

    def get_effect(self) -> tuple[str, dict]:
        """
        Return the selected dynamic lighting effect. Requires the ambient light to be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- effect: Selected dynamic effect: pulse, wave, or rainbow. (type=string)

        Error Codes:
        - POWER_OFF: The ambient light must be powered on.
        """
        code, value = self.effect.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"effect": value}

    def set_effect(self, value: str) -> tuple[str, dict]:
        """
        Select the pulse, wave, or rainbow dynamic lighting effect. Selection does not start a stopped effect; if an effect is already running, the newly selected effect becomes active immediately. Requires the ambient light to be powered on. Invalid input or a failed power precondition leaves state unchanged.

        Args:
        - value: Dynamic lighting effect to select. (choices=['pulse', 'wave', 'rainbow'])

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The ambient light must be powered on.
        - INVALID_INPUT_ERROR: Effect must be pulse, wave, or rainbow.
        """
        if type(value) is not str or value not in ("pulse", "wave", "rainbow"):
            return "[INVALID_INPUT_ERROR]", {}

        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        code = self.effect.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_effect_state(self) -> tuple[str, dict]:
        """
        Return whether the selected dynamic effect is stopped or running. Requires the ambient light to be powered on.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	- effect_state: Current dynamic effect state: stopped or running. (type=string)

        Error Codes:
        - POWER_OFF: The ambient light must be powered on.
        """
        code, value = self.effect_state.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"effect_state": value}

    def start_effect(self) -> tuple[str, dict]:
        """
        Start the selected dynamic lighting effect and leave static color mode. Requires the ambient light to be powered on and the effect state to be stopped. A failed precondition leaves state unchanged.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The ambient light must be powered on.
        - PRECONDITION_FAILED: The dynamic effect is already running.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        state_code, state = self.effect_state.get()
        if state_code != "[PASS]":
            return state_code, {}
        if state != "stopped":
            return "[PRECONDITION_FAILED]", {}

        code = self.effect_state.internal_set("running")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def stop_effect(self) -> tuple[str, dict]:
        """
        Stop the running dynamic lighting effect and return to the inherited static color mode. Requires the ambient light to be powered on and the effect state to be running. The selected effect is preserved for a later start. A failed precondition leaves state unchanged.

        Args:
        (no arguments required)

        Returns:
        - Return Code: The return code of this function, either "[PASS]" or one of Error Codes built-in or listed below (type=str)
        - Response Data: A dictionary containing response data (type=dict)
        	(no explicit response)

        Error Codes:
        - POWER_OFF: The ambient light must be powered on.
        - PRECONDITION_FAILED: No dynamic effect is running.
        """
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, {}
        if powered is not True:
            return "[POWER_OFF]", {}

        state_code, state = self.effect_state.get()
        if state_code != "[PASS]":
            return state_code, {}
        if state != "running":
            return "[PRECONDITION_FAILED]", {}

        code = self.effect_state.internal_set("stopped")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}