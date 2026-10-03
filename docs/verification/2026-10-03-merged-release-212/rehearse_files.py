# ABOUTME: Rehearses the release file plan on disposable copies of actual installed code.
# ABOUTME: Checks byte restoration and preservation of current data without touching services.
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

release = Path(sys.argv[1])
plan = json.loads((release / 'preflight.json').read_text())
tree = ast.parse((release / 'deploy_release.py').read_text())
functions = ast.Module(body=[node for node in tree.body if isinstance(node, ast.FunctionDef)], type_ignores=[])
with tempfile.TemporaryDirectory(prefix='file-rehearsal-', dir=release) as directory:
    root = Path(directory)
    profile = root / 'profile'
    backup = root / 'snapshot'
    profile.mkdir()
    (profile / 'plugins').mkdir()
    backup.mkdir()
    (backup / 'profile-before/plugins').mkdir(parents=True)
    baseline = root / 'baseline.json'
    baseline.write_text('{"fixture": "prior"}\n')
    shutil.copy2(baseline, backup / 'baseline-before.json')
    marker = profile / 'current-user-data.txt'
    marker.write_text('Current data must survive a code rollback.\n')
    digest = hashlib.sha256(marker.read_bytes()).hexdigest()
    entries = []
    for index, item in enumerate(plan['code']):
        target = root / 'code' / item['component'] / item['relative']
        target.parent.mkdir(parents=True, exist_ok=True)
        if item['before'] is not None:
            shutil.copy2(item['target'], target)
            shutil.copy2(target, backup / f'code-{index}')
        entries.append({**item, 'target': str(target)})
    recorder = None
    if plan['recorder']:
        configuration = root / 'recorder-config.json'
        configuration.write_text('{"enabled": true}\n')
        shutil.copy2(configuration, backup / 'recorder-config-before.json')
        recorder = {'configuration': str(configuration)}
    namespace = dict(globals(), RELEASE=root, BACKUP=backup, PROFILE=profile,
                     BASELINE=baseline, OPERATING_HOME=root, ENV=dict(os.environ))
    exec(compile(functions, 'release-functions', 'exec'), namespace)
    for item in entries:
        namespace['copy_code'](item)
        assert namespace['sha'](item['target']) == item['after']
    baseline.write_text('{"fixture": "after"}\n')
    (profile / 'plugins/.install-metadata.json').write_text('{"fixture": "after"}\n')
    namespace['restore_code']({'code': entries, 'recorder': recorder})
    for item in entries:
        target = Path(item['target'])
        if item['before'] is None:
            assert not target.exists()
        else:
            assert namespace['sha'](target) == item['before']
    assert baseline.read_text() == '{"fixture": "prior"}\n'
    assert not (profile / 'plugins/.install-metadata.json').exists()
    assert hashlib.sha256(marker.read_bytes()).hexdigest() == digest
    print(json.dumps({'target': plan['target'], 'real_code_files': len(entries),
                      'apply_bytes_verified': True, 'rollback_bytes_verified': True,
                      'current_data_preserved': True, 'service_calls': 0}))
