# ABOUTME: Refuses other account services and processes that consume software selected for removal.
# ABOUTME: Inspects bounded owner metadata and exports no command text, environment, or credentials.
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess

from .release_catalog import ReleaseRejected


def _tokens(profile, installed):
    profile,installed=Path(profile).absolute(),Path(installed).absolute()
    return tuple(str(path).encode() for path in (installed,profile/'plugins/lifeos',profile.parent/'.local/bin/bun'))


def _expanded(data, profile):
    home=str(Path(profile).parent).encode()
    for prefix in (b'${HOME}',b'$HOME',b'%h',b'~'):
        data=data.replace(prefix+b'/',home+b'/')
    return data


def _consumes(data, profile, tokens):
    data=_expanded(data,profile)
    return any(token in data for token in tokens) or re.search(rb'(?<![A-Za-z0-9_./-])bun(?![A-Za-z0-9_.-])',data)


def _manager(*arguments):
    try:
        result=subprocess.run(['systemctl','--user',*arguments],capture_output=True,text=True,timeout=45)
    except (OSError,subprocess.TimeoutExpired) as error:
        raise ReleaseRejected('The account service consumer metadata is unavailable') from error
    if result.returncode or result.stderr or len(result.stdout)>4*1024*1024:
        raise ReleaseRejected('The account service consumer metadata is unsupported')
    return result.stdout


def _paths(value):
    if any(character in value for character in ('\\','"',"'")):
        raise ReleaseRejected('Escaped account service paths require review')
    paths=[Path(item) for item in value.split()]
    if any(not path.is_absolute() or '..' in path.parts for path in paths):
        raise ReleaseRejected('Account service definitions require absolute paths')
    return paths


