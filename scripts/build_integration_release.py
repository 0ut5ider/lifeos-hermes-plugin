# ABOUTME: Builds the in-place integration archive: the bridge, the release manager, and their exact identities.
# ABOUTME: Records a reproducible candidate without publishing a certificate or changing any installation.
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from lifeos_hook_bridge import install_source
from optional.lifeos_release_manager.integration_package import COMPATIBILITY, MANIFEST_NAME, file_map


SELECTED = ('lifeos_hook_bridge', 'optional/lifeos_release_manager', 'VERSION', 'CHANGELOG.md')


def _archive(package, destination):
    """Write a reproducible gzip tar: sorted members, fixed owner and time, normalized modes."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w', format=tarfile.PAX_FORMAT) as archive:
        for path in sorted(package.rglob('*')):
            if '__pycache__' in path.parts or path.suffix == '.pyc':
                continue
            info = archive.gettarinfo(str(path), arcname=path.relative_to(package).as_posix())
            info.uid = info.gid = 0
            info.uname = info.gname = ''
            info.mtime = 0
            if info.isdir():
                info.mode = 0o755
                archive.addfile(info)
            elif info.isfile():
                info.mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                with path.open('rb') as stream:
                    archive.addfile(info, stream)
            else:
                raise ValueError('The integration package contains a non-regular file: ' + str(path))
    with destination.open('xb') as output, gzip.GzipFile(fileobj=output, mode='wb', mtime=0, filename='') as packed:
        packed.write(buffer.getvalue())


def build(output, *, lifeos_source=install_source.UPSTREAM_LIFEOS):
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=REPOSITORY).strip():
        raise ValueError('Commit tracked changes before building an integration release')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPOSITORY, text=True).strip()
    version = (REPOSITORY / 'VERSION').read_text().strip()
    output = Path(output).absolute()
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    name = 'lifeos-integration-' + version + '-' + head[:8]
    package = output / name
    package.mkdir(mode=0o700)
    data = subprocess.check_output(['git', 'archive', head, '--', *SELECTED], cwd=REPOSITORY)
    with tarfile.open(fileobj=io.BytesIO(data)) as source:
        source.extractall(package, filter='data')
    with tempfile.TemporaryDirectory(prefix='lifeos-integration-') as directory:
        lifeos = install_source.prepare_lifeos(lifeos_source, Path(directory) / 'lifeos',
                                               install_source.SUPPORTED_LIFEOS_COMMIT,
                                               package / 'lifeos_hook_bridge/patches', install_source.LIFEOS_PATCHES)
    manifest = {
        'format': 2, 'version': version, 'head': head,
        'plugin_files': file_map(package / 'lifeos_hook_bridge'),
        'manager_files': file_map(package / 'optional/lifeos_release_manager'),
        'host_compatibility_sha256': hashlib.sha256((package / COMPATIBILITY).read_bytes()).hexdigest(),
        'lifeos': {'upstream': install_source.UPSTREAM_LIFEOS, 'commit': lifeos['upstream_commit'],
                   'tree_sha256': lifeos['tree_sha256']},
    }
    (package / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    archive = output / (name + '.tgz')
    _archive(package, archive)
    record = {'version': version, 'head': head, 'archive_name': archive.name,
              'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
              'archive_bytes': archive.stat().st_size,
              'host_compatibility_sha256': manifest['host_compatibility_sha256'], 'lifeos': manifest['lifeos']}
    (output / (name + '-build.json')).write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    return record


def main():
    parser = argparse.ArgumentParser(description='Build an in-place LifeOS integration release candidate.')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--lifeos-source', default=install_source.UPSTREAM_LIFEOS,
                        help='The LifeOS Git repository to fetch the pinned commit from.')
    arguments = parser.parse_args()
    print(json.dumps(build(arguments.output, lifeos_source=arguments.lifeos_source), indent=2))


if __name__ == '__main__':
    main()
