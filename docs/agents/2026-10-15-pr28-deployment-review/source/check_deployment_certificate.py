# ABOUTME: Mutates actual safe deployment receipts to check immutable certificate refusal gates.
# ABOUTME: Keeps corrupted variants in memory and never writes a guest completion receipt.
import copy,json
from pathlib import Path
from certify_deployment import load,certify

values,hashes=load(Path(__file__).parent)
report=certify(values,hashes)
assert report['status']=='PASS'
assert (Path(__file__).with_name('DEPLOYMENT-ACCEPTANCE.json')).read_bytes()==(json.dumps(report,indent=2)+'\n').encode()
cases=[]
def mutate(name,path,value):
 variant=copy.deepcopy(values);target=variant[name]
 for key in path[:-1]:target=target[key]
 target[path[-1]]=value;cases.append((name+'.'+'.'.join(map(str,path)),variant,dict(hashes)))
mutate('daily-ui-owner-apply.json',('actions',0,'intent'),'lifeos')
mutate('daily-ui-owner-apply.json',('actions',2,'http_status'),403)
mutate('daily-ui-owner-apply.json',('version_field_blank',),False)
mutate('current-server-identities.json',('servers','development','package_sha256'),'0'*64)
mutate('daily-native-skill-review.json',('after_admitted_skill_count',),55)
mutate('daily-editor-activation.json',('anonymous_native_pulse_status',),200)
mutate('daily-editor-activation.json',('sealed_read_status',),200)
mutate('daily-editor-activation.json',('only_modules_hermes_changed',),False)
mutate('daily-post-admission-verification.json',('model_and_tiers_preserved',),False)
mutate('daily-complete-runtime-artifacts.json',('private_map_sha256',),'0'*64)
mutate('daily-complete-runtime-artifacts.json',('runtime_roots',),['package'])
mutate('daily-complete-runtime-artifacts.json',('private_map_exported',),True)
mutate('daily-current-programs-restored.json',('current_mount_checkpoint_sha256',),'0'*64)
mutate('daily-current-programs-restored.json',('native_mount_targets',),6)
mutate('daily-current-programs-restored.json',('program_targets',),220)
mutate('daily-current-programs-restored.json',('prior_release_restore_available',),True)
mutate('daily-current-programs-restored.json',('generated_baseline_public_programs_verified',),1741)
mutate('daily-complete-restore.json',('cases',),values['daily-complete-restore.json']['cases'][:2])
mutate('daily-complete-restore.json',('cases',2,'later_edit_refused'),False)
mutate('daily-complete-restore.json',('source_writers_resumed',),False)
mutate('daily-complete-restore.json',('backup_pruning_protection_verified',),False)
mutate('daily-post-backup-health.json',('normal_morning_schedule',),'0 18 * * *')
mutate('daily-post-backup-health.json',('services','hermes-gateway.service','ActiveState'),'inactive')
mutate('release-test-cleanup.json',('owned_guests_removed',),[102,111,112])
mutate('release-test-cleanup.json',('operations',),values['release-test-cleanup.json']['operations']+[{'command':['pct','destroy','102','--purge','1'],'exit_code':0}])
mutate('daily-final-recovery-operations.json',(0,'exit_code'),1)
index=next(i for i,row in enumerate(values['daily-final-recovery-operations.json']) if row['label']=='destroy-disposable')
mutate('daily-final-recovery-operations.json',(index,'command'),['pct','status','110'])
mutate('daily-verification.json',('personal_data_imported_or_reset',),True)
for name in ('RELEASE-CERTIFICATE.json','PUBLIC-LATEST-ACCEPTANCE.json'):
 changed=dict(hashes);changed[name]='0'*64;cases.append(('hash-'+name,values,changed))
variant=copy.deepcopy(values);del variant['daily-complete-restore.json'];cases.append(('missing-restore',variant,hashes))
for name,variant,digests in cases:
 try:certify(variant,digests)
 except (AssertionError,KeyError,ValueError,TypeError):pass
 else:raise AssertionError('Invalid deployment evidence accepted: '+name)
print(json.dumps({'status':'PASS','positive':1,'refusals':len(cases),'actual_safe_receipts_used':True,'remote_calls':False,'mutated_receipts_written':False},indent=2))
