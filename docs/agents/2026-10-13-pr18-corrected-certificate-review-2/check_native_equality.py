# ABOUTME: Binds retained native test results to unchanged native files in the corrected archive.
# ABOUTME: Separates reused native evidence from the new complete integration test execution.
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '2026-10-13-release-ui-install'))
from qualification_artifacts import archive_files, file_map_digest
out = Path(__file__).resolve().parent
old_out = out.parent / '2026-10-13-release-ui-install'
first = json.loads((old_out / 'baseline-preserved-candidate-build.json').read_text())
new = json.loads((out / 'reviewed-candidate-build.json').read_text())
for build in (first, new):
    path = Path(build['archive'])
    assert path.stat().st_size == build['archive_bytes']
    with path.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == build['archive_sha256']
a, b = archive_files(first['archive']), archive_files(new['archive'])
selected = lambda files: {name: value for name, value in files.items()
    if name.startswith(('hermes/', 'lifeos/', 'python-runtime/')) and '/.git/' not in name}
assert selected(a) == selected(b)
native = json.loads((old_out / 'native-sealed-914ad24b.json').read_text())
assert native['package_commit'] == first['head'] and native['archive_sha256'] == first['archive_sha256']
assert native['exit_code'] == 0 and native['archived_source_files_unchanged']
assert '38 files, 716 tests passed, 0 failed' in (old_out / 'native-sealed-914ad24b.stdout').read_text()
assert not (old_out / 'native-sealed-914ad24b.stderr').read_bytes()
report = {'status': 'PASS', 'old_commit': first['head'], 'new_commit': new['head'],
    'old_archive_sha256': first['archive_sha256'], 'new_archive_sha256': new['archive_sha256'],
    'native_and_python_runtime_files': len(selected(b)), 'file_map_sha256': file_map_digest(selected(b)),
    'all_native_non_git_files_identical': True, 'reused_official_native_tests': 716,
    'native_test_commit': native['package_commit'], 'new_native_tests_claimed': False,
    'native_receipt_sha256': hashlib.sha256((old_out / 'native-sealed-914ad24b.json').read_bytes()).hexdigest()}
(out / 'native-equality.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
