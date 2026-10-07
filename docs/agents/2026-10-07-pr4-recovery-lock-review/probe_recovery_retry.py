# ABOUTME: Measures later owner edits across real native selection recovery process exits.
# ABOUTME: Uses synthetic fixture roots and service callback records without contacting live services.
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

import test_mount_transaction as fixture_module

OUTPUT = Path(__file__).parent
CHILD = r'''
import json, os, sys
from pathlib import Path
from lifeos_hook_bridge import installation_selection as selection
from lifeos_hook_bridge import selection_worker as worker
from lifeos_hook_bridge.memory_service import MemoryConfiguration
profile, target, job, hermes, phase, source = sys.argv[1:]
profile, target, job = map(Path, (profile, target, job))
if source != 'current':
    exec(compile(Path(source).read_text(), source, 'exec'), selection.__dict__)
native = worker._mount(profile, {'hermes_command': hermes})
class Services:
    def stop(self): pass
    def start(self): pass
    def point_pulse(self, home): pass
configuration = MemoryConfiguration(profile / 'lifeos-memory.json')
def mount(installed, baseline):
    native(installed, baseline)
    if phase in {'select', 'previous-committed'}: os._exit(91)
if phase == 'checkpoint':
    record = selection._record
    def crash(job, journal, state):
        record(job, journal, state)
        if journal.get('target_mount_recovered'): os._exit(92)
    selection._record = crash
arguments = dict(configuration=configuration, services=Services(), mount=mount,
    recover_mount=lambda installed: worker._recover_mount(installed, profile), verify=lambda: None)
if phase == 'select':
    selection.select_home(job, profile=profile, target=target, baseline_data=None, **arguments)
else:
    selection.recover_selection(job, **arguments)
'''

def run_case(phase, source):
    fixture = fixture_module.MountTransactionTests()
    fixture.setUp()
    try:
        from lifeos_hook_bridge import installation_selection as selection
        from lifeos_hook_bridge.selection_worker import _mount, _recover_mount
        from lifeos_hook_bridge.lifeos_installation import selection as current
        fixture.fixture.configuration.update(lambda config: config.update(ownership_enabled=False))
        (fixture.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        target = fixture.root.parent / 'selection-target/home/.claude'
        shutil.copytree(fixture.root, target)
        (target / 'LIFEOS/LIFEOS_SYSTEM_PROMPT.md').write_text('# SyntheticTargetConstitution\n')
        environment = {key: value for key, value in fixture.environment.items()
                       if key != 'LIFEOS_MEMORY_ADMINISTRATION'}
        with patch.dict(os.environ, environment, clear=True):
            native = _mount(fixture.profile, {'hermes_command': str(fixture.hermes)})
            native(fixture.root, None)
            job = fixture.profile / 'selection-retry'
            def child(mode):
                result = subprocess.run([sys.executable, '-c', CHILD, str(fixture.profile), str(target.parent),
                    str(job), str(fixture.hermes), mode, source], text=True, capture_output=True, timeout=120)
                return {'phase': mode, 'code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
            children = [child('select'), child(phase)]
            assert children[0]['code'] == 91, children
            assert children[1]['code'] == (92 if phase == 'checkpoint' else 91), children
            before_journal = json.loads((job / 'journal.json').read_text())
            before_inner = json.loads((fixture.profile / '.lifeos-mount/operation.json').read_text())
            assert before_journal['target_mount_recovered'] is True, before_journal
            soul = fixture.profile / 'SOUL.md'
            owner_edit = '# SyntheticOwnerEditAfterRecoveryExit\n'
            soul.write_text(owner_edit)
            events = []
            class Services:
                def stop(self): events.append('stop')
                def start(self): events.append('start')
                def point_pulse(self, home): events.append('pulse')
            recover = selection.recover_selection
            if source != 'current':
                import types
                control = types.ModuleType('lifeos_hook_bridge.selection_control')
                control.__package__ = 'lifeos_hook_bridge'
                exec(compile(Path(source).read_text(), source, 'exec'), control.__dict__)
                recover = control.recover_selection
            try:
                result = recover(job, configuration=fixture.fixture.configuration, services=Services(),
                    mount=native, recover_mount=lambda installed: _recover_mount(installed, fixture.profile),
                    verify=lambda: events.append('verify'))
                outcome = {'state': result['state']}
            except Exception as error:
                outcome = {'error': str(error)}
            actual = soul.read_text()
            return {'phase': phase, 'selection_source': source, 'children': children,
                'outer_before_retry': before_journal, 'inner_before_retry': before_inner,
                'retry': outcome, 'service_events': events,
                'owner_edit_preserved': actual == owner_edit,
                'soul_after_retry_sha256': hashlib.sha256(actual.encode()).hexdigest(),
                'soul_contains_target': 'SyntheticTargetConstitution' in actual,
                'selected_after_retry': str(current(fixture.profile).installed),
                'config_root_after_retry': fixture.fixture.configuration.load()['root']}
    finally:
        fixture.doCleanups()

if __name__ == '__main__':
    data = []
    for source in sys.argv[1:] or ['current']:
        for phase in ('checkpoint', 'previous-committed'):
            result = run_case(phase, source)
            data.append(result)
            (OUTPUT / 'recovery-retry-results.json').write_text(json.dumps(data, indent=2) + '\n')
            print(json.dumps(result), flush=True)
