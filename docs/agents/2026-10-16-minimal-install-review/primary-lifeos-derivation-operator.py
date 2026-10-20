# ABOUTME: Derives pinned LifeOS files from local upstream objects and the distributed patch set.
# ABOUTME: Compares the result to qualified hashes without running hooks or touching user data.
import hashlib, io, json, runpy, subprocess, tarfile, tempfile
from pathlib import Path

r=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
o=r/'docs/agents/2026-10-16-minimal-install-review'
c=Path(__file__).parent
s=Path('/home/outsider/.cache/minimal-install-review-20261016/extract/lifeos')
module=runpy.run_path(str(r/'lifeos_hook_bridge/install_source.py'))
expected=json.loads((s/'lifeos-source-manifest.json').read_text())
archive=subprocess.check_output(['git','archive',module['SUPPORTED_LIFEOS_COMMIT']],cwd=s)
commands=[]
with tempfile.TemporaryDirectory(prefix='lifeos-derive-',dir=c) as td:
    root=Path(td)
    with tarfile.open(fileobj=io.BytesIO(archive)) as t:t.extractall(root,filter='data')
    for name in module['LIFEOS_PATCHES']:
        patch=str(r/'lifeos_hook_bridge/patches'/name)
        for argv in [['git','apply','--check',patch],['git','apply',patch]]:
            v=subprocess.run(argv,cwd=root,capture_output=True,text=True)
            commands.append({'argv':argv,'exit':v.returncode,'stdout':v.stdout,'stderr':v.stderr})
            assert v.returncode==0,commands[-1]
    caps=runpy.run_path(str(r/'lifeos_hook_bridge/native_capabilities.py'))
    caps['install_capability_record'](root/'LifeOS/install')
    digest=module['_tree_digest'](root)
    assert digest==expected['tree_sha256'],(digest,expected['tree_sha256'])
    result={'status':'PASS','upstream_commit':module['SUPPORTED_LIFEOS_COMMIT'],'upstream_archive_sha256':hashlib.sha256(archive).hexdigest(),'patches':len(module['LIFEOS_PATCHES']),'commands':commands,'derived_tree_sha256':digest,'qualified_tree_sha256':expected['tree_sha256'],'qualified_tree_matches':True,'services_or_hooks_executed':False,'network_used':False,'user_data_read':False,'limit':'Program-tree derivation only; not installation, dependency resolution, ownership activation, or live recovery qualification.'}
    (o/'primary-lifeos-derivation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='commands'}))
