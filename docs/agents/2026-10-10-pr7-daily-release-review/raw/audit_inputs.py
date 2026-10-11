# ABOUTME: Independently checks exact review bytes and retained release evidence.
# ABOUTME: Replays personal template emptying in a private temporary tree.
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
import tempfile

from lifeos_hook_bridge.fresh_store import _empty_personal_templates, PERSONAL_DIRECTORIES, EXAMPLE_DIRECTORIES
from lifeos_hook_bridge.memory_access import MemoryUnavailable

root = Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
out = Path(__file__).parent
evidence = root / 'docs/verification/2026-10-10-daily-text-release'
package = Path('/home/outsider/.cache/lifeos-atlas-20261010/daily-text-0.2.0-11577ed4')
source = package / 'lifeos/LifeOS/install/USER'
digest = lambda data: hashlib.sha256(data).hexdigest()
load = lambda name: json.loads((evidence / name).read_text())
record = {}
hashes = load('combined-final.json')['source_hashes']
for relative, expected in hashes.items():
    assert digest((root / relative).read_bytes()) == expected, relative
record['review_head_plugin_files_equal_tested_package'] = len(hashes)
manifest = json.loads((package / 'DAILY-CANDIDATE.json').read_text())
assert manifest['head'] == '11577ed4873a0b6186a1dfa13aa44f893254cb99'
record['immutable_manifest'] = {'head': manifest['head'], 'plugin_files': len(manifest['plugin_files'])}
record['post_candidate_non_documentation_diff'] = subprocess.check_output([
    'git', 'diff', '--name-only', manifest['head'], '4034bc27796433f71c6ba2ec061d1e7e8e135b8f',
    '--', 'lifeos_hook_bridge', 'tests', 'VERSION', 'plugin.json', 'pyproject.toml',
], cwd=root, text=True)
assert not record['post_candidate_non_documentation_diff']
certificate = load('DAILY-RELEASE.json')
assert certificate == json.loads((out / 'regenerated-certificate.json').read_text())
record['certificate_exactly_reproduced'] = True
archive = Path(certificate['archives']['programs']['path'])
archived = {}
pulse_frontend = []
with tarfile.open(archive) as bundle:
    for member in bundle:
        if not member.isfile():
            continue
        relative = member.name.removeprefix('./')
        if relative in hashes:
            archived[relative] = digest(bundle.extractfile(member).read())
        if '/PULSE/' in relative and '/out/' in relative and relative.endswith('.html'):
            pulse_frontend.append(relative)
assert archived == hashes
assert pulse_frontend
record['archive_plugin_files_match_review_head'] = len(archived)
record['archive_pulse_html_pages'] = pulse_frontend
record['live_baseline_exact_match'] = load('live-before.json') == load('live-after.json')
assert record['live_baseline_exact_match']
recover = load('installed-profile-recovery.json')
assert recover['history_before'] == recover['history_recovered'] == {'sessions': 6, 'messages': 28}
assert recover['candidate_ownership_disabled'] and not recover['candidate_services_started']
assert not recover['offserver_restore_verified']
record['recovery_scope'] = {key: recover[key] for key in (
    'reference', 'history_before', 'history_recovered', 'candidate_ownership_disabled',
    'candidate_services_started', 'offserver_restore_verified',
)}
with tempfile.TemporaryDirectory(prefix='pr7-personal-replay-') as directory:
    destination = Path(directory)
    user = destination / 'home/USER'
    shutil.copytree(source, user)
    before = {str(path.relative_to(user)): path.read_bytes() for path in user.rglob('*') if path.is_file()}
    emptied, omitted = _empty_personal_templates(user, destination)
    for relative in emptied + omitted:
        retained = destination / 'template-originals' / relative
        assert retained.read_bytes() == before[relative]
        assert retained.stat().st_mode & 0o077 == 0
    assert destination.stat().st_mode & 0o077 == 0
    record['retained_directory_modes'] = {
        str(path.relative_to(destination)): oct(path.stat().st_mode & 0o777)
        for path in (destination / 'template-originals').rglob('*') if path.is_dir()
    }
    for relative in emptied:
        path = user / relative
        text = path.read_text()
        if path.suffix == '.md':
            front = re.match(r'\A---\n(.*?)\n---\n', text, re.S)
            assert front and 'provenance: template' in front[1]
            assert all(not line or re.match(r'^#{1,6} ', line) for line in text[front.end():].splitlines())
            assert not re.search('sample|placeholder', text, re.I)
        else:
            assert text == f'{path.stem}: []\n'
    for directory in EXAMPLE_DIRECTORIES:
        assert not (user / directory).exists()
    for relative, original in before.items():
        if relative not in emptied + omitted:
            assert (user / relative).read_bytes() == original
        assert (source / relative).read_bytes() == original
    (out / 'replayed-personal-headings.json').write_text(json.dumps({
        relative: (user / relative).read_text() for relative in emptied
    }, indent=2) + '\n')
    record['personal_replay'] = {'emptied_count': len(emptied), 'omitted_count': len(omitted),
        'exact_private_originals': True, 'only_headings_and_metadata_remain': True,
        'all_other_template_files_unchanged': True, 'pinned_source_unchanged': True}
for case in ('missing-provenance', 'symlink-leaf', 'missing-finance-template-marker'):
    with tempfile.TemporaryDirectory(prefix='pr7-personal-refusal-') as directory:
        destination = Path(directory)
        user = destination / 'home/USER'
        shutil.copytree(source, user)
        path = user / 'FINANCES/ACCOUNTS.md'
        if case == 'missing-provenance':
            path.write_text(path.read_text().replace('provenance: template', 'provenance: owner'))
        elif case == 'symlink-leaf':
            path.unlink()
            path.symlink_to(source / 'FINANCES/ACCOUNTS.md')
        else:
            path = user / 'FINANCES/vendors.yaml'
            path.write_text('vendors: []\n')
        try:
            _empty_personal_templates(user, destination)
        except MemoryUnavailable as error:
            record[case] = {'refused': True, 'reason': str(error)}
        else:
            raise AssertionError(case)
        if case == 'symlink-leaf':
            assert path.is_symlink()
(out / 'input-audit.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
