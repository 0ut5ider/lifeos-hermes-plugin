# ABOUTME: Validates an extracted in-place integration package against its qualified release certificate.
# ABOUTME: Checks the exact plugin file maps, version declarations, compatibility manifest, and LifeOS pin.
from __future__ import annotations

from pathlib import Path

from .release_catalog import ReleaseRejected, _directory, _json
from .release_stage import load_bridge, read_manifest, sha, validate_files


MANIFEST_NAME = 'INTEGRATION.json'
TOP_LEVEL = {'lifeos_hook_bridge', 'optional', 'VERSION', 'CHANGELOG.md', MANIFEST_NAME}
COMPATIBILITY = 'optional/lifeos_release_manager/host-compatibility.json'


def source_paths(root):
    """Return every path below ``root`` in sorted order, without bytecode caches or compiled files."""
    return [path for path in sorted(Path(root).rglob('*')) if '__pycache__' not in path.parts and path.suffix != '.pyc']


def file_map(root):
    """Return the exact SHA-256 map of the regular files below ``root``, excluding bytecode."""
    root = Path(root)
    return {path.relative_to(root).as_posix(): sha(path) for path in source_paths(root) if path.is_file()}


def _manager_version(manager):
    from ruamel.yaml import YAML
    declared = YAML(typ='safe').load((manager / 'plugin.yaml').read_text())
    dashboard = _json((manager / 'dashboard/manifest.json').read_bytes())
    if not isinstance(declared, dict) or not isinstance(dashboard, dict) or declared.get('version') != dashboard.get('version'):
        raise ReleaseRejected('The release manager version declarations differ')
    return declared['version']


def validate_integration(package, certificate):
    """Return the package manifest when the extracted package is exactly the certified integration."""
    package = _directory(package)
    if {path.name for path in package.iterdir()} != TOP_LEVEL or {
            path.name for path in (package / 'optional').iterdir()} != {'lifeos_release_manager'}:
        raise ReleaseRejected('The integration package has missing or additional top-level entries')
    manifest = _json(read_manifest(package / MANIFEST_NAME))
    expected = {'format', 'version', 'head', 'plugin_files', 'manager_files', 'host_compatibility_sha256', 'lifeos'}
    if not isinstance(manifest, dict) or set(manifest) != expected or manifest['format'] != 2:
        raise ReleaseRejected('The integration package manifest has an invalid structure')
    if (manifest['version'] != certificate.get('version') or manifest['head'] != certificate.get('program_commit')
            or manifest['lifeos'] != certificate.get('lifeos')
            or manifest['host_compatibility_sha256'] != certificate.get('host_compatibility_sha256')):
        raise ReleaseRejected('The integration package does not match its release certificate')
    if sha(package / COMPATIBILITY) != manifest['host_compatibility_sha256']:
        raise ReleaseRejected('The compatibility manifest differs from its certified identity')
    validate_files(package / 'lifeos_hook_bridge', manifest['plugin_files'], forbid_bytecode=True)
    validate_files(package / 'optional/lifeos_release_manager', manifest['manager_files'], forbid_bytecode=True)
    versions = load_bridge(package / 'lifeos_hook_bridge').memory_module('release_version')
    try:
        bridge_version = versions.versions(package)
    except ValueError as error:
        raise ReleaseRejected('The integration version declarations differ') from error
    if bridge_version != manifest['version'] or _manager_version(package / 'optional/lifeos_release_manager') != manifest['version']:
        raise ReleaseRejected('The integration version declarations differ from the release')
    return manifest
