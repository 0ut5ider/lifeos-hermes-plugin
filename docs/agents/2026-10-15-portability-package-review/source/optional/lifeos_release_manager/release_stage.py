# ABOUTME: Validates qualified integration packages and prepares their complete dependency generation.
# ABOUTME: Builds candidate runtimes and native reference installations without changing the selected profile.
from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tarfile
import types

from .release_catalog import (ReleaseRejected, _directory, extract_package, _json,
    COMMIT, DIGEST, VERSION, MAX_ARCHIVE_BYTES, MAX_EXTRACTED_BYTES, MAX_MEMBERS)
from .release_programs import publish, fingerprint
from .release_tools import prepare_bun


def sha(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def runtime_source_fingerprint(path):
    return fingerprint(path, excluded_root_entries=frozenset({'.hermes', '.bytecode-fingerprint'}))


def validate_files(root, files, *, forbid_bytecode=False):
    root = Path(root).absolute()
    if root.resolve() != root or not root.is_dir() or not isinstance(files, dict) or not 1 <= len(files) <= 2048:
        raise ReleaseRejected('The release requires a bounded exact program file map')
    for name, digest in files.items():
        if (not isinstance(name, str) or not name or '\\' in name or PurePosixPath(name).is_absolute()
                or str(PurePosixPath(name)) != name or any(part in {'.', '..'} for part in PurePosixPath(name).parts)
                or not isinstance(digest, str) or len(digest) != 64):
            raise ReleaseRejected('The release file map contains invalid paths or hashes')
        path = root / name
        if not path.is_file() or path.resolve() != path or path.is_symlink() or sha(path) != digest:
            raise ReleaseRejected('A release program differs from its qualified identity')
    actual = set()
    for path in root.rglob('*'):
        relative = path.relative_to(root)
        if '__pycache__' in relative.parts or path.suffix == '.pyc':
            if forbid_bytecode:
                raise ReleaseRejected('Qualified source trees cannot contain unrecorded bytecode')
            continue
        if path.is_symlink():
            raise ReleaseRejected('A release program tree contains a symbolic link')
        if path.is_file():
            actual.add(relative.as_posix())
        elif not path.is_dir():
            raise ReleaseRejected('A release program tree contains an unsupported artifact')
    if actual != set(files):
        raise ReleaseRejected('The release program tree has missing or additional files')


def load_bridge(directory):
    # Isolated Python ignores environment bytecode settings. Keep qualified source trees unchanged during imports.
    sys.dont_write_bytecode = True
    directory = Path(directory).absolute()
    name = 'lifeos_release_source_' + hashlib.sha256(str(directory).encode()).hexdigest()[:16]
    if name not in sys.modules:
        namespace = types.ModuleType(name)
        namespace.__path__ = [str(directory)]
        sys.modules[name] = namespace
    return importlib.import_module(name + '.install_source')


def archived_manifest(package, certificate):
    version, commit, digest, size = (certificate.get(key)
        for key in ('version', 'program_commit', 'archive_sha256', 'archive_bytes'))
    if (not isinstance(version, str) or VERSION.fullmatch(version) is None
            or not isinstance(commit, str) or COMMIT.fullmatch(commit) is None
            or not isinstance(digest, str) or DIGEST.fullmatch(digest) is None
            or type(size) is not int or not 0 < size <= MAX_ARCHIVE_BYTES):
        raise ReleaseRejected('The package requires an authenticated archive identity')
    archive = package.parent / 'download' / (version + '-' + commit[:8] + '.tgz')
    if archive.resolve() != archive:
        raise ReleaseRejected('The package requires a regular authenticated archive')
    try:
        descriptor = os.open(archive, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, 'rb') as content:
            info = os.fstat(content.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_size != size
                    or hashlib.file_digest(content, 'sha256').hexdigest() != digest):
                raise ReleaseRejected('The package differs from its authenticated archive identity')
            content.seek(0)
            manifest, total = None, 0
            with tarfile.open(fileobj=content, mode='r|gz') as source:
                for number, member in enumerate(source, 1):
                    total += member.size
                    if number > MAX_MEMBERS or member.size < 0 or total > MAX_EXTRACTED_BYTES:
                        raise ReleaseRejected('The authenticated archive exceeds its package limits')
                    if member.name == 'DAILY-CANDIDATE.json':
                        if manifest is not None or not member.isfile() or not 0 < member.size <= 512 * 1024:
                            raise ReleaseRejected('The authenticated archive requires one bounded program manifest')
                        with source.extractfile(member) as program_manifest:
                            manifest = program_manifest.read(512 * 1024 + 1)
            if manifest is None:
                raise ReleaseRejected('The authenticated archive has no program manifest')
            return manifest
    except (OSError, tarfile.TarError) as error:
        raise ReleaseRejected('The package authenticated archive is unavailable') from error


def read_manifest(path):
    if path.resolve() != path:
        raise ReleaseRejected('The package requires a bounded regular owner manifest')
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, 'rb') as content:
            info = os.fstat(content.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or not 0 < info.st_size <= 512 * 1024:
                raise ReleaseRejected('The package requires a bounded regular owner manifest')
            manifest_bytes = content.read(512 * 1024 + 1)
            if len(manifest_bytes) > 512 * 1024:
                raise ReleaseRejected('The package requires a bounded regular owner manifest')
    except OSError as error:
        raise ReleaseRejected('The package requires a bounded regular owner manifest') from error
    return manifest_bytes


def validate_package(package, certificate):
    package = _directory(package)
    manifest_bytes = read_manifest(package / 'DAILY-CANDIDATE.json')
    manifest = _json(manifest_bytes)
    if (not isinstance(manifest, dict) or not isinstance(certificate, dict)
            or certificate.get('format') != 1 or certificate.get('status') != 'QUALIFIED'
            or manifest.get('head') != certificate.get('program_commit')
            or manifest.get('version') != certificate.get('version')):
        raise ReleaseRejected('The package does not match its qualified release certificate')
    if not isinstance(manifest.get('python_runtime_files'), dict):
        raise ReleaseRejected('The release has no qualified frozen dependency closure')
    if manifest_bytes != archived_manifest(package, certificate):
        raise ReleaseRejected('The extracted program manifest differs from its authenticated archive')
    source_manifests = manifest.get('prepared_manifest_files')
    if (not isinstance(source_manifests, dict) or set(source_manifests)
            != {'hermes/hermes-source-manifest.json', 'lifeos/lifeos-source-manifest.json'}):
        raise ReleaseRejected('The package has no authenticated native source manifest map')
    for name, digest in source_manifests.items():
        if (not isinstance(digest, str) or DIGEST.fullmatch(digest) is None
                or hashlib.sha256(read_manifest(package / name)).hexdigest() != digest):
            raise ReleaseRejected('A native source manifest differs from its authenticated program map')
    if 'stock_hermes' in manifest:
        from .stock_hermes import validate_archive
        stock=validate_archive(package/'stock-hermes.tgz',manifest['stock_hermes'])
        if stock['commit']!=certificate.get('hermes_base'):
            raise ReleaseRejected('The stock source does not match the qualified Hermes base')
    validate_files(package / 'python-runtime', manifest['python_runtime_files'], forbid_bytecode=True)
    if not {'pyproject.toml', 'uv.lock'} <= set(manifest['python_runtime_files']):
        raise ReleaseRejected('The release lacks a frozen dependency closure')
    plugin_files = manifest.get('plugin_files')
    if not isinstance(plugin_files, dict) or any(not name.startswith('lifeos_hook_bridge/') for name in plugin_files):
        raise ReleaseRejected('The release has no exact bridge file map')
    validate_files(package / 'lifeos_hook_bridge',
        {name.removeprefix('lifeos_hook_bridge/'): digest for name, digest in plugin_files.items()}, forbid_bytecode=True)
    validate_files(package / 'optional/lifeos_release_manager', manifest.get('manager_files'), forbid_bytecode=True)
    bridge = load_bridge(package / 'lifeos_hook_bridge')
    versions = bridge.memory_module('release_version')
    if versions.versions(package) != manifest['version']:
        raise ReleaseRejected('The integration version declarations differ')
    hermes = bridge.validate_supported_hermes(package / 'hermes')
    lifeos = bridge.validate_prepared_lifeos(package / 'lifeos')
    if (hermes['base_commit'] != certificate.get('hermes_base')
            or lifeos['upstream_commit'] != certificate.get('lifeos_base')
            or len(hermes['patches']) != certificate.get('hermes_patch_count')
            or len(lifeos['patches']) != certificate.get('lifeos_patch_count')):
        raise ReleaseRejected('The native source manifests do not match the release certificate')
    return manifest


def _environment(profile, *, home, source=None):
    environment = {key: value for key, value in os.environ.items()
        if key in {'PATH', 'LANG', 'LC_ALL', 'TZ', 'SSL_CERT_FILE', 'SSL_CERT_DIR'}}
    environment.update(HOME=str(home), HERMES_HOME=str(profile), PYTHONDONTWRITEBYTECODE='1')
    if source is not None:
        environment['PYTHONPATH'] = str(source)
    return environment


def run_stage(command, job, label, *, environment, cwd=None, timeout=1800):
    with (job / (label + '.stdout')).open('wb') as stdout, (job / (label + '.stderr')).open('wb') as stderr:
        os.fchmod(stdout.fileno(), 0o600); os.fchmod(stderr.fileno(), 0o600)
        result = subprocess.run([str(part) for part in command], env=environment, cwd=cwd or job,
            stdout=stdout, stderr=stderr, timeout=timeout, umask=0o077)
    if result.returncode:
        raise ReleaseRejected('Release preparation fails at ' + label + '. The active installation is unchanged.')


def prepare_runtime(job, package, dashboard, profile, *, stock=False):
    job, package = _directory(job), _directory(package)
    helpers = load_bridge(package / 'lifeos_hook_bridge')
    dependencies = _json((package / 'lifeos_hook_bridge/dependency_locks/catalog.json').read_bytes())
    tools = job / 'tools'
    tools.mkdir(mode=0o700)
    bun = prepare_bun(tools, package / 'optional/lifeos_release_manager/release-tools.json', dependencies['bun_version'])
    build_profile = job / 'dependency-profile'
    build_profile.mkdir(mode=0o700)
    environment = _environment(build_profile, home=job, source=package / 'hermes')
    script = ('from pathlib import Path\nimport pm\n'
        'result=pm.build_environment(source=Path(__import__("sys").argv[1]), out=Path(__import__("sys").argv[2]),'
        ' extras=["discord"], no_install_project=True, frozen=True, explicit=True)\n'
        'print(result)\n')
    run_stage([sys.executable, '-B', '-c', script, package / 'python-runtime', job / 'python-environment'],
        job, 'python-dependencies', environment=environment)
    python = job / 'python-environment/bin/python'
    if not python.is_file():
        raise ReleaseRejected('The prepared Python environment has no interpreter')
    runtime = job / 'hermes'
    if stock:
        from .stock_hermes import prepare_source
        manifest=_json(read_manifest(package/'DAILY-CANDIDATE.json'))
        if 'stock_hermes' not in manifest:
            raise ReleaseRejected('This package has no qualified stock Hermes removal source')
        record=prepare_source(package/'stock-hermes.tgz',job/'stock-source',manifest['stock_hermes'])
        publish(job/'stock-source.json',(json.dumps(record,sort_keys=True)+'\n').encode())
        shutil.copytree(job/'stock-source',runtime)
    else:
        shutil.copytree(package / 'hermes', runtime, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    compiled = job / 'compiled-dashboard'
    extract_package(dashboard, compiled)
    expected = compiled / 'hermes_cli/web_dist'
    if not expected.is_dir() or any(not path.relative_to(compiled).as_posix().startswith('hermes_cli/web_dist/')
            for path in compiled.rglob('*') if path.is_file()):
        raise ReleaseRejected('The dashboard asset contains files outside its compiled output')
    commands = job / 'bin'
    environment = _environment(build_profile, home=job, source=runtime)
    script = ('import importlib.util,sys\nfrom pathlib import Path\n'
        'spec=importlib.util.spec_from_file_location("lifeos_release_payload",sys.argv[1])\n'
        'module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)\n'
        'module.assemble_runtime(*map(Path,sys.argv[2:7]),integration=sys.argv[7]=="integration")\n')
    run_stage([python, '-B', '-c', script, package / 'optional/lifeos_release_manager/release_payload.py',
        job, runtime, package, expected, profile, 'stock' if stock else 'integration'], job, 'launcher', environment=environment)
    if stock:
        result={'python':str(python),'hermes':str(commands/'hermes'),'source':str(runtime),
            'stock_source':record,'integration':False}
        publish(job/'runtime.json',(json.dumps(result,sort_keys=True)+'\n').encode())
        return result
    reference = job / 'reference-home'
    reference.mkdir(mode=0o700)
    script = ('import importlib.util,sys\nfrom pathlib import Path\n'
        'spec=importlib.util.spec_from_file_location("lifeos_release_install",Path(sys.argv[1])/"install_source.py")\n'
        'source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)\n'
        'source.install_lifeos(Path(sys.argv[2]),Path(sys.argv[3])/".claude",Path(sys.argv[3])/"failed",'
        'sys.argv[4],source.SUPPORTED_LIFEOS_COMMIT,Path(sys.argv[1])/"patches",source.LIFEOS_PATCHES)\n')
    environment = _environment(build_profile, home=reference, source=runtime)
    environment['PATH'] = str(tools) + os.pathsep + environment.get('PATH', os.defpath)
    run_stage([python, '-B', '-c', script, package / 'lifeos_hook_bridge', package / 'lifeos', reference, bun],
        job, 'native-dependencies', environment=environment, timeout=1800)
    publish(job / 'runtime.json', (json.dumps({'python': str(python), 'bun': str(bun),
        'hermes': str(commands / 'hermes'), 'source': str(runtime), 'reference': str(reference / '.claude')}, indent=2) + '\n').encode())
    return _json((job / 'runtime.json').read_bytes())
