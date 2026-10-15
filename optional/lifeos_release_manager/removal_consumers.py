# ABOUTME: Refuses other account services and processes that consume software selected for removal.
# ABOUTME: Inspects bounded owner metadata and exports no command text, environment, or credentials.
import os
from pathlib import Path

from .release_catalog import ReleaseRejected


def _tokens(profile, installed):
    profile,installed=Path(profile).absolute(),Path(installed).absolute()
    return tuple(str(path).encode() for path in (installed,profile/'plugins/lifeos',profile.parent/'.local/bin/bun'))


def _expanded(data, profile):
    home=str(Path(profile).parent).encode()
    for prefix in (b'${HOME}',b'$HOME',b'%h',b'~'):
        data=data.replace(prefix+b'/',home+b'/')
    return data


def unit_files(profile, installed, *, known):
    directory=Path(profile).parent/'.config/systemd/user'
    if not directory.exists():return
    if directory.resolve()!=directory or not directory.is_dir():
        raise ReleaseRejected('Removal requires physical account service definitions')
    known={Path(path).absolute() for path in known};tokens=_tokens(profile,installed)+(str(profile).encode(),)
    for path in directory.rglob('*'):
        if path in known or path.resolve() in known or path.is_dir():continue
        if not path.is_file() or path.stat().st_size>1024*1024:
            raise ReleaseRejected('An account service has an unsupported definition')
        data=_expanded(path.read_bytes(),profile)
        if any(token in data for token in tokens):
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
