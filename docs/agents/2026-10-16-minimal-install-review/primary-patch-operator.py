# ABOUTME: Measures plugin payloads and reversible patch mechanics in a disposable source copy.
# ABOUTME: Leaves release archives, running services, and repository source unchanged.
import gzip, hashlib, importlib.util, io, json, os, shutil, subprocess, tarfile, tempfile, time
from pathlib import Path

repo=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
out=Path(__file__).parent
archive=Path('/home/outsider/.cache/lifeos-release-0.7.3-20261016/packages/0.7.3-70fa8390.tgz')
spec=importlib.util.spec_from_file_location('source',repo/'lifeos_hook_bridge/install_source.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
result={'status':'RUNNING','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'runtime_behavior_tested':False,'servers_modified':False}
def save(): (out/'measurements.json').write_text(json.dumps(result,indent=2)+'\n')
save()
try:
    result['plugin_archives']={}
    for name in ['optional/lifeos_release_manager','lifeos_hook_bridge']:
        data=subprocess.check_output(['git','archive','HEAD','--',name],cwd=repo)
        result['plugin_archives'][name]={'git_tar_bytes':len(data),'gzip_level_9_bytes':len(gzip.compress(data,mtime=0))}
    with tarfile.open(archive,'r:gz') as t:
        stock=t.extractfile('stock-hermes.tgz').read()
    result['stock_archive']={'bytes':len(stock),'sha256':hashlib.sha256(stock).hexdigest()}
    with tempfile.TemporaryDirectory(prefix='patch-mechanics-',dir=out) as temp:
        root=Path(temp)
        with tarfile.open(fileobj=io.BytesIO(stock),mode='r:gz') as t:t.extractall(root,filter='data')
        def files():
            return {p.relative_to(root).as_posix():{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mode':p.stat().st_mode&0o777,'bytes':p.stat().st_size} for p in sorted(root.rglob('*')) if p.is_file()}
        before=files();commands=[]
        def run(*args):
            p=subprocess.run(args,cwd=root,capture_output=True,text=True)
            commands.append({'argv':list(args),'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
            assert p.returncode==0,commands[-1]
        for name in m.HERMES_PATCHES:
            patch=str(repo/'lifeos_hook_bridge/patches'/name)
            run('git','apply','--check',patch);run('git','apply',patch)
        after=files();changed=sorted(n for n in before.keys()|after.keys() if before.get(n)!=after.get(n))
        result['patches']={'groups':len(m.HERMES_PATCHES),'before_files':len(before),'after_files':len(after),'changed_paths':changed,'changed_path_count':len(changed),'patch_bytes':sum((repo/'lifeos_hook_bridge/patches'/n).stat().st_size for n in m.HERMES_PATCHES),'original_touched_file_bytes':sum(before[n]['bytes'] for n in changed if n in before)}
        for name in reversed(m.HERMES_PATCHES):
            patch=str(repo/'lifeos_hook_bridge/patches'/name)
            run('git','apply','--reverse','--check',patch);run('git','apply','--reverse',patch)
        restored=files();assert before==restored
        result['patches']['reverse_restores_all_regular_file_contents_and_modes']=True
        (out/'patch-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        (out/'stock-file-map.json').write_text(json.dumps(before,indent=2)+'\n')
    result['status']='PASS'
finally:
    save();(out/'measure.done').write_text('0\n' if result['status']=='PASS' else '1\n')
