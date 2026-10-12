# ABOUTME: Selects a sealed integration package while preserving the existing profile and native store.
# ABOUTME: Drains owner services, retains exact prior programs, and records recoverable deployment state.
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone

parser=argparse.ArgumentParser()
parser.add_argument('package',type=Path)
parser.add_argument('--archive-sha256',required=True)
parser.add_argument('--apply',action='store_true')
args=parser.parse_args()
os.umask(0o077)
base=Path('/home/lifeos-hermes');profile=base/'.hermes';package=args.package.resolve()
assert package.parent==base/'releases' and re.fullmatch('[0-9a-f]{64}',args.archive_sha256)
assert hashlib.sha256(Path(str(package)+'.tgz').read_bytes()).hexdigest()==args.archive_sha256
manifest=json.loads((package/'DAILY-CANDIDATE.json').read_text())
configuration=json.loads((profile/'lifeos-memory.json').read_text())
root=Path(configuration['root']);assert root.resolve()==root and root.is_dir()
os.environ.update(HERMES_HOME=str(profile),XDG_RUNTIME_DIR='/run/user/'+str(os.getuid()),
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/'+str(os.getuid())+'/bus',PYTHONDONTWRITEBYTECODE='1')
sys.path[:0]=[str(package),str(package/'hermes')]
from ruamel.yaml import YAML
from lifeos_hook_bridge import install_source,release_version
from lifeos_hook_bridge.profile_services import ProfileServices
from lifeos_hook_bridge.memory_transaction import publish
from lifeos_hook_bridge.installation_lock import installation_lock
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
assert release_version.versions(package)==manifest['version']
hermes=install_source.validate_supported_hermes(package/'hermes')
lifeos=install_source.validate_prepared_lifeos(package/'lifeos')
assert all(sha(package/name)==digest for name,digest in manifest['plugin_files'].items())
bridge=profile/'plugins/lifeos-hook-bridge'
services=ProfileServices(profile,root)
preview=services.preview()
native_changes=[]
native=package/'lifeos/LifeOS/install'
for source in native.rglob('*'):
    relative=source.relative_to(native)
    if ({'USER','MEMORY','node_modules','__pycache__'}&set(relative.parts) or not source.is_file()
            or relative.parts[0] not in {'LIFEOS','hooks'}
            or str(relative)=='LIFEOS/DOCUMENTATION/ARCHITECTURE_SUMMARY.md'):
        continue
    target=root/relative
    if not target.is_file() or sha(target)!=sha(source):native_changes.append((target,source))
launchers=[]
for unit in ('hermes-gateway.service','hermes-dashboard.service'):
    text=(base/'.config/systemd/user'/unit).read_text()
    command=next(line.split('=',1)[1] for line in text.splitlines() if line.startswith('ExecStart='))
    executable=Path(shlex.split(command)[0])
    assert executable.is_absolute() and executable.is_file() and executable.stat().st_uid==os.getuid()
    launchers.append(executable)
launchers=sorted(set(launchers))
evidence=base/'deployment'/('release-'+manifest['version']+'-'+manifest['head'][:8])
report={'version':manifest['version'],'commit':manifest['head'],'package_sha256':args.archive_sha256,
    'native_program_changes':len(native_changes),'active':release_version.status(profile,bridge)['active'],
    'model_settings_preserved':True,'data_preserved':True,'apply_requested':args.apply}
if not args.apply:
    print(json.dumps(report));sys.exit(0)
assert not evidence.exists(),'The retained deployment already exists'
evidence.mkdir(parents=True,mode=0o700)
runtime=base/'runtime/releases'/(manifest['version']+'-'+manifest['head'][:8])/'hermes'
assert not runtime.exists()
runtime.parent.mkdir(parents=True,mode=0o700)
shutil.copytree(package/'hermes',runtime)
dashboard=base/'releases/hermes-dashboard-078d6da5.tgz'
assert sha(dashboard)=='078d6da534408339fefcb3893431835ccfc7ce9483cc85a46ebf6b917e8cb2ee'
import tarfile
with tarfile.open(dashboard) as bundle:bundle.extractall(runtime,filter='data')
before_yaml=(profile/'config.yaml').read_bytes()
yaml=YAML()
selected=yaml.load(before_yaml)
before_model=json.dumps({'model':selected.get('model'),
    'tiers':{k:v for k,v in selected['plugins']['entries']['lifeos-hook-bridge']['settings'].items()
        if k.startswith(('haiku','sonnet','opus','fable','pinned'))}},sort_keys=True)
old_programs=evidence/'plugin-before'
shutil.copytree(bridge,old_programs,symlinks=True)
retained=[]
def save(path):
    path=Path(path)
    before=path.read_bytes() if path.is_file() else None
    mode=path.stat().st_mode & 0o777 if before is not None else 0o600
    name=str(len(retained))+'.before'
    if before is not None:publish(evidence/name,before)
    retained.append({'path':str(path),'retained':name if before is not None else None,'mode':mode,
        'before_sha256':None if before is None else hashlib.sha256(before).hexdigest()})
    publish(evidence/'retained-files.json',json.dumps(retained,indent=2).encode())
def data_hashes():
    paths=[profile/'lifeos-memory.json',profile/'.env']
    for directory in [root/'LIFEOS/USER',root.parent/'.local/state/lifeos/atlas',profile/'memories']:
        if directory.is_dir():paths.extend(p for p in directory.resolve().rglob('*') if p.is_file() and not p.is_symlink())
    return {str(p):sha(p) for p in paths if p.is_file()}
with installation_lock(profile) as lease:
    services=ProfileServices(profile,root,installation_lease=lease)
    services.drain(signature=preview['signature']);services.verify_stopped()
    before_data=data_hashes()
    publish(evidence/'data-hashes-before.json',json.dumps(before_data,indent=2).encode())
    try:
        for path in [profile/'config.yaml',profile/'integration-release.json',profile/'daily-release.json',*launchers]:save(path)
        new=evidence/'plugin-incoming'
        shutil.copytree(package/'lifeos_hook_bridge',new)
        bridge.rename(evidence/'plugin-outgoing')
        new.rename(bridge)
        for target,source in native_changes:
            assert not target.is_symlink()
            save(target);publish(target,source.read_bytes(),mode=source.stat().st_mode & 0o777)
        command='#!/bin/sh\nexport PYTHONPATH='+shlex.quote(str(runtime))+'\nexec '+shlex.quote(sys.executable)+' -B -m hermes_cli.main "$@"\n'
        for launcher in launchers:publish(launcher,command.encode(),mode=0o700)
        if native_changes:
            selected['plugins']['entries']['lifeos-hook-bridge']['settings']['lifeos_source_dir']=str(native)
            import io
            stream=io.StringIO();yaml.dump(selected,stream);publish(profile/'config.yaml',stream.getvalue().encode())
            from lifeos_hook_bridge import version_drift
            from lifeos_hook_bridge.mount_transaction import MountTransaction
            baseline=version_drift.default_baseline_path(root.parent)
            for path in [baseline,root/'settings.json',profile/'SOUL.md',profile/'AGENTS.md']:save(path)
            environment=install_source.memory_administration().mount_environment(root,profile)
            environment['PATH']=str(base/'.local/bin')+':'+str(Path(sys.executable).parent)+':'+environment.get('PATH','')
            data=json.dumps(version_drift.create_baseline(native,root)).encode()
            MountTransaction(root,profile,baseline).execute(environment,str(base/'.local/bin/bun'),str(launchers[0]),baseline_data=data)
        record={'format':1,'version':manifest['version'],'commit':manifest['head'],
            'package_sha256':args.archive_sha256,'installed_at':datetime.now(timezone.utc).isoformat(),
            'plugin_files':{str(Path(k).relative_to('lifeos_hook_bridge')):v for k,v in manifest['plugin_files'].items()},
            'upstream':{'hermes':hermes['base_commit'],'lifeos':lifeos['upstream_commit']},
            'patches':{'hermes':len(hermes['patches']),'lifeos':len(lifeos['patches'])},'operators':manifest['operators']}
        publish(profile/'integration-release.json',json.dumps(record,indent=2).encode())
        if (evidence/'retained-files.json').is_file() and any(row['path']==str(profile/'daily-release.json') and row['retained'] for row in retained):
            daily={'version':manifest['version'],'program_head':manifest['head'],'plugin_files':manifest['plugin_files'],
                'hermes_manifest':hermes,'lifeos_manifest':lifeos,'operators':manifest['operators'],'archive_sha256':args.archive_sha256}
            publish(profile/'daily-release.json',json.dumps(daily,indent=2).encode())
        assert data_hashes()==before_data,'Existing store or credentials change during program selection'
        after_yaml=yaml.load((profile/'config.yaml').read_bytes())
        after_model=json.dumps({'model':after_yaml.get('model'),'tiers':{k:v for k,v in after_yaml['plugins']['entries']['lifeos-hook-bridge']['settings'].items()
            if k.startswith(('haiku','sonnet','opus','fable','pinned'))}},sort_keys=True)
        assert after_model==before_model
        status=release_version.status(profile,bridge)
        assert status['active']['verification']=='verified',status
        services.resume()
        report.update(status='SELECTED',active=status['active'],services=services.status(),
            preserved_files=len(before_data),retained_program_files=len(retained),runtime=str(runtime))
        publish(evidence/'selection.json',json.dumps(report,indent=2).encode())
    except BaseException:
        services.drain(signature=services.preview()['signature']) if services.status()['state']=='active' else services.verify_stopped()
        if (evidence/'plugin-outgoing').exists():
            bridge.rename(evidence/'plugin-failed');(evidence/'plugin-outgoing').rename(bridge)
        for row in reversed(retained):
            path=Path(row['path'])
            if row['retained'] is None:path.unlink(missing_ok=True)
            else:publish(path,(evidence/row['retained']).read_bytes(),mode=row['mode'])
        services.resume()
        raise
print(json.dumps({k:v for k,v in report.items() if k!='runtime'}))
