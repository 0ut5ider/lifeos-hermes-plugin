# ABOUTME: Verifies automatic user-service startup and the selected Bun runtime after a development guest reboot.
# ABOUTME: Reports safe unit metadata without starting services or exporting account configuration.
import json,os,subprocess,sys
from pathlib import Path
home=Path.home();environment=dict(os.environ,XDG_RUNTIME_DIR='/run/user/'+str(os.getuid()),DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/'+str(os.getuid())+'/bus',PYTHONDONTWRITEBYTECODE='1')
profile=home/'.hermes';job=profile/'.lifeos-releases'/sys.argv[1]
request=json.loads((job/'request.json').read_bytes())
assert json.loads((job/'status.json').read_bytes())['state']=='applied'
version=subprocess.run([str(home/'.local/bin/hermes'),'lifeos-version'],env=environment,capture_output=True,text=True,check=True,timeout=90)
active=json.loads(version.stdout)['active'];assert active['verification']=='verified'
identity={key:active[key] for key in ('version','commit','package_sha256')}
assert identity=={key:request[key] for key in identity}
assert identity['version']=='0.4.1' and identity['commit']=='96f4f8fbef21f53ee704eb16f34698bc35b5dc77'
boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot_id!=sys.argv[2]
units={}
for name in ('hermes-gateway.service','hermes-dashboard.service','com.lifeos.pulse.service'):
 result=subprocess.run(['systemctl','--user','show',name,'-p','ActiveState','-p','SubState','-p','UnitFileState','-p','NRestarts'],env=environment,capture_output=True,text=True,check=True,timeout=30)
 data=dict(line.split('=',1) for line in result.stdout.splitlines());assert data['ActiveState']=='active' and data['SubState']=='running' and data['UnitFileState']=='enabled',name
 assert data['NRestarts']=='0',name
 units[name]=data
bun=subprocess.run([str(home/'.local/bin/bun'),'--version'],capture_output=True,text=True,check=True,timeout=10);assert bun.stdout.strip()=='1.4.3' and not bun.stderr
print(json.dumps({'status':'PASS','operation':sys.argv[1],'active_identity':identity,'before_boot_id':sys.argv[2],'boot_id':boot_id,'units':units,'bun_version':bun.stdout.strip(),'manual_service_start_after_reboot':False,'daily_server_changed':False},indent=2))
