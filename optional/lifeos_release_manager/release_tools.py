# ABOUTME: Prepares the exact qualified Bun binary without changing account tools.
# ABOUTME: Verifies its official archive bytes, executable identity, and platform before installation.
import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
from urllib.request import urlopen
import zipfile

from .release_catalog import ReleaseRejected, owner_directory
from .release_catalog import DIGEST
from .release_programs import publish


def prepare_bun(directory, catalog, required_version):
    directory = owner_directory(directory)
    values = json.loads(Path(catalog).read_bytes())
    selected = values.get(platform.system().lower() + '-' + platform.machine())
    if (values.get('format') != 1 or not isinstance(selected, dict)
            or selected.get('version') != required_version
            or selected.get('name') != 'bun-linux-x64-baseline.zip'
            or selected.get('url') != 'https://github.com/oven-sh/bun/releases/download/bun-v'
                + required_version + '/' + selected['name']
            or selected.get('member') != 'bun-linux-x64-baseline/bun'
            or type(selected.get('size')) is not int or not 0 < selected['size'] <= 128 * 1024 * 1024
            or not isinstance(selected.get('sha256'), str) or DIGEST.fullmatch(selected['sha256']) is None):
        raise ReleaseRejected('This release has no qualified Bun archive for the selected platform')
    archive = directory / selected['name']
    digest, size = hashlib.sha256(), 0
    with urlopen(selected['url'], timeout=60) as response, archive.open('xb') as output:
        os.fchmod(output.fileno(), 0o600)
        for block in iter(lambda: response.read(1024 * 1024), b''):
            size += len(block)
            if size > selected['size']:
                raise ReleaseRejected('The Bun archive exceeds its declared size')
            digest.update(block)
            output.write(block)
    if size != selected['size'] or digest.hexdigest() != selected['sha256']:
        raise ReleaseRejected('The Bun archive differs from its qualified identity')
    with zipfile.ZipFile(archive) as source:
        entries = [item for item in source.infolist() if item.filename == selected['member']]
        if (len(entries) != 1 or entries[0].is_dir() or entries[0].file_size > 256 * 1024 * 1024
                or stat.S_IFMT(entries[0].external_attr >> 16) == stat.S_IFLNK):
            raise ReleaseRejected('The Bun archive lacks one bounded regular executable')
        target = directory / 'bun'
        publish(target, source.read(entries[0]), 0o700)
    result = subprocess.run([str(target), '--version'], text=True, capture_output=True, timeout=20)
    if result.returncode or result.stderr or result.stdout.strip() != required_version:
        raise ReleaseRejected('The prepared Bun executable does not match the selected version')
    return target
