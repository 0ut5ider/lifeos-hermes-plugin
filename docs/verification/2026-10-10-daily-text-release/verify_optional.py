# ABOUTME: Confirms the disabled Pulse core-file editor through actual installed HTTP routes.
# ABOUTME: Checks that refused editor operations preserve the selected Hermes configuration.
import json
from pathlib import Path
import urllib.error
import urllib.request

stage=Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
prepared=json.loads((stage/'applications-prepared.json').read_text())
profile=Path(prepared['profile'])
before=(profile/'config.yaml').read_bytes()
client=urllib.request.build_opener(urllib.request.ProxyHandler({}))
observations=[]
for method,path,content in [('GET','/api/hermes',None),('GET','/api/hermes/',None),
    ('GET','/api/hermes/log-analysis',None),('GET','/api/hermes/file/principal-memory',None),
    ('PUT','/api/hermes/file/config',{'content':'Synthetic refused editor write'}),
    ('POST','/api/hermes/remount',None)]:
    request=urllib.request.Request('http://127.0.0.1:18837'+path,method=method,
        data=None if content is None else json.dumps(content).encode(),
        headers={} if content is None else {'Content-Type':'application/json'})
    try:reply=client.open(request,timeout=15)
    except urllib.error.HTTPError as error:reply=error
    with reply:
        body=reply.read().decode()
        row={'method':method,'path':path,'status':reply.status,'body':body}
    assert row['status']==404,row
    observations.append(row)
assert (profile/'config.yaml').read_bytes()==before
report={'status':'PASS','observations':observations,'configuration_preserved':True,
    'pulse_core_editor_enabled':False,'live_profile_changed':False}
(stage/'release-optional.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
