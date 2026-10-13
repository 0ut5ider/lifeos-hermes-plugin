# ABOUTME: Verifies dashboard profile admission with actual isolated Hermes user services.
# ABOUTME: Preserves the main dashboard and removes only task-owned synthetic profiles and units.
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from types import SimpleNamespace
from uuid import uuid4

home = Path.home()
main = home / '.hermes'
source = home / 'release-ui-review-sources'
sys.path.insert(0, str(source))
sys.path.insert(0, str(main / '.lifeos-releases/73697ad3e0ef44e89d48842fb714a77c/hermes'))
from optional.lifeos_release_manager.release_stage import load_bridge
from optional.lifeos_release_manager.release_services import fresh_services, fresh_preview
from optional.lifeos_release_manager.release_catalog import ReleaseRejected
from hermes_cli.dashboard_procs import _hermes_home_for_pid
from ruamel.yaml import YAML
bridge = load_bridge(main / 'plugins/lifeos-hook-bridge')
core = bridge.memory_module('profile_services')


def command(*arguments):
    return core._run(*arguments)


def state(unit):
    return dict(line.split('=', 1) for line in command('show', unit,
        '--property=MainPID,ActiveState,ControlGroup,Environment', '--no-pager').splitlines())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


before = {'pid': state('hermes-dashboard.service')['MainPID'],
    'config': digest(main / 'config.yaml'), 'release': digest(main / 'integration-release.json')}
# These checks use the actual fixed installed service without draining it.
fixed = fresh_preview(bridge, main, home / '.claude')
marker = uuid4().hex
work = home / ('release-service-trial-' + marker)
work.mkdir(mode=0o700)
target_name = 'release-review-target-' + marker
foreign_name = 'release-review-foreign-' + marker
target = main / 'profiles' / target_name
foreign = main / 'profiles' / foreign_name
unit = 'lifeos-release-review-' + marker + '.service'
definition = home / '.config/systemd/user' / unit
results = {'scope': 'Actual Hermes process, user unit, procfs, control group and drain/resume; no complete installer/browser claim.',
    'fixed_main_service_preview_pass': bool(fixed['signature']), 'before': before}
created = []
profiles_existed = (main / 'profiles').exists()
(main / 'profiles').mkdir(mode=0o700, exist_ok=True)
try:
    yaml = YAML(typ='safe')
    configured = yaml.load((main / 'config.yaml').read_text())
    for profile in (target, foreign):
        profile.mkdir(mode=0o700);created.append(profile)
        data = {'model': configured['model'], 'plugins': {'lifeos-hook-bridge': {'enabled': False},
            'lifeos-release-manager': {'enabled': False}}}
        with (profile / 'config.yaml').open('w') as stream:
            yaml.dump(data, stream)
        (profile / 'config.yaml').chmod(0o600)
    choice = work / 'profile-name'
    choice.write_text(target_name);choice.chmod(0o600)
    launcher = work / 'hermes'
    launcher.write_text('#!/bin/sh\nexec ' + str(home / '.local/bin/hermes') +
        ' --profile "$(cat ' + str(choice) + ')" dashboard --isolated --no-open --host 127.0.0.1 --port 0\n')
    launcher.chmod(0o700)
    definition.write_text('[Unit]\nDescription=Isolated PR18 Hermes profile control\n[Service]\nType=simple\n'
        'WorkingDirectory=' + str(home) + '\nEnvironment=HERMES_HOME=' + str(target) +
        '\nEnvironment=PYTHONDONTWRITEBYTECODE=1\nExecStart=' + str(launcher) +
        ' dashboard --isolated --no-open\nKillMode=control-group\nTimeoutStopSec=20s\nRestart=no\n')
    definition.chmod(0o600)
    command('daemon-reload')
    class TrialServices(core.ProfileServices):
        def __init__(self, *args, first_installation=False, **kwargs):
            super().__init__(*args, units={'dashboard': unit}, first_installation=first_installation, **kwargs)
    facade = SimpleNamespace(ProfileServices=TrialServices, _run=core._run, _digest=core._digest,
        UNITS={'dashboard': unit})
    current = SimpleNamespace(memory_module=lambda name: facade)
    services = fresh_services(current, target, home / '.release-trial-uninstalled')
    def start(expected):
        command('start', unit)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            values = state(unit)
            pid = int(values['MainPID'])
            if pid and Path(_hermes_home_for_pid(pid) or "/") == expected:
                return values
            time.sleep(0.25)
        raise RuntimeError('Actual Hermes trial profile does not start')
    target_state = start(target)
    preview = services.preview()
    definition_hash = digest(definition)
    command('stop', unit)
    choice.write_text(foreign_name)
    foreign_state = start(foreign)
    try:
        services.drain(signature=preview['signature'])
    except ReleaseRejected as error:
        results['foreign_refusal'] = {'error': str(error), 'same_definition': digest(definition) == definition_hash,
            'pid_before': foreign_state['MainPID'], 'pid_after': state(unit)['MainPID'],
            'journal_absent': not services.journal.exists()}
    else:
        raise AssertionError('Foreign real dashboard was admitted')
    assert results['foreign_refusal']['pid_before'] == results['foreign_refusal']['pid_after']
    assert results['foreign_refusal']['journal_absent']
    command('stop', unit)
    services.preview()
    choice.write_text(target_name)
    target_state = start(target)
    stopped = services.drain(signature=services.preview()['signature'])
    resumed = services.resume()
    restarted = state(unit)
    assert Path(_hermes_home_for_pid(int(restarted['MainPID'])) or "/") == target
    results['matching_restart'] = {'drain': stopped['state'], 'resume': resumed['state'],
        'pid_before': target_state['MainPID'], 'pid_after': restarted['MainPID'],
        'same_definition': digest(definition) == definition_hash}
    assert target_state['MainPID'] != restarted['MainPID']
finally:
    if definition.exists():
        command('stop', unit)
        assert state(unit)['MainPID'] == '0'
        definition.unlink();command('daemon-reload')
        subprocess.run(['systemctl', '--user', 'reset-failed', unit], capture_output=True, text=True)
    for profile in created:
        shutil.rmtree(profile)
    if not profiles_existed:
        (main / 'profiles').rmdir()
    shutil.rmtree(work)
    after = {'pid': state('hermes-dashboard.service')['MainPID'],
        'config': digest(main / 'config.yaml'), 'release': digest(main / 'integration-release.json')}
    results['after'] = after
    results['main_unchanged'] = before == after
    (source / 'guest-service-trial.json').write_text(json.dumps(results, indent=2) + '\n')
    assert results['main_unchanged']
print(json.dumps(results, indent=2))
