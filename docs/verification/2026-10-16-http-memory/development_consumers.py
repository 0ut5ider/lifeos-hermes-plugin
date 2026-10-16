# ABOUTME: Checks removal process boundaries under the development service account.
# ABOUTME: Uses disposable profiles and owned units without selecting another release.
import os,json,subprocess,time
from pathlib import Path
base=Path(__file__).resolve().parent
source=base/'source'
python='/home/lifeos-hermes/.hermes/.lifeos-releases/29cf5b400b4c48c783eb72d3774c838f/python-environment/bin/python'
env=dict(os.environ,HOME='/home/lifeos-hermes',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(source/'tests')+':'+str(source),PATH='/home/lifeos-hermes/.local/bin:/usr/local/bin:/usr/bin:/bin',XDG_RUNTIME_DIR='/run/user/1008',DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1008/bus')
started=time.monotonic()
with (base/'tests.stdout').open('w') as out,(base/'tests.stderr').open('w') as err:
 result=subprocess.run([python,'-W','error::ResourceWarning','-m','unittest','test_removal_consumers','test_removal_coordinator','-v'],cwd=source,env=env,stdout=out,stderr=err,timeout=180)
receipt={'status':'PASS' if result.returncode==0 else 'FAIL','exit_code':result.returncode,'elapsed_seconds':time.monotonic()-started,'test_data':'synthetic','test_assertions_changed':False,'product_policy_changed':False,'selected_development_release_changed':False,'daily_changed':False}
(base/'verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
(base/'verification.done').write_text(str(result.returncode)+'\n')
