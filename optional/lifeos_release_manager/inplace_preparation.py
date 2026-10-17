# ABOUTME: Prepares an in-place LifeOS operation for the owner's existing Hermes installation.
# ABOUTME: Downloads the integration, stages host patches and LifeOS, and records the reviewed request.
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from .host_compatibility import check, load_manifest
from .host_patches import stage_host_files
from .host_record import check_originals, load_record
from .integration_package import COMPATIBILITY, validate_integration
from .release_accounts import account_home
from .release_catalog import ReleaseCatalog, ReleaseRejected, _json, extract_package
from .release_programs import publish
from .release_stage import _environment, load_bridge, run_stage, runtime_source_fingerprint, sha
from .release_tools import prepare_bun


def _first_reason(result):
    reasons = result['reasons']
    return reasons[0]['message'] if reasons else 'The Hermes installation is not in the required state.'


def host_python(source):
    """Return the interpreter of the dependency environment that Hermes selected for ``source``."""
    from pm.environments import selected_venv, venv_python
    python = venv_python(selected_venv(Path(source)))
    if not python.is_file():
        raise ReleaseRejected('The Hermes installation has no selected Python environment')
    return python


def host_launcher(source):
    launcher = Path(source) / '.hermes/bin/hermes'
    if launcher.is_symlink() or not launcher.is_file() or not os.access(launcher, os.X_OK):
        raise ReleaseRejected('The Hermes installation has no source launcher')
    return launcher


def state_directory(source):
    from pm.environments import install_state_dir
    return install_state_dir(Path(source))


def desired_host_files(entry, staged, record=None, originals=None):
    """Map each host target to its desired file after the operation, or None for an absent file.

    Targets of the new entry receive their staged patched file. Targets that only the recorded release
    changed return to their retained original, or to absence when that release added them.
    """
    desired = {relative: paths['patched'] for relative, paths in staged.items()}
    if record is not None:
        for relative, hashes in record['files'].items():
            if relative not in desired:
                desired[relative] = None if hashes['stock'] is None else originals[relative]
    return desired


def stock_source(source, record, originals, entry, destination):
    """Assemble the stock files of ``entry`` for an installed host: retained originals, plus unpatched host files.

    A target that the recorded release did not change is still stock on the host, so it is read from there;
    staging verifies every copied file against its stock hash.
    """
    destination = Path(destination)
    destination.mkdir(mode=0o700)
    for relative, hashes in entry['files'].items():
        if hashes['stock'] is None:
            continue
        if relative in originals:
            origin = originals[relative]
        elif relative in record['files']:
            raise ReleaseRejected('The host record and the release disagree about an original Hermes file: ' + relative)
        else:
            origin = Path(source) / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, target)
    return destination


