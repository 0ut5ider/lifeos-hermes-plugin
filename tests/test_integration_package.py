# ABOUTME: Checks validation of extracted in-place integration packages against their certificates.
# ABOUTME: Builds packages from this repository's bridge and release manager in disposable directories.
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from optional.lifeos_release_manager.integration_package import (
    COMPATIBILITY, MANIFEST_NAME, file_map, validate_integration)
from optional.lifeos_release_manager.release_catalog import ReleaseRejected


REPOSITORY = Path(__file__).resolve().parents[1]
IGNORED = shutil.ignore_patterns('__pycache__', '*.pyc')


class IntegrationPackageTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.package = Path(self.folder.name) / 'package'
        self.package.mkdir(mode=0o700)
        shutil.copytree(REPOSITORY / 'lifeos_hook_bridge', self.package / 'lifeos_hook_bridge', ignore=IGNORED)
        shutil.copytree(REPOSITORY / 'optional/lifeos_release_manager',
                        self.package / 'optional/lifeos_release_manager', ignore=IGNORED)
        for name in ('VERSION', 'CHANGELOG.md'):
            shutil.copy2(REPOSITORY / name, self.package / name)
        self.version = (REPOSITORY / 'VERSION').read_text().strip()
        self.lifeos = {'upstream': 'https://github.com/danielmiessler/LifeOS.git', 'commit': 'c' * 40,
                       'tree_sha256': 'd' * 64}
        self.write_manifest()
        self.certificate = {'format': 2, 'status': 'QUALIFIED', 'version': self.version, 'program_commit': 'a' * 40,
                            'host_compatibility_sha256': self.manifest['host_compatibility_sha256'],
                            'lifeos': dict(self.lifeos)}

    def write_manifest(self):
        self.manifest = {'format': 2, 'version': self.version, 'head': 'a' * 40,
                         'plugin_files': file_map(self.package / 'lifeos_hook_bridge'),
                         'manager_files': file_map(self.package / 'optional/lifeos_release_manager'),
                         'host_compatibility_sha256': hashlib.sha256(
                             (self.package / COMPATIBILITY).read_bytes()).hexdigest(),
                         'lifeos': dict(self.lifeos)}
        (self.package / MANIFEST_NAME).write_text(json.dumps(self.manifest))

    def test_exact_package_is_accepted(self):
        self.assertEqual(validate_integration(self.package, self.certificate), self.manifest)

    def test_changed_plugin_file_is_refused(self):
        (self.package / 'lifeos_hook_bridge/plugin.yaml').write_text('changed\n')
        with self.assertRaises(ReleaseRejected):
            validate_integration(self.package, self.certificate)

    def test_additional_top_level_entry_is_refused(self):
        (self.package / 'hermes').mkdir()
        with self.assertRaisesRegex(ReleaseRejected, 'top-level'):
            validate_integration(self.package, self.certificate)

    def test_certificate_mismatches_are_refused(self):
        for changes in ({'version': '9.9.9'}, {'program_commit': 'b' * 40}, {'host_compatibility_sha256': 'e' * 64},
                        {'lifeos': {**self.lifeos, 'tree_sha256': 'f' * 64}}):
            with self.subTest(changes=changes), self.assertRaises(ReleaseRejected):
                validate_integration(self.package, {**self.certificate, **changes})

    def test_changed_compatibility_manifest_is_refused_even_with_a_matching_file_map(self):
        path = self.package / COMPATIBILITY
        path.write_text(path.read_text().replace('v0.21.7', 'v9.9.9'))
        self.manifest['manager_files'] = file_map(self.package / 'optional/lifeos_release_manager')
        (self.package / MANIFEST_NAME).write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ReleaseRejected, 'compatibility'):
            validate_integration(self.package, self.certificate)

    def test_manager_version_must_match_the_release(self):
        path = self.package / 'optional/lifeos_release_manager/plugin.yaml'
        path.write_text(path.read_text().replace('version: ' + self.version, 'version: 9.9.9'))
        self.write_manifest()
        with self.assertRaises(ReleaseRejected):
            validate_integration(self.package, self.certificate)


if __name__ == '__main__':
    unittest.main()
