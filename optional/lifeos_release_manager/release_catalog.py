# ABOUTME: Downloads qualified integration assets from the fixed public release repository.
# ABOUTME: Verifies release identities and extracts bounded regular files before live selection.
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import tempfile
from urllib.parse import urlparse
from urllib.request import Request, urlopen

REPOSITORY = '0ut5ider/lifeos-hermes-plugin'
LIFEOS_UPSTREAM = 'https://github.com/danielmiessler/LifeOS.git'
MAX_ARCHIVE_BYTES = 1024 * 1024 * 1024
MAX_EXTRACTED_BYTES = 5 * MAX_ARCHIVE_BYTES
MAX_MEMBERS = 100000
VERSION = re.compile(r'(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-(?:dev|rc)\.[0-9]+)?')
DIGEST = re.compile('[0-9a-f]{64}')
COMMIT = re.compile('[0-9a-f]{40}')


class ReleaseRejected(ValueError):
    pass


def _unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ReleaseRejected('Release metadata contains duplicate fields')
        value[key] = item
    return value


def _json(data):
    try:
        return json.loads(data, object_pairs_hook=_unique_pairs)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise ReleaseRejected('Release metadata is invalid') from error


def _directory(path):
    path = Path(path).absolute()
    info = path.lstat()
    if (path.resolve() != path or not path.is_dir() or info.st_uid != os.getuid()
            or info.st_mode & 0o077):
        raise ReleaseRejected('Release staging requires a private owner directory')
    return path


def extract_package(archive, destination, *, max_bytes=MAX_EXTRACTED_BYTES):
    destination = Path(destination).absolute()
    _directory(destination.parent)
    if destination.exists() or destination.is_symlink():
        raise ReleaseRejected('The package destination already exists')
    staging = Path(tempfile.mkdtemp(prefix='.release-', dir=destination.parent))
    try:
        with tarfile.open(archive, 'r:gz') as source:
            names, total = set(), 0
            for number, member in enumerate(source, 1):
                name = member.name.rstrip('/')
                relative = PurePosixPath(name)
                total += member.size
                if (number > MAX_MEMBERS or total > max_bytes or member.size < 0 or not name
                        or '\\' in name or relative.is_absolute() or str(relative) != name
                        or any(part in {'.', '..'} for part in relative.parts) or name in names
                        or not (member.isdir() or member.isfile())):
                    raise ReleaseRejected('The archive exceeds its limits or contains unsupported paths')
                names.add(name)
                target = staging / name
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True, mode=0o700)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    with source.extractfile(member) as content, target.open('xb') as output:
                        os.fchmod(output.fileno(), 0o700 if member.mode & 0o111 else 0o600)
                        shutil.copyfileobj(content, output, length=1024 * 1024)
                        output.flush()
                        os.fsync(output.fileno())
        os.replace(staging, destination)
    except (tarfile.TarError, OSError) as error:
        raise ReleaseRejected('The archive cannot be extracted safely') from error
    finally:
        if staging.exists():
            shutil.rmtree(staging)


