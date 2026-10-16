# ABOUTME: Qualifies the exact reviewed archive from measured tests and installed receipts.
# ABOUTME: Identifies inherited checks and workstation process-inspection limits without changing policy.
import hashlib,json,re
from pathlib import Path
c=Path(__file__).parent;used={}
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(name):
 p=c/name;used[name]=digest(p);return json.loads(p.read_bytes())
def passed(name):
 v=load(name);assert v['status']=='PASS',name;return v
b=load('build.stdout');assert b['version']=='0.7.1' and b['head']=='3cfddbfce4d82808f0277f53b8a1f06a8be0aa72'
assert digest(b['archive'])==b['archive_sha256']=='46eb23cdc82880a2292f05e9031f18cb252a8261abc3621e292ba0326b8b68e9'
assert Path(b['archive']).stat().st_size==b['archive_bytes']==288195487
r=passed('review-equivalence.json');assert r['all_packaged_tracked_files_identical'] and r['review_round_2_clear']
p=passed('package-verification.json');assert p['native']['lifeos']['matches_qualified_070'] and p['python_closure_matches_qualified_070'] and p['stock_program_files_match_qualified_070']
assert p['runtime_changes']['hermes']==['gateway/mirror.py','gateway/platforms/webhook.py','hermes-source-manifest.json']
n=passed('native-delta.json');assert n['program_commit']==b['head'] and n['archive_sha256']==b['archive_sha256'] and n['native_source_unchanged']
assert '177 passed' in (c/'native-delta.stdout').read_text() and not (c/'native-delta.stderr').read_bytes()
i=load('archive-integration-3cfddbfc.json');assert i['archive_sha256']==b['archive_sha256'] and i['archive_files_match_before'] and i['archive_files_match_after'] and not i['unhandled_diagnostics']
t=(c/'archive-integration-3cfddbfc.stderr').read_text();count=int(re.search(r'Ran (\d+) tests',t).group(1));assert count>1030
actual=[(line.split(': ',1)[0],line.split(': ',1)[1]) for line in t.splitlines() if line.startswith(('ERROR: ','FAIL: '))]
expected={'test_exact_running_coordinator_is_admitted (test_removal_coordinator.RemovalCoordinatorTests.test_exact_running_coordinator_is_admitted)','test_running_bun_outside_reviewed_service_groups_refuses (test_removal_consumers.RemovalConsumersTests.test_running_bun_outside_reviewed_service_groups_refuses)'}
if i['exit_code']==0:assert not actual and t.rstrip().endswith('OK')
else:
 assert {x[1] for x in actual}==expected and len(actual)==2 and {x[0] for x in actual}=={'ERROR','FAIL'}
 assert re.search(r"PermissionError:.*'/proc/[0-9]+/exe'",t)
 assert 'skipped=' not in t
boundary=passed('process-boundary-equivalence.json');assert boundary['tests']==8 and boundary['test_assertions_changed'] is False
installed=passed('installed-verification.json');assert installed['archive_sha256']==b['archive_sha256'] and installed['exact_archive_process_boundary_cases']==8 and installed['exact_installed_notification_cases']==18
fresh=passed('installed-fresh-verification.json');assert fresh['active_identity']['package_sha256']==b['archive_sha256'] and fresh['actual_model_round_trip'] and fresh['model_mapping_preserved']
owned=passed('installed-owned-model.json');assert owned['actual_model_reply'] and owned['tool_names']==[]
http=passed('installed-http-enable.json');assert http['actual_native_save_or_recall'] and http['dashboard_cookie_separation'] and http['owner_authenticated']
u=passed('complete-update-restore.json');assert u['archive_sha256']==b['archive_sha256'] and u['authenticated_owner_apply_and_restore'] and u['actual_http_recall_after_update_and_restore'] and u['actual_http_credential_revocation']
old=Path('/home/outsider/.cache/lifeos-release-0.7.0-20261016/RELEASE-CERTIFICATE.json');old_digest=digest(old);assets=load('release-assets-before.json');assert any(v['release']=='v0.7.0' and v['name']=='RELEASE-CERTIFICATE.json' and v['digest']=='sha256:'+old_digest for v in assets.values())
certificate={'format':1,'status':'QUALIFIED','production_qualified':True,'version':b['version'],'program_commit':b['head'],'archive_sha256':b['archive_sha256'],'archive_bytes':b['archive_bytes'],'hermes_dashboard_sha256':'e7c93e754de99b6ec66ae17ae313377dc513104da2776a099c391a7aab347bec','hermes_base':b['hermes_base'],'lifeos_base':b['lifeos_base'],'hermes_patch_count':10,'lifeos_patch_count':25,'independent_review_rounds':2,'final_independent_review':'CLEAR','integration_executed_cases':count,'integration_workstation_passed':count-len(actual),'integration_workstation_errors':sum(x[0]=='ERROR' for x in actual),'integration_workstation_failures':sum(x[0]=='FAIL' for x in actual),'integration_service_account_replay_tests':8,'single_clean_full_run':i['exit_code']==0,'native_changed_path_tests':177,'installed_notification_cases':18,'actual_owner_model_reply':True,'authenticated_complete_update_and_rollback':True,'actual_http_memory_recall_after_update_and_rollback':True,'actual_http_revocation':True,'qualification_receipt_sha256':used,'inherited_release':'0.7.0','inherited_release_certificate_sha256':old_digest,'inherited_checks':'Unchanged LifeOS native programs, Python closure, stock Hermes, compiled dashboards, release-manager runtime, and HTTP runtime retain 0.7.0 qualification. Earlier full native gate, UI gate, worker-interruption and whole-guest recovery remain earlier-version evidence. The changed native mirror and webhook paths pass 177 exact-package tests.','process_inspection_limit':'The workstation refuses two /proc executable inspections. All eight unchanged process-boundary cases pass on the disposable guest service account. No policy or test assertion is weakened.','fixture_corrections':'The retained correction receipt identifies missing inputs, safety-mask removal, pristine comparisons, normal ownership activation and the existing CACHE permission normalization. Directory-creation attribution remains open.','development_promotion_verified':False,'daily_promotion_verified':False,'automatic_morning_observed':False,'http_enabled_on_existing_servers':False,'personal_data_imported_or_reset':False}
with (c/'RELEASE-CERTIFICATE.json').open('x') as f:f.write(json.dumps(certificate,indent=2)+'\n')
print(json.dumps({'status':'QUALIFIED','program_commit':b['head'],'certificate_sha256':digest(c/'RELEASE-CERTIFICATE.json'),'integration_cases':count}))
