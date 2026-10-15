# ABOUTME: Verifies refusal of altered qualification evidence before release publication.
# ABOUTME: Uses private temporary copies of real receipts without creating guest completion evidence.
import contextlib,io,json,runpy,shutil,tempfile
from pathlib import Path
source=Path(__file__).resolve().parent

def restore_guest(rows):
 next(row for row in rows if row['label']=='restore')['command'][2]='253'

def backup_storage(rows):
 next(row for row in rows if row['label']=='backup-source')['command'].extend(['--storage','local'])

cases=[
 ('completed-inputs',None,None),
 ('failed-integration','integration-04efe633.json',lambda row:row.update(exit_code=1)),
 ('wrong-tested-commit','integration-04efe633.json',lambda row:row.update(package_commit='0'*40)),
 ('failed-native','native-sealed-04efe633.json',lambda row:row.update(exit_code=1)),
 ('wrong-bootstrap-ref','manager-bootstrap.json',lambda row:row.update(ref='0'*40)),
 ('fresh-owner-absent','stock-first-install.json',lambda row:row.update(authenticated_owner_verified=False)),
 ('stock-source-changed','stock-source.json',lambda row:row.update(commit='0'*40)),
 ('unsafe-editor-mode','installed-editor-verification.json',lambda row:row.update(private_save_mode='0644')),
 ('editor-remount-fails','installed-editor-verification.json',lambda row:row.update(actual_remount_status=503)),
 ('browser-retains-revoked-draft','browser-editor-verification.json',lambda row:row.update(after_logout_textarea_absent=False)),
 ('changed-compiled-page','compiled-page-identity.json',lambda row:row.update(served_page_sha256='0'*64)),
 ('empty-services','verify-applied.json',lambda row:row.update(services={key:{} for key in row['services']})),
 ('wrong-prior-identity','verify-restored.json',lambda row:row['active'].update(commit='0'*40)),
 ('interruption-owner-absent','interrupted-action.json',lambda row:row.update(authenticated_owner_verified=False)),
 ('interruption-mount-absent','interrupted-action.json',lambda row:row.update(native_mount_required=False)),
 ('interrupted-programs-applied','synthetic-operation-states.json',lambda row:next(item for item in row['operations'] if item['operation']=='bfde95e2edb14efcade77b4951352d4e').update(program_state='applied')),
 ('stale-restore-commit','bound-whole-guest-recovery.json',lambda row:row.update(program_commit='0'*40)),
 ('missing-atlas-case','bound-whole-guest-recovery.json',lambda row:row['cases'].pop()),
 ('later-edit-not-refused','bound-whole-guest-recovery.json',lambda row:next(item for item in row['cases'] if item['case']=='later-edit').update(later_edit_refused=False)),
 ('changed-runtime-count','bound-whole-guest-artifact-coverage.json',lambda row:row.update(artifacts=row['artifacts']-1)),
 ('changed-restore-operation','bound-whole-guest-program-coverage.json',lambda row:row.update(operation='0'*32)),
 ('missing-native-restore','bound-whole-guest-program-coverage.json',lambda row:row.update(native_mount_required=False)),
 ('missing-owner-configuration-proof','bound-whole-guest-program-coverage.json',lambda row:row.update(owner_memory_configuration_verified=False)),
 ('wrong-restore-command-guest','bound-whole-guest-operations.json',restore_guest),
 ('wrong-backup-storage','source-backup-operations.json',backup_storage),
 ('no-reboot','reboot-verification.json',lambda row:row.update(boot_identity_changed=False)),
 ('wrong-development-version','development-verification.json',lambda row:row['active_identity'].update(version='0.4.3')),
 ('development-loses-memory-config','development-verification.json',lambda row:row.update(memory_configuration_bytes_preserved=False)),
 ('owner-turn-reuses-session','development-owner-turn-verification.json',lambda row:row.update(sessions=[row['sessions'][0],row['sessions'][0]])),
]
results=[]
with tempfile.TemporaryDirectory(prefix='lifeos-050-certificate-controls-') as temporary:
 for name,file,mutation in cases:
  root=Path(temporary)/name/'docs/verification/2026-10-14-release-0.5.0'
  root.mkdir(parents=True)
  for path in source.iterdir():
   if path.is_file() and path.name!='RELEASE-CERTIFICATE.json':shutil.copyfile(path,root/path.name)
  report=root.parents[1]/'agents/2026-10-14-pr27-baseline-review/pr27-baseline-review.md'
  report.parent.mkdir(parents=True)
  shutil.copyfile(source.parents[1]/'agents/2026-10-14-pr27-baseline-review/pr27-baseline-review.md',report)
  if file:
   path=root/file;value=json.loads(path.read_bytes());mutation(value);path.write_text(json.dumps(value))
  rejected=False
  with contextlib.redirect_stdout(io.StringIO()):
   try:runpy.run_path(str(root/'certify_release.py'),run_name='__main__')
   except (AssertionError,FileNotFoundError):rejected=True
  correct=rejected==bool(mutation) and (root/'RELEASE-CERTIFICATE.json').exists()==(mutation is None)
  results.append({'case':name,'expected_result_verified':correct,'result':'refused' if rejected else 'accepted'})
report={'status':'PASS' if all(row['expected_result_verified'] for row in results) else 'FAIL',
 'controls':results,'temporary_evidence_mutations_only':True,'guest_completion_receipt_constructed':False,'published_asset_changed':False}
(source/'certificate-negative-controls.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
assert report['status']=='PASS','The certifier accepts changed evidence or refuses complete evidence'
