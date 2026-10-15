# ABOUTME: Waits for the already authorized daily worker and verifies its exact selected release.
# ABOUTME: Saves safe status and acceptance receipts without repeating installation or reading personal records.
import json,os,subprocess,time
from pathlib import Path
os.umask(0o077)
out=Path('/home/outsider/.cache/lifeos-release-0.5.0-20261014/daily-applied-verification')
assert not out.exists();out.mkdir(mode=0o700)
source=Path(__file__).resolve().parent
identifier='b9e873b251604202a58442b502a3c2b2'
job='/home/lifeos-hermes/.hermes/.lifeos-releases/'+identifier
stage='/home/lifeos-hermes/releases/qualification-0.5.0'
try:
 deadline=time.monotonic()+1800
 while True:
  r=subprocess.run(['ssh','-o','BatchMode=yes','root@192.168.8.253','cat '+job+'/status.json'],capture_output=True,text=True,timeout=30)
  assert r.returncode==0
  status=json.loads(r.stdout);assert status['identifier']==identifier
  (out/'last-status.json').write_text(json.dumps(status,indent=2)+'\n')
  if status['state']=='applied':break
  assert status['state'] in {'ready','queued-apply','applying'},'The actual daily release does not apply: '+status['state']
  assert time.monotonic()<deadline,'The daily application wait expires'
  time.sleep(15)
 command='runuser -u lifeos-hermes -- '+job+'/python-environment/bin/python -B '+stage+'/verify_promotion.py daily '+identifier+' '+stage+'/daily-prepromotion-baseline.json'
 result=subprocess.run(['ssh','-o','BatchMode=yes','root@192.168.8.253',command],capture_output=True,text=True,timeout=1800)
 (out/'verification.stdout').write_text(result.stdout);(out/'verification.stderr').write_text(result.stderr)
 assert result.returncode==0,'Daily installed verification refuses; inspect private operator output'
 receipt=json.loads(result.stdout);assert receipt['status']=='PASS' and receipt['server']=='daily' and receipt['operation']==identifier
 (source/'daily-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
 (out/'process.done').write_text('0\n')
except BaseException:
 (out/'process.done').write_text('1\n');raise
