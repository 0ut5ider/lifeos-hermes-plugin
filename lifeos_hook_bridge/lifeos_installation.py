# ABOUTME: Reads and publishes the profile setting that selects the LifeOS home for one Hermes profile.
# ABOUTME: Without the setting, the account home holds the installed LifeOS at ~/.claude.

from dataclasses import dataclass
import json
import os
from pathlib import Path
import stat
import tempfile

SETTING = 'lifeos-installation.json'


@dataclass(frozen=True)
class Selection:
    home: Path
    workspace: Path
    configured: bool

    @property
    def installed(self) -> Path:
        return self.home / '.claude'

    @property
    def user_data(self) -> Path:
        return self.home / '.config/LIFEOS/USER'


def _absolute(value, name):
    if not isinstance(value, str) or not Path(value).is_absolute():
        raise ValueError(f'The LifeOS installation setting needs an absolute {name}')
    return Path(value)


def account_home(profile: Path) -> Path:
    """Return the account home that holds a Hermes profile, including named profiles."""
    profile = Path(profile).absolute()
    if profile.parent.name == 'profiles' and profile.parent.parent.name == '.hermes':
        return profile.parent.parent.parent
    return profile.parent


def selection(profile: Path) -> Selection:
    path = Path(profile) / SETTING
    if not path.exists() and not path.is_symlink():
        home = account_home(profile)
        return Selection(home, home / 'HermesWorkspace', False)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('The LifeOS installation setting must be a regular file')
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('The LifeOS installation setting needs private owner permissions')
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict) or set(value) != {'version', 'home', 'workspace'} or value['version'] != 1:
        raise ValueError('Unsupported LifeOS installation setting')
    home = _absolute(value['home'], 'home')
    workspace = _absolute(value['workspace'], 'workspace')
    installed = home / '.claude'
    if installed.is_symlink() or not installed.is_dir():
        raise ValueError('The selected LifeOS home has no installed LifeOS')
    return Selection(home, workspace, True)


def publish(profile: Path, home: Path, workspace: Path) -> None:
    value = {'version': 1, 'home': str(_absolute(str(home), 'home')),
             'workspace': str(_absolute(str(workspace), 'workspace'))}
    destination = Path(profile) / SETTING
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=profile, prefix='.lifeos-installation-',
                                     delete=False) as stream:
        temporary = Path(stream.name)
        os.fchmod(stream.fileno(), 0o600)
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    selection(profile)


def clear(profile: Path) -> None:
    (Path(profile) / SETTING).unlink(missing_ok=True)
