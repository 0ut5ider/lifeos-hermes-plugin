# ABOUTME: Certifies the corrected synthetic prerelease from completed archive and actual guest evidence.
# ABOUTME: Reuses only byte-identical native inputs and writes each new certificate once.
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '2026-10-13-release-ui-install'))
from qualification_artifacts import archive_files, file_map_digest
out = Path(__file__).resolve().parent
old = out.parent / '2026-10-13-release-ui-install'
load = lambda name: json.loads((out / name).read_text())
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
build = load('private-stage-candidate-build.json')
assert build['head'] == '10459df6c2b27bda8911dfd96a25b92bee769c93'
assert build['version'] == '0.4.2-rc.3'
assert Path(build['archive']).stat().st_size == build['archive_bytes']
assert sha(build['archive']) == build['archive_sha256']
full = load('integration-archive-bound-10459df6.json')
assert full['package_commit'] == build['head'] and full['exit_code'] == 0
assert full['archive_sha256'] == build['archive_sha256'] and full['archive_bytes'] == build['archive_bytes']
expected = archive_files(build['archive'])
assert full['archive_file_map_sha256'] == file_map_digest(expected)
assert full['archive_regular_files'] == len(expected)
assert full['archive_files_match_before'] and full['archive_files_match_after']
output = (out / 'integration-archive-bound-10459df6.stderr').read_text()
assert 'Ran 674 tests' in output and output.rstrip().endswith('OK')
assert ' ... skipped' not in output and 'ResourceWarning' not in output
native = load('private-stage-native-equality.json')
assert native['status'] == 'PASS' and native['new_commit'] == build['head']
assert native['new_archive_sha256'] == build['archive_sha256']
assert native['all_native_non_git_files_identical'] and native['reused_official_native_tests'] == 716
prior = json.loads((old / 'native-sealed-914ad24b.json').read_text())
assert sha(old / 'native-sealed-914ad24b.json') == native['native_receipt_sha256']
front = Path('/home/outsider/.cache/lifeos-hermes-managed-20261012/frontend-profile/hermes-dashboard.tgz')
assert sha(front) == 'e7c93e754de99b6ec66ae17ae313377dc513104da2776a099c391a7aab347bec'
interruption = load('private-stage-interruption-observation.json')['interruption']
assert interruption['phase'] == 'programs-published' and interruption['exit_code'] == 73
assert interruption['commit'] == build['head']
def applied(name):
    receipt = load(name)
    assert receipt['operation']['state'] == 'applied'
    assert receipt['active_release'] == {'version': build['version'], 'commit': build['head'], 'package_sha256': build['archive_sha256']}
    assert receipt['model_configuration_preserved'] and receipt['prior_tier_settings_preserved']
    assert receipt['memory_ownership_configuration_present'] is False
    assert receipt['services']['hermes-dashboard.service']['ActiveState'] == 'active'
    assert all(receipt['services'][unit]['ActiveState'] == 'inactive' for unit in ('hermes-gateway.service','com.lifeos.pulse.service'))
    assert receipt['later_synthetic_preserved'] and not receipt.get('failure')
    return receipt
fresh = applied('private-stage-fresh-recovery.json')
assert fresh['operation']['identifier'] == interruption['identifier']
update = applied('private-stage-installed-update.json')
assert update['operation']['identifier'] != fresh['operation']['identifier']
subprocess.run(['git', 'merge-base', '--is-ancestor', build['head'], 'origin/main'], check=True)
receipts = ['integration-archive-bound-10459df6.json','integration-archive-bound-10459df6.stderr',
    'private-stage-native-equality.json','private-stage-interruption-observation.json',
    'private-stage-recovery-admission.json','private-stage-fresh-recovery.json','private-stage-installed-update.json',
    'permissions-before.stderr','permissions-after.stderr','primary-native-metadata/native-metadata-probe.json']
certificate = {'format':1,'status':'QUALIFIED','production_qualified':False,'test_fixture_only':False,
    'qualification_scope':'synthetic-managed-dashboard-installation-and-complete-package-update',
    'version':build['version'],'program_commit':build['head'],'archive_sha256':build['archive_sha256'],
    'archive_bytes':build['archive_bytes'],'hermes_dashboard_sha256':sha(front),
    **{key:build[key] for key in ('hermes_base','lifeos_base','hermes_patch_count','lifeos_patch_count')},
    'integration_tests':674,'integration_test_program_commit':build['head'],
    'native_tests':716,'native_test_program_commit':prior['package_commit'],
    'native_source_manifest_sha256':prior['source_manifest_sha256'],'native_source_tree_sha256':prior['source_tree_sha256'],
    'native_inputs_byte_identical_verified':True,'native_equality_receipt_sha256':sha(out/'private-stage-native-equality.json'),
    'bun_version':prior['bun_version'],'bun_binary_sha256':prior['bun_binary_sha256'],
    'fresh_interruption_recovery_verified':True,'installed_synthetic_update_verified':True,
    'whole_guest_recovery_verified':False,'memory_ownership_activation_verified':False,
    'daily_deployment_verified':False,'public_user_action_acceptance':'PENDING',
    'qualification_receipt_sha256':{name:sha(out/name) for name in receipts}}
destination = out / 'test-release-0.4.2-rc.3'
destination.mkdir(exist_ok=True)
with (destination / 'RELEASE-CERTIFICATE.json').open('x') as stream:
    stream.write(json.dumps(certificate, indent=2) + '\n')
print(json.dumps({'version':build['version'],'archive_sha256':build['archive_sha256'],
    'certificate_sha256':sha(destination/'RELEASE-CERTIFICATE.json'),'production_qualified':False},indent=2))
