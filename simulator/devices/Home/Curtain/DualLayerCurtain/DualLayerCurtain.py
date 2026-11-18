# v20260913

from __future__ import annotations
from src.object_model import BoolProperty, DictProperty, FloatProperty, IntProperty, StringProperty
from ..Curtain import Curtain


class DualLayerCurtain(Curtain):
    """
    DualLayerCurtain
    Description: A dual-layer curtain variant. It provides separate open or closed states and opening percentages for the sheer and fabric layers, which can be controlled independently; the overall light-blocking effect is determined jointly by both layers.
    Version: 1.0.0
    Base: Curtain
    """

    def __init__(self, position: int = None, sheer_open_state: str = None, sheer_position: int = None, fabric_open_state: str = None, fabric_position: int = None, **base_kwargs) -> None:
        # initialize base Curtain class
        super().__init__(**base_kwargs)
        # define properties
        self.position = IntProperty(
            name='position',
            description='Derived overall opening percentage, equal to the lower of the sheer and fabric layer opening percentages.',
            default=0,
            mode=2,
            unit='%',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.sheer_open_state = StringProperty(
            name='sheer_open_state',
            description='Whether the sheer layer is open or closed. It is closed at 0 percent and open above 0 percent.',
            default='closed',
            choices=['open', 'closed']
        )
        self.sheer_position = IntProperty(
            name='sheer_position',
            description='Opening percentage of the sheer layer, where 0 is fully closed and 100 is fully open.',
            default=0,
            unit='%',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )
        self.fabric_open_state = StringProperty(
            name='fabric_open_state',
            description='Whether the fabric layer is open or closed. It is closed at 0 percent and open above 0 percent.',
            default='closed',
            choices=['open', 'closed']
        )
        self.fabric_position = IntProperty(
            name='fabric_position',
            description='Opening percentage of the fabric layer, where 0 is fully closed and 100 is fully open.',
            default=0,
            unit='%',
            minimum=0,
            maximum=100,
            step=1,
            step_origin=0
        )

        # initialize properties
        if position is not None: code = self.position.internal_set(position)
        if sheer_open_state is not None: code = self.sheer_open_state.internal_set(sheer_open_state)
        if sheer_position is not None: code = self.sheer_position.internal_set(sheer_position)
        if fabric_open_state is not None: code = self.fabric_open_state.internal_set(fabric_open_state)
        if fabric_position is not None: code = self.fabric_position.internal_set(fabric_position)
        self._disabled = {
            'properties': [],
            'functions': [],
            'events': []
        }
        self.sheer_open_state.internal_set('open' if self.sheer_position.value > 0 else 'closed')
        self.fabric_open_state.internal_set('open' if self.fabric_position.value > 0 else 'closed')
        self._sync_overall_state()

    def get_open_state(self) -> tuple[str, dict]:
        code, sheer = self.sheer_position.get()
        if code != '[PASS]':
            return (code, {})
        code, fabric = self.fabric_position.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'open_state': 'open' if sheer > 0 and fabric > 0 else 'closed'})

    def set_open_state(self, value: str) -> tuple[str, dict]:
        if type(value) is not str or value not in ('open', 'closed'):
            return ('[INVALID_INPUT_ERROR]', {})
        position = 100 if value == 'open' else 0
        code = self.sheer_position.set(position)
        if code != '[PASS]':
            return (code, {})
        code = self.fabric_position.set(position)
        if code != '[PASS]':
            self.sheer_position.internal_set(0 if value == 'closed' else 100)
            return (code, {})
        code = self.sheer_open_state.set(value)
        if code != '[PASS]':
            return (code, {})
        code = self.fabric_open_state.set(value)
        if code != '[PASS]':
            return (code, {})
        code = self.position.internal_set(position)
        if code != '[PASS]':
            return (code, {})
        self._sync_overall_state()
        return ('[PASS]', {})

    def get_position(self) -> tuple[str, dict]:
        code, sheer = self.sheer_position.get()
        if code != '[PASS]':
            return (code, {})
        code, fabric = self.fabric_position.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'position': min(sheer, fabric)})

    def set_position(self, value: int) -> tuple[str, dict]:
        if type(value) is not int or isinstance(value, bool) or value < 0 or value > 100:
            return ('[INVALID_INPUT_ERROR]', {})
        state = 'closed' if value == 0 else 'open'
        code = self.sheer_position.set(value)
        if code != '[PASS]':
            return (code, {})
        code = self.fabric_position.set(value)
        if code != '[PASS]':
            return (code, {})
        code = self.sheer_open_state.set(state)
        if code != '[PASS]':
            return (code, {})
        code = self.fabric_open_state.set(state)
        if code != '[PASS]':
            return (code, {})
        code = self.position.internal_set(value)
        if code != '[PASS]':
            return (code, {})
        self._sync_overall_state()
        return ('[PASS]', {})

    def open_incrementally(self, percentage_points: int) -> tuple[str, dict]:
        if type(percentage_points) is not int or isinstance(percentage_points, bool) or percentage_points < 1 or percentage_points > 100:
            return ('[INVALID_INPUT_ERROR]', {})
        code, sheer = self.sheer_position.get()
        if code != '[PASS]':
            return (code, {})
        code, fabric = self.fabric_position.get()
        if code != '[PASS]':
            return (code, {})
        self._sync_overall_state()
        return self.set_position(min(100, sheer + percentage_points)) if sheer == fabric else self.set_sheer_position(min(100, sheer + percentage_points))

    def close_incrementally(self, percentage_points: int) -> tuple[str, dict]:
        if type(percentage_points) is not int or isinstance(percentage_points, bool) or percentage_points < 1 or percentage_points > 100:
            return ('[INVALID_INPUT_ERROR]', {})
        code, sheer = self.sheer_position.get()
        if code != '[PASS]':
            return (code, {})
        code, fabric = self.fabric_position.get()
        if code != '[PASS]':
            return (code, {})
        self._sync_overall_state()
        return self.set_position(max(0, sheer - percentage_points)) if sheer == fabric else self.set_sheer_position(max(0, sheer - percentage_points))

    def get_sheer_open_state(self) -> tuple[str, dict]:
        code, value = self.sheer_open_state.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'sheer_open_state': value})

    def set_sheer_open_state(self, value: str) -> tuple[str, dict]:
        if type(value) is not str or value not in ('open', 'closed'):
            return ('[INVALID_INPUT_ERROR]', {})
        self._sync_overall_state()
        return self.set_sheer_position(100 if value == 'open' else 0)

    def get_sheer_position(self) -> tuple[str, dict]:
        code, value = self.sheer_position.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'sheer_position': value})

    def set_sheer_position(self, value: int) -> tuple[str, dict]:
        if type(value) is not int or isinstance(value, bool) or value < 0 or value > 100:
            return ('[INVALID_INPUT_ERROR]', {})
        state = 'closed' if value == 0 else 'open'
        code = self.sheer_position.set(value)
        if code != '[PASS]':
            return (code, {})
        code = self.sheer_open_state.set(state)
        if code != '[PASS]':
            return (code, {})
        code, fabric = self.fabric_position.get()
        if code != '[PASS]':
            return (code, {})
        return_code = self.position.internal_set(min(value, fabric))
        if return_code != '[PASS]':
            return (return_code, {})
        self._sync_overall_state()
        return ('[PASS]', {})

    def get_fabric_open_state(self) -> tuple[str, dict]:
        code, value = self.fabric_open_state.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'fabric_open_state': value})

    def set_fabric_open_state(self, value: str) -> tuple[str, dict]:
        if type(value) is not str or value not in ('open', 'closed'):
            return ('[INVALID_INPUT_ERROR]', {})
        self._sync_overall_state()
        return self.set_fabric_position(100 if value == 'open' else 0)

    def get_fabric_position(self) -> tuple[str, dict]:
        code, value = self.fabric_position.get()
        if code != '[PASS]':
            return (code, {})
        return ('[PASS]', {'fabric_position': value})

    def set_fabric_position(self, value: int) -> tuple[str, dict]:
        if type(value) is not int or isinstance(value, bool) or value < 0 or value > 100:
            return ('[INVALID_INPUT_ERROR]', {})
        state = 'closed' if value == 0 else 'open'
        code = self.fabric_position.set(value)
        if code != '[PASS]':
            return (code, {})
        code = self.fabric_open_state.set(state)
        if code != '[PASS]':
            return (code, {})
        code, sheer = self.sheer_position.get()
        if code != '[PASS]':
            return (code, {})
        return_code = self.position.internal_set(min(sheer, value))
        if return_code != '[PASS]':
            return (return_code, {})
        self._sync_overall_state()
        return ('[PASS]', {})

    def _on_after_action(self, context: dict) -> tuple[str, list[dict]]:
        code, sheer = self.sheer_position.get()
        if code != '[PASS]':
            return (code, [])
        code, fabric = self.fabric_position.get()
        if code != '[PASS]':
            return (code, [])
        illuminance = int(6 * (sheer / 100) * (fabric / 100))
        return ('[PASS]', [{
            'trigger': 'after_action',
            'source': context['object_id'],
            'target': context['space_id'],
            'function': 'set_contribution',
            'parameters': {
                'property': 'illuminance',
                'value': illuminance,
                'unit': 'lux'
            }
        }])
    def _sync_overall_state(self):
        sheer = self.sheer_position.value
        fabric = self.fabric_position.value
        self.position.internal_set(min(sheer, fabric))
        self.open_state.internal_set('open' if min(sheer, fabric) > 0 else 'closed')
