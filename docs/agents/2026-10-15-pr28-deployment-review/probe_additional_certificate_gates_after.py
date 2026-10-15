# ABOUTME: Mutates real safe deployment receipts to expose command and scope binding gaps.
# ABOUTME: Keeps all altered receipt variants in memory and never writes a release certificate.
import copy,hashlib,importlib.util,json
from pathlib import Path
r=Path(__file__).resolve().parent;s=r/'current/certify_deployment.py'
spec=importlib.util.spec_from_file_location('review_deployment_certificate',s);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
values,hashes=m.load(s.parent);assert m.certify(values,hashes)['status']=='PASS'
mutations=[]
def add(label,name,mutate):mutations.append((label,name,mutate))
def command(label,tag,change):
 def mutate(row):change(next(x for x in row if x['label']==tag)['command'])
 add(label,'daily-final-recovery-operations.json',mutate)
command('backup-wrong-source','backup-source',lambda cmd:cmd.__setitem__(1,'101'))
command('restore-wrong-destination','restore',lambda cmd:cmd.__setitem__(2,'102'))
command('resume-wrong-source','resume-source',lambda cmd:cmd.__setitem__(2,'111'))
command('verify-programs-wrong-guest','verify-stable-programs',lambda cmd:cmd.__setitem__(2,'102'))
add('cleanup-shutdown-unowned-daily','release-test-cleanup.json',lambda row:row['operations'].append({'command':['pct','shutdown','102','--timeout','90'],'exit_code':0}))
def wrongstorage(row):next(x for x in row['operations'] if x['command'][:2]==['pvesm','remove'])['command'][2]='PBS-01'
add('cleanup-removes-unowned-storage','release-test-cleanup.json',wrongstorage)
add('cleanup-drops-preserved-100','release-test-cleanup.json',lambda row:row['other_guests_preserved'].pop('100'))
add('cleanup-drops-preserved-106','release-test-cleanup.json',lambda row:row['other_guests_preserved'].pop('106'))
add('admission-wrong-program-commit','daily-native-skill-review.json',lambda row:row.update(program_commit='0'*40))
add('admission-wrong-package','daily-native-skill-review.json',lambda row:row.update(archive_sha256='0'*64))
add('admission-wrong-server','daily-native-skill-review.json',lambda row:row.update(server='development'))
add('preservation-wrong-server','daily-post-admission-verification.json',lambda row:row.update(server='development'))
add('capture-is-verify','daily-current-program-capture.json',lambda row:row.update(action='verify'))
add('restored-is-capture','daily-current-programs-restored.json',lambda row:row.update(action='capture'))
add('capture-missing-baseline-proof','daily-current-program-capture.json',lambda row:row.update(generated_baseline_public_programs_verified=0))
add('restored-claims-exact-old-timestamp','daily-current-programs-restored.json',lambda row:row.update(generated_baseline_timestamp_scope='Exact historical timestamp preservation is verified.'))
add('capture-missing-timestamp-scope','daily-current-program-capture.json',lambda row:row.pop('generated_baseline_timestamp_scope'))
results=[]
for label,name,mutate in mutations:
 variant=copy.deepcopy(values);mutate(variant[name]);digests=dict(hashes);digests[name]=hashlib.sha256(json.dumps(variant[name],indent=2).encode()).hexdigest()
 accepted=True;error=None
 try:m.certify(variant,digests)
 except (AssertionError,KeyError,ValueError,TypeError) as exc:accepted=False;error=type(exc).__name__
 results.append({'case':label,'receipt':name,'accepted':accepted,'error_type':error,'desired_refusal_verified':not accepted})
report={'status':'PASS' if all(x['desired_refusal_verified'] for x in results) else 'FAIL','cases':results,'actual_safe_inputs_used':True,'remote_calls':False,'mutated_guest_receipts_written':False,'release_certificate_written':False}
(r/'additional-certificate-gates-after.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

assert report['status']=='PASS'
