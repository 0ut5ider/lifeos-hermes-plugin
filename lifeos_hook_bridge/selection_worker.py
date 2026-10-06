# ABOUTME: Runs a LifeOS home selection or return as a detached user service job.
# ABOUTME: Wires the selection transaction to systemd, the native mount, and the VersionDrift baseline.

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types
from pathlib import Path

if not __package__:
    package = types.ModuleType("lifeos_hook_bridge")
    package.__path__ = [str(Path(__file__).resolve().parent)]
    sys.modules[package.__name__] = package
    __package__ = package.__name__

from . import program_lock
from .installation_lock import installation_lock
from .installation_selection import SelectionError, recover_selection, select_home
from .memory_administration import mount_environment
from .memory_service import MemoryConfiguration
from .mount_transaction import MountTransaction
from .native_output import failure_message
from .version_drift import create_baseline, default_baseline_path, save_baseline

GATEWAY = 'hermes-gateway.service'
DASHBOARD = 'hermes-dashboard.service'
PULSE = 'com.lifeos.pulse.service'
TURN_WAIT_SECONDS = 600


def _systemctl(*arguments: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(['systemctl', '--user', *arguments], text=True, capture_output=True, timeout=60)
    if check and result.returncode:
        raise RuntimeError(failure_message('systemctl ' + ' '.join(arguments), result))
    return result


def _unit_exists(unit: str) -> bool:
    return _systemctl('cat', unit, check=False).returncode == 0


def _gateway_pid() -> str:
    return _systemctl('show', GATEWAY, '-p', 'MainPID', '--value').stdout.strip()


class SystemdServices:
    """Stops and starts the profile services; points native Pulse at the selected home."""

    def __init__(self, account: Path):
        self.dropin = account / '.config/systemd/user' / (PULSE + '.d') / 'lifeos-installation.conf'
        self.pulse = _unit_exists(PULSE)
        self.dashboard = _unit_exists(DASHBOARD)
        self.gateway_pid = None

    def stop(self) -> None:
        if self.gateway_pid is None:
            self.gateway_pid = _gateway_pid()
        _systemctl('stop', GATEWAY)
        if self.pulse:
            _systemctl('stop', PULSE)

    def point_pulse(self, home: Path | None) -> None:
        if not self.pulse:
            return
        if home is None:
            self.dropin.unlink(missing_ok=True)
        else:
            self.dropin.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.dropin.write_text(f'[Service]\nWorkingDirectory={home}/.claude/LIFEOS/PULSE\n'
                                   f'Environment=HOME={home}\n')
        _systemctl('daemon-reload')

    def start(self) -> None:
        if self.pulse:
            _systemctl('start', PULSE)
        _systemctl('start', GATEWAY)
        if self.dashboard:
            _systemctl('restart', DASHBOARD)

    def verify(self) -> None:
        time.sleep(3)
        if _systemctl('is-active', GATEWAY, check=False).stdout.strip() != 'active':
            raise RuntimeError('The Hermes gateway did not start')
        if _gateway_pid() in {'', '0', self.gateway_pid}:
            raise RuntimeError('The Hermes gateway did not restart')


def _write_status(job: Path, state: str, error: str | None = None) -> None:
    target = job / 'status.json'
    previous = json.loads(target.read_text(encoding='utf-8')) if target.is_file() else {}
    document = {'state': state, **({'unit': previous['unit']} if 'unit' in previous else {}),
                **({'error': error[:400]} if error else {})}
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=job, delete=False) as stream:
        os.fchmod(stream.fileno(), 0o600)
        json.dump(document, stream)
        stream.write('\n')
        temporary = Path(stream.name)
    os.replace(temporary, target)


def _baseline_data(candidate: Path | None, installed: Path) -> bytes | None:
    if default_baseline_path(installed.parent).exists():
        return None
    if candidate is None:
        raise SelectionError('The selected home needs a VersionDrift baseline source')
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'baseline.json'
        save_baseline(create_baseline(candidate / 'LifeOS/install', installed), path)
        return path.read_bytes()


def _mount(profile: Path, request: dict):
    bun = shutil.which('bun') or str(Path.home() / '.bun/bin/bun')
    hermes = request['hermes_command']

    def mount(installed: Path, baseline_data: bytes | None) -> None:
        transaction = MountTransaction(installed, profile, default_baseline_path(installed.parent))
        if transaction.status()['recovery_required']:
            transaction.recover()
        environment = mount_environment(installed, profile)
        environment['PATH'] = str(Path(bun).parent) + os.pathsep + environment.get('PATH', '')
        transaction.execute(environment, bun, hermes, baseline_data=baseline_data)
    return mount


def run_selection_job(job: Path, action: str = 'select') -> dict:
    request = json.loads((job / 'request.json').read_text(encoding='utf-8'))
    profile = Path(request['profile'])
    configuration = MemoryConfiguration(profile / 'lifeos-memory.json')
    with installation_lock(profile, wait=True), program_lock.exclusive(profile, TURN_WAIT_SECONDS):
        services = SystemdServices(Path.home())
        mount = _mount(profile, request)
        snapshot = job / 'transaction'
        if action == 'recover':
            return recover_selection(snapshot, configuration=configuration, services=services, mount=mount,
                                     verify=services.verify)
        target = None if request['target_home'] is None else Path(request['target_home'])
        candidate = None if request.get('candidate') is None else Path(request['candidate'])
        baseline = None if target is None else _baseline_data(candidate, target / '.claude')
        return select_home(snapshot, profile=profile, target=target, configuration=configuration,
                           services=services, mount=mount, verify=services.verify, baseline_data=baseline)


def _main() -> int:
    parser = argparse.ArgumentParser(description='Select or return a LifeOS home')
    parser.add_argument('job', type=Path)
    parser.add_argument('--action', choices=('select', 'recover'), default='select')
    arguments = parser.parse_args()
    _write_status(arguments.job, 'running' if arguments.action == 'select' else 'recovering')
    try:
        result = run_selection_job(arguments.job, arguments.action)
    except BaseException as error:
        journal = arguments.job / 'transaction/journal.json'
        state = json.loads(journal.read_text())['state'] if journal.is_file() else 'failed'
        _write_status(arguments.job, state if state == 'rolled_back' else
                      'interrupted' if state not in {'prepared', 'applied'} else 'failed', str(error))
        print(f'LifeOS selection failed: {error}', file=sys.stderr)
        return 1
    _write_status(arguments.job, result['state'])
    return 0


if __name__ == '__main__':
    raise SystemExit(_main())
