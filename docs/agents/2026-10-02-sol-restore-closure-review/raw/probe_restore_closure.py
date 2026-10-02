# ABOUTME: Checks target filesystem archives and recovery after actual process death.
# ABOUTME: Uses disposable synthetic data and scoped rename boundary instrumentation.
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
from unittest.mock import patch
from test_update_transaction import UpdateTransactionTests
from lifeos_hook_bridge.update_transaction import apply_update, restore_update, recover_update

CHILD = '''import os, signal, sys
from pathlib import Path
from unittest.mock import patch
from lifeos_hook_bridge.update_transaction import restore_update, recover_update
snapshot, profile, baseline = map(Path, sys.argv[1:4])
action, boundary = sys.argv[4:]
original = os.replace
def interrupted(source, destination):
    original(source, destination)
    source, destination = Path(source), Path(destination)
    hit = (boundary == 'index' and destination.name == 'archive-manifest.json' or
           boundary == 'config' and source == profile / 'config.yaml' or
           boundary == 'plugin' and source == profile / 'plugins/lifeos' or
           boundary == 'baseline' and source == baseline or
           boundary == 'published' and destination == baseline)
    if hit:
        os.kill(os.getpid(), signal.SIGKILL)
with patch('lifeos_hook_bridge.update_transaction.os.replace', side_effect=interrupted):
    (restore_update if action == 'restore' else recover_update)(snapshot, stop=lambda: None, start=lambda: None, verify=lambda: None)
'''

def indexes(snapshot):
    return [json.loads(p.read_text())['targets'] for p in sorted(snapshot.glob('mount-before-restore/*/archive-manifest.json'))]

def fixture(root, alternate, layout):
    test = UpdateTransactionTests()
    installed, profile, prior, selected, reference, baseline, snapshot = test.fixture(root)
    if layout in ('profile', 'both'):
        remote = alternate / 'profile'
        shutil.copytree(profile, remote)
        profile = remote
    if layout in ('baseline', 'both'):
        remote = alternate / 'state/baseline.json'
        remote.parent.mkdir()
        shutil.copy2(baseline, remote)
        baseline = remote
    (profile / '.env').write_text('SYNTHETIC_KEY=selected-private-value\n')
    (profile / '.env').chmod(0o600)
    (profile / 'plugins/lifeos').mkdir(parents=True)
    (profile / 'plugins/lifeos/guard.py').write_text('Synthetic selected guard')
    before = baseline.read_bytes()
    events, stop, start, mount, renew, verify = test.callbacks(profile, baseline)
    apply_update(installed, profile, prior, selected, reference, baseline, snapshot,
        stop=stop, start=start, mount=mount, renew=renew, verify=verify)
    return installed, profile, baseline, snapshot, before, events, stop, start

def check_final(installed, profile, baseline, snapshot, before):
    assert (installed / 'hooks/owned.ts').read_text() == 'owned-v1'
    assert (profile / 'config.yaml').read_text() == 'prior config'
    assert (profile / '.env').read_text() == 'SYNTHETIC_KEY=selected-private-value\n'
    assert (profile / '.env').stat().st_mode & 0o777 == 0o600
    assert (profile / 'plugins/lifeos/guard.py').read_text() == 'Synthetic selected guard'
    assert baseline.read_bytes() == before
    assert json.loads((snapshot / 'manifest.json').read_text())['state'] == 'rolled_back'
    for mapping in indexes(snapshot):
        for name, value in mapping.items():
            target = Path(value)
            if target.exists():
                parent = baseline.parent if name == 'baseline.json' else (profile / name).parent
                assert target.stat().st_dev == parent.stat().st_dev
                assert target.parent.stat().st_mode & 0o777 == 0o700

def kill(snapshot, profile, baseline, action, boundary):
    process = subprocess.run([sys.executable, '-c', CHILD, str(snapshot), str(profile), str(baseline), action, boundary],
        capture_output=True, text=True, timeout=30)
    assert process.returncode == -signal.SIGKILL, (process.returncode, process.stderr)
    assert process.stdout == process.stderr == ''
    assert json.loads((snapshot / 'manifest.json').read_text())['state'] == 'restoring'
    return process.returncode

for layout in ('profile', 'baseline', 'both'):
    with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory(dir='/dev/shm') as remote:
        installed, profile, baseline, snapshot, before, events, stop, start = fixture(Path(temp), Path(remote), layout)
        events.clear()
        original = os.replace
        def late_edit(source, destination):
            result = original(source, destination)
            if Path(source) == installed and Path(destination) == snapshot / 'restored-selected':
                (profile / 'config.yaml').write_text('Synthetic late edit retained')
            return result
        with patch('lifeos_hook_bridge.update_transaction.os.replace', side_effect=late_edit):
            restore_update(snapshot, stop=stop, start=start, verify=lambda: events.append('verify'))
        check_final(installed, profile, baseline, snapshot, before)
        assert any(Path(mapping['config.yaml']).read_text() == 'Synthetic late edit retained' for mapping in indexes(snapshot))
        assert events == ['stop', 'start', 'verify']
        print(json.dumps({'case': 'late_edit_' + layout, 'events': events, 'profile_dev': profile.stat().st_dev,
            'baseline_dev': baseline.stat().st_dev, 'snapshot_dev': snapshot.stat().st_dev, 'indexes': indexes(snapshot)}, sort_keys=True))

for boundary in ('index', 'config', 'plugin', 'baseline', 'published'):
    with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory(dir='/dev/shm') as remote:
        installed, profile, baseline, snapshot, before, events, stop, start = fixture(Path(temp), Path(remote), 'both')
        code = kill(snapshot, profile, baseline, 'restore', boundary)
        before_recovery = indexes(snapshot)
        retained = {value: (Path(value).read_bytes() if Path(value).is_file() else None)
                    for mapping in before_recovery for value in mapping.values() if Path(value).exists()}
        recover_update(snapshot, stop=stop, start=start, verify=lambda: None)
        check_final(installed, profile, baseline, snapshot, before)
        assert all(Path(value).exists() and (content is None or Path(value).read_bytes() == content) for value, content in retained.items())
        print(json.dumps({'case': 'kill_' + boundary, 'exit': code, 'indexes_before_recovery': before_recovery,
            'index_count_after_recovery': len(indexes(snapshot)), 'archive_count_retained': len(retained)}, sort_keys=True))

with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory(dir='/dev/shm') as remote:
    installed, profile, baseline, snapshot, before, events, stop, start = fixture(Path(temp), Path(remote), 'both')
    first = kill(snapshot, profile, baseline, 'restore', 'config')
    selected_archive = Path(indexes(snapshot)[0]['config.yaml'])
    assert selected_archive.read_text() == 'selected config'
    second = kill(snapshot, profile, baseline, 'recover', 'baseline')
    third = kill(snapshot, profile, baseline, 'recover', 'config')
    recover_update(snapshot, stop=stop, start=start, verify=lambda: None)
    check_final(installed, profile, baseline, snapshot, before)
    assert selected_archive.read_text() == 'selected config'
    print(json.dumps({'case': 'repeated_recovery_kills', 'exits': [first, second, third],
        'selected_archive_retained': True, 'index_count': len(indexes(snapshot))}, sort_keys=True))
