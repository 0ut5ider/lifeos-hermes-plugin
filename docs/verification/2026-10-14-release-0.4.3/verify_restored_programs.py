# ABOUTME: Checks the exact selected synthetic program targets in a disconnected restored guest.
# ABOUTME: Verifies private configuration bytes without exporting their values.
import json
import os
from pathlib import Path
import sys

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
source = Path('/home/lifeos-hermes/releases/0.4.3-a1abb579')
sys.path.insert(0, str(source))
from optional.lifeos_release_manager.release_operation import validate_plan
from optional.lifeos_release_manager.release_programs import fingerprint

profile = Path('/home/lifeos-hermes/.hermes')
job = profile / '.lifeos-releases' / sys.argv[1]
request = json.loads((job / 'request.json').read_bytes())
assert request['version'] == '0.4.3'
assert request['commit'] == 'a1abb579558edcf29f7cd04ecfd998995d48db54'
assert request['package_sha256'] == '1c7de7abc4014bfee83bc9bdcd4bfdb6c169526844d44491741d56645f400177'
assert json.loads((job / 'status.json').read_bytes())['state'] == 'applied'
plan = validate_plan(job, request)
assert not plan['native_mount_required']
programs = json.loads((job / 'program-snapshot/programs.json').read_bytes())
assert programs['state'] == 'applied'
for row in programs['entries']:
    path = Path(row['target'])
    assert fingerprint(path, allow_links=row['allow_links']) == row['after'], row['target']
units = Path('/home/lifeos-hermes/.config/systemd/user')
for name in ('hermes-dashboard.service', 'hermes-gateway.service', 'com.lifeos.pulse.service'):
    assert (units / name).is_symlink() and os.readlink(units / name) == '/dev/null'
    assert (units / (name + '.before-restore')).is_file()
receipt = json.loads((profile / 'integration-release.json').read_bytes())
assert all(receipt[key] == request[key] for key in ('version', 'commit', 'package_sha256'))
print(json.dumps({'status': 'PASS', 'operation': job.name, 'version': request['version'],
    'program_commit': request['commit'], 'archive_sha256': request['package_sha256'],
    'program_targets': len(programs['entries']), 'application_services_masked': True,
    'private_configuration_exported': False}, indent=2))