def _definition(physical):
    descriptor=os.open(physical,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(descriptor,'rb') as stream:
        before=os.fstat(stream.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_uid not in {0,os.getuid()}
                or before.st_mode & 0o022 or before.st_size>1024*1024):
            raise ReleaseRejected('An account service has an unsupported definition')
        data=stream.read(1024*1024+1);after=os.fstat(stream.fileno())
    stamp=lambda value:(value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns,value.st_mode)
    if len(data)>1024*1024 or stamp(before)!=stamp(after) or stamp(after)!=stamp(physical.stat()):
        raise ReleaseRejected('An account service definition changes during inspection')
    return data,stamp(after)


def coordinator(profile, job):
    from .cli import read_private
    from .memory_workflow import _job
    from .release_programs import fingerprint
    job=Path(job).absolute()
    fixed,request=_job(profile,job.name)
    if fixed!=job or request['selection']['kind']!='removal':
        raise ReleaseRejected('The removal coordinator belongs to another workflow')
    launch=job/'launch.json'
    if not launch.exists() and not launch.is_symlink():return None
    admitted=read_private(launch)
    if (set(admitted)!={'unit'} or not isinstance(admitted['unit'],str)
            or re.fullmatch('lifeos-memory-'+job.name+'-[0-9a-f]{8}',admitted['unit']) is None):
        raise ReleaseRejected('The removal coordinator loses its exact launched unit')
    unit=admitted['unit']+'.service'
    properties=('MainPID','ControlGroup','FragmentPath','DropInPaths','Transient')
    values=dict(line.split('=',1) for line in _manager('show',unit,
        '--property='+','.join(properties),'--no-pager').splitlines() if line)
    fragment=Path('/run/user')/str(os.getuid())/'systemd/transient'/unit
    groups={line.removeprefix('0::') for line in Path('/proc/self/cgroup').read_text().splitlines()
        if line.startswith('0::')}
    if (set(values)!=set(properties) or values['MainPID']!=str(os.getpid()) or values['Transient']!='yes'
            or values['FragmentPath']!=str(fragment)
            or not values['ControlGroup'] or groups!={values['ControlGroup']}
            or not values['ControlGroup'].endswith('/'+unit)):
        raise ReleaseRejected('The running removal worker does not own its admitted coordinator unit')
    identity=fingerprint(fragment)
    if identity is None or identity['type']!='file':
        raise ReleaseRejected('The admitted removal coordinator loses its private definition')
    dropins={};tokens=_tokens(profile,Path(request['profile']).parent/'.claude')+(str(profile).encode(),)
    for path in _paths(values['DropInPaths']):
        physical=path.resolve(strict=True);data,stamp=_definition(physical)
        if path.resolve()!=physical or _consumes(data,profile,tokens):
            raise ReleaseRejected('A removal coordinator override consumes the reviewed integration programs or profile')
        dropins[physical]={'metadata':stamp,'sha256':hashlib.sha256(data).hexdigest()}
    return {'unit':unit,'fragment':fragment,'identity':identity,'group':values['ControlGroup'],'dropins':dropins}


def unit_files(profile, installed, *, known, coordinator=None):
    directories=[Path(profile).parent/'.config/systemd/user',
        *_paths(_manager('show','--property=UnitPath','--value'))]
    known={Path(path).absolute() for path in known};tokens=_tokens(profile,installed)+(str(profile).encode(),)
    paths=[];visited=set()
    while directories:
        directory=directories.pop()
        if not directory.exists():continue
        physical=directory.resolve(strict=True)
        if physical in visited:continue
        visited.add(physical)
        metadata=physical.stat()
        if not physical.is_dir() or metadata.st_uid not in {0,os.getuid()} or metadata.st_mode & 0o022:
            raise ReleaseRejected('Account service paths require trusted physical directories')
        for path in directory.iterdir():
            if path.is_dir():directories.append(path)
            else:paths.append(path)
        if len(paths)+len(visited)>20000:
            raise ReleaseRejected('The account service definition inventory exceeds its supported limit')
    import json
    units=json.loads(_manager('list-units','--all','--output=json','--no-pager'))
    if not isinstance(units,list) or len(units)>4096:
        raise ReleaseRejected('The loaded account service inventory exceeds its supported limit')
    names=[item['unit'] for item in units]
    if any(not isinstance(name,str) or '\x00' in name for name in names):
        raise ReleaseRejected('The loaded account service inventory has unsupported names')
    if coordinator is not None:
        names=[name for name in names if name!=coordinator['unit']]
    properties=('FragmentPath','DropInPaths','ExecStart','ExecStartPre','ExecStartPost','ExecStop',
        'ExecStopPost','ExecReload','WorkingDirectory','EnvironmentFiles')
    for offset in range(0,len(names),128):
        output=_manager('show','--property='+','.join(properties),'--no-pager','--',*names[offset:offset+128])
        for block in output.strip().split('\n\n'):
            values=dict(line.split('=',1) for line in block.splitlines() if line)
            if not set(values)<=set(properties):
                raise ReleaseRejected('The loaded account service metadata has unsupported fields')
            definitions=_paths(values.get('FragmentPath',''))+_paths(values.get('DropInPaths',''))
            paths.extend(definitions)
            if (values.get('FragmentPath') and definitions
                    and all(path in known or path.resolve() in known for path in definitions)):continue
            if _consumes(block.encode(),profile,tokens):
                raise ReleaseRejected('Another loaded account service uses the reviewed integration programs or profile')
    visited=set()
    for path in paths:
        if not path.exists():
            target=os.readlink(path) if path.is_symlink() else str(path)
            if any(token in _expanded(target.encode(),profile) for token in tokens):
                raise ReleaseRejected('An unavailable account service definition selects the reviewed programs or profile')
            continue
        physical=path.resolve(strict=True)
        if physical==Path('/dev/null') or physical in visited:continue
        visited.add(physical)
        if path in known or physical in known:continue
        data,_=_definition(physical)
        if path.resolve()!=physical:
            raise ReleaseRejected('An account service definition changes during inspection')
        if _consumes(data,profile,tokens):
            raise ReleaseRejected('Another account service uses the reviewed integration programs or profile')


def processes(profile, installed, *, groups):
    tokens=_tokens(profile,installed);profile_marker=b'HERMES_HOME='+str(profile).encode()
    for process in Path('/proc').iterdir():
        if not process.name.isdecimal() or int(process.name)==os.getpid():continue
        try:
            if process.stat().st_uid!=os.getuid():continue
            current={line.removeprefix('0::') for line in (process/'cgroup').read_text().splitlines() if line.startswith('0::')}
            manager='/user.slice/user-'+str(os.getuid())+'.slice/user@'+str(os.getuid())+'.service/init.scope'
            if current and (current<=groups or current=={manager}):continue
            arguments=(process/'cmdline').read_bytes()
            executable=os.readlink(process/'exe').removesuffix(' (deleted)').encode()
            relevant=any(token in arguments or token in executable for token in tokens)
            hermes=any(name in arguments.lower() for name in (b'hermes',b'run_agent'))
            if not relevant and not hermes:continue
            environment=(process/'environ').read_bytes().split(b'\0') if hermes else ()
            if not relevant and profile_marker not in environment:continue
            if not current or not current<=groups:
                raise ReleaseRejected('Another account process uses the reviewed integration programs or profile')
        except FileNotFoundError:continue
        except (PermissionError,UnicodeError) as error:
            raise ReleaseRejected('The account process boundary cannot be verified') from error


def hooks(settings, profile, installed):
    import re
    import json
    data=_expanded(json.dumps(settings.get('hooks',{})).encode(),profile)
    if (any(token in data for token in _tokens(profile,installed))
            or re.search(rb'(?<![A-Za-z0-9_])bun(?![A-Za-z0-9_])',data)
            or b'~/.claude/' in data or b'$HOME/.claude/' in data):
        raise ReleaseRejected('A retained owner hook requires the selected Bun or native programs')
