# ABOUTME: Certifies synthetic installation and update prereleases against exact completed evidence.
# ABOUTME: Excludes production qualification and preserves each certificate as an immutable checkpoint.
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

from qualification_artifacts import archive_files, file_map_digest, version_derivative

OUT = Path(__file__).resolve().parent
CACHE = Path('/home/outsider/.cache/lifeos-ui-install-20261013/packages')
FIRST = '914ad24b0eea7f0022e75edc815f5be08566d0f9'
SECOND = '6a0a241a0b1227d440938aa7156d8d59b87e5740'
FRONT = Path('/home/outsider/.cache/lifeos-hermes-managed-20261012/frontend-profile/hermes-dashboard.tgz')
FRONT_SHA = 'e7c93e754de99b6ec66ae17ae313377dc513104da2776a099c391a7aab347bec'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name):
    return json.loads((OUT / name).read_bytes())


def identity(build):
    return {'version': build['version'], 'commit': build['head'], 'package_sha256': build['archive_sha256']}


def applied(name, build):
    value = load(name)
    assert value['operation']['state'] == 'applied'
    assert value['active_release'] == identity(build)
    assert value['model_configuration_preserved'] and value['prior_tier_settings_preserved']
    assert value['memory_ownership_configuration_present'] is False
    assert value['services']['hermes-dashboard.service']['ActiveState'] == 'active'
    for unit in ('hermes-gateway.service', 'com.lifeos.pulse.service'):
        assert value['services'][unit]['LoadState'] == 'loaded'
        assert value['services'][unit]['ActiveState'] == 'inactive'
    assert not value.get('failure')
    return value


