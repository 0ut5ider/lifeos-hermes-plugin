# ABOUTME: Returns native numeric installation counts to the current unrestricted owner.
# ABOUTME: Binds count sources to the selected installation and checks authority before output.
from pathlib import Path

from .memory_access import MemoryUnavailable
from .memory_sources import authorize


KEYS = ('skills', 'workflows', 'hooks', 'signals', 'files', 'work', 'research', 'ratings')
DATA_PATHS = {
    'signals': 'LIFEOS/MEMORY/LEARNING/',
    'files': 'LIFEOS/USER/',
    'work': 'LIFEOS/MEMORY/WORK/',
    'research': 'LIFEOS/MEMORY/RESEARCH/',
    'ratings': 'LIFEOS/MEMORY/LEARNING/SIGNALS/ratings.jsonl',
}


def read(memory, scope, root, lifeos_dir, only, *, check_current):
    authorize(scope)
    if (not isinstance(root, str) or not Path(root).is_absolute() or Path(root).resolve() != memory.physical_root
            or not isinstance(lifeos_dir, str) or not Path(lifeos_dir).is_absolute()
            or Path(lifeos_dir).resolve() != memory.physical_root / 'LIFEOS'
            or only is not None and (not isinstance(only, str) or only not in KEYS)):
        raise MemoryUnavailable('Native counts require the selected installation and a fixed count key')
    with memory._transaction():
        selected_paths = [path for key, path in DATA_PATHS.items() if only is None or only == key]
        for path in selected_paths:
            memory._path(path)
        values = memory._native('counts', only=only)
        if (not isinstance(values, dict) or set(values) != set(KEYS)
                or any(type(value) is not int or not 0 <= value <= 2 ** 53 - 1 for value in values.values())):
            raise MemoryUnavailable('The native installation counts have invalid numeric fields')
        check_current()
        memory._boundary()
        for path in selected_paths:
            memory._path(path)
        if memory._native('counts', only=only) != values:
            raise MemoryUnavailable('The native installation counts change during collection')
        check_current()
        return {'ok': True, 'counts': values}
