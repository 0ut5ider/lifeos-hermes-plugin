# ABOUTME: Records, for each Hermes process, whether the bridge registered with the patched or reduced hook set.
# ABOUTME: Lets the release worker prove that a restarted service loaded the bridge in patched mode.
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

MODES = ('patched', 'reduced', 'inactive')


def _start_time(pid):
    # The bridge runs without the release manager, so it reads the kernel start time itself.
    fields = Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()
    return int(fields[19])


def hermes_source():
    """Return the Hermes checkout that this process imports, or None when Hermes is not importable."""
    try:
        import hermes_cli
    except ImportError:
        return None
    module = getattr(hermes_cli, '__file__', None)
    return str(Path(module).resolve().parents[1]) if module else None


def directory(profile):
    return Path(profile) / '.lifeos-bridge/registrations'


def write_receipt(profile, mode, *, pid=None):
    """Publish this process's registration mode; never fail the plugin registration itself."""
    if mode not in MODES:
        raise ValueError('Unknown bridge registration mode')
    pid = os.getpid() if pid is None else pid
    try:
        root = directory(profile)
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        for stale in root.glob('*.json'):
            if stale.stem.isdecimal() and not Path('/proc', stale.stem).exists():
                stale.unlink(missing_ok=True)
        value = {'pid': pid, 'start_time': _start_time(pid), 'mode': mode, 'source': hermes_source()}
        descriptor, name = tempfile.mkstemp(prefix='.registration-', dir=root)
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(value, stream)
        os.replace(name, root / (str(pid) + '.json'))
    except OSError:
        return None
    return value


def read_receipt(profile, pid):
    """Return the receipt of the live process ``pid``, or None when it has not registered the bridge."""
    try:
        value = json.loads((directory(profile) / (str(int(pid)) + '.json')).read_text())
        if (value.get('pid') != int(pid) or value.get('start_time') != _start_time(int(pid)) or value.get('mode') not in MODES
                or not isinstance(value.get('source'), (str, type(None)))):
            return None
    except (OSError, ValueError):
        return None
    return value