def build_preview(source, desired, destination):
    """Copy the tracked Hermes files, then overlay the desired host files, for preparation checks only."""
    source, destination = Path(source), Path(destination)
    listed = subprocess.run(['git', '--no-optional-locks', '-C', str(source), 'ls-files', '-z'],
                            capture_output=True, timeout=120, env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'})
    if listed.returncode:
        raise ReleaseRejected('Git cannot list the Hermes source files')
    destination.mkdir(mode=0o700)
    for name in listed.stdout.split(b'\0'):
        if not name:
            continue
        relative = name.decode()
        target = destination / relative
        origin = source / relative
        if origin.is_symlink() or not origin.is_file():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, target)
    for relative, path in desired.items():
        target = destination / relative
        if path is None:
            target.unlink(missing_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    return destination


def resolve_dependencies(job, python, source, profile, bridge):
    """Lock the bridge with the enabled plugins in a throwaway workspace under the host interpreter."""
    output = job / 'dependency-resolution.json'
    environment = {**_environment(Path(profile), home=account_home(profile), source=Path(source)),
                   'XDG_RUNTIME_DIR': '/run/user/' + str(os.getuid())}
    run_stage([python, '-B', Path(__file__).with_name('dependency_plan.py'), 'resolve', source, profile, bridge,
               job / 'dependency-workspace', output], job, 'dependency-resolution', environment=environment)
    return _json(output.read_bytes())


def prepare_inplace(profile, job, version=None, *, name, assistant, intent, catalog=None):
    """Prepare the reviewed in-place request in ``job``; the active installation is not changed."""
    profile, job = Path(profile), Path(job)
    home = account_home(profile)
    downloaded = (catalog or ReleaseCatalog()).download_integration(job / 'download', version)
    result = check(profile)
    record = load_record(profile)
    if result['state'] not in {'compatible', 'installed'}:
        raise ReleaseRejected('LifeOS cannot be installed on this Hermes installation: ' + _first_reason(result))
    source = Path(result['detected']['source'])
    certificate = downloaded['certificate']
    package = job / 'package'
    extract_package(downloaded['archive'], package)
    manifest = validate_integration(package, certificate)
    entry = next((item for item in load_manifest(package / COMPATIBILITY)['hermes']
                  if item['commit'] == result['detected']['commit']), None)
    if entry is None:
        raise ReleaseRejected('This LifeOS release does not support the installed Hermes version')
    bridge = load_bridge(package / 'lifeos_hook_bridge')
    names = bridge.memory_module('fresh_store')
    names._name(name)
    names._name(assistant)
    selected = bridge.memory_module('lifeos_installation').selection(profile)
    fresh = not selected.installed.exists() and not selected.installed.is_symlink()
    if intent == 'install' and (not fresh or record is not None):
        raise ReleaseRejected('Use an update for the existing LifeOS installation')
    if result['transition'] and (fresh or record is not None or intent == 'install'):
        raise ReleaseRejected('Moving from a managed runtime requires the installed managed release and an update')
    if intent in {'update', 'plugin'} and fresh:
        raise ReleaseRejected('Install LifeOS before requesting an update')
    if fresh:
        from .release_services import require_fresh_services
        require_fresh_services(bridge)
    if bridge.SUPPORTED_LIFEOS_COMMIT != certificate['lifeos']['commit']:
        raise ReleaseRejected('The integration bridge pins another LifeOS commit than its certificate')
    patches = package / 'lifeos_hook_bridge/patches'
    originals = None
    if record is not None:
        originals = check_originals(record)
        staged = stage_host_files(stock_source(source, record, originals, entry, job / 'host-source'),
                                  entry, patches, job / 'host')
    else:
        staged = stage_host_files(source, entry, patches, job / 'host')
    desired = desired_host_files(entry, staged, record, originals)
    lifeos = bridge.prepare_lifeos(certificate['lifeos']['upstream'], job / 'lifeos', certificate['lifeos']['commit'],
                                   patches, bridge.LIFEOS_PATCHES, expected_tree=certificate['lifeos']['tree_sha256'])
    dependencies = _json((package / 'lifeos_hook_bridge/dependency_locks/catalog.json').read_bytes())
    (job / 'tools').mkdir(mode=0o700)
    bun = prepare_bun(job / 'tools', package / 'optional/lifeos_release_manager/release-tools.json',
                      dependencies['bun_version'])
    python = host_python(source)
    preview = build_preview(source, desired, job / 'hermes-preview')
    dependencies = resolve_dependencies(job, python, source, profile, package / 'lifeos_hook_bridge')
    if dependencies['changed']:
        raise ReleaseRejected('LifeOS would change installed Python packages: ' + ', '.join(sorted(dependencies['changed'])))
    reference = job / 'reference-home'
    reference.mkdir(mode=0o700)
    script = ('import importlib.util,sys\nfrom pathlib import Path\n'
        'spec=importlib.util.spec_from_file_location("lifeos_release_install",Path(sys.argv[1])/"install_source.py")\n'
        'source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)\n'
        'source.install_lifeos(Path(sys.argv[2]),Path(sys.argv[3])/".claude",Path(sys.argv[3])/"failed",'
        'sys.argv[4],source.SUPPORTED_LIFEOS_COMMIT,Path(sys.argv[1])/"patches",source.LIFEOS_PATCHES)\n')
    environment = _environment(job / 'reference-profile', home=reference, source=preview)
    (job / 'reference-profile').mkdir(mode=0o700)
    environment['PATH'] = str(job / 'tools') + os.pathsep + environment.get('PATH', os.defpath)
    run_stage([python, '-B', '-c', script, package / 'lifeos_hook_bridge', job / 'lifeos', reference, bun],
              job, 'native-dependencies', environment=environment, timeout=1800)
    request = {
        'format': 2, 'identifier': job.name, 'profile': str(profile), 'account_home': str(home),
        'installed': str(selected.installed), 'version': manifest['version'], 'commit': manifest['head'],
        'package_sha256': sha(downloaded['archive']), 'certificate': certificate,
        'configuration_sha256': sha(profile / 'config.yaml'),
        'host': {'source': str(source), 'commit': entry['commit'], 'label': entry['label'],
                 'state': result['state'], 'state_directory': str(state_directory(source)),
                 'transition': result['transition'],
                 'record_sha256': None if record is None else sha(profile / 'lifeos-host.json')},
        'runtime': {'python': str(python), 'bun': str(bun), 'hermes': str(host_launcher(source)),
                    'source': str(preview), 'reference': str(reference / '.claude'),
                    'lifeos': str(job / 'lifeos'), 'host_files': str(job / 'host')},
        'name': name, 'assistant': assistant, 'lifeos_tree_sha256': lifeos['tree_sha256'],
        'runtime_fingerprint': runtime_source_fingerprint(preview), 'dependencies': dependencies,
    }
    publish(job / 'request.json', (json.dumps(request, indent=2) + '\n').encode())
    shutil.copytree(package / 'optional/lifeos_release_manager', job / 'worker',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    return request, manifest
