# ABOUTME: Prepares an isolated stock Hermes dashboard from previously qualified public test inputs.
# ABOUTME: Creates only synthetic credentials and leaves Discord and model delivery inactive.
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import pwd
import secrets
import shlex
import subprocess
import sys
import tarfile


home=Path('/home/lifeos-hermes')
profile=home/'.hermes'
stage=home/'releases/portability-acceptance-20261015'
runtime=home/'runtime/stock-hermes'


def configure():
    from ruamel.yaml import YAML
    sys.path.insert(0,str(runtime))
    from plugins.dashboard_auth.basic import hash_password
    if (profile/'config.yaml').exists():raise RuntimeError('The synthetic profile is already configured')
    password=secrets.token_urlsafe(32)
    credentials=home/'install-input/dashboard-access.json'
    credentials.write_text(json.dumps({'username':'portability-owner','password':password})+'\n')
    credentials.chmod(0o600)
    model={'default':'flashnext-w4a16-fp8ple','provider':'custom','base_url':'http://127.0.0.1:9/v1','api_mode':'chat_completions'}
    tiers={**{name+'_model':model['default'] for name in ('haiku','sonnet','opus','fable')},
        'haiku_effort':'low','sonnet_effort':'medium','opus_effort':'xhigh','fable_effort':'xhigh'}
    settings={'model':model,'agent':{'max_turns':10},'memory':{'provider':'builtin'},
        'plugins':{'enabled':[],'entries':{'lifeos-hook-bridge':{'settings':tiers}}},
        'dashboard':{'public_url':'http://192.168.8.244:18819',
            'basic_auth':{'username':'portability-owner','password_hash':hash_password(password)}}}
    stream=io.StringIO();YAML().dump(settings,stream)
    (profile/'config.yaml').write_text(stream.getvalue());(profile/'config.yaml').chmod(0o600)
    (profile/'.env').write_text('CUSTOM_API_KEY='+secrets.token_urlsafe(32)+'\n');(profile/'.env').chmod(0o600)
    python=home/'stock-venv/bin/python'
    launcher=home/'.local/bin/hermes'
    launcher.write_text('#!/bin/sh\nexport PYTHONPATH='+shlex.quote(str(runtime))+'\nexec '+shlex.quote(str(python))+' -B -m hermes_cli.main "$@"\n')
    launcher.chmod(0o700)
    unit=home/'.config/systemd/user/hermes-dashboard.service'
    unit.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    environment={'HOME':str(home),'HERMES_HOME':str(profile),'PYTHONPATH':str(runtime),
        'PATH':str(home/'.local/bin')+':/usr/bin:/bin','TZ':'America/Toronto','LANG':'C.UTF-8',
        'PYTHONDONTWRITEBYTECODE':'1','BUN_CONFIG_NO_AUTO_INSTALL':'1'}
    lines=['[Unit]','Description=Stock Hermes portability fixture','[Service]','Type=simple','UMask=0077',
        'KillMode=control-group','TimeoutStopSec=45','Restart=on-failure','WorkingDirectory='+str(home),
        'ExecStart='+str(launcher)+' dashboard --isolated --skip-build --no-open --host 127.0.0.1 --port 18819']
    lines.extend('Environment="'+key+'='+value+'"' for key,value in environment.items())
    lines.extend(['[Install]','WantedBy=default.target'])
    unit.write_text('\n'.join(lines)+'\n');unit.chmod(0o600)
    os.environ.update(environment,XDG_RUNTIME_DIR='/run/user/'+str(os.getuid()),
        DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/'+str(os.getuid())+'/bus')
    subprocess.run(['systemctl','--user','daemon-reload'],check=True,capture_output=True)
    subprocess.run(['systemctl','--user','enable','--now',unit.name],check=True,capture_output=True)
    (stage/'stock-dashboard.json').write_text(json.dumps({'status':'STARTED','guest':110,'address':'192.168.8.244',
        'hermes_commit':'71d34bad1045610252eda02ee79549436896e784','hermes_patches':0,
        'model_delivery_enabled':False,'discord_enabled':False,'production_changed':False},indent=2)+'\n')


def bootstrap(archive_sha256):
    folder=Path('/root/lifeos-portability-bootstrap');folder.mkdir(mode=0o700,exist_ok=True)
    archive=folder/'stock-bootstrap.tgz'
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=archive_sha256:raise RuntimeError('The bootstrap archive differs')
    environment={**os.environ,'DEBIAN_FRONTEND':'noninteractive'}
    for label,command in [('apt-update',['apt-get','update']),('apt-install',['apt-get','install','-y','ca-certificates','git','curl','unzip','xz-utils','dbus-user-session','sudo'])]:
        with (folder/(label+'.stdout')).open('w') as out,(folder/(label+'.stderr')).open('w') as err:
            subprocess.run(command,env=environment,stdout=out,stderr=err,check=True,timeout=600)
    try:owner=pwd.getpwnam('lifeos-hermes')
    except KeyError:
        subprocess.run(['useradd','--create-home','--shell','/bin/bash','lifeos-hermes'],check=True,capture_output=True)
        owner=pwd.getpwnam('lifeos-hermes')
    if Path(owner.pw_dir)!=home:raise RuntimeError('The test account has another home')
    home.chmod(0o700)
    subprocess.run(['tar','-xzf',str(archive),'-C',str(home)],check=True,capture_output=True)
    stage.mkdir(parents=True,mode=0o700)
    (home/'install-input').mkdir(mode=0o700)
    runtime.mkdir(parents=True,mode=0o700)
    source=home/'releases/stock-source.tar'
    if hashlib.sha256(source.read_bytes()).hexdigest()!='e8acf0dfc6329d85b75c5625412c463798d1cd3ae6507aaf88b717dc74e2c6fc':
        raise RuntimeError('The pinned stock source archive differs')
    with tarfile.open(source) as data:data.extractall(runtime,filter='data')
    with tarfile.open(home/'releases/hermes-dashboard.tgz') as data:data.extractall(runtime,filter='data')
    interpreter=home/'.hermes/tools/python-3.14.7+20260901-linux-x64/bin/python3.14'
    for name in ('python','python3','python3.14'):
        path=home/'stock-venv/bin'/name
        path.unlink(missing_ok=True);path.symlink_to(interpreter)
    program=stage/'bootstrap_guest.py'
    program.write_bytes(Path(__file__).read_bytes())
    os.chown(home,owner.pw_uid,owner.pw_gid)
    for path in home.rglob('*'):os.chown(path,owner.pw_uid,owner.pw_gid,follow_symlinks=False)
    subprocess.run(['loginctl','enable-linger','lifeos-hermes'],check=True,capture_output=True)
    subprocess.run(['systemctl','start','user@'+str(owner.pw_uid)+'.service'],check=True,capture_output=True)
    subprocess.run(['runuser','-u','lifeos-hermes','--',str(home/'stock-venv/bin/python'),str(program),'--configure'],
        check=True,capture_output=True,timeout=120)
    (folder/'bootstrap.done').write_text('0\n')


if __name__=='__main__':
    os.umask(0o077)
    parser=argparse.ArgumentParser()
    parser.add_argument('--configure',action='store_true')
    parser.add_argument('--archive-sha256')
    args=parser.parse_args()
    if args.configure:configure()
    else:bootstrap(args.archive_sha256)
