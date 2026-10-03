# ABOUTME: Checks environment projection and echo scrubbing at the recorder boundary.
# ABOUTME: Uses private disposable artifacts and synthetic secret values.
import gzip
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'development'))
from hook_capture.store import Recorder
secret='SYNTHETIC-ENV-VALUE-REVIEW-8814'
env={'CUSTOM_PROVIDER_VALUE':secret,'LANG':'C.UTF-8','LIFEOS_CHILD_EFFORT':'high'}
for case in ('env','environment','ENV','outer_json','alias','later_echo','bytes_json'):
    with tempfile.TemporaryDirectory() as tmp:
        recorder=Recorder(Path(tmp),'synthetic-review')
        if case in ('env','environment','ENV'): value={case:env,'echo':secret,'prompt':'Ordinary synthetic prompt remains useful'}
        elif case=='outer_json': value=json.dumps({'options':{'environment':env},'echo':secret})
        elif case=='alias': value={'unlabeled_alias':env,'options':{'env':env},'echo':secret}
        elif case=='later_echo':
            recorder.artifact({'env':env}); value={'echo':secret,'prompt':'Ordinary synthetic prompt remains useful'}
        else: value=json.dumps({'env':env,'echo':secret}).encode()
        ref=recorder.artifact(value); data=json.loads(gzip.decompress((Path(tmp)/ref['path']).read_bytes()))
        if case=='bytes_json':
            import base64
            inspect=base64.b64decode(data['bytes']).decode()
        else: inspect=json.dumps(data)
        print(json.dumps({'case':case,'secret_retained':secret in inspect,'clean':data},sort_keys=True))
        assert secret not in inspect
        if case in ('env','environment','ENV','later_echo'): assert 'Ordinary synthetic prompt remains useful' in inspect
