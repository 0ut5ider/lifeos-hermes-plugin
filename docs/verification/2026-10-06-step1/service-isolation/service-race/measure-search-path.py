# ABOUTME: Measures whether linking another disposable unit invalidates a bound service.
# ABOUTME: Uses real user systemd properties and restores the temporary unit after observation.
import json,subprocess,sys,tempfile
from pathlib import Path
from uuid import uuid4
sys.path.insert(0,'/home/outsider/Projects/Hermes_agent/LifeOS_plugin/tests')
from test_profile_services import ProfileServicesTests
fixture=ProfileServicesTests()
fixture.setUp()
unit='lifeos-search-path-probe-'+uuid4().hex+'.service'
root=Path(__file__).resolve().parent
try:
 def properties():
  text=subprocess.check_output(['systemctl','--user','show',fixture.units['dashboard'],
    '--property=Id,ActiveState,MainPID,NeedDaemonReload','--no-pager'],text=True)
  return dict(line.split('=',1) for line in text.splitlines())
 before=properties()
 with tempfile.TemporaryDirectory(prefix='unit-search-probe-') as text:
  path=Path(text)/unit
  path.write_text('[Unit]\nDescription=Synthetic search path probe\n[Service]\nType=oneshot\nExecStart=/usr/bin/true\n')
  subprocess.run(['systemctl','--user','--quiet','link','--runtime',str(path)],check=True,capture_output=True)
  linked=properties()
  subprocess.run(['systemctl','--user','daemon-reload'],check=True,capture_output=True)
  reloaded=properties()
  subprocess.run(['systemctl','--user','--quiet','disable','--runtime',unit],check=True,capture_output=True)
  disabled=properties()
  subprocess.run(['systemctl','--user','daemon-reload'],check=True,capture_output=True)
  result={'before':before,'another_unit_linked':linked,'after_reload':reloaded,'another_unit_disabled':disabled,'after_second_reload':properties()}
  (root/'search-path-result.json').write_text(json.dumps(result,indent=2)+'\n')
  print(json.dumps(result,indent=2))
finally:
 subprocess.run(['systemctl','--user','--quiet','disable','--runtime',unit],check=True,capture_output=True)
 subprocess.run(['systemctl','--user','daemon-reload'],check=True,capture_output=True)
 fixture.doCleanups()
