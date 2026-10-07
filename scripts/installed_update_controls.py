# ABOUTME: Measures complete installed LifeOS update and restore with exact prepared source bundles.
# ABOUTME: Uses real dependency trees, native mount checks, and an isolated operating-system writer.
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys


def run(config_path, output, plugins, runtime_python=None):
    config=json.loads(config_path.read_text());spec=config['hermes']
    if runtime_python is not None:
        assert runtime_python.is_file(),'The installed Hermes interpreter is missing'
        spec['command'][0]=str(runtime_python)
    output.mkdir();os.chown(output,spec['uid'],spec['gid'])
    home=Path(spec['home_root'])/output.name;home.mkdir()
    prior_home=Path(spec['home_root'])/'full-installed-pinned'
    source_home=Path(spec['home_root'])/config['installed_home']
    for source,target in [(prior_home/'.claude',home/'.claude'),(source_home/'.hermes',home/'.hermes')]:
        subprocess.run(['cp','-a','--reflink=auto',str(source),str(target)],check=True)
    user=home/'.claude/LIFEOS/USER'
    if user.is_symlink():
        original=user.resolve();user.unlink();shutil.copytree(original,user)
    profile=home/'.hermes'
    plugindir=profile/'plugins'
    if plugindir.is_symlink():plugindir.unlink()
    plugindir.mkdir(exist_ok=True)
    if not (plugindir/'lifeos-hook-bridge').exists():
        (plugindir/'lifeos-hook-bridge').symlink_to(plugins.resolve()/'lifeos-hook-bridge',target_is_directory=True)
    worker_config=home/'fixture-config.json'
    worker_config.write_text(json.dumps({'hermes':spec,'installed_home':config['installed_home']}))
    for name in ['lifeos-memory.json','lifeos-memory-runtime.json']:
        (profile/name).unlink(missing_ok=True)
    (profile/'SOUL.md').write_text('Synthetic full update control.\n')
    (profile/'config.yaml').write_text('plugins:\n  enabled:\n    - lifeos-hook-bridge\nmodel:\n'
        '  provider: custom\n  api_mode: chat_completions\n  default: synthetic-update\n')
    for item in [home,*home.rglob('*')]:
        if not item.is_symlink():os.chown(item,spec['uid'],spec['gid'])
    environment={**spec['environment'],'HOME':str(home),'HERMES_HOME':str(profile),
        'XDG_RUNTIME_DIR':'/run/user/'+str(spec['uid']),
        'DBUS_SESSION_BUS_ADDRESS':'unix:path=/run/user/'+str(spec['uid'])+'/bus',
        'PYTHONPATH':str(plugins.resolve().parent)+':'+spec['environment']['PYTHONPATH']}
    arguments=[spec['command'][0],str(Path(__file__).resolve()),'worker',str(worker_config),str(output),str(home)]
    result=subprocess.run(arguments,env=environment,cwd=home,user=spec['uid'],group=spec['gid'],extra_groups=[],
        capture_output=True,text=True,timeout=600)
    (output/'worker.stdout').write_text(result.stdout);(output/'worker.stderr').write_text(result.stderr)
    assert result.returncode==0,(result.stdout[-2000:],result.stderr[-6000:])
    (output/'.done').write_text('0\n')