def certify(version):
    first = load('baseline-preserved-candidate-build.json')
    second = load('corrected-numeric-update-candidate-build.json')
    assert first['head'] == FIRST and first['version'] == '0.4.2-rc.1'
    assert second['head'] == SECOND and second['version'] == '0.4.2-rc.2'
    for build in (first, second):
        assert digest(build['archive']) == build['archive_sha256']
        assert Path(build['archive']).stat().st_size == build['archive_bytes']
    full = load('integration-archive-bound-914ad24b.json')
    assert full['package_commit'] == FIRST and full['exit_code'] == 0
    assert full['archive_sha256'] == first['archive_sha256'] and full['archive_bytes'] == first['archive_bytes']
    expected_files = archive_files(first['archive'])
    assert full['archive_regular_files'] == len(expected_files)
    assert full['archive_file_map_sha256'] == file_map_digest(expected_files)
    assert full['archive_files_match_before'] is True and full['archive_files_match_after'] is True
    output = (OUT / 'integration-archive-bound-914ad24b.stderr').read_text()
    assert 'Ran 661 tests' in output and output.rstrip().endswith('OK')
    assert ' ... skipped' not in output and 'ResourceWarning' not in output
    native = load('native-sealed-914ad24b.json')
    assert native['package_commit'] == FIRST and native['archive_sha256'] == first['archive_sha256']
    assert native['exit_code'] == 0 and native['archived_source_files_unchanged'] is True
    assert native['bun_version'] == '1.4.3'
    assert '38 files, 716 tests passed, 0 failed' in (OUT / 'native-sealed-914ad24b.stdout').read_text()
    assert not (OUT / 'native-sealed-914ad24b.stderr').read_bytes()
    assert digest(FRONT) == FRONT_SHA
    with tarfile.open(first['archive']) as archive:
        source = archive.extractfile('hermes/hermes-source-manifest.json').read()
        assert hashlib.sha256(source).hexdigest() == native['source_manifest_sha256']
        assert json.loads(source)['tree_sha256'] == native['source_tree_sha256']
    interruption = load('baseline-preserved-fresh-interruption.json')['interruption']
    fresh = applied('baseline-preserved-fresh-recovery.json', first)
    assert interruption['phase'] == 'programs-published' and interruption['exit_code'] == 73
    assert interruption['commit'] == FIRST and interruption['identifier'] == fresh['operation']['identifier']
    assert fresh['program_targets'] == 11 and fresh['need_daemon_reload'] == 'no'
    assert fresh['later_synthetic_sha256'] == 'd4cd62d6595033de4e952672dc025be2e9cd599a015106ca3e40d82e9880405d'
    admission = load('baseline-preserved-recovery-admission.json')
    assert admission['recovery_command_status'] == 0 and admission['interruption'] == interruption
    update = applied('baseline-preserved-private-update.json', first)
    assert update['operation']['identifier'] == '2309a88382d7496092e6dcc9ce6ba842'
    receipts = ['integration-archive-bound-914ad24b.json', 'integration-archive-bound-914ad24b.stderr',
        'native-sealed-914ad24b.json', 'native-sealed-914ad24b.stdout', 'native-sealed-914ad24b.stderr',
        'baseline-preserved-fresh-interruption.json', 'baseline-preserved-fresh-recovery.json',
        'baseline-preserved-recovery-admission.json', 'baseline-preserved-private-update.json']
    build = first
    if version == '0.4.2-rc.2':
        build = second
        delta = load('corrected-numeric-update-version-delta.json')
        assert delta['status'] == 'PASS' and delta['commits'] == [FIRST, SECOND]
        assert delta['archives'] == [first['archive_sha256'], second['archive_sha256']]
        assert delta['native_source_manifests_identical'] and delta['all_other_non_git_archive_files_identical']
        expected = ['CHANGELOG.md', 'DAILY-CANDIDATE.json', 'VERSION',
            'lifeos_hook_bridge/dashboard/manifest.json', 'lifeos_hook_bridge/plugin.yaml',
            'optional/lifeos_release_manager/dashboard/manifest.json', 'optional/lifeos_release_manager/plugin.yaml']
        assert delta['changed_program_files'] == expected
        version_derivative(first['archive'], second['archive'], FIRST, SECOND)
        numeric = applied('corrected-numeric-private-update.json', second)
        assert numeric['operation']['identifier'] == '1abaa47a92804c99a532dbe765a37a99'
        receipts += ['corrected-numeric-update-version-delta.json', 'corrected-numeric-private-update.json']
    certificate = {'format': 1, 'status': 'QUALIFIED', 'production_qualified': False,
        'test_fixture_only': False, 'qualification_scope': 'synthetic-managed-dashboard-installation-and-complete-package-update',
        'version': version, 'program_commit': build['head'], 'archive_sha256': build['archive_sha256'],
        'archive_bytes': build['archive_bytes'], 'hermes_dashboard_sha256': FRONT_SHA,
        **{key: build[key] for key in ('hermes_base', 'lifeos_base', 'hermes_patch_count', 'lifeos_patch_count')},
        'integration_tests': 661, 'integration_test_program_commit': FIRST,
        'native_tests': 716, 'native_test_program_commit': FIRST,
        'native_source_manifest_sha256': native['source_manifest_sha256'],
        'native_source_tree_sha256': native['source_tree_sha256'],
        'bun_version': native['bun_version'], 'bun_binary_sha256': native['bun_binary_sha256'],
        'fresh_interruption_recovery_verified': True, 'installed_synthetic_update_verified': True,
        'version_only_derivative': version == '0.4.2-rc.2',
        'whole_guest_recovery_verified': False, 'memory_ownership_activation_verified': False,
        'daily_deployment_verified': False, 'public_user_action_acceptance': 'PENDING',
        'qualification_receipt_sha256': {name: digest(OUT / name) for name in receipts}}
    destination = OUT / ('test-release-' + version)
    destination.mkdir(exist_ok=True)
    with (destination / 'RELEASE-CERTIFICATE.json').open('x') as stream:
        stream.write(json.dumps(certificate, indent=2) + '\n')
    print(json.dumps({'version': version, 'program_commit': build['head'],
        'certificate_sha256': digest(destination / 'RELEASE-CERTIFICATE.json'), 'production_qualified': False}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('version', choices=('0.4.2-rc.1', '0.4.2-rc.2'))
    certify(parser.parse_args().version)
