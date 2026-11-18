# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty


class Infotainment:
    """
    Infotainment
    Description: Vehicle multimedia system. Supports volume, mute, audio source selection, play, pause, and stop. Supports radio, MP3, and Bluetooth modes. Radio mode supports switching between FM and AM, tuning frequencies, and saving or recalling stations. MP3 mode supports repeat modes, previous/next track selection, and querying information such as the current artist, track title, and album. Bluetooth mode supports querying connectable and connected Bluetooth devices, saving devices, and connecting or disconnecting them. Whether playback is active affects the cabin sound level.
    Version: 1.0.0
    Base: -
    """

    def __init__(self, power: bool = None, volume: int = None, muted: bool = None, source: str = None, playback_state: str = None, radio_band: str = None, fm_frequency: float = None, am_frequency: int = None, radio_presets: dict = None, repeat_mode: str = None, mp3_tracks: dict = None, current_track_id: str = None, bluetooth_devices: dict = None, *, _defer_power_init: bool = False) -> None:
        _power_init_value = power if power is not None else False
        # define properties
        self.power = BoolProperty(
            name='power',
            description='Whether the infotainment system is powered on.',
            default=False
        )
        self.volume = IntProperty(
            name='volume',
            description='Configured media audio contribution level.',
            default=40,
            unit='dBA',
            minimum=0,
            maximum=120,
            step=1,
            step_origin=0
        )
        self.muted = BoolProperty(
            name='muted',
            description='Whether media audio output is muted.',
            default=False
        )
        self.source = StringProperty(
            name='source',
            description='Selected multimedia source.',
            default='radio',
            choices=['radio', 'mp3', 'bluetooth']
        )
        self.playback_state = StringProperty(
            name='playback_state',
            description='Current playback state.',
            default='stopped',
            mode=2,
            choices=['playing', 'paused', 'stopped']
        )
        self.radio_band = StringProperty(
            name='radio_band',
            description='Selected radio band.',
            default='fm',
            choices=['fm', 'am']
        )
        self.fm_frequency = FloatProperty(
            name='fm_frequency',
            description='Currently tuned FM frequency.',
            default=99.5,
            unit='MHz',
            minimum=87.5,
            maximum=108.0,
            step=0.1,
            step_origin=87.5,
            precision=1
        )
        self.am_frequency = IntProperty(
            name='am_frequency',
            description='Currently tuned AM frequency.',
            default=1000,
            unit='kHz',
            minimum=520,
            maximum=1710,
            step=10,
            step_origin=520
        )
        self.radio_presets = DictProperty(
            name='radio_presets',
            description='Saved radio stations keyed by generated preset ID.',
            default={},
            mode=2,
            schema={'type': 'object', 'additionalProperties': {'type': 'object', 'properties': {'band': {'type': 'string', 'enum': ['fm', 'am']}, 'frequency': {'type': 'number'}}, 'required': ['band', 'frequency'], 'additionalProperties': False}}
        )
        self.repeat_mode = StringProperty(
            name='repeat_mode',
            description='MP3 repeat preference.',
            default='off',
            choices=['off', 'one', 'all']
        )
        self.mp3_tracks = DictProperty(
            name='mp3_tracks',
            description='Deterministic local MP3 library keyed by track ID.',
            default={'track_1': {'artist': 'Northbound', 'title': 'Morning Drive', 'album': 'Open Roads'}, 'track_2': {'artist': 'Signal Coast', 'title': 'City Lights', 'album': 'Night Routes'}, 'track_3': {'artist': 'Quiet Engine', 'title': 'Homeward', 'album': 'Open Roads'}},
            mode=2,
            schema={'type': 'object', 'additionalProperties': {'type': 'object', 'properties': {'artist': {'type': 'string'}, 'title': {'type': 'string'}, 'album': {'type': 'string'}}, 'required': ['artist', 'title', 'album'], 'additionalProperties': False}}
        )
        self.current_track_id = StringProperty(
            name='current_track_id',
            description='ID of the currently selected MP3 track.',
            default='track_1',
            mode=2,
            choices=['track_1', 'track_2', 'track_3']
        )
        self.bluetooth_devices = DictProperty(
            name='bluetooth_devices',
            description='Known Bluetooth devices keyed by device ID, including connectable, saved, and connected state.',
            default={'phone_1': {'name': 'Driver Phone', 'connectable': True, 'saved': True, 'connected': False}, 'phone_2': {'name': 'Passenger Phone', 'connectable': True, 'saved': False, 'connected': False}, 'player_1': {'name': 'Portable Player', 'connectable': True, 'saved': False, 'connected': False}},
            mode=2,
            schema={'type': 'object', 'additionalProperties': {'type': 'object', 'properties': {'name': {'type': 'string'}, 'connectable': {'type': 'boolean'}, 'saved': {'type': 'boolean'}, 'connected': {'type': 'boolean'}}, 'required': ['name', 'connectable', 'saved', 'connected'], 'additionalProperties': False}}
        )
        code = self.power.internal_set(_power_init_value)

        # initialize properties
        if volume is not None: code = self.volume.internal_set(volume)
        if muted is not None: code = self.muted.internal_set(muted)
        if source is not None: code = self.source.internal_set(source)
        if playback_state is not None: code = self.playback_state.internal_set(playback_state)
        if radio_band is not None: code = self.radio_band.internal_set(radio_band)
        if fm_frequency is not None: code = self.fm_frequency.internal_set(fm_frequency)
        if am_frequency is not None: code = self.am_frequency.internal_set(am_frequency)
        if radio_presets is not None: code = self.radio_presets.internal_set(radio_presets)
        if repeat_mode is not None: code = self.repeat_mode.internal_set(repeat_mode)
        if mp3_tracks is not None: code = self.mp3_tracks.internal_set(mp3_tracks)
        if current_track_id is not None: code = self.current_track_id.internal_set(current_track_id)
        if bluetooth_devices is not None: code = self.bluetooth_devices.internal_set(bluetooth_devices)
        self._power_managed_properties = (self.volume, self.muted, self.source, self.playback_state, self.radio_band, self.fm_frequency, self.am_frequency, self.radio_presets, self.repeat_mode, self.mp3_tracks, self.current_track_id, self.bluetooth_devices,)
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

    def get_volume(self) -> tuple[str, dict]:
        """
        Return the configured media audio level. The system must be powered on.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, value = self.volume.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"volume": value}

    def set_volume(self, volume: int) -> tuple[str, dict]:
        """
        Set the media audio level to an integer from 0 through 120. The system must be powered on. Invalid input or a failed precondition leaves state unchanged.
        """
        if type(volume) is not int or volume < 0 or volume > 120:
            return "[INVALID_INPUT_ERROR]", {}
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code = self.volume.set(volume)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_muted(self) -> tuple[str, dict]:
        """
        Return whether multimedia audio is muted. The system must be powered on.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, value = self.muted.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"muted": value}

    def set_muted(self, muted: bool) -> tuple[str, dict]:
        """
        Set the multimedia mute state without changing the saved volume. The system must be powered on.
        """
        if type(muted) is not bool:
            return "[INVALID_INPUT_ERROR]", {}
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code = self.muted.set(muted)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_source(self) -> tuple[str, dict]:
        """
        Return the selected multimedia source. The system must be powered on.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, value = self.source.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"source": value}

    def set_source(self, source: str) -> tuple[str, dict]:
        """
        Select radio, MP3, or Bluetooth as the multimedia source. The system must be powered on. Invalid values leave state unchanged.
        """
        if type(source) is not str or source not in ("radio", "mp3", "bluetooth"):
            return "[INVALID_INPUT_ERROR]", {}
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code = self.source.set(source)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_playback_state(self) -> tuple[str, dict]:
        """
        Return the current multimedia playback state. The system must be powered on.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, value = self.playback_state.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"playback_state": value}

    def play(self) -> tuple[str, dict]:
        """
        Start or resume playback while powered on. Playback must currently be paused or stopped; otherwise the action is rejected without mutation.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, state = self.playback_state.get()
        if code != "[PASS]":
            return code, {}
        if state not in ("paused", "stopped"):
            return "[PRECONDITION_FAILED]", {}
        code = self.playback_state.internal_set("playing")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def pause(self) -> tuple[str, dict]:
        """
        Pause active playback while powered on. The action is rejected without mutation unless playback is currently playing.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, state = self.playback_state.get()
        if code != "[PASS]":
            return code, {}
        if state != "playing":
            return "[PRECONDITION_FAILED]", {}
        code = self.playback_state.internal_set("paused")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def stop(self) -> tuple[str, dict]:
        """
        Stop playback while powered on, preserving source, volume, mute, tuning, and device settings.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code = self.playback_state.internal_set("stopped")
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_radio_band(self) -> tuple[str, dict]:
        """
        Return the selected radio band. The system must be powered on with radio selected.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, source = self.source.get()
        if code != "[PASS]":
            return code, {}
        if source != "radio":
            return "[PRECONDITION_FAILED]", {}
        code, value = self.radio_band.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"radio_band": value}

    def set_radio_band(self, band: str) -> tuple[str, dict]:
        """
        Select the FM or AM radio band. The system must be powered on with radio selected. Invalid input leaves state unchanged.
        """
        if type(band) is not str or band not in ("fm", "am"):
            return "[INVALID_INPUT_ERROR]", {}
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, source = self.source.get()
        if code != "[PASS]":
            return code, {}
        if source != "radio":
            return "[PRECONDITION_FAILED]", {}
        code = self.radio_band.set(band)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_fm_frequency(self) -> tuple[str, dict]:
        """
        Return the current FM frequency. The system must be powered on with radio and the FM band selected.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, source = self.source.get()
        if code != "[PASS]":
            return code, {}
        code, band = self.radio_band.get()
        if code != "[PASS]":
            return code, {}
        if source != "radio" or band != "fm":
            return "[PRECONDITION_FAILED]", {}
        code, value = self.fm_frequency.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"fm_frequency": value}

    def set_fm_frequency(self, frequency: float) -> tuple[str, dict]:
        """
        Tune FM from 87.5 through 108.0 MHz in 0.1 MHz increments. The system must be powered on with radio and FM selected. Failure leaves state unchanged.
        """
        if type(frequency) not in (int, float):
            return "[INVALID_INPUT_ERROR]", {}
        normalized = round(float(frequency), 1)
        if frequency < 87.5 or frequency > 108.0 or abs(float(frequency) - normalized) > 0.000000001:
            return "[INVALID_INPUT_ERROR]", {}
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, source = self.source.get()
        if code != "[PASS]":
            return code, {}
        code, band = self.radio_band.get()
        if code != "[PASS]":
            return code, {}
        if source != "radio" or band != "fm":
            return "[PRECONDITION_FAILED]", {}
        code = self.fm_frequency.set(normalized)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_am_frequency(self) -> tuple[str, dict]:
        """
        Return the current AM frequency. The system must be powered on with radio and the AM band selected.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, source = self.source.get()
        if code != "[PASS]":
            return code, {}
        code, band = self.radio_band.get()
        if code != "[PASS]":
            return code, {}
        if source != "radio" or band != "am":
            return "[PRECONDITION_FAILED]", {}
        code, value = self.am_frequency.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"am_frequency": value}

    def set_am_frequency(self, frequency: int) -> tuple[str, dict]:
        """
        Tune AM from 520 through 1710 kHz in 10 kHz increments. The system must be powered on with radio and AM selected. Failure leaves state unchanged.
        """
        if type(frequency) is not int or frequency < 520 or frequency > 1710 or (frequency - 520) % 10 != 0:
            return "[INVALID_INPUT_ERROR]", {}
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, source = self.source.get()
        if code != "[PASS]":
            return code, {}
        code, band = self.radio_band.get()
        if code != "[PASS]":
            return code, {}
        if source != "radio" or band != "am":
            return "[PRECONDITION_FAILED]", {}
        code = self.am_frequency.set(frequency)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def save_fm_station(self, frequency: float) -> tuple[str, dict]:
        """
        Save an FM frequency as a new preset and return its generated ID. The system must be powered on with radio selected. Existing presets are inspected to generate a deterministic noncolliding ID. Failure preserves all existing presets.
        """
        if type(frequency) not in (int, float):
            return "[INVALID_INPUT_ERROR]", {}
        normalized = round(float(frequency), 1)
        if frequency < 87.5 or frequency > 108.0 or abs(float(frequency) - normalized) > 0.000000001:
            return "[INVALID_INPUT_ERROR]", {}
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, source = self.source.get()
        if code != "[PASS]":
            return code, {}
        if source != "radio":
            return "[PRECONDITION_FAILED]", {}
        code, presets = self.radio_presets.get()
        if code != "[PASS]":
            return code, {}
        index = 1
        preset_id = "preset_1"
        while preset_id in presets:
            index += 1
            preset_id = "preset_" + str(index)
        updated = {
            key: {
                "band": record["band"],
                "frequency": record["frequency"]
            }
            for key, record in presets.items()
        }
        updated[preset_id] = {"band": "fm", "frequency": normalized}
        code = self.radio_presets.internal_set(updated)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"preset_id": preset_id}

    def save_am_station(self, frequency: int) -> tuple[str, dict]:
        """
        Save an AM frequency as a new preset and return its generated ID. The system must be powered on with radio selected. Existing presets are inspected to generate a deterministic noncolliding ID. Failure preserves all existing presets.
        """
        if type(frequency) is not int or frequency < 520 or frequency > 1710 or (frequency - 520) % 10 != 0:
            return "[INVALID_INPUT_ERROR]", {}
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, source = self.source.get()
        if code != "[PASS]":
            return code, {}
        if source != "radio":
            return "[PRECONDITION_FAILED]", {}
        code, presets = self.radio_presets.get()
        if code != "[PASS]":
            return code, {}
        index = 1
        preset_id = "preset_1"
        while preset_id in presets:
            index += 1
            preset_id = "preset_" + str(index)
        updated = {
            key: {
                "band": record["band"],
                "frequency": record["frequency"]
            }
            for key, record in presets.items()
        }
        updated[preset_id] = {"band": "am", "frequency": frequency}
        code = self.radio_presets.internal_set(updated)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"preset_id": preset_id}

    def get_radio_preset(self, preset_id: str) -> tuple[str, dict]:
        """
        Return one saved radio preset by ID. The system must be powered on with radio selected, and the preset must exist.
        """
        if type(preset_id) is not str or preset_id == "":
            return "[INVALID_INPUT_ERROR]", {}
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, source = self.source.get()
        if code != "[PASS]":
            return code, {}
        if source != "radio":
            return "[PRECONDITION_FAILED]", {}
        code, presets = self.radio_presets.get()
        if code != "[PASS]":
            return code, {}
        if preset_id not in presets:
            return "[NOT_FOUND]", {}
        record = presets[preset_id]
        return "[PASS]", {
            "preset": {
                "band": record["band"],
                "frequency": record["frequency"]
            }
        }

    def recall_radio_station(self, preset_id: str) -> tuple[str, dict]:
        """
        Recall an existing preset by selecting its stored band and tuning the matching FM or AM frequency. The system must be powered on with radio selected. Failure leaves tuning unchanged.
        """
        if type(preset_id) is not str or preset_id == "":
            return "[INVALID_INPUT_ERROR]", {}
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, source = self.source.get()
        if code != "[PASS]":
            return code, {}
        if source != "radio":
            return "[PRECONDITION_FAILED]", {}
        code, presets = self.radio_presets.get()
        if code != "[PASS]":
            return code, {}
        if preset_id not in presets:
            return "[NOT_FOUND]", {}

        record = presets[preset_id]
        band = record["band"]
        frequency = record["frequency"]

        if band == "fm":
            if type(frequency) not in (int, float):
                return "[INVALID_INPUT_ERROR]", {}
            normalized = round(float(frequency), 1)
            if frequency < 87.5 or frequency > 108.0 or abs(float(frequency) - normalized) > 0.000000001:
                return "[INVALID_INPUT_ERROR]", {}
        elif band == "am":
            if type(frequency) is not int or frequency < 520 or frequency > 1710 or (frequency - 520) % 10 != 0:
                return "[INVALID_INPUT_ERROR]", {}
        else:
            return "[INVALID_INPUT_ERROR]", {}

        code = self.radio_band.set(band)
        if code != "[PASS]":
            return code, {}
        if band == "fm":
            code = self.fm_frequency.set(normalized)
        else:
            code = self.am_frequency.set(frequency)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_repeat_mode(self) -> tuple[str, dict]:
        """
        Return the MP3 repeat preference. The system must be powered on with MP3 selected.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, source = self.source.get()
        if code != "[PASS]":
            return code, {}
        if source != "mp3":
            return "[PRECONDITION_FAILED]", {}
        code, value = self.repeat_mode.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"repeat_mode": value}

    def set_repeat_mode(self, mode: str) -> tuple[str, dict]:
        """
        Set the MP3 repeat preference to off, one, or all. The system must be powered on with MP3 selected. Invalid input leaves state unchanged.
        """
        if type(mode) is not str or mode not in ("off", "one", "all"):
            return "[INVALID_INPUT_ERROR]", {}
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, source = self.source.get()
        if code != "[PASS]":
            return code, {}
        if source != "mp3":
            return "[PRECONDITION_FAILED]", {}
        code = self.repeat_mode.set(mode)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def get_current_track_id(self) -> tuple[str, dict]:
        """
        Return the selected MP3 track ID. The system must be powered on with MP3 selected.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, source = self.source.get()
        if code != "[PASS]":
            return code, {}
        if source != "mp3":
            return "[PRECONDITION_FAILED]", {}
        code, value = self.current_track_id.get()
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {"current_track_id": value}

    def get_current_track_info(self) -> tuple[str, dict]:
        """
        Return the artist, title, and album of the selected MP3 track. The system must be powered on with MP3 selected. This query does not change state.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, source = self.source.get()
        if code != "[PASS]":
            return code, {}
        if source != "mp3":
            return "[PRECONDITION_FAILED]", {}
        code, current = self.current_track_id.get()
        if code != "[PASS]":
            return code, {}
        code, tracks = self.mp3_tracks.get()
        if code != "[PASS]":
            return code, {}
        if current not in tracks:
            return "[NOT_FOUND]", {}
        record = tracks[current]
        return "[PASS]", {
            "artist": record["artist"],
            "title": record["title"],
            "album": record["album"]
        }

    def previous_track(self) -> tuple[str, dict]:
        """
        Select the previous MP3 track in deterministic library order, wrapping from the first track to the last. The system must be powered on with MP3 selected.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, source = self.source.get()
        if code != "[PASS]":
            return code, {}
        if source != "mp3":
            return "[PRECONDITION_FAILED]", {}
        code, tracks = self.mp3_tracks.get()
        if code != "[PASS]":
            return code, {}
        code, current = self.current_track_id.get()
        if code != "[PASS]":
            return code, {}
        track_ids = list(tracks.keys())
        if not track_ids or current not in tracks:
            return "[NOT_FOUND]", {}
        index = track_ids.index(current)
        selected = track_ids[(index - 1) % len(track_ids)]
        code = self.current_track_id.internal_set(selected)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def next_track(self) -> tuple[str, dict]:
        """
        Select the next MP3 track in deterministic library order, wrapping from the last track to the first. The system must be powered on with MP3 selected.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, source = self.source.get()
        if code != "[PASS]":
            return code, {}
        if source != "mp3":
            return "[PRECONDITION_FAILED]", {}
        code, tracks = self.mp3_tracks.get()
        if code != "[PASS]":
            return code, {}
        code, current = self.current_track_id.get()
        if code != "[PASS]":
            return code, {}
        track_ids = list(tracks.keys())
        if not track_ids or current not in tracks:
            return "[NOT_FOUND]", {}
        index = track_ids.index(current)
        selected = track_ids[(index + 1) % len(track_ids)]
        code = self.current_track_id.internal_set(selected)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def list_connectable_bluetooth_devices(self) -> tuple[str, dict]:
        """
        Return known Bluetooth records whose connectable field is true. The system must be powered on with Bluetooth selected.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, source = self.source.get()
        if code != "[PASS]":
            return code, {}
        if source != "bluetooth":
            return "[PRECONDITION_FAILED]", {}
        code, devices = self.bluetooth_devices.get()
        if code != "[PASS]":
            return code, {}
        result = {
            key: {
                "name": record["name"],
                "connectable": record["connectable"],
                "saved": record["saved"],
                "connected": record["connected"]
            }
            for key, record in devices.items()
            if record["connectable"]
        }
        return "[PASS]", {"devices": result}

    def list_connected_bluetooth_devices(self) -> tuple[str, dict]:
        """
        Return known Bluetooth records whose connected field is true. The system must be powered on with Bluetooth selected.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, source = self.source.get()
        if code != "[PASS]":
            return code, {}
        if source != "bluetooth":
            return "[PRECONDITION_FAILED]", {}
        code, devices = self.bluetooth_devices.get()
        if code != "[PASS]":
            return code, {}
        result = {
            key: {
                "name": record["name"],
                "connectable": record["connectable"],
                "saved": record["saved"],
                "connected": record["connected"]
            }
            for key, record in devices.items()
            if record["connected"]
        }
        return "[PASS]", {"devices": result}

    def list_saved_bluetooth_devices(self) -> tuple[str, dict]:
        """
        Return known Bluetooth records whose saved field is true. The system must be powered on with Bluetooth selected.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, source = self.source.get()
        if code != "[PASS]":
            return code, {}
        if source != "bluetooth":
            return "[PRECONDITION_FAILED]", {}
        code, devices = self.bluetooth_devices.get()
        if code != "[PASS]":
            return code, {}
        result = {
            key: {
                "name": record["name"],
                "connectable": record["connectable"],
                "saved": record["saved"],
                "connected": record["connected"]
            }
            for key, record in devices.items()
            if record["saved"]
        }
        return "[PASS]", {"devices": result}

    def save_bluetooth_device(self, device_id: str) -> tuple[str, dict]:
        """
        Mark an existing known Bluetooth device as saved. The system must be powered on with Bluetooth selected, and the device ID must exist. Failure leaves every record unchanged.
        """
        if type(device_id) is not str or device_id == "":
            return "[INVALID_INPUT_ERROR]", {}
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, source = self.source.get()
        if code != "[PASS]":
            return code, {}
        if source != "bluetooth":
            return "[PRECONDITION_FAILED]", {}
        code, devices = self.bluetooth_devices.get()
        if code != "[PASS]":
            return code, {}
        if device_id not in devices:
            return "[NOT_FOUND]", {}
        updated = {
            key: {
                "name": record["name"],
                "connectable": record["connectable"],
                "saved": record["saved"],
                "connected": record["connected"]
            }
            for key, record in devices.items()
        }
        updated[device_id]["saved"] = True
        code = self.bluetooth_devices.internal_set(updated)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def connect_bluetooth_device(self, device_id: str) -> tuple[str, dict]:
        """
        Connect an existing known Bluetooth device. The system must be powered on with Bluetooth selected, the device must exist, and its connectable field must be true. Invalid requests leave every device record unchanged.
        """
        if type(device_id) is not str or device_id == "":
            return "[INVALID_INPUT_ERROR]", {}
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, source = self.source.get()
        if code != "[PASS]":
            return code, {}
        if source != "bluetooth":
            return "[PRECONDITION_FAILED]", {}
        code, devices = self.bluetooth_devices.get()
        if code != "[PASS]":
            return code, {}
        if device_id not in devices:
            return "[NOT_FOUND]", {}
        if not devices[device_id]["connectable"]:
            return "[DEVICE_UNAVAILABLE]", {}
        updated = {
            key: {
                "name": record["name"],
                "connectable": record["connectable"],
                "saved": record["saved"],
                "connected": record["connected"]
            }
            for key, record in devices.items()
        }
        updated[device_id]["connected"] = True
        code = self.bluetooth_devices.internal_set(updated)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def disconnect_bluetooth_device(self, device_id: str) -> tuple[str, dict]:
        """
        Disconnect an existing known Bluetooth device by setting only that record's connected field to false. The system must be powered on with Bluetooth selected, and the device must exist.
        """
        if type(device_id) is not str or device_id == "":
            return "[INVALID_INPUT_ERROR]", {}
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, {}
        if not powered:
            return "[PRECONDITION_FAILED]", {}
        code, source = self.source.get()
        if code != "[PASS]":
            return code, {}
        if source != "bluetooth":
            return "[PRECONDITION_FAILED]", {}
        code, devices = self.bluetooth_devices.get()
        if code != "[PASS]":
            return code, {}
        if device_id not in devices:
            return "[NOT_FOUND]", {}
        updated = {
            key: {
                "name": record["name"],
                "connectable": record["connectable"],
                "saved": record["saved"],
                "connected": record["connected"]
            }
            for key, record in devices.items()
        }
        updated[device_id]["connected"] = False
        code = self.bluetooth_devices.internal_set(updated)
        if code != "[PASS]":
            return code, {}
        return "[PASS]", {}

    def _on_tick(self, context: dict) -> tuple[str, list[dict]]:
        """
        While power is on, playback is playing, and audio is not muted, contribute the configured volume to cabin audio_level. While power is off, playback is paused or stopped, or audio is muted, contribute zero.

    Effect properties:
    - power: Determines whether the infotainment system may produce an audio contribution.
    - volume: Audio level contributed during powered, active, unmuted playback.
    - muted: Determines whether the audio contribution is cleared.
    - playback_state: Determines whether playback is active.
        """
        code, powered = self.power.get()
        if code != "[PASS]":
            return code, []

        contribution = 0
        if powered:
            code, volume = self.volume.get()
            if code != "[PASS]":
                return code, []
            code, muted = self.muted.get()
            if code != "[PASS]":
                return code, []
            code, playback_state = self.playback_state.get()
            if code != "[PASS]":
                return code, []
            if playback_state == "playing" and not muted:
                contribution = volume

        return "[PASS]", [{
            "trigger": "tick",
            "source": context["object_id"],
            "target": context["space_id"],
            "function": "set_contribution",
            "parameters": {
                "property": "audio_level",
                "value": contribution,
                "unit": "dBA"
            }
        }]