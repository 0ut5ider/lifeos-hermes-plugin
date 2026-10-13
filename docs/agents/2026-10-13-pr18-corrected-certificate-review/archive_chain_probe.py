# ABOUTME: Independently binds corrected qualification receipts to actual immutable archives and prior native source.
# ABOUTME: Reads archives without extraction and writes only compact review results.
import hashlib
import json
from pathlib import Path
import sys
import tarfile

ROOT = Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
OUT = Path(__file__).resolve().parent
OLD = ROOT / 'docs/verification/2026-10-13-release-ui-install'
sys.path.insert(0, str(OLD))
from qualification_artifacts import archive_files, file_map_digest


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


first = json.loads((OLD / 'baseline-preserved-candidate-build.json').read_bytes())
new = json.loads((OUT / 'private-stage-candidate-build.json').read_bytes())
prior = json.loads((OLD / 'native-sealed-914ad24b.json').read_bytes())
equality = json.loads((OUT / 'private-stage-native-equality.json').read_bytes())
full = json.loads((OUT / 'integration-archive-bound-10459df6.json').read_bytes())
for build in (first, new):
    assert sha(build['archive']) == build['archive_sha256']
    assert Path(build['archive']).stat().st_size == build['archive_bytes']
a, b = archive_files(first['archive']), archive_files(new['archive'])
selected = lambda files: {name: value for name, value in files.items()
    if name.startswith(('hermes/', 'lifeos/', 'python-runtime/')) and '/.git/' not in name}
assert selected(a) == selected(b)
assert file_map_digest(selected(b)) == equality['file_map_sha256']
assert len(selected(b)) == equality['native_and_python_runtime_files']
assert full['archive_file_map_sha256'] == file_map_digest(b)
assert full['archive_regular_files'] == len(b)
assert full['package_commit'] == new['head'] and full['archive_sha256'] == new['archive_sha256']
assert full['exit_code'] == 0 and full['archive_files_match_before'] and full['archive_files_match_after']
summary = (OUT / 'integration-archive-bound-10459df6.stderr').read_text()
assert 'Ran 674 tests' in summary and summary.rstrip().endswith('OK')
assert ' ... skipped' not in summary and 'ResourceWarning' not in summary
source_identities = {}
for build in (first, new):
    with tarfile.open(build['archive']) as archive:
        content = archive.extractfile('hermes/hermes-source-manifest.json').read()
    identity = {'manifest_sha256': hashlib.sha256(content).hexdigest(), 'tree_sha256': json.loads(content)['tree_sha256']}
    assert identity['manifest_sha256'] == prior['source_manifest_sha256']
    assert identity['tree_sha256'] == prior['source_tree_sha256']
    source_identities[build['head']] = identity
assert prior['package_commit'] == first['head'] and prior['archive_sha256'] == first['archive_sha256']
assert prior['exit_code'] == 0 and prior['archived_source_files_unchanged'] is True
assert sha(OLD / 'native-sealed-914ad24b.json') == equality['native_receipt_sha256']
assert '38 files, 716 tests passed, 0 failed' in (OLD / 'native-sealed-914ad24b.stdout').read_text()
assert not (OLD / 'native-sealed-914ad24b.stderr').read_bytes()
report = {'new_archive_sha256': new['archive_sha256'], 'new_archive_bytes': new['archive_bytes'],
    'new_archive_regular_files': len(b), 'new_archive_file_map_sha256': file_map_digest(b),
    'native_and_python_runtime_files_equal': len(selected(b)), 'selected_file_map_sha256': file_map_digest(selected(b)),
    'prior_native_source_bindings': source_identities, 'recorded_integration_gate': '674 pass, no skips, exit 0',
    'recorded_native_gate': '716 pass across 38 files, reused from byte-identical native inputs',
    'new_archive_extracted': False, 'certificate_issued': False}
(OUT / 'archive-chain-probe.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
