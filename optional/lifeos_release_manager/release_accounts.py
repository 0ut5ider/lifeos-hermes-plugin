# ABOUTME: Resolves the account that owns a selected Hermes profile.
# ABOUTME: Keeps native service HOME separate from trusted release launcher storage.
import os
from pathlib import Path
import stat

from .release_catalog import ReleaseRejected


def account_home(profile):
    profile = Path(profile).absolute()
    if profile.parent.name == 'profiles' and profile.parent.parent.name == '.hermes':
        home = profile.parent.parent.parent
    elif profile.name == '.hermes':
        home = profile.parent
    else:
        home = Path.home()
    try:
        info = home.lstat()
        profile_info = profile.lstat()
        if (home.resolve() != home or profile.resolve() != profile
                or not stat.S_ISDIR(info.st_mode) or not stat.S_ISDIR(profile_info.st_mode)
                or info.st_uid != os.getuid() or profile_info.st_uid != os.getuid()
                or info.st_mode & 0o022 or profile_info.st_mode & 0o022):
            raise ReleaseRejected('Release management requires a physical owner account and profile')
    except OSError as error:
        raise ReleaseRejected('The owner account or profile is unavailable') from error
    return home
