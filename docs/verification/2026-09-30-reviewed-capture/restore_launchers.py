# ABOUTME: Restores managed interpreter paths in review-modified ignored launchers.
# ABOUTME: Preserves each launcher before an exact, validated path replacement.

import json
from pathlib import Path

home = Path.home()
old = '/tmp/independent-host-effects-7a1ur1h_/hermes/tools/python-3.14.7+20260901-linux-x64/bin/python3'
correct = str(home / '.hermes/tools/python-3.14.7+20260901-linux-x64/bin/python3')
assert Path(correct).is_file(), 'Managed interpreter is missing'
results = []
for name in ('hermes', 'hermes-acp'):
    path = home / 'workspace/hermes-agent/.hermes/bin' / name
    text = path.read_text()
    assert text.count(old) == 1, 'Unexpected launcher interpreter reference'
    backup = path.with_name(name + '.before-review-interpreter-20260930')
    assert not backup.exists(), 'Backup already exists'
    backup.write_bytes(path.read_bytes())
    backup.chmod(0o600)
    temporary = path.with_name(name + '.review-restore.tmp')
    temporary.write_text(text.replace(old, correct))
    temporary.chmod(path.stat().st_mode & 0o777)
    temporary.replace(path)
    results.append({'launcher': str(path), 'backup': str(backup), 'interpreter_exists': True})
print(json.dumps({'restored': results}))
