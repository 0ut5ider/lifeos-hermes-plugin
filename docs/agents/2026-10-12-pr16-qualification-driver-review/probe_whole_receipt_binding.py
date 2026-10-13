# ABOUTME: Tests actual historical whole-guest evidence against the new release certificate in isolated fixtures.
# ABOUTME: Labels pending installed and restore receipts as synthetic tests without claiming completed acceptance.
import hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
repo=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin');source=repo/'docs/verification/2026-10-12-release-0.4.1';old=source.parent/'2026-10-12-release-0.4.0';out=Path(__file__).parent
build=json.loads((source/'stable-build.json').read_bytes());identity=build['head'][:8]
completed=['stable-build.json','frontend-build.json','integration-sealed-'+identity+'.json','integration-sealed-'+identity+'.stderr',
'native-sealed-'+identity+'.json','native-sealed-'+identity+'.stdout','native-sealed-'+identity+'.stderr',
'fresh-install-'+identity+'-041.json','development-preparation-interruption.json','development-bunfixed-interruption-exit.json']
exit_receipt=json.loads((source/'development-bunfixed-interruption-exit.json').read_bytes())
active={'version':'0.4.1','commit':build['head'],'package_sha256':build['archive_sha256']}
prior={'version':'0.3.1','commit':'9af633252004a0ac8dd780d5fc12e9644f97bb0c','package_sha256':'2aada985dd26dee4ffb4da1d3348c43c76cff2e697d04028cfbba9d6f1b11a24'}
normal='synthetic-normal-041-operation';results=[]
for name in ['synthetic-complete-baseline','actual-historical-040-whole-receipt','missing-whole-receipt']:
 with tempfile.TemporaryDirectory(prefix='pr16-whole-binding-') as temp:
  root=Path(temp)
  shutil.copy2(out/'certify_release.py',root/'certify_release.py')
  for filename in completed:shutil.copy2(source/filename,root/filename)
  fixtures={
   'development-bunfixed-update.json':{'status':'PASS','operation':normal,'active_identity':active},
   'development-bunfixed-rollback.json':{'status':'PASS','operation':normal,'active_identity':prior},
   'development-bunfixed-interruption-recovery.json':{'status':'PASS','operation':exit_receipt['operation'],'active_identity':prior},
   'development-bunfixed-boot.json':{'status':'PASS','operation':normal,'active_identity':active,'bun_version':'1.4.3','manual_service_start_after_reboot':False},
   'whole-guest-program-coverage.json':{'status':'PASS','version':'0.4.1','program_commit':build['head'],'archive_sha256':build['archive_sha256'],'program_targets':143,'backup_archive':'synthetic-041-backup'},
   'whole-guest-recovery.json':{'status':'PASS','archive':'synthetic-041-backup','source_guest':101,'restored_guest':110,'network_disconnected':True,'application_services_masked':True,'cases':[{'case':c,'status':'PASS'} for c in ['baseline','interrupted','later-edit']]}}
  for filename,value in fixtures.items():
   value['synthetic_probe_only']=True;(root/filename).write_text(json.dumps(value))
  if name=='actual-historical-040-whole-receipt':shutil.copy2(old/'whole-guest-recovery.json',root/'whole-guest-recovery.json')
  if name=='missing-whole-receipt':(root/'whole-guest-recovery.json').unlink()
  r=subprocess.run([sys.executable,'-B',str(root/'certify_release.py')],env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True)
  (out/(name+'.stdout')).write_text(r.stdout);(out/(name+'.stderr')).write_text(r.stderr)
  certpath=root/'RELEASE-CERTIFICATE.json';row={'case':name,'exit_code':r.returncode,'certificate_written':certpath.exists(),'synthetic_pending_receipts':True}
  if certpath.exists():
   cert=json.loads(certpath.read_bytes());row.update(output_version=cert['version'],output_program_commit=cert['program_commit'],output_archive_sha256=cert['archive_sha256'],whole_backup_archive=cert['whole_guest_history_recovery']['archive'],coverage_backup_archive=cert['whole_guest_program_coverage']['backup_archive'])
  results.append(row)
(out/'whole-receipt-binding-results.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
assert [r['certificate_written'] for r in results]==[True,True,False]
