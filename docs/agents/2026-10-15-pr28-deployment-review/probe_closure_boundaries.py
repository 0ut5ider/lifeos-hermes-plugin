# ABOUTME: Checks exact command ordering and preservation metadata against real safe receipts.
# ABOUTME: Keeps every corrupted input in memory and records only control outcomes.
import copy,hashlib,importlib.util,json,subprocess
from pathlib import Path
r=Path(__file__).resolve().parent;s=r/'current/certify_deployment.py'
spec=importlib.util.spec_from_file_location('closure_boundaries',s);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
values,hashes=m.load(s.parent);cases=[]
def add(label,name,fn):cases.append((label,name,fn))
add('recovery-order','daily-final-recovery-operations.json',lambda x:x.reverse())
add('recovery-label','daily-final-recovery-operations.json',lambda x:x[0].update(label='unbound'))
add('recovery-bool-exit','daily-final-recovery-operations.json',lambda x:x[0].update(exit_code=False))
add('missing-disconnection','daily-final-recovery-operations.json',lambda x:x.pop(next(i for i,v in enumerate(x) if v['label']=='disconnect-net0')))
add('cleanup-order','release-test-cleanup.json',lambda x:x['operations'].reverse())
add('cleanup-bool-exit','release-test-cleanup.json',lambda x:x['operations'][0].update(exit_code=False))
add('processing-status-changed','release-test-cleanup.json',lambda x:x['other_guests_preserved']['801'].update(status='stopped'))
add('processing-identity-changed','release-test-cleanup.json',lambda x:x['other_guests_preserved']['801'].update(name='other'))
add('personal-source-reviewed','daily-native-skill-review.json',lambda x:x.update(personal_sources_reviewed=1))
add('source-credential-preservation-false','daily-current-program-capture.json',lambda x:x.update(credential_file_bytes_preserved=False))
add('source-masked','daily-current-program-capture.json',lambda x:x.update(application_services_masked=True))
add('source-personal-records-read','daily-current-program-capture.json',lambda x:x.update(personal_records_read=True))
add('restored-mount-not-required','daily-current-programs-restored.json',lambda x:x.update(native_mount_required=False))
add('wall-clock-claim','daily-post-backup-health.json',lambda x:x.update(original_0700_wall_clock_observed=True))
add('wrong-freshness','daily-ui-owner-apply.json',lambda x:x['actions'][1].update(fresh=True))
results=[]
for label,name,fn in cases:
 variant=copy.deepcopy(values);fn(variant[name]);digests=dict(hashes);digests[name]=hashlib.sha256(json.dumps(variant[name]).encode()).hexdigest()
 try:m.certify(variant,digests)
 except (AssertionError,KeyError,ValueError,TypeError) as exc:results.append({'case':label,'refused':True,'error':type(exc).__name__})
 else:results.append({'case':label,'refused':False})
report={'status':'PASS' if all(x['refused'] for x in results) else 'FAIL','cases':results,'real_safe_inputs_used':True,'remote_calls':False,'guest_receipts_written':False,'release_certificates_written':False}
(r/'closure-boundaries.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));assert report['status']=='PASS'
p=subprocess.run(['python','-W','error::ResourceWarning','check_deployment_certificate.py'],cwd=s.parent,capture_output=True,text=True)
(r/'primary-certificate-controls-after.stdout').write_text(p.stdout);(r/'primary-certificate-controls-after.stderr').write_text(p.stderr)
assert p.returncode==0
