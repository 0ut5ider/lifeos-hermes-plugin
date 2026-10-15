# ABOUTME: Checks the proposed public acceptance record against the actual safe receipt bundle.
# ABOUTME: Saves local hash and claim checks without changing release assets or guest evidence.
import hashlib,json,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[3]
s=root/'docs/verification/2026-10-14-release-0.5.0'
r=Path(__file__).resolve().parent
receipt=json.loads((s/'PUBLIC-LATEST-ACCEPTANCE.json').read_bytes())
inputs=r/'safe-inputs';inputs.mkdir(exist_ok=True)
checks=[]
def check(label,condition):
 assert condition,label
 checks.append({'claim':label,'status':'PASS'})
docs={}
for name,digest in receipt['evidence_sha256'].items():
 raw=(s/name).read_bytes();actual=hashlib.sha256(raw).hexdigest()
 check('evidence-hash:'+name,actual==digest)
 docs[name]=json.loads(raw);(inputs/name).write_bytes(raw)
for name in ['PUBLIC-LATEST-ACCEPTANCE.json','publication.json','RELEASE-CERTIFICATE.json']:
 shutil.copyfile(s/name,inputs/name)
b=docs['public-stock-baseline.json'];p=docs['public-stock-source-verification.json']
m=docs['public-manager-verification.json'];a=docs['public-ui-actions.json']
u=docs['public-ui-readonly-completion.json'];v=docs['public-installation-verification.json']
publication=json.loads((s/'publication.json').read_bytes())
check('exact-product-identity',receipt['version']==v['active_identity']['version']=='0.5.0' and receipt['program_commit']==v['active_identity']['commit']==u['package_commit']==publication['program_commit'] and receipt['package_sha256']==v['active_identity']['package_sha256']==u['archive_sha256']==publication['archive_sha256'])
check('exact-fixture-and-operation',all(x['guest']==113 and x['address']=='192.168.8.244' for x in [b,p,m,a,u,v]) and receipt['operation']==a['operation']==u['operation']==v['operation']=='568cd8927be849e7a92f0d048999d070')
check('original-actions-preserved',a['status']=='RUNNING' and a['operation_state']=='queued-apply' and a['actions']==u['actions'] and len(a['actions'])==4)
x1,x2,x3,x4=a['actions']
check('default-github-url-and-ref',receipt['public_default_github_url']==x1['identifier']=='https://github.com/0ut5ider/lifeos-hermes-plugin.git#optional/lifeos_release_manager' and x1['action']=='native-web-github-install' and x1['http_status']==200 and x1['ref'] is None and x1['force'] is False and m['ref'] is None and m['force'] is False and receipt['default_ref_used'] is True)
check('latest-stable-review-and-apply',receipt['latest_stable_selected_from_public_catalog'] is True and x2['action']=='install-lifeos-latest-stable' and x2['http_status']==202 and x2['version_field_blank'] is True and x3['http_status']==200 and x3['version']==receipt['version'] and x3['commit']==receipt['program_commit'] and x3['package_sha256']==receipt['package_sha256'] and x3['fresh'] is True and x4=={'action':'owner-ui-apply','http_status':200,'identifier':receipt['operation']})
check('readonly-browser-completion',receipt['actual_native_ui_install_review_apply_verified'] is True and receipt['fresh_owner_browser_final_status']==u['operation_state']=='applied' and u['status']=='UI_APPLIED' and u['last_operation_http_status']==200 and u['read_only_completion'] is True and u['original_observer_completed'] is False and u['authenticated_owner_verified'] is True and receipt['owner_session_renewed_for_readonly_completion'] is True and receipt['duplicate_install_or_apply_performed'] is False and u['duplicate_apply_performed'] is False)
check('actual-observer-process-zero',(Path('/home/outsider/.cache/lifeos-release-0.5.0-20261014/public-ui-replay-5/process.done').read_text().strip()=='0') and Path('/home/outsider/.cache/lifeos-release-0.5.0-20261014/public-ui-replay-5/receipt.json').read_bytes()==(s/'public-ui-readonly-completion.json').read_bytes())
check('exact-manager-and-stock-counts',receipt['manager_files_verified']==m['manager_files_verified']==21 and m['status']=='PASS' and m['method']=='actual-native-web-default-github-install' and receipt['fresh_stock_source_and_dashboard_files_verified']==p['runtime_files_verified']==p['source_files_verified']+p['dashboard_files_verified']==18309 and p['complete_runtime_file_set_verified'] is True)
check('actual-installed-program-proof',receipt['exact_selected_programs_verified'] is True and v['status']=='PASS' and v['active_identity']['verification']=='verified' and v['active_identity']['modified_files']==[] and v['sealed_program_targets']==11 and v['native_mount_required'] is True and v['prior_stock_source_receipt_sha256']==receipt['evidence_sha256']['public-stock-source-verification.json'])
check('model-preservation',receipt['model_and_tiers_preserved'] is True and v['selected_model_and_tiers_preserved'] is True)
check('public-fixture-writers-inactive',v['services']['hermes-dashboard.service']=={'ActiveState':'active','SubState':'running'} and all(v['services'][n]=={'ActiveState':'inactive','SubState':'dead'} for n in ['hermes-gateway.service','com.lifeos.pulse.service']))
check('memory-and-model-turn-excluded',receipt['new_owner_memory_activation_in_scope'] is False and receipt['real_model_turn_on_public_fixture'] is False)
check('no-production-or-personal-data-claim',receipt['production_guest_changed'] is False and all(x['production_guest_changed'] is False for x in [b,p,m,a,u,v]) and receipt['personal_records_exported'] is False and receipt['personal_data_imported_or_reset'] is False and v['personal_records_read'] is False and v['personal_data_imported_or_reset'] is False)
check('initial-certificate-preserved',receipt['initial_certificate_unchanged'] is True and hashlib.sha256((s/'RELEASE-CERTIFICATE.json').read_bytes()).hexdigest()==v['public_certificate_sha256']==publication['certificate_sha256']=='c8a0ac35fa6f084d417951fd7538bee8f9d330ff101a9f71e3855b5da8a2dd20')
result={'status':'PASS','checks':checks,'scope':'Local consistency and hash checks over real safe receipts. No remote calls or new guest receipts. Original live poll HTTP cause is not established.'}
(r/'acceptance-bundle-checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
