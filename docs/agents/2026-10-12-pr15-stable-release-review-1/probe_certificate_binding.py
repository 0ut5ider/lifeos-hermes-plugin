# ABOUTME: Tests release qualification refusal and receipt identity binding in isolated temporary directories.
# ABOUTME: Uses labeled synthetic future gates only for negative certificate tests and never publishes artifacts.
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

repo=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
source=repo/'docs/verification/2026-10-12-release-0.4.0'
out=Path(__file__).parent
results=[]
selected=['certify_release.py','stable-bunfixed-build.json','frontend-build.json',
'integration-sealed-a87e7ae9.json','integration-sealed-a87e7ae9.stderr',
'native-sealed-a87e7ae9.json','native-sealed-a87e7ae9.stdout','native-sealed-a87e7ae9.stderr',
'fresh-install-a87e7ae9-bunfixed.json','development-bunfixed-update.json',
'development-bunfixed-interruption-recovery.json','development-bunfixed-boot.json']
build=json.loads((source/'stable-bunfixed-build.json').read_bytes())
def run_case(name,*,fill_missing=False,stale_integration=False,wrong_fresh_digest=False):
    with tempfile.TemporaryDirectory(prefix='pr15-certificate-') as temp:
        root=Path(temp)
        for filename in selected:shutil.copy2(source/filename,root/filename)
        if fill_missing:
            # These invented future gate receipts are local test fixtures, not acceptance evidence.
            rollback=json.loads((source/'development-bunfixed-interruption-recovery.json').read_bytes())
            rollback['operation']='synthetic-certificate-binding-probe'
            (root/'development-bunfixed-rollback.json').write_text(json.dumps(rollback))
            (root/'whole-guest-recovery.json').write_text(json.dumps({'status':'PASS',
                'network_disconnected':True,'application_services_masked':True,
                'cases':[{'case':c,'status':'PASS'} for c in ('baseline','interrupted','later-edit')],
                'synthetic_probe_only':True}))
            (root/'whole-guest-program-coverage.json').write_text(json.dumps({'status':'PASS',
                'program_commit':build['head'],'archive_sha256':build['archive_sha256'],
                'synthetic_probe_only':True}))
        if stale_integration:
            shutil.copy2(source/'integration-sealed-4644f90c.json',root/'integration-sealed-a87e7ae9.json')
            shutil.copy2(source/'integration-sealed-4644f90c.stderr',root/'integration-sealed-a87e7ae9.stderr')
        if wrong_fresh_digest:
            path=root/'fresh-install-a87e7ae9-bunfixed.json'
            receipt=json.loads(path.read_bytes());receipt['preparation']['package_sha256']='0'*64
            path.write_text(json.dumps(receipt))
        command=[sys.executable,'-B',str(root/'certify_release.py')]
        process=subprocess.run(command,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True)
        certificate=root/'RELEASE-CERTIFICATE.json'
        result={'case':name,'exit_code':process.returncode,'certificate_written':certificate.exists(),
            'input_integration_commit':json.loads((root/'integration-sealed-a87e7ae9.json').read_bytes())['package_commit'],
            'input_fresh_archive_sha256':json.loads((root/'fresh-install-a87e7ae9-bunfixed.json').read_bytes())['preparation']['package_sha256'],
            'synthetic_future_gates':fill_missing}
        if certificate.exists():
            content=json.loads(certificate.read_bytes())
            result.update(output_status=content['status'],output_program_commit=content['program_commit'],
                output_archive_sha256=content['archive_sha256'])
        (out/(name+'.stdout')).write_text(process.stdout)
        (out/(name+'.stderr')).write_text(process.stderr)
        results.append(result)
run_case('incomplete-current-gates')
run_case('synthetic-future-gates-baseline',fill_missing=True)
run_case('stale-integration-receipt',fill_missing=True,stale_integration=True)
run_case('wrong-fresh-archive-digest',fill_missing=True,wrong_fresh_digest=True)
(out/'certificate-binding-results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
