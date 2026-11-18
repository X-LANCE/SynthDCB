"""Public user context and weighted, uniquely resolvable device names."""
from collections import defaultdict
from copy import deepcopy
import math
import re

# Edit each template's weight here to control task target wording.
TARGET_REFERENCE_CONFIG = {
    'device_labels': {'Television': 'TV', 'TV': 'TV', 'WiFi': 'Wi-Fi'},
    'templates': {
        'room_device': {'text': '{room} {device}', 'scope': 'room', 'weight': 6},
        'device_in_room': {'text': '{device} in the {room}', 'scope': 'room', 'weight': 6},
        'device_only': {'text': '{device}', 'scope': 'world', 'weight': 3},
        'current_room_device': {'text': 'the {device}', 'scope': 'user_room', 'weight': 3},
        'numbered_device': {'text': '{device} {index}', 'scope': 'world', 'weight': 1},
        'room_numbered_device': {'text': '{room} {device} {index}', 'scope': 'room', 'weight': 1},
        'canonical': {'text': '{canonical}', 'scope': 'world', 'weight': 1},
    },
}


def current_user(inventory, requested, rng):
    """Resolve an explicit user or sample a person already in the World."""
    if requested is None:
        if not inventory.people:
            return None
        requested = rng.choice(sorted(inventory.people))
    if isinstance(requested, str):
        person = inventory.people[requested]
        user = {'user_id': requested, 'name': inventory.person_name(requested), 'space_id': person['space_id']}
    else:
        user = deepcopy(requested)
    space_id = user.get('space_id')
    if space_id is not None:
        user['space_name'] = inventory.space_names[space_id]
    return user


def reference_candidates(inventory, user=None, config=None):
    """Return only names that identify one device globally or in the user's room."""
    config = config if config is not None else TARGET_REFERENCE_CONFIG
    templates = config['templates']
    for key, spec in templates.items():
        if spec['scope'] not in {'world', 'room', 'user_room'}:
            raise ValueError(f'unknown reference scope: {key}')
        if not isinstance(spec['weight'], (int, float)) or not math.isfinite(spec['weight']) or spec['weight'] < 0:
            raise ValueError(f'invalid reference weight: {key}')
    owners = defaultdict(set)
    candidates = defaultdict(list)
    user_room = user.get('space_id') if user else None
    for target_id, device in inventory.initial['objects'].items():
        seen = set()
        canonical = inventory.device_names[target_id]
        space_id = device.get('space_id')
        labels = dict.fromkeys((device['class'].rsplit('.', 1)[-1], device['class'].split('.')[1]))
        for class_name in labels:
            label = config['device_labels'].get(class_name, re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', class_name).lower())
            values = {'device': label, 'room': inventory.space_names.get(space_id, '').lower(),
                      'index': canonical.rsplit(' ', 1)[-1], 'canonical': canonical}
            for key, spec in templates.items():
                scope = spec['scope']
                if scope == 'room' and space_id is None:
                    continue
                if scope == 'user_room' and (user_room is None or space_id != user_room):
                    continue
                text = spec['text'].format(**values)
                owners[text.casefold()].add(target_id)
                if (key, text) not in seen:
                    candidates[target_id].append({'template': key, 'text': text, 'weight': spec['weight']})
                    seen.add((key, text))
    return {target_id: [item for item in items if owners[item['text'].casefold()] == {target_id}]
            for target_id, items in candidates.items()}
