# ABOUTME: Runs the extended qualification refusal matrix with completed proof and labeled synthetic pending inputs.
# ABOUTME: Keeps fixture source and generated certificates in temporary report workspaces without changing acceptance receipts.
import json,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
out=Path(__file__).parent/'primary-matrix';out.mkdir(exist_ok=True);source=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/verification/2026-10-12-release-0.4.1')
build=json.loads((source/'stable-build.json').read_bytes());identity=build['head'][:8]
completed=['stable-build.json','frontend-build.json','integration-sealed-'+identity+'.json','integration-sealed-'+identity+'.stderr',
'native-sealed-'+identity+'.json','native-sealed-'+identity+'.stdout','native-sealed-'+identity+'.stderr',
'fresh-install-'+identity+'-041.json','development-preparation-interruption.json','development-bunfixed-interruption-exit.json']
exit_receipt=json.loads((source/'development-bunfixed-interruption-exit.json').read_bytes())
active={'version':'0.4.1','commit':build['head'],'package_sha256':build['archive_sha256']}
prior={'version':'0.3.1','commit':'9af633252004a0ac8dd780d5fc12e9644f97bb0c','package_sha256':'2aada985dd26dee4ffb4da1d3348c43c76cff2e697d04028cfbba9d6f1b11a24'}
normal='synthetic-normal-041-operation'
with tempfile.TemporaryDirectory(prefix='synthetic-matrix-',dir=out) as temp:
 root=Path(temp)
 for name in completed:shutil.copy2(source/name,root/name)
 fixtures={'development-bunfixed-update.json':{'status':'PASS','operation':normal,'active_identity':active},
 'development-bunfixed-interruption-recovery.json':{'status':'PASS','operation':exit_receipt['operation'],'active_identity':prior},
 'development-bunfixed-boot.json':{'status':'PASS','operation':normal,'active_identity':active,'bun_version':'1.4.3','manual_service_start_after_reboot':False}}
 for name,value in fixtures.items():value['synthetic_probe_only']=True;(root/name).write_text(json.dumps(value))
 shutil.copy2(source/'test_certificate_binding.py',root/'test_certificate_binding.py')
 started=time.monotonic()
 with (out/'extended-binding.stdout').open('w') as stdout,(out/'extended-binding.stderr').open('w') as stderr:
  r=subprocess.run([sys.executable,'-B',str(root/'test_certificate_binding.py'),str((source/'certify_release.py').resolve())],env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=stdout,stderr=stderr,timeout=600)
 (out/'process.done').write_text(str(r.returncode)+'\n')
 report={'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-started,'synthetic_pending_inputs_only':True}
 (out/'extended-binding.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert r.returncode==0
