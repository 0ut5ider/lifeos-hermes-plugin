# ABOUTME: Inventories the Hermes services and processes that an in-place operation must stop and restart.
# ABOUTME: Binds existing user units, offers standard units for hand-started consumers, and refuses the rest.
from __future__ import annotations

import os
from pathlib import Path
import subprocess

from .consumer_scan import source_consumers, start_time
from .release_catalog import ReleaseRejected


UNITS = {'gateway': 'hermes-gateway.service', 'dashboard': 'hermes-dashboard.service',
         'pulse': 'com.lifeos.pulse.service'}
OFFERABLE = ('gateway', 'dashboard')


def _properties(unit):
    result = subprocess.run(['systemctl', '--user', 'show', unit, '--no-pager',
                             '--property=LoadState,ActiveState,ControlGroup,FragmentPath'],
                            capture_output=True, text=True, timeout=45)
    if result.returncode or result.stderr:
        raise ReleaseRejected('The owner service manager does not report the Hermes services')
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)


def ancestors(pid=None):
    """Return the process IDs above ``pid`` (default: this process), which run the operation itself."""
    chain, current = set(), os.getpid() if pid is None else pid
    while current > 1:
        try:
            fields = Path('/proc', str(current), 'stat').read_text().rsplit(')', 1)[1].split()
        except (FileNotFoundError, ProcessLookupError):
            break
        current = int(fields[1])
        chain.add(current)
    return chain


def inventory(source, state_dir, *, units=UNITS, excluded_pids=frozenset(), operators=frozenset()):
    """Return the bound unit roles, the processes outside them, and the units the owner can create.

    A role is bound when its standard user unit is loaded from a definition file. A hand-started
    gateway or dashboard outside its unit can be replaced by a created unit when the owner accepts.
    Any other consumer, such as an interactive CLI session, must be closed before the operation.
    """
    bound, groups = [], set()
    for role, unit in units.items():
        values = _properties(unit)
        if values.get('LoadState') == 'loaded' and values.get('FragmentPath'):
            bound.append(role)
            if values.get('ControlGroup'):
                groups.add(values['ControlGroup'])
    consumers = [item for item in source_consumers(source, state_dir, excluded_pids=excluded_pids, excluded_groups=groups)
                 if not (item['pid'] in operators and item['role'] == 'other')]
    offers = sorted({item['role'] for item in consumers if item['role'] in OFFERABLE and item['role'] not in bound})
    blocking = [item for item in consumers if item['role'] not in offers]
    return {'bound': bound, 'consumers': consumers, 'offers': offers, 'blocking': blocking}


def profile_units(profile, *, units=UNITS):
    """Return the unit bindings for profile service barriers, or None to bind every standard role.

    A managed installation always has all three units. An in-place host has only the units its owner
    created and the Pulse unit that LifeOS added, so its barriers bind exactly the loaded definitions.
    """
    from .host_record import record_path
    path = record_path(profile)
    if not path.exists() and not path.is_symlink():
        return None
    present = {}
    for role, unit in units.items():
        values = _properties(unit)
        if values.get('LoadState') == 'loaded' and values.get('FragmentPath'):
            present[role] = unit
    return present


def replace_with_units(admitted, created):
    """Return the admitted hand-started processes that the created units replace, if they are unchanged.

    Each process must still have its reviewed start time; a restarted or reused process ID refuses.
    """
    selected = []
    for item in admitted:
        if item['role'] not in created:
            continue
        try:
            current = start_time(item['pid'])
        except (FileNotFoundError, ProcessLookupError):
            continue
        if current != item['start_time']:
            raise ReleaseRejected('A reviewed Hermes process restarted after review; prepare the operation again')
        selected.append(item)
    return selected
