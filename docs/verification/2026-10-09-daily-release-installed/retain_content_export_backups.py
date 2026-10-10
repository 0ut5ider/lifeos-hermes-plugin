# ABOUTME: Retains prior Content exports outside the selected native source tree.
# ABOUTME: Checks exact export hashes before and after relocating only the acceptance backups.
import hashlib
import json
import os
from pathlib import Path

stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
os.umask(0o077)
selection = json.loads((stage / 'installed-content-response-selection.json').read_text())
def digest(directory):
    result = hashlib.sha256()
    for path in sorted(directory.rglob('*')):
        if path.is_file():
            assert not path.is_symlink()
            result.update(path.relative_to(directory).as_posix().encode() + b'\0'
                + hashlib.sha256(path.read_bytes()).hexdigest().encode() + b'\n')
    return result.hexdigest()
rows = []
for index, name in enumerate(selection['exports']):
    selected = Path(name)
    previous = selected.with_name('out.before-content-responses')
    retained = stage / 'content-response-retained' / ('export-' + str(index) + '.before')
    assert digest(selected) == selection['after_export_sha256']
    assert previous.is_dir() and not retained.exists()
    assert digest(previous) == selection['before_export_sha256']
    assert previous.stat().st_dev == retained.parent.stat().st_dev
    os.rename(previous, retained)
    assert digest(retained) == selection['before_export_sha256']
    assert digest(selected) == selection['after_export_sha256']
    rows.append({'selected': name, 'retained': str(retained)})
report = {'status': 'PASS', 'exports': rows, 'selected_bytes_unchanged': True,
    'retained_bytes_unchanged': True, 'live_profile_changed': False}
(stage / 'installed-content-export-retention.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
