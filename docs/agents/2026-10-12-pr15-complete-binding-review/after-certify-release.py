# ABOUTME: Certifies exact stable release assets only after completed frozen and installed qualification gates.
# ABOUTME: Keeps historical candidate manifests immutable and reports daily promotion as a separate checkpoint.
import hashlib,json,re,tarfile
from pathlib import Path
out=Path(__file__).resolve().parent
load=lambda name:json.loads((out/name).read_bytes())
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
build=load('stable-bunfixed-build.json');head=build['head'];identity=head[:8]
assert head=='a87e7ae94894dabc3651454d1334cb23c4fae27e' and build['version']=='0.4.0'
assert sha(build['archive'])==build['archive_sha256']
assert Path(build['archive']).stat().st_size==build['archive_bytes']
full=load('integration-sealed-'+identity+'.json');assert full['exit_code']==0
assert full['package_commit']==head
text=(out/('integration-sealed-'+identity+'.stderr')).read_text()
assert text.rstrip().endswith('OK') and ' ... skipped' not in text and 'ResourceWarning' not in text
count=re.search(r'Ran (\d+) tests',text);assert count and int(count[1])==625
native=load('native-sealed-'+identity+'.json');assert native['exit_code']==0
with tarfile.open(build['archive']) as archive:
 source_bytes=archive.extractfile('hermes/hermes-source-manifest.json').read()
 source_manifest=json.loads(source_bytes)
assert native['package_commit']==head and native['archive_sha256']==build['archive_sha256']
assert native['source_manifest_sha256']==hashlib.sha256(source_bytes).hexdigest()
assert native['source_tree_sha256']==source_manifest['tree_sha256']
assert native['archived_source_files_unchanged'] is True
assert native['bun_version']=='1.4.3'
assert native['bun_binary_sha256']=='7ce7d6b654eddeec20afddf2396317fba6dc19ab52788a27e894e1806bf8f24b'
text=(out/('native-sealed-'+identity+'.stdout')).read_text()
assert '38 files, 716 tests passed, 0 failed (100% complete)' in text
assert not (out/('native-sealed-'+identity+'.stderr')).read_text()
fresh=load('fresh-install-'+identity+'-bunfixed.json')
assert fresh['status']=='PASS' and fresh['package_commit']==head and fresh['actual_process_exit']==73
assert {key:fresh['preparation'][key] for key in ('version','commit','package_sha256')}=={'version':build['version'],'commit':head,'package_sha256':build['archive_sha256']}
assert fresh['later_user_data_preserved']=='PASS' and fresh['installed_identity']=='PASS'
update=load('development-bunfixed-update.json');rollback=load('development-bunfixed-rollback.json')
interrupted=load('development-bunfixed-interruption-recovery.json')
assert update['status']==rollback['status']==interrupted['status']=='PASS'
assert update['operation']==rollback['operation']
interrupted_preparation=load('development-preparation-bunfixed-interruption.json')['preparation']
assert interrupted_preparation['identifier']==interrupted['operation']
assert {key:interrupted_preparation[key] for key in ('version','commit','package_sha256')}=={'version':build['version'],'commit':head,'package_sha256':build['archive_sha256']}
assert update['active_identity']=={'version':'0.4.0','commit':head,'package_sha256':build['archive_sha256']}
assert rollback['active_identity']==interrupted['active_identity']=={'version':'0.3.1','commit':'9af633252004a0ac8dd780d5fc12e9644f97bb0c','package_sha256':'2aada985dd26dee4ffb4da1d3348c43c76cff2e697d04028cfbba9d6f1b11a24'}
whole=load('whole-guest-recovery.json');coverage=load('whole-guest-program-coverage.json')
assert whole['status']==coverage['status']=='PASS' and len(whole['cases'])==3
assert whole['network_disconnected'] and whole['application_services_masked']
assert coverage['program_commit']==head and coverage['archive_sha256']==build['archive_sha256']
assert coverage['program_targets']==143
boot=load('development-bunfixed-boot.json');assert boot['status']=='PASS' and boot['bun_version']=='1.4.3' and boot['manual_service_start_after_reboot'] is False
assert boot['operation']==update['operation'] and boot['active_identity']==update['active_identity']
front=load('frontend-build.json');assert sha(front['archive'])==front['sha256']
certificate={'format':1,'status':'QUALIFIED','production_qualified':True,'version':build['version'],
 'program_commit':head,'archive_sha256':build['archive_sha256'],'archive_bytes':build['archive_bytes'],
 'hermes_dashboard_sha256':front['sha256'],'hermes_base':build['hermes_base'],'lifeos_base':build['lifeos_base'],
 'hermes_patch_count':build['hermes_patch_count'],'lifeos_patch_count':build['lifeos_patch_count'],
 'bun_version':'1.4.3','bun_archive_sha256':'1fc2edac843102909e3a1be1d8d9802cc6071cf074e67e88231f4ffe0f8b397b',
 'frozen_native_locks_unchanged':True,'integration_tests':625,'native_tests':716,'native_test_files':38,
 'fresh_interruption_recovery_verified':True,'installed_development_verified':True,
 'development_interruption_recovery_verified':True,'development_program_rollback_verified':True,'development_boot_verified':True,
 'whole_guest_history_recovery':whole,'whole_guest_program_coverage':coverage,
 'qualification_receipt_sha256':{name:sha(out/name) for name in (
 'integration-sealed-'+identity+'.json','integration-sealed-'+identity+'.stderr',
 'native-sealed-'+identity+'.json','native-sealed-'+identity+'.stdout','native-sealed-'+identity+'.stderr',
 'fresh-install-'+identity+'-bunfixed.json','development-bunfixed-update.json',
 'development-bunfixed-rollback.json','development-bunfixed-interruption-recovery.json',
 'development-preparation-bunfixed-interruption.json',
 'whole-guest-recovery.json','whole-guest-program-coverage.json','development-bunfixed-boot.json')},
 'daily_promotion_verified':False,'automatic_morning_observed':False,
 'build_manifest_note':'The immutable candidate manifest records build-time state. This certificate records completed release qualification.'}
path=out/'RELEASE-CERTIFICATE.json';assert not path.exists();path.write_text(json.dumps(certificate,indent=2)+'\n')
print(json.dumps({'status':'QUALIFIED','program_commit':head,'certificate_sha256':sha(path)},indent=2))