class ReleaseCatalog:
    def __init__(self, *, api_origin='https://api.github.com', asset_origin='https://github.com'):
        self.api_origin, self.asset_origin = api_origin, asset_origin

    @staticmethod
    def _request(url):
        return urlopen(Request(url, headers={'User-Agent': 'LifeOS-Hermes-release',
            'Accept': 'application/vnd.github+json'}), timeout=60)

    def _metadata(self, url, limit=512 * 1024):
        with self._request(url) as response:
            data = response.read(limit + 1)
        if len(data) > limit:
            raise ReleaseRejected('Release metadata exceeds its size limit')
        return _json(data)

    def _asset(self, value, *, tag):
        if not isinstance(value, dict):
            raise ReleaseRejected('Release assets require exact identities')
        name, size, digest, url = (value.get(key) for key in ('name', 'size', 'digest', 'browser_download_url'))
        prefix = self.asset_origin + '/' + REPOSITORY + '/releases/download/' + tag + '/'
        if (not isinstance(name, str) or re.fullmatch('[a-zA-Z0-9_.-]+', name) is None
                or type(size) is not int or not 0 < size <= MAX_ARCHIVE_BYTES
                or not isinstance(digest, str) or not digest.startswith('sha256:')
                or DIGEST.fullmatch(digest[7:]) is None or not isinstance(url, str)
                or url != prefix + name or urlparse(url).query or urlparse(url).fragment):
            raise ReleaseRejected('A release asset has an invalid origin, size, name, or digest')
        return {'name': name, 'size': size, 'sha256': digest[7:], 'url': url}

    def _download(self, asset, directory):
        target = directory / asset['name']
        descriptor, name = tempfile.mkstemp(prefix='.download-', dir=directory)
        temporary = Path(name)
        try:
            digest, size = hashlib.sha256(), 0
            with os.fdopen(descriptor, 'wb') as output, self._request(asset['url']) as response:
                for block in iter(lambda: response.read(1024 * 1024), b''):
                    size += len(block)
                    if size > asset['size']:
                        raise ReleaseRejected('The release asset exceeds its declared size')
                    digest.update(block)
                    output.write(block)
                output.flush()
                os.fsync(output.fileno())
            if size != asset['size'] or digest.hexdigest() != asset['sha256']:
                raise ReleaseRejected('The release asset differs from its published identity')
            if target.exists() or target.is_symlink():
                raise ReleaseRejected('The release asset destination already exists')
            os.replace(temporary, target)
            return target
        finally:
            temporary.unlink(missing_ok=True)

    def _release(self, version):
        """Return the tag and exact asset identities of the selected published release."""
        if version is not None and (not isinstance(version, str) or VERSION.fullmatch(version) is None):
            raise ReleaseRejected('Choose an exact integration version')
        selector = 'latest' if version is None else 'tags/v' + version
        release = self._metadata(self.api_origin + '/repos/' + REPOSITORY + '/releases/' + selector)
        tag = release.get('tag_name') if isinstance(release, dict) else None
        if (not isinstance(tag, str) or not tag.startswith('v') or VERSION.fullmatch(tag[1:]) is None
                or release.get('draft') is not False
                or version is None and release.get('prerelease') is not False
                or version is not None and tag != 'v' + version):
            raise ReleaseRejected('The selected published release is unavailable')
        assets = {}
        if not isinstance(release.get('assets'), list):
            raise ReleaseRejected('The selected release has no asset list')
        for value in release['assets']:
            asset = self._asset(value, tag=tag)
            if asset['name'] in assets:
                raise ReleaseRejected('The selected release has duplicate assets')
            assets[asset['name']] = asset
        if 'RELEASE-CERTIFICATE.json' not in assets:
            raise ReleaseRejected('The release certificate is missing')
        return tag, assets

    def _certificate(self, assets, directory):
        directory = Path(directory).absolute()
        _directory(directory.parent)
        directory.mkdir(mode=0o700)
        certificate_asset = assets['RELEASE-CERTIFICATE.json']
        if certificate_asset['size'] > 512 * 1024:
            raise ReleaseRejected('The release certificate exceeds its size limit')
        return directory, _json(self._download(certificate_asset, directory).read_bytes())

    def download(self, directory, version=None):
        tag, assets = self._release(version)
        if 'hermes-dashboard.tgz' not in assets:
            raise ReleaseRejected('The complete integration assets are missing')
        directory, certificate = self._certificate(assets, directory)
        if (not isinstance(certificate, dict) or type(certificate.get('format')) is not int or certificate['format'] != 1
                or certificate.get('status') != 'QUALIFIED' or certificate.get('version') != tag[1:]
                or not isinstance(certificate.get('program_commit'), str)
                or COMMIT.fullmatch(certificate['program_commit']) is None):
            raise ReleaseRejected('The integration release is not qualified')
        archive_name = tag[1:] + '-' + certificate['program_commit'][:8] + '.tgz'
        archive, dashboard = assets.get(archive_name), assets['hermes-dashboard.tgz']
        if (archive is None or archive['sha256'] != certificate.get('archive_sha256')
                or archive['size'] != certificate.get('archive_bytes')
                or dashboard['sha256'] != certificate.get('hermes_dashboard_sha256')):
            raise ReleaseRejected('The certificate does not bind the complete release assets')
        return {'certificate': certificate, 'archive': str(self._download(archive, directory)),
                'dashboard': str(self._download(dashboard, directory)), 'tag': tag}

    def download_integration(self, directory, version=None):
        """Download an in-place integration release: its format 2 certificate and integration archive only."""
        tag, assets = self._release(version)
        directory, certificate = self._certificate(assets, directory)
        if not isinstance(certificate, dict) or certificate.get('format') != 2 or type(certificate['format']) is not int:
            raise ReleaseRejected('This release is not an in-place integration release')
        lifeos = certificate.get('lifeos')
        if (certificate.get('status') != 'QUALIFIED' or certificate.get('version') != tag[1:]
                or not isinstance(certificate.get('program_commit'), str)
                or COMMIT.fullmatch(certificate['program_commit']) is None
                or not isinstance(certificate.get('host_compatibility_sha256'), str)
                or DIGEST.fullmatch(certificate['host_compatibility_sha256']) is None
                or not isinstance(lifeos, dict) or set(lifeos) != {'upstream', 'commit', 'tree_sha256'}
                or lifeos['upstream'] != LIFEOS_UPSTREAM
                or not isinstance(lifeos['commit'], str) or COMMIT.fullmatch(lifeos['commit']) is None
                or not isinstance(lifeos['tree_sha256'], str) or DIGEST.fullmatch(lifeos['tree_sha256']) is None):
            raise ReleaseRejected('The integration release is not qualified')
        archive = assets.get('lifeos-integration-' + tag[1:] + '-' + certificate['program_commit'][:8] + '.tgz')
        if (archive is None or archive['sha256'] != certificate.get('archive_sha256')
                or archive['size'] != certificate.get('archive_bytes')):
            raise ReleaseRejected('The certificate does not bind the integration archive')
        return {'certificate': certificate, 'archive': str(self._download(archive, directory)), 'tag': tag}
