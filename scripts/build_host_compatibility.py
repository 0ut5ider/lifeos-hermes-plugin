# ABOUTME: Builds the Hermes compatibility manifest from an exact stock Hermes archive and the patch set.
# ABOUTME: Records stock and patched hashes of every changed file, the pinned interpreter, and required capabilities.

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from lifeos_hook_bridge import PATCHED_HOOKS
from lifeos_hook_bridge.install_source import HERMES_PATCHES, SUPPORTED_HERMES_COMMIT
from optional.lifeos_release_manager.host_compatibility import MANIFEST, load_manifest
from optional.lifeos_release_manager.release_stage import sha


PIN = re.compile(r'([A-Za-z0-9][A-Za-z0-9._-]*)==([0-9][0-9A-Za-z.+!_-]*)')
# The bridge's memory provider requires middleware API version 1 (lifeos_hook_bridge/memory_provider.py).
MIDDLEWARE_API = 1


class ManifestBuildError(RuntimeError):
    """The inputs cannot produce a trustworthy compatibility entry."""


def _files(root: Path) -> dict[str, str]:
    hashes = {}
    for directory, names, files in os.walk(root, followlinks=False):
        names.sort()
        for name in sorted(files):
            path = Path(directory) / name
            hashes[path.relative_to(root).as_posix()] = 'symlink' if path.is_symlink() else sha(path)
    return hashes


def _archive_commit(archive: Path) -> str:
    with tarfile.open(archive, 'r:*') as stream:
        commit = stream.pax_headers.get('comment')
    if commit is None or re.fullmatch('[0-9a-f]{40}', commit) is None:
        raise ManifestBuildError('The stock archive does not record its Git commit')
    return commit


def bridge_capabilities() -> dict:
    """Return the host capabilities the bridge requires: its patched hooks and the middleware API version."""
    return {'hooks': sorted(PATCHED_HOOKS), 'middleware_api': MIDDLEWARE_API}


def _python(source: Path) -> str:
    """Return the major.minor version of the interpreter that Hermes pins in ``pm/lock.json``."""
    try:
        version = json.loads((source / 'pm/lock.json').read_text())['packages']['python']['version']
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ManifestBuildError('The stock archive does not pin its Python interpreter in pm/lock.json') from error
    match = re.match(r'([0-9]+\.[0-9]+)\.', version) if isinstance(version, str) else None
    if match is None:
        raise ManifestBuildError('The stock archive pins an unreadable Python version: ' + repr(version))
    return match.group(1)


def build_entry(archive: Path, patches: Path, names: tuple[str, ...], label: str, commit: str, *,
                capabilities: dict, known_conflicts: list[str] | None = None) -> dict:
    """Apply the ordered patches to the stock archive and record each changed file's hashes."""
    if _archive_commit(archive) != commit:
        raise ManifestBuildError('The stock archive was built from another commit')
    with tempfile.TemporaryDirectory(prefix='hermes-compatibility-') as directory:
        source = Path(directory) / 'source'
        source.mkdir()
        with tarfile.open(archive, 'r:*') as stream:
            stream.extractall(source, filter='data')
        before = _files(source)
        python = _python(source)
        environment = {**os.environ, 'GIT_CEILING_DIRECTORIES': directory}
        identities = []
        for name in names:
            patch = patches / name
            result = subprocess.run(['git', 'apply', str(patch)], cwd=source, env=environment,
                                    capture_output=True, text=True, timeout=120)
            if result.returncode:
                raise ManifestBuildError(f'{name} does not apply to the stock archive: {result.stderr.strip()}')
            identities.append({'name': name, 'sha256': sha(patch)})
        after = _files(source)
    removed = sorted(set(before) - set(after))
    if removed:
        raise ManifestBuildError('The patches remove files, which the compatibility manifest cannot express: '
                                 + ', '.join(removed))
    files = {path: {'stock': before.get(path), 'patched': value}
             for path, value in sorted(after.items()) if before.get(path) != value}
    if any(value['patched'] == 'symlink' for value in files.values()):
        raise ManifestBuildError('The patches create a symbolic link')
    entry = {'label': label, 'commit': commit, 'patches': identities, 'files': files, 'python': python,
             'capabilities': capabilities}
    if known_conflicts:
        entry['known_conflicts'] = list(known_conflicts)
    return entry


def plugin_dependencies(plugin: Path) -> list[dict]:
    """Read the bridge's exact Python dependency pins from the block list in its plugin manifest."""
    requirements, inside = [], False
    for line in plugin.read_text().splitlines():
        if line.startswith('python_dependencies:'):
            inside = True
        elif inside and line.startswith('  - '):
            requirements.append(line[4:].strip())
        elif inside:
            break
    dependencies = []
    for requirement in requirements:
        match = PIN.fullmatch(requirement)
        if match is None:
            raise ManifestBuildError(f'The bridge dependency {requirement!r} needs an exact version pin')
        dependencies.append({'name': match.group(1), 'version': match.group(2)})
    return dependencies


def build_manifest(entries: list[dict], plugin: Path) -> dict:
    return load_manifest({'format': 1, 'hermes': entries, 'dependencies': plugin_dependencies(plugin)})


def main() -> None:
    parser = argparse.ArgumentParser(description='Build the Hermes compatibility manifest from an exact stock Hermes archive.')
    parser.add_argument('--stock-archive', type=Path, required=True,
                        help='The qualified stock-hermes.tgz created by git archive at the supported commit.')
    parser.add_argument('--label', required=True, help='The Hermes version shown to the owner, such as v0.21.7.')
    parser.add_argument('--known-conflict', action='append', dest='known_conflicts',
                        help='A known conflict that the releases page shows for this Hermes version; repeat for each.')
    parser.add_argument('--output', type=Path, default=MANIFEST)
    arguments = parser.parse_args()
    entry = build_entry(arguments.stock_archive, REPOSITORY / 'lifeos_hook_bridge/patches', HERMES_PATCHES,
                        arguments.label, SUPPORTED_HERMES_COMMIT, capabilities=bridge_capabilities(),
                        known_conflicts=arguments.known_conflicts)
    manifest = build_manifest([entry], REPOSITORY / 'lifeos_hook_bridge/plugin.yaml')
    arguments.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
