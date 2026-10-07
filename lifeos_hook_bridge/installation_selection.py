# ABOUTME: Selects which LifeOS home a Hermes profile uses through a journaled, recoverable transaction.
# ABOUTME: Return to the account home runs the same transaction with no target home.

import base64
import json
import os
from pathlib import Path

from .lifeos_installation import SETTING, account_home, clear, publish, selection
from .memory_transaction import publish as publish_file

STATES = ('prepared', 'stopped', 'published', 'mounted', 'applied', 'rolling_back', 'rolled_back')


class SelectionError(RuntimeError):
    pass


def _record(job: Path, journal: dict, state: str) -> None:
    journal['state'] = state
    publish_file(job / 'journal.json', (json.dumps(journal, sort_keys=True, indent=2) + '\n').encode())


def _setting_bytes(profile: Path):
    path = profile / SETTING
    return base64.b64encode(path.read_bytes()).decode() if path.is_file() else None


def _set_root(configuration, root: str) -> None:
    if configuration is not None and configuration.path.exists():
        configuration.update(lambda value: value.update(root=root))


def select_home(job: Path, *, profile: Path, target: Path | None, configuration, services, mount, verify,
                baseline_data: bytes | None) -> dict:
    """Point the profile at target, or at the account home when target is None, and mount it."""
    profile = Path(profile).absolute()
    current = selection(profile)
    home = account_home(profile) if target is None else Path(target).absolute()
    installed = home / '.claude'
    if installed.is_symlink() or not (installed / 'LIFEOS').is_dir():
        raise SelectionError('The selected home has no installed LifeOS')
    job.mkdir(parents=True, mode=0o700)
    journal = {'version': 1, 'profile': str(profile),
               'previous': {'setting': _setting_bytes(profile), 'home': str(current.home),
                            'configured': current.configured,
                            'root': configuration.load()['root'] if configuration is not None
                            and configuration.path.exists() else None},
               'target': {'home': None if target is None else str(home), 'workspace': str(current.workspace)}}
    _record(job, journal, 'prepared')
    try:
        services.stop()
        _record(job, journal, 'stopped')
        if target is None:
            clear(profile)
        else:
            publish(profile, home, current.workspace)
        _set_root(configuration, str(installed))
        services.point_pulse(None if target is None else home)
        _record(job, journal, 'published')
        mount(installed, baseline_data)
        _record(job, journal, 'mounted')
        services.start()
        verify()
        _record(job, journal, 'applied')
        return journal
    except Exception as error:
        try:
            _roll_back(job, journal, configuration=configuration, services=services, mount=mount, verify=verify)
        except Exception as rollback_error:
            raise SelectionError(f'{error}; rollback failed: {rollback_error}') from error
        raise SelectionError(str(error)) from error


def _roll_back(job, journal, *, configuration, services, mount, verify) -> dict:
    profile = Path(journal['profile'])
    remount = journal['state'] in {'mounted', 'applied'} or journal.get('remount') is True
    journal['remount'] = remount
    _record(job, journal, 'rolling_back')
    services.stop()
    previous = journal['previous']
    if previous['setting'] is None:
        clear(profile)
    else:
        publish_file(profile / SETTING, base64.b64decode(previous['setting']))
        os.chmod(profile / SETTING, 0o600)
    if previous['root'] is not None:
        _set_root(configuration, previous['root'])
    previous_home = Path(previous['home'])
    services.point_pulse(previous_home if previous['configured'] else None)
    if remount:
        mount(previous_home / '.claude', None)
    services.start()
    verify()
    _record(job, journal, 'rolled_back')
    return journal


def recover_selection(job: Path, *, configuration, services, mount, verify) -> dict:
    journal = json.loads((job / 'journal.json').read_text(encoding='utf-8'))
    if journal.get('state') not in {'prepared', 'stopped', 'published', 'mounted', 'rolling_back'}:
        raise SelectionError('The installation selection does not need recovery')
    return _roll_back(job, journal, configuration=configuration, services=services, mount=mount, verify=verify)
