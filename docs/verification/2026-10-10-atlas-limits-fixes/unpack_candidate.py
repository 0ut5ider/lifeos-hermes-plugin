# ABOUTME: Checks candidate archive bytes before extraction into a separate acceptance stage.
# ABOUTME: Sets the existing test account ownership without changing live configuration.
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tarfile

tag, expected = sys.argv[1:]
assert re.fullmatch(r'[0-9a-f]{8}', tag)
assert re.fullmatch(r'[0-9a-f]{64}', expected)
parent = Path('/home/lifeos-hermes/migration/2026-10-09')
archive = parent / ('daily-text-0.2.0-' + tag + '.tgz')
stage = parent / ('daily-text-0.2.0-' + tag)
digest = hashlib.sha256()
with archive.open('rb') as stream:
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(chunk)
assert digest.hexdigest() == expected
assert not stage.exists()
os.umask(0o077)
package = stage / 'package'
package.mkdir(parents=True, mode=0o700)
with tarfile.open(archive, 'r:gz') as source:
    source.extractall(package, filter='data')
for path in [stage, *stage.rglob('*')]:
    os.chown(path, 1008, 1008, follow_symlinks=False)
report = {'status': 'PASS', 'archive_sha256': expected, 'stage': str(stage),
    'separate_candidate_only': True, 'live_configuration_changed': False}
(stage / 'archive-verification.json').write_text(json.dumps(report, indent=2) + '\n')
os.chown(stage / 'archive-verification.json', 1008, 1008)
print(json.dumps(report, indent=2))
