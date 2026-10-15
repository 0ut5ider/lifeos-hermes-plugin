# ABOUTME: Refuses cleanup of a guest without the exact disposable identity and owned volume.
# ABOUTME: Uses configuration strings only and performs no Proxmox operations.
import json
from cleanup_release_guests import validate_guest
base={'hostname':'lifeos-050-daily-rehearsal','rootfs':'lifeos-050-tests:111/vm-111-disk-0.raw,size=120G','tags':'disposable;lifeos-test'}
assert validate_guest(111,base) is None
cases=[(102,base),(111,dict(base,hostname='lifeos-daily')),
 (111,dict(base,tags='production')),(111,dict(base,rootfs='local:111/vm-111-disk-0.raw,size=120G')),
 (111,dict(base,mp0='/personal,mp=/personal')),(111,dict(base,unused0='other:volume'))]
for guest,config in cases:
 try:validate_guest(guest,config)
 except (AssertionError,KeyError):pass
 else:raise AssertionError('Unsafe cleanup admitted')
print(json.dumps({'status':'PASS','positive':1,'refusals':len(cases),'remote_calls':False}))
