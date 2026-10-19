# ABOUTME: Records which Hermes configuration values LifeOS changed and checks that it left the rest alone.
# ABOUTME: Removal and an in-place restore return changed values only where the owner has not changed them since.
from __future__ import annotations

import copy
import json
from pathlib import Path

from .release_catalog import ReleaseRejected
from .release_programs import publish


ABSENT = {'absent': True}
OWNED_ROOTS = ('plugins',)
PROTECTED_ROOTS = ('model', 'providers', 'custom_providers', 'fallback_model', 'auxiliary', 'mcp_servers',
                   'toolsets', 'platforms')
RECORD = '.lifeos-host/configuration.json'


class ConfigurationConflict(ReleaseRejected):
    """The owner changed a configuration value after an operation that also changed it."""


def parse_configuration(data):
    from ruamel.yaml import YAML
    value = YAML(typ='safe').load(data) if data else {}
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ReleaseRejected('The Hermes configuration is not a mapping')
    return value


def changed_paths(before, after, prefix=()):
    """Return ``[(path, before_value, after_value)]`` for the leaf mapping values that differ."""
    changes = []
    for key in sorted(set(before) | set(after), key=str):
        left, right = before.get(key, ABSENT), after.get(key, ABSENT)
        path = (*prefix, key)
        if isinstance(left, dict) and isinstance(right, dict) and left is not ABSENT and right is not ABSENT:
            changes.extend(changed_paths(left, right, path))
        elif left != right:
            changes.append((path, left, right))
    return changes


def check_preserved(before_data, after_data):
    """Refuse a configuration change under a protected root, such as the model or a messaging platform."""
    changed = [path for path, _, _ in changed_paths(parse_configuration(before_data), parse_configuration(after_data))
               if path[0] in PROTECTED_ROOTS]
    if changed:
        raise ReleaseRejected('LifeOS changed protected Hermes settings: ' + ', '.join('.'.join(map(str, path)) for path in changed))


def check_memory_provider(before_data, after_data, *, owned):
    """Refuse a change of the memory provider selection unless the operation owns it, as a fresh installation does."""
    if owned:
        return
    path = ('memory', 'provider')
    if _get(parse_configuration(before_data), path) != _get(parse_configuration(after_data), path):
        raise ReleaseRejected('The operation changed the Hermes memory provider selection (memory.provider)')


def record(profile, before_data, after_data):
    """Merge this operation's changed values into the profile record, keeping the earliest before-values."""
    path = Path(profile) / RECORD
    existing = json.loads(path.read_text()) if path.exists() else {'format': 1, 'values': []}
    values = {tuple(item['path']): item for item in existing['values']}
    after = parse_configuration(after_data)
    for key, item in values.items():
        item['installed'] = _get(after, key)
    for key, left, right in changed_paths(parse_configuration(before_data), after):
        if key[0] in OWNED_ROOTS or any(key[:len(recorded)] == recorded for recorded in values):
            continue
        values[key] = {'path': list(key), 'before': left, 'installed': right}
    value = {'format': 1, 'values': [values[key] for key in sorted(values, key=lambda item: [str(part) for part in item])]}
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    publish(path, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())
    return value


def record_restored(profile):
    """After a rollback, record the restored configuration as the installed value of every recorded path."""
    if not (Path(profile) / RECORD).exists():
        return None
    configuration = (Path(profile) / 'config.yaml').read_bytes()
    return record(profile, configuration, configuration)


def _get(mapping, path):
    for key in path:
        if not isinstance(mapping, dict) or key not in mapping:
            return ABSENT
        mapping = mapping[key]
    return mapping


def restore(current, recorded):
    """Return ``(configuration, conflicts)``: recorded values restored where they still hold their installed value."""
    result, conflicts = copy.deepcopy(current), []
    for item in recorded['values']:
        path = tuple(item['path'])
        if _get(result, path) != item['installed']:
            conflicts.append('.'.join(map(str, path)))
            continue
        parent = result
        for key in path[:-1]:
            parent = parent.setdefault(key, {})
        if item['before'] == ABSENT:
            parent.pop(path[-1], None)
        else:
            parent[path[-1]] = copy.deepcopy(item['before'])
    return result, conflicts


def restore_operation(before_data, after_data, current_data):
    """Return ``current_data`` with each value that an operation changed from ``before_data`` to ``after_data`` restored.

    The owner's later changes to other values stay. A changed value that the owner changed again refuses.
    """
    if current_data == after_data:
        return before_data
    import io
    from ruamel.yaml import YAML
    yaml = YAML()
    yaml.preserve_quotes = True
    def load(data):
        value = yaml.load(data) if data else {}
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ReleaseRejected('The Hermes configuration is not a mapping')
        return value
    values = [{'path': list(path), 'before': left, 'installed': right}
              for path, left, right in changed_paths(load(before_data), load(after_data))]
    result, conflicts = restore(load(current_data), {'values': values})
    if conflicts:
        raise ConfigurationConflict('You changed configuration values after this operation that it also changed: '
                                    + ', '.join(conflicts) + '. Set them back to the values the operation installed, '
                                    'then restore again.')
    rendered = io.StringIO()
    yaml.dump(result, rendered)
    return rendered.getvalue().encode()
