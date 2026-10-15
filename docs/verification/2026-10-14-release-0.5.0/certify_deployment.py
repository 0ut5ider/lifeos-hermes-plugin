# ABOUTME: Binds actual safe public installation, daily activation, recovery, and cleanup evidence.
# ABOUTME: Creates supplementary deployment acceptance without changing the initial release certificate.
import hashlib,json
from pathlib import Path

VERSION='0.5.0'
COMMIT='04efe633296eb2b1a1d95561ca6d3e9516cd47dc'
ARCHIVE='a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813'
OPERATION='b9e873b251604202a58442b502a3c2b2'
NAMES=('daily-manager-bootstrap.json','daily-ui-owner-apply.json','PUBLIC-LATEST-ACCEPTANCE.json','current-server-identities.json','daily-verification.json',
 'daily-native-skill-review.json','daily-editor-activation.json','daily-post-admission-verification.json',
 'daily-post-backup-health.json','daily-complete-restore.json','daily-current-programs-restored.json',
 'daily-current-program-capture.json','daily-complete-runtime-artifacts.json','daily-runtime-artifact-capture.json',
 'daily-atlas-restored.json','daily-final-recovery-operations.json','release-test-cleanup.json')

def load(folder):
 values={name:json.loads((folder/name).read_bytes()) for name in NAMES}
 hashes={name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in (*NAMES,'RELEASE-CERTIFICATE.json')}
 return values,hashes

