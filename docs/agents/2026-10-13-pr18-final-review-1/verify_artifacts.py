# ABOUTME: Verifies the public acceptance evidence and exact published prerelease program identities.
# ABOUTME: Extracts only fresh task-owned sources and records immutable archive and certificate hashes.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
OUT = Path(__file__).resolve().parent
EVIDENCE = ROOT / 'docs/verification/2026-10-13-release-ui-install'
sys.path.insert(0, str(EVIDENCE))
from qualification_artifacts import archive_files, file_map_digest, package_matches, version_derivative
from optional.lifeos_release_manager.release_catalog import extract_package
from optional.lifeos_release_manager.release_stage import validate_package


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    report = {}
    acceptance = json.loads((EVIDENCE / 'PUBLIC-USER-ACTION-ACCEPTANCE.json').read_bytes())
    report['acceptance_hash_matches'] = {name: sha(EVIDENCE / name) == digest
        for name, digest in acceptance['evidence_sha256'].items()}
    assert all(report['acceptance_hash_matches'].values())
    report['production_qualified'] = acceptance['production_qualified']
    report['default_branch_web_bootstrap'] = acceptance['default_branch_web_bootstrap']
    report['acceptance_cases'] = acceptance['cases']
    first = json.loads((EVIDENCE / 'baseline-preserved-candidate-build.json').read_bytes())
    second = json.loads((EVIDENCE / 'corrected-numeric-update-candidate-build.json').read_bytes())
    report['archives'] = {}
    for build in (first, second):
        archive = Path(build['archive'])
        assert sha(archive) == build['archive_sha256']
        assert archive.stat().st_size == build['archive_bytes']
        certificate_path = EVIDENCE / ('test-release-' + build['version']) / 'RELEASE-CERTIFICATE.json'
        certificate = json.loads(certificate_path.read_bytes())
        assert certificate['archive_sha256'] == build['archive_sha256']
        assert certificate['program_commit'] == build['head']
        assert certificate['production_qualified'] is False
        receipt_matches = {name: sha(EVIDENCE / name) == digest
            for name, digest in certificate['qualification_receipt_sha256'].items()}
        assert all(receipt_matches.values())
        report['archives'][build['version']] = {'sha256': sha(archive), 'bytes': archive.stat().st_size,
            'certificate_sha256': sha(certificate_path), 'receipt_hash_matches': receipt_matches,
            'public_user_action_acceptance': certificate['public_user_action_acceptance']}
    report['version_derivative'] = version_derivative(first['archive'], second['archive'], first['head'], second['head'])
    expected = archive_files(first['archive'])
    receipt = json.loads((EVIDENCE / 'integration-archive-bound-914ad24b.json').read_bytes())
    report['first_archive_regular_files'] = len(expected)
    report['first_archive_file_map_sha256'] = file_map_digest(expected)
    assert report['first_archive_regular_files'] == receipt['archive_regular_files']
    assert report['first_archive_file_map_sha256'] == receipt['archive_file_map_sha256']
    report['recorded_integration_summary'] = (EVIDENCE / 'integration-archive-bound-914ad24b.stderr').read_text().splitlines()[-4:]
    report['recorded_native_summary'] = (EVIDENCE / 'native-sealed-914ad24b.stdout').read_text().splitlines()[-6:]
    workspace = Path(tempfile.mkdtemp(prefix='sealed-review-', dir=OUT))
    package = workspace / 'package'
    extract_package(first['archive'], package)
    (workspace / 'download').mkdir(mode=0o700)
    os.link(first['archive'], workspace / 'download' / Path(first['archive']).name)
    certificate = json.loads((EVIDENCE / 'test-release-0.4.2-rc.1/RELEASE-CERTIFICATE.json').read_bytes())
    manifest = validate_package(package, certificate)
    report['fresh_extraction'] = str(package)
    report['fresh_package_validate_version'] = manifest['version']
    report['fresh_package_matches_before'] = package_matches(package, expected)
    bound_build = workspace / 'build.json'
    bound_build.write_text(json.dumps(dict(first, package=str(package))) + '\n')
    command = [sys.executable, '-B', '-W', 'error::ResourceWarning', '-m', 'unittest', '-v',
        'test_release_operation.ReleaseOperationTests.test_fresh_recovery_keeps_one_lease_namespace_after_bridge_publication',
        'test_qualification_artifacts']
    environment = dict(os.environ, LIFEOS_QUALIFICATION_BUILD=str(bound_build),
        PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(ROOT)+':'+str(ROOT/'tests')+':'+str(EVIDENCE)+':/home/outsider/.cache/lifeos-hermes-managed-20261012/upstream')
    started = time.monotonic()
    with (OUT / 'artifact-tests.stdout').open('w') as stdout, (OUT / 'artifact-tests.stderr').open('w') as stderr:
        result = subprocess.run(command, cwd=ROOT, env=environment, stdout=stdout, stderr=stderr, timeout=300)
    report['artifact_test_command'] = command
    report['artifact_test_exit_code'] = result.returncode
    report['artifact_test_seconds'] = time.monotonic() - started
    report['fresh_package_matches_after'] = package_matches(package, expected)
    (OUT / 'artifact-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    assert result.returncode == 0
    print(json.dumps({key: value for key, value in report.items() if key != 'acceptance_cases'}, indent=2))


if __name__ == '__main__':
    main()
