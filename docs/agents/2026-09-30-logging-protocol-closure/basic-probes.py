# ABOUTME: Checks recognizable Basic authorization components in native hook results.
# ABOUTME: Records synthetic leak counts and reviewed source hashes.
import base64
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('basic_test_fixture',ROOT/'development/tests/test_capture.py')
fixture=importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
case=fixture.OverlayTests()
password='SYNTHETIC-BASIC-PASSWORD-483729'
encoded=base64.b64encode(('synthetic-user:'+password).encode()).decode()
setup='''
def invoke(bridge):
    import json,sys,base64
    password='SYNTHETIC-BASIC-PASSWORD-483729'
    encoded=base64.b64encode(('synthetic-user:'+password).encode()).decode()
    value={'headers':{'Authorization':'Basic '+encoded},'echo':password,'encoded_echo':encoded}
    path=bridge.root/'basic-hook.py'
    path.write_text('import json\\nprint(json.dumps('+repr(value)+'))\\n')
    bridge.hooks['PreToolUse'][0]['hooks'][0]['command']=sys.executable+' '+str(path)
    return bridge.pre_tool_call('terminal',{'command':'pwd'},session_id='basic')
'''
try:
    hooks={'PreToolUse':[{'hooks':[{'type':'command','command':'true'}]}]}
    _,baseline,_=case.run_bridge(hooks,'invoke(bridge)',setup=setup,traced=False)
    root,observed,events=case.run_bridge(hooks,'invoke(bridge)',setup=setup)
    password_stages=[]
    encoded_stages=[]
    for event in events:
        if not event.get('data_ref'):
            continue
        raw=gzip.decompress((root/'capture'/event['data_ref']['path']).read_bytes()).decode()
        if password in raw:
            password_stages.append(event['stage'])
        if encoded in raw:
            encoded_stages.append(event['stage'])
    result={'same_native_outcome':baseline==observed,'password_leak_stages':sorted(set(password_stages)),
        'encoded_leak_stages':sorted(set(encoded_stages)),'event_count':len(events),
        'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'development/hook_capture').glob('*.py')}}
    print(json.dumps(result,indent=2,sort_keys=True))
finally:
    case.doCleanups()