def worker(config_path, output, home):
    from lifeos_hook_bridge.update_transaction import apply_update,restore_update
    from lifeos_hook_bridge.version_drift import create_baseline,save_baseline,load_baseline,changed_paths
    from lifeos_hook_bridge.mount_transaction import MountTransaction
    from lifeos_hook_bridge.install_source import install_prepared_lifeos
    config=json.loads(config_path.read_text());spec=config['hermes']
    root=home/'.claude';profile=home/'.hermes';baseline=home/'baseline.json'
    selected=Path(spec['home_root'])/config['installed_home']/'candidate-review-final/LifeOS/install'
    prior=Path(spec['hook_root']).parent/'candidate-reminder-final/LifeOS/install'
    reference=home/'reference-home/.claude'
    receipt=install_prepared_lifeos(selected.parents[1],reference,home/'reference-failed')
    (output/'reference-installation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    save_baseline(create_baseline(prior,root),baseline)
    unit='lifeos-installed-update-control.service'
    launcher=home/'hermes';launcher.write_text('#!/bin/sh\nexec '+shlex.quote(spec['command'][0])+' -m hermes_cli.main "$@"\n');launcher.chmod(0o755)
    unit_file=home/unit
    unit_file.write_text('# ABOUTME: Runs the isolated installed update writer.\n# ABOUTME: Uses no production messaging configuration.\n'
        '[Service]\nType=simple\nExecStart=/usr/bin/sleep infinity\nRestart=no\n')
    events=[]
    def command(args):
        result=subprocess.run(args,capture_output=True,text=True,timeout=120)
        events.append({'command':args,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
        assert result.returncode==0,(args,result.stdout,result.stderr)
        return result.stdout.strip()
    def service(action):return command(['systemctl','--user',action,unit])
    def pid():return command(['systemctl','--user','show',unit,'-p','MainPID','--value'])
    def mount():MountTransaction(root,profile,baseline).execute(dict(os.environ),shutil.which('bun'),str(launcher))
    def renew(current,source):save_baseline(create_baseline(source,current),baseline,renew=True)
    def verify():
        assert service('is-active')=='active'
        command(['bun',str(root/'LIFEOS/TOOLS/Doctor.ts'),'--hooks'])
        command(['bun',str(root/'LIFEOS/HERMES/Mount.ts'),'--check'])
        command([str(launcher),'config','check'])
        assert not changed_paths(load_baseline(baseline,root),root)
    command(['systemctl','--user','link','--runtime',str(unit_file)])
    command(['systemctl','--user','daemon-reload']);service('start')
    def digest():return hashlib.sha256((root/'hooks/MemoryReviewFire.hook.ts').read_bytes()).hexdigest()
    before=digest();before_pid=pid()
    try:
        mount()
        # Native mount changes reviewed generated files; the baseline captures this exact initial state.
        save_baseline(create_baseline(prior,root),baseline,renew=True)
        applied=apply_update(root,profile,prior,selected,reference,baseline,home/'snapshot',
            stop=lambda:service('stop'),start=lambda:service('start'),mount=mount,renew=renew,verify=verify,
            verify_restored=verify)
        after=digest();after_pid=pid();assert before!=after and after_pid!=before_pid
        assert after==hashlib.sha256((selected/'hooks/MemoryReviewFire.hook.ts').read_bytes()).hexdigest()
        note=root/'LIFEOS/MEMORY/update-control-note.txt';note.write_text('PAIR_POST_UPDATE_MEMORY\n')
        restored=restore_update(home/'snapshot',stop=lambda:service('stop'),start=lambda:service('start'),verify=verify)
        assert digest()==before and note.read_text()=='PAIR_POST_UPDATE_MEMORY\n'
        report={'applied':applied,'restored':restored,'prior_review_sha256':before,'selected_review_sha256':after,
            'restored_review_sha256':digest(),'prior_pid':before_pid,'updated_pid':after_pid,'restored_pid':pid(),
            'post_update_memory_preserved':True,'mount_and_doctor_checked':True,'events':events,
            'limit':'The isolated service is an operating-system writer. This control does not send gateway messages.'}
        (output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    finally:
        service('stop');command(['systemctl','--user','disable','--runtime',unit]);command(['systemctl','--user','daemon-reload'])
        (output/'events.json').write_text(json.dumps(events,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['run','worker']);parser.add_argument('paths',nargs='+',type=Path)
    args=parser.parse_args()
    if args.action=='run':run(*(path.resolve() if index<3 else path.absolute()
                              for index,path in enumerate(args.paths)))
    else:worker(*args.paths)
