# ABOUTME: Checks exact test-package and version-derivative bindings with real archives and files.
# ABOUTME: Refuses altered source, unexpected files, and changes hidden in permitted version files.
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from qualification_artifacts import archive_files, package_matches, version_derivative

DECLARATIONS = ('VERSION', 'lifeos_hook_bridge/plugin.yaml', 'lifeos_hook_bridge/dashboard/manifest.json',
    'optional/lifeos_release_manager/plugin.yaml', 'optional/lifeos_release_manager/dashboard/manifest.json')


class QualificationArtifactTests(unittest.TestCase):
    def archive(self, path, values):
        with tarfile.open(path, 'w:gz') as archive:
            for name, data in values.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                info.mode = 0o644
                archive.addfile(info, io.BytesIO(data))

    def test_actual_archive_and_package_match_then_changed_source_refuses(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive, package = root / 'archive.tgz', root / 'package'
            self.archive(archive, {'manager.py': b'value = 1\n'})
            package.mkdir()
            (package / 'manager.py').write_bytes(b'value = 1\n')
            (package / 'manager.py').chmod(0o600)
            expected = archive_files(archive)
            self.assertEqual(package_matches(package, expected)['generated_bytecode_files'], 0)
            (package / 'manager.py').write_bytes(b'value = 2\n')
            with self.assertRaisesRegex(ValueError, 'archived file'):
                package_matches(package, expected)

    def test_added_source_and_symlink_refuse(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive, package = root / 'archive.tgz', root / 'package'
            self.archive(archive, {'manager.py': b'value = 1\n'})
            package.mkdir()
            source = package / 'manager.py'
            source.write_bytes(b'value = 1\n')
            source.chmod(0o600)
            expected = archive_files(archive)
            (package / 'extra.py').write_text('unexpected\n')
            with self.assertRaisesRegex(ValueError, 'unexpected file'):
                package_matches(package, expected)
            (package / 'extra.py').unlink()
            source.unlink()
            source.symlink_to(archive)
            with self.assertRaisesRegex(ValueError, 'archived file'):
                package_matches(package, expected)

    def test_generated_bytecode_requires_an_archived_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive, package = root / 'archive.tgz', root / 'package'
            self.archive(archive, {'manager.py': b'value = 1\n'})
            package.mkdir()
            source = package / 'manager.py'
            source.write_bytes(b'value = 1\n')
            source.chmod(0o600)
            cache = Path(importlib.util.cache_from_source(str(source)))
            cache.parent.mkdir()
            cache.write_bytes(b'synthetic cache metadata')
            expected = archive_files(archive)
            self.assertEqual(package_matches(package, expected, allow_generated=True)['generated_bytecode_files'], 1)
            cache.rename(cache.with_name('unexpected.cpython-314.pyc'))
            with self.assertRaisesRegex(ValueError, 'unexpected file'):
                package_matches(package, expected)

    def versions(self):
        import hashlib
        first = {name: b'version: 0.4.2-rc.1\n' for name in DECLARATIONS}
        first['CHANGELOG.md'] = b'# Changelog\n\n## 0.4.2-rc.1\n'
        second = {name: data.replace(b'0.4.2-rc.1', b'0.4.2-rc.2') for name, data in first.items()}
        second['CHANGELOG.md'] = first['CHANGELOG.md'].replace(b'# Changelog\n', CHANGELOG_ADDITION, 1)
        manifest = {'version': '0.4.2-rc.1', 'head': 'a' * 40,
            'plugin_files': {p: hashlib.sha256(v).hexdigest() for p, v in first.items() if p.startswith('lifeos_hook_bridge/')},
            'manager_files': {p.removeprefix('optional/lifeos_release_manager/'): hashlib.sha256(v).hexdigest()
                for p, v in first.items() if p.startswith('optional/lifeos_release_manager/')}}
        first['DAILY-CANDIDATE.json'] = json.dumps(manifest).encode()
        next_manifest = dict(manifest, version='0.4.2-rc.2', head='b' * 40,
            plugin_files={p: hashlib.sha256(v).hexdigest() for p, v in second.items() if p.startswith('lifeos_hook_bridge/')},
            manager_files={p.removeprefix('optional/lifeos_release_manager/'): hashlib.sha256(v).hexdigest()
                for p, v in second.items() if p.startswith('optional/lifeos_release_manager/')})
        second['DAILY-CANDIDATE.json'] = json.dumps(next_manifest).encode()
        return first, second

    def test_version_only_derivative_matches_exact_transformations(self):
        with tempfile.TemporaryDirectory() as temp:
            first, second = self.versions()
            a, b = Path(temp) / 'first.tgz', Path(temp) / 'second.tgz'
            self.archive(a, first)
            self.archive(b, second)
            version_derivative(a, b, 'a' * 40, 'b' * 40)

    def test_allowed_plugin_filename_cannot_hide_another_change(self):
        with tempfile.TemporaryDirectory() as temp:
            first, second = self.versions()
            second['lifeos_hook_bridge/plugin.yaml'] += b'dependency: unexpected\n'
            a, b = Path(temp) / 'first.tgz', Path(temp) / 'second.tgz'
            self.archive(a, first)
            self.archive(b, second)
            with self.assertRaisesRegex(ValueError, 'version declaration'):
                version_derivative(a, b, 'a' * 40, 'b' * 40)

    def test_main_manifest_cannot_hide_a_dependency_change(self):
        with tempfile.TemporaryDirectory() as temp:
            first, second = self.versions()
            manifest = json.loads(second['DAILY-CANDIDATE.json'])
            manifest['python_runtime_files'] = {'uv.lock': 'changed'}
            second['DAILY-CANDIDATE.json'] = json.dumps(manifest).encode()
            a, b = Path(temp) / 'first.tgz', Path(temp) / 'second.tgz'
            self.archive(a, first)
            self.archive(b, second)
            with self.assertRaisesRegex(ValueError, 'candidate manifest'):
                version_derivative(a, b, 'a' * 40, 'b' * 40)


CHANGELOG_ADDITION = b'# Changelog\n\n## 0.4.2-rc.2 (unpublished version-only test candidate)\n\n- Change the complete integration version to verify a numerical update through Hermes and both dashboard update controls.\n- Keep the program behavior from the corrected 0.4.2-rc.1 candidate.\n'
