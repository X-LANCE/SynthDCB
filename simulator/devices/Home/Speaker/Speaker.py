# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty


class Speaker:
    """
    Speaker
    Description: Speaker. Users can query and set the playback state, volume, playback content, and playback mode, and can perform play, pause, previous-track, and next-track actions.
    Version: 1.0.0
    Base: -
    """

    def __init__(
        self,
        power: bool = None,
        playback_state: str = None,
        volume: int = None,
        content: str = None,
        playback_mode: str = None,
        *,
        _defer_power_init: bool = False,
    ) -> None:
        _power_init_value = power if power is not None else False
        self.power = BoolProperty(
            name="power",
            description="Whether the speaker is powered.",
            default=False,
        )
        self.playback_state = StringProperty(
            name="playback_state",
            description="The current playback state.",
            default="stopped",
            choices=["playing", "paused", "stopped"],
        )
        self.volume = IntProperty(
            name="volume",
            description="Speaker volume level as a percentage.",
            default=50,
            unit="%",
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0,
        )
        self.content = StringProperty(
            name="content",
            description="The currently selected playback content.",
            default="",
            max_length=500,
        )
        self.playback_mode = StringProperty(
            name="playback_mode",
            description="The playback mode used for the selected content.",
            default="normal",
            choices=["normal", "repeat_all", "repeat_one", "shuffle"],
        )
        code = self.power.internal_set(_power_init_value)

        if playback_state is not None:
            code = self.playback_state.internal_set(playback_state)
        if volume is not None:
            code = self.volume.internal_set(volume)
        if content is not None:
            code = self.content.internal_set(content)
        if playback_mode is not None:
            code = self.playback_mode.internal_set(playback_mode)

        self._power_managed_properties = (
            self.playback_state,
            self.volume,
            self.content,
            self.playback_mode,
        )
        self._power_initialized = False
        self._disabled = {
            "properties": [],
            "functions": [],
            "events": [],
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

    def _powered(self) -> tuple[str, bool]:
        code, value = self.power.get()
        if code != "[PASS]":
            return code, False
        if value is not True:
            return "[ERROR] POWER_OFF", False
        return "[PASS]", True

    def get_playback_state(self) -> tuple[str, dict]:
        code, powered = self._powered()
        if code != "[PASS]":
            return code, {}
        code, value = self.playback_state.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"playback_state": value}

    def set_playback_state(self, value: str) -> tuple[str, dict]:
        code, powered = self._powered()
        if code != "[PASS]":
            return code, {}
        code = self.playback_state.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_volume(self) -> tuple[str, dict]:
        code, powered = self._powered()
        if code != "[PASS]":
            return code, {}
        code, value = self.volume.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"volume": value}

    def set_volume(self, value: int) -> tuple[str, dict]:
        code, powered = self._powered()
        if code != "[PASS]":
            return code, {}
        code = self.volume.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_content(self) -> tuple[str, dict]:
        code, powered = self._powered()
        if code != "[PASS]":
            return code, {}
        code, value = self.content.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"content": value}

    def set_content(self, value: str) -> tuple[str, dict]:
        code, powered = self._powered()
        if code != "[PASS]":
            return code, {}
        code = self.content.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_playback_mode(self) -> tuple[str, dict]:
        code, powered = self._powered()
        if code != "[PASS]":
            return code, {}
        code, value = self.playback_mode.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"playback_mode": value}

    def set_playback_mode(self, value: str) -> tuple[str, dict]:
        code, powered = self._powered()
        if code != "[PASS]":
            return code, {}
        code = self.playback_mode.set(value)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def play(self) -> tuple[str, dict]:
        code, powered = self._powered()
        if code != "[PASS]":
            return code, {}
        content_code, content = self.content.get()
        if content_code != "[PASS]":
            return content_code, {}
        if content == "":
            return "[ERROR] NO_CONTENT", {}
        code = self.playback_state.set("playing")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def pause(self) -> tuple[str, dict]:
        code, powered = self._powered()
        if code != "[PASS]":
            return code, {}
        code = self.playback_state.set("paused")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def previous_track(self) -> tuple[str, dict]:
        code, powered = self._powered()
        if code != "[PASS]":
            return code, {}
        code = self.playback_state.set("playing")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def next_track(self) -> tuple[str, dict]:
        code, powered = self._powered()
        if code != "[PASS]":
            return code, {}
        code = self.playback_state.set("playing")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        power_code, powered = self.power.get()
        if power_code != "[PASS]":
            return power_code, []

        if powered is not True:
            noise = 0
        else:
            state_code, playback_state = self.playback_state.get()
            if state_code != "[PASS]":
                return state_code, []

            volume_code, volume = self.volume.get()
            if volume_code != "[PASS]":
                return volume_code, []

            noise = volume if playback_state == "playing" else 0

        effect = {
            "trigger": "after_action",
            "source": context["object_id"],
            "target": context["space_id"],
            "function": "set_contribution",
            "parameters": {
                "property": "noise",
                "value": noise,
                "unit": "dBA",
            },
        }
        return "[PASS]", [effect]