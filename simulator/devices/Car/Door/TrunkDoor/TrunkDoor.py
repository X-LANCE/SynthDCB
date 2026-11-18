# v20260920

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..Door import Door

class TrunkDoor(Door):
    """
    TrunkDoor
    Description: Trunk door that inherits Door locking, unlocking, and door-state queries. Represents the door connection between trunk and exterior; opening and closing affect exchange between the trunk Space and the outside.
    Version: 1.0.0
    Base: Door
    """

    def __init__(self, **base_kwargs) -> None:
        # initialize base Door class
        super().__init__(**base_kwargs)
        # define properties
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }

    pass