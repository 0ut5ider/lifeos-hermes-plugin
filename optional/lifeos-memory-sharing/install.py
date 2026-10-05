# ABOUTME: Installs or removes the optional SSH sharing component in one Hermes profile.
# ABOUTME: Publishes a private copy that the LifeOS plugin verifies before each use.
import argparse
import os
from pathlib import Path
import shutil
import stat
import tempfile

NAME = 'memory_sharing.py'


def target(profile: Path) -> Path:
    profile = profile.expanduser().absolute()
    info = profile.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise SystemExit('The Hermes profile must be a physical owner directory without shared write access')
    return profile / 'lifeos-memory-sharing'


def install(profile: Path) -> Path:
    directory = target(profile)
    directory.mkdir(mode=0o700, exist_ok=True)
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise SystemExit('The component directory must be a physical owner directory')
    os.chmod(directory, 0o700)
    data = (Path(__file__).resolve().parent / NAME).read_bytes()
    with tempfile.NamedTemporaryFile(dir=directory, prefix='.' + NAME + '.', delete=False) as stream:
        temporary = Path(stream.name)
        os.fchmod(stream.fileno(), 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temporary, directory / NAME)
    finally:
        temporary.unlink(missing_ok=True)
    return directory


def remove(profile: Path) -> None:
    directory = target(profile)
    if not directory.is_symlink() and not directory.exists():
        return
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise SystemExit('The component directory must be a physical owner directory')
    program = directory / NAME
    if program.is_symlink() or program.exists():
        program.unlink()
    cache = directory / '__pycache__'
    if cache.is_dir() and not cache.is_symlink():
        shutil.rmtree(cache)
    try:
        directory.rmdir()
    except OSError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description='Install the optional LifeOS SSH memory sharing component')
    parser.add_argument('--hermes-home', type=Path, required=True)
    parser.add_argument('--remove', action='store_true')
    args = parser.parse_args()
    if args.remove:
        remove(args.hermes_home)
        print('Removed the sharing component. Existing connection grants and SSH entries are unchanged.')
    else:
        print('Installed the sharing component at ' + str(install(args.hermes_home)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