def certify(values,hashes):
 assert hashes['RELEASE-CERTIFICATE.json']=='c8a0ac35fa6f084d417951fd7538bee8f9d330ff101a9f71e3855b5da8a2dd20'
 assert hashes['PUBLIC-LATEST-ACCEPTANCE.json']=='b359e50f0ad885d62d2d3c89ccc3ca89c516feb32202382ae8720ff3001cf0b0'
 assert set(values)==set(NAMES) and set(hashes)==set(NAMES)|{'RELEASE-CERTIFICATE.json'}
 for name,row in values.items():
  if name not in ('daily-final-recovery-operations.json','daily-ui-owner-apply.json'):assert row['status']=='PASS',name
 def identity(row):
  assert row['version']==VERSION and row['commit']==COMMIT and row['package_sha256']==ARCHIVE
  assert row['verification']=='verified' and row['modified_files']==[]
 def selected(row):
  assert row['version']==VERSION and row['program_commit']==COMMIT and row['archive_sha256']==ARCHIVE
  assert row['operation']==OPERATION
 def truths(name,keys):
  for key in keys:assert values[name][key] is True,(name,key)
 bootstrap=values['daily-manager-bootstrap.json']
 assert bootstrap['manager_files_verified']==21 and bootstrap['program_commit']==COMMIT and bootstrap['ref'] is None
 assert bootstrap['configuration_file_bytes_preserved'] is True and bootstrap['dashboard_restarted_after_bootstrap'] is True
 ui=values['daily-ui-owner-apply.json']
 assert ui['status']=='APPLY_QUEUED' and ui['operation']==OPERATION and ui['version_field_blank'] is True
 actions=ui['actions'];assert len(actions)==3 and all(row['method']=='POST' and row['identifier']==OPERATION for row in actions)
 prepare,review,apply=actions
 assert prepare['path']=='/api/plugins/lifeos-release-manager/prepare' and prepare['http_status']==202 and prepare['intent']=='plugin'
 assert review['path']=='/api/plugins/lifeos-release-manager/operations/'+OPERATION+'/review' and review['http_status']==200
 assert review['version']==VERSION and review['commit']==COMMIT and review['package_sha256']==ARCHIVE and review['fresh'] is False
 assert apply['path']=='/api/plugins/lifeos-release-manager/operations/'+OPERATION+'/apply' and apply['http_status']==200
 assert apply['action']=='apply' and apply['state']=='queued'
 public=values['PUBLIC-LATEST-ACCEPTANCE.json']
 assert public['version']==VERSION and public['program_commit']==COMMIT and public['package_sha256']==ARCHIVE
 truths('PUBLIC-LATEST-ACCEPTANCE.json',('default_ref_used','latest_stable_selected_from_public_catalog',
  'actual_native_ui_install_review_apply_verified','exact_selected_programs_verified'))
 assert public['manager_files_verified']==21 and public['fresh_stock_source_and_dashboard_files_verified']==18309
 identities=values['current-server-identities.json'];assert set(identities['servers'])=={'development','daily'}
 for active in identities['servers'].values():identity(active)
 assert identities['same_exact_package'] is True
 applied=values['daily-verification.json'];identity(applied['active_identity'])
 assert applied['operation']==OPERATION and applied['sealed_program_targets']==221
 truths('daily-verification.json',('model_and_tiers_preserved','credential_file_bytes_preserved',
  'memory_configuration_bytes_preserved','synthetic_memory_preserved','prior_forgotten_fact_stays_absent'))
 assert applied['personal_data_imported_or_reset'] is False and applied['personal_records_read'] is False
 admission=values['daily-native-skill-review.json'];assert admission['operation']==OPERATION
 assert admission['after_admitted_skill_count']==56 and admission['after_omitted_program_skills']==0
 assert admission['reviewed_sources']==57 and admission['personal_sources_reviewed']==0
 assert admission['review_status']=='committed' and admission['review_http_status']==200 and admission['launcher_present'] is True
 editor=values['daily-editor-activation.json'];selected(dict(editor,version=VERSION))
 assert editor['actual_owner_remount_status']==200 and editor['actual_owner_remount_state']=='committed'
 assert editor['prior_release_restore_available'] is False and editor['owner_metadata_status']==200
 assert editor['declared_files']==24 and editor['anonymous_native_pulse_status']==401 and editor['sealed_read_status']==403
 assert editor['only_modules_hermes_changed'] is True and editor['normal_morning_schedule']=='0 7 * * *'
 preservation=values['daily-post-admission-verification.json'];identity(preservation['active_identity'])
 truths('daily-post-admission-verification.json',('model_and_tiers_preserved','credential_file_bytes_preserved',
  'memory_configuration_bytes_preserved','all_three_services_and_homes_preserved'))
 health=values['daily-post-backup-health.json']
 assert health['pulse_user_configuration_sha256']==editor['user_configuration_after_sha256']
 assert health['normal_morning_schedule']=='0 7 * * *' and health['normal_morning_job_enabled'] is True
 assert health['pulse_editor_enabled'] is True and health['manual_job_run'] is False
 assert health['original_0700_wall_clock_observed'] is False
 assert set(health['services'])=={'hermes-dashboard.service','hermes-gateway.service','com.lifeos.pulse.service'}
 assert all(state=={'ActiveState':'active','SubState':'running'} for state in health['services'].values())
 restored=values['daily-complete-restore.json'];selected(restored)
 assert restored['source_guest']==102 and restored['restored_guest']==110
 archive=restored['archive'];assert archive.startswith('PBS-01:backup/ct/102/')
 truths('daily-complete-restore.json',('network_disconnected','application_services_masked','source_writers_resumed','backup_pruning_protection_verified'))
 assert restored['source_programs_or_personal_data_changed'] is False
 expected_cases={'baseline':51,'interrupted':55,'later-edit':55}
 assert len(restored['cases'])==3 and {row['case'] for row in restored['cases']}==set(expected_cases)
 for row in restored['cases']:
  assert row['status']=='PASS' and row['restored_files']==expected_cases[row['case']]
  assert row['archive_and_live_group_verified'] is True and row['later_edit_refused'] is (row['case']=='later-edit')
 atlas=values['daily-atlas-restored.json'];assert atlas['action']=='verify' and atlas['version']==VERSION and atlas['cases']==restored['cases']
 assert atlas['personal_data_used'] is False and atlas['live_store_modified'] is False
 programs=values['daily-current-programs-restored.json'];selected(programs)
 assert programs['program_targets']==221 and programs['native_mount_targets']==7
 assert programs['generated_baseline_public_programs_verified']==1742
 assert programs['prior_release_restore_available'] is False and programs['normal_morning_schedule']=='0 7 * * *'
 truths('daily-current-programs-restored.json',('current_owner_mount_verified','retained_public_archive_and_certificate_verified',
  'owner_memory_configuration_verified','credential_file_bytes_preserved','model_and_tiers_preserved','pulse_editor_enabled','application_services_masked'))
 captured=values['daily-current-program-capture.json'];selected(captured)
 assert captured['current_mount_checkpoint_sha256']==programs['current_mount_checkpoint_sha256']
 assert captured['program_targets']==221 and captured['native_mount_targets']==7
 artifacts=values['daily-complete-runtime-artifacts.json'];selected(dict(artifacts,version=VERSION))
 captured_artifacts=values['daily-runtime-artifact-capture.json']
 assert {key:value for key,value in artifacts.items() if key!='action'}=={key:value for key,value in captured_artifacts.items() if key!='action'}
 assert artifacts['action']=='verify' and captured_artifacts['action']=='capture'
 assert restored['runtime_artifact_coverage']==artifacts and artifacts['private_map_exported'] is False
 assert artifacts['artifacts']==64567 and artifacts['regular_files']==58080
 assert set(artifacts['runtime_roots'])=={'bin','compiled-dashboard','dependency-profile','hermes','package','pm-runtime','python-environment','tools','worker'}
 operations=values['daily-final-recovery-operations.json']
 assert all(type(row['exit_code']) is int and row['exit_code']==0 for row in operations)
 required=('inventory','editor-checkpoint','check-existing-synthetic-atlas','drain-source','capture-current-owner-mount',
  'capture-program-artifacts','backup-source','archives','resume-source','protect-archive','verify-protection','restore',
  'restored-config-before-disconnect','disable-automatic-start','verify-disconnected-before-boot','mount','unmount',
  'boot-isolated','restored-config','network','verify-history','verify-program-artifacts','verify-stable-programs',
  'shutdown-restore','cleanup-config','destroy-disposable')
 for name in required:assert len([row for row in operations if row['label']==name])==1,name
 removal=next(row for row in operations if row['label']=='destroy-disposable')
 assert removal['command']==['pct','destroy','110','--purge','1']
 cleanup=values['release-test-cleanup.json']
 assert cleanup['owned_guests_removed']==[111,112,113] and cleanup['restore_guest_already_removed']==110
 assert cleanup['owned_storage_removed'] is True and cleanup['protected_archive_preserved']==archive
 assert all(type(row['exit_code']) is int and row['exit_code']==0 for row in cleanup['operations'])
 deletes=[row['command'] for row in cleanup['operations'] if row['command'][:2]==['pct','destroy']]
 assert deletes==[['pct','destroy',str(guest),'--purge','1'] for guest in (111,112,113)]
 assert {'101','102','801'}<=set(cleanup['other_guests_preserved'])
 assert all(cleanup['other_guests_preserved'][key]['status']=='running' for key in ('101','102','801'))
 return {'format':1,'status':'PASS','version':VERSION,'program_commit':COMMIT,'package_sha256':ARCHIVE,
  'development_and_daily_same_exact_package':True,'daily_operation':OPERATION,
  'public_default_url_installation_verified':True,'daily_native_update_plugin_action_verified':True,
  'daily_selected_program_targets':221,'daily_current_owner_mount_targets':7,'public_native_skills_admitted':56,
  'governed_pulse_editor_active':True,'model_and_tiers_preserved':True,'credential_and_memory_configuration_preserved':True,
  'daily_services_and_homes_preserved':True,'synthetic_memory_preserved':True,'prior_forgotten_facts_stay_absent':True,
  'protected_complete_backup':archive,'disconnected_complete_guest_restore_verified':True,
  'restored_runtime_artifacts':64567,'restored_regular_files':58080,'restored_runtime_roots':9,'restored_atlas_cases':3,
  'generated_baseline_public_program_hashes_verified':1742,'generated_baseline_exact_historical_timestamp_claimed':False,
  'source_and_restored_current_mount_checkpoint_equal':True,'earlier_release_restore_available':False,
  'owned_rehearsal_guests_removed':[111,112,113],'owned_restore_guest_removed':110,'owned_test_storage_removed':True,
  'processing_vm_and_other_guests_preserved':True,'normal_morning_schedule':'0 7 * * *',
  'original_0700_wall_clock_observed':False,'manual_morning_job_run':False,'personal_records_exported':False,
  'personal_data_imported_or_reset':False,'public_fixture_new_owner_memory_activation_in_scope':False,
  'initial_certificate_unchanged':True,'evidence_sha256':dict(sorted(hashes.items())),
  'scope':'Supplementary actual public installation and daily deployment evidence. The initial release certificate keeps its historical checkpoint. Full guest recovery protects the later owner mount.'}

if __name__=='__main__':
 folder=Path(__file__).parent;values,hashes=load(folder);report=certify(values,hashes)
 out=folder/'DEPLOYMENT-ACCEPTANCE.json';assert not out.exists();out.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'status':report['status'],'asset':out.name,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}))
