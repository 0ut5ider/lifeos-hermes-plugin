# ABOUTME: Reproduces profile restoration failure boundaries with synthetic fixtures.
# ABOUTME: Emits JSON observations without changing repository implementation.
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from test_update_transaction import UpdateTransactionTests
from lifeos_hook_bridge.update_transaction import apply_update, restore_update, recover_update

def run(case):
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory(dir='/dev/shm') as shm:
        fixture = UpdateTransactionTests()
        installed, hermes, prior, selected, reference, baseline, snapshot = fixture.fixture(Path(tmp))
        if case == 'cross_filesystem':
            alternate = Path(shm) / 'hermes'
            alternate.mkdir()
            for file in hermes.iterdir():
                (alternate / file.name).write_bytes(file.read_bytes())
            hermes = alternate
        events, stop, start, mount, renew, verify = fixture.callbacks(hermes, baseline)
        apply_update(installed, hermes, prior, selected, reference, baseline, snapshot,
                     stop=stop, start=start, mount=mount, renew=renew, verify=verify)
        events.clear()
        original = os.replace
        def during_swap(source, destination):
            result = original(source, destination)
            if case == 'late_refusal' and Path(source) == installed and Path(destination) == snapshot / 'restored-selected':
                (hermes / 'config.yaml').write_text('Synthetic edit after post-stop validation')
            return result
        try:
            with patch('lifeos_hook_bridge.update_transaction.os.replace', side_effect=during_swap):
                restore_update(snapshot, stop=stop, start=start, verify=lambda: events.append('verify'))
        except Exception as error:
            output = {'case':case, 'error':str(error), 'errno':getattr(error,'errno',None),
                      'restore_events':list(events), 'manifest_state':json.loads((snapshot/'manifest.json').read_text())['state'],
                      'installed_hook':(installed/'hooks/owned.ts').read_text(),
                      'profile_config':(hermes/'config.yaml').read_text(),
                      'profile_dev':hermes.stat().st_dev, 'snapshot_dev':snapshot.stat().st_dev,
                      'archived_configs':[p.read_text() for p in snapshot.glob('mount-before-restore/*/config.yaml')]}
            events.clear()
            try:
                recover_update(snapshot, stop=stop, start=start, verify=lambda:events.append('verify'))
                output['recover']='passed'
            except Exception as recovery_error:
                output['recover']=str(recovery_error)
            output['recovery_events']=events
            output['archived_configs_after_recovery']=[p.read_text() for p in snapshot.glob('mount-before-restore/*/config.yaml')]
            print(json.dumps(output, sort_keys=True))
        else:
            raise AssertionError('The probe did not reach its expected failure')
for case in ('late_refusal','cross_filesystem'):
    run(case)
