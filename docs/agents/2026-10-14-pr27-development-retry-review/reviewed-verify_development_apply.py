# ABOUTME: Verifies the actual owner-applied development package before private-model memory acceptance.
# ABOUTME: Exports only safe native verification receipts and leaves raw controlled conversations on the development guest.
import json,os,subprocess,time
from pathlib import Path

os.umask(0o077)
source=Path(__file__).resolve().parent
cache=Path('/home/outsider/.cache/lifeos-release-0.5.0-20261014')
out=cache/'development-retry-applied-verification'
assert not out.exists();out.mkdir(mode=0o700)
remote='root@192.168.8.252'
identifier='4eac8d1b398e47138d80f8b67b6df596'
job='/home/lifeos-hermes/.hermes/.lifeos-releases/'+identifier
python=job+'/python-environment/bin/python'
stage='/home/lifeos-hermes/releases/qualification-0.5.0'
operations=[]
def run(command,label,*,timeout=120):
 started=time.monotonic();r=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
 (out/(label+'.stdout')).write_text(r.stdout);(out/(label+'.stderr')).write_text(r.stderr)
 operations.append({'label':label,'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-started})
 (out/'operations.json').write_text(json.dumps(operations,indent=2)+'\n')
 assert r.returncode==0,label+' fails; inspect private operation metadata'
 return r.stdout
try:
 deadline=time.monotonic()+3600
 while True:
  value=json.loads(run(['ssh','-o','BatchMode=yes',remote,'cat '+job+'/status.json'],'selected-operation-status'))
  assert value['identifier']==identifier
  if value['state']=='applied':break
  assert value['state'] in {'ready','queued-apply','applying'},'The actual development operation does not apply'
  assert time.monotonic()<deadline,'The development application wait expires'
  time.sleep(20)
 command='runuser -u lifeos-hermes -- env HOME=/home/lifeos-hermes HERMES_HOME=/home/lifeos-hermes/.hermes '+python+' -B '
 text=run(['ssh','-o','BatchMode=yes',remote,command+stage+'/verify_promotion.py development '+identifier+' '+stage+'/development-prepromotion-baseline.json'],'verify-actual-development',timeout=1800)
 receipt=json.loads(text)
 assert receipt['status']=='PASS' and receipt['operation']==identifier
 assert receipt['active_identity']['commit']=='04efe633296eb2b1a1d95561ca6d3e9516cd47dc'
 assert receipt['active_identity']['package_sha256']=='a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813'
 (source/'development-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
 run(['ssh','-o','BatchMode=yes',remote,command+stage+'/run_development_owner_turn.py'],'actual-owner-conversations',timeout=600)
 run(['ssh','-o','BatchMode=yes',remote,command+stage+'/verify_development_owner_turn.py'],'verify-actual-owner-conversations',timeout=120)
 run(['scp',remote+':'+stage+'/release-owner-turn-verification.json',str(source/'development-owner-turn-verification.json')],'export-safe-owner-receipt')
 receipt=json.loads((source/'development-owner-turn-verification.json').read_bytes())
 assert receipt['status']=='PASS' and receipt['actual_write_and_fresh_conversation_read_verified'] is True
 (out/'process.done').write_text('0\n')
except BaseException:
 (out/'process.done').write_text('1\n');raise
