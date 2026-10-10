# ABOUTME: Restores retained release bytes and then reselects the final isolated candidate.
# ABOUTME: Drains actual services and verifies synthetic user data, Atlas state, and configuration preservation.
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys

stage=Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
prepared=json.loads((stage/'applications-prepared.json').read_text())
profile,root=Path(prepared['profile']),Path(prepared['installed'])
sys.path[:0]=[str(profile/'plugins'),str(stage/'package/hermes')]
module=lambda name:importlib.import_module('lifeos-hook-bridge.'+name)
os.environ.update(HOME=str(root.parent),HERMES_HOME=str(profile),XDG_RUNTIME_DIR='/run/user/1008',
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1008/bus')
units=json.loads((stage/'application-units.json').read_text())['units']
services=module('profile_services').ProfileServices(profile,root,units=units)
publish=module('memory_transaction').publish
manifest_path=stage/'APPLICATION-CANDIDATE.json'
manifest=manifest_path.read_bytes()
head=json.loads(manifest)['head']
retained=stage/('atlas-selection-retained-'+head[:8])
rows=json.loads((retained/'files.json').read_text())
services.drain(signature=services.preview()['signature'])
services.verify_stopped()
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
selected={Path(row['path']):(Path(row['path']).read_bytes(),row['mode']) for row in rows}
paths=[profile/'config.yaml',profile/'lifeos-memory.json']
user=root/'LIFEOS/USER'
paths.extend(p for p in user.resolve().rglob('*') if p.is_file() and not p.is_symlink())
atlas=root.parent/'.local/state/lifeos/atlas'
paths.extend(p for p in atlas.rglob('*') if p.is_file())
preserved={str(p):sha(p) for p in paths}
try:
    for row in rows:
        path=Path(row['path'])
        assert sha(path)==row['after_sha256']
        if row['retained'] is None:path.unlink()
        else:
            data=(retained/row['retained']).read_bytes()
            assert hashlib.sha256(data).hexdigest()==row['before_sha256']
            publish(path,data,mode=row['mode'])
    publish(manifest_path,(retained/'APPLICATION-CANDIDATE.json').read_bytes())
    services.resume()
    assert services.status()['state']=='active'
    assert {str(p):sha(p) for p in paths}==preserved
    prior=json.loads(manifest_path.read_text())['head']
    assert prior!=head
finally:
    services.drain(signature=services.preview()['signature'])
    services.verify_stopped()
    for path,(content,mode) in selected.items():publish(path,content,mode=mode)
    publish(manifest_path,manifest)
    services.resume()
assert services.status()['state']=='active'
assert {str(p):sha(p) for p in paths}==preserved
assert manifest_path.read_bytes()==manifest
report={'status':'PASS','head':head,'retained_head':prior,'restored_files':len(rows),
    'preserved_file_count':len(preserved),'actual_services_restarted_for_both_versions':True,
    'configuration_and_synthetic_data_preserved':True,'final_candidate_reselected':True,
    'live_profile_changed':False}
(stage/'release-rollback.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
