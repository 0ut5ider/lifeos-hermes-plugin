# ABOUTME: Verifies that managed release configuration enables its required plugins and preserves model choices.
# ABOUTME: Uses real YAML files with disabled plugin entries and existing tier settings.
from pathlib import Path
import tempfile
import unittest

from ruamel.yaml import YAML
from optional.lifeos_release_manager.release_worker import _yaml_configuration, _program_plan


class ReleaseConfigurationTests(unittest.TestCase):
    def test_program_plan_rebuilds_private_outputs_after_incomplete_preparation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job, profile, package = root / 'job', root / '.hermes', root / 'package'
            for path in (job, profile, package):
                path.mkdir(mode=0o700)
            (profile / 'config.yaml').write_text('model:\n  default: synthetic-model\n')
            (package / 'DAILY-CANDIDATE.json').write_text('{"plugin_files":{}}')
            request = {'account_home': str(root), 'runtime': {'hermes': str(job / 'bin/hermes'), 'bun': str(job / 'tools/bun')},
                       'certificate': {'hermes_base': 'synthetic', 'lifeos_base': 'synthetic',
                           'hermes_patch_count': 10, 'lifeos_patch_count': 25},
                       'version': '0.4.0-dev.1', 'commit': 'a' * 40, 'package_sha256': 'b' * 64}
            selected = {'profile': profile, 'installed': root / '.claude', 'package': package,
                        'bridge': profile / 'plugins/lifeos-hook-bridge', 'launchers': [root / '.local/bin/hermes'],
                        'current': None, 'fresh': True}
            first = _program_plan(job, request, selected)
            second = _program_plan(job, request, selected)
            self.assertEqual(first, second)
            self.assertFalse(selected['installed'].exists())

    def test_required_enablement_preserves_other_plugins_and_model_tiers(self):
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp)
            data = {'model': {'default': 'synthetic-flash', 'provider': 'custom', 'reasoning_effort': 'high'},
                'plugins': {'enabled': ['another-plugin'], 'disabled': ['lifeos-hook-bridge', 'disabled-plugin'],
                    'entries': {'lifeos-hook-bridge': {'settings': {'haiku_effort': 'low', 'fable_effort': 'ultra'}}}}}
            yaml = YAML()
            with (profile / 'config.yaml').open('w') as output:
                yaml.dump(data, output)
            result = yaml.load(_yaml_configuration(profile, profile / 'source'))
            self.assertEqual(result['model'], data['model'])
            self.assertEqual(result['plugins']['enabled'], ['another-plugin', 'lifeos-hook-bridge', 'lifeos-release-manager'])
            self.assertEqual(result['plugins']['disabled'], ['disabled-plugin'])
            settings = result['plugins']['entries']['lifeos-hook-bridge']['settings']
            self.assertEqual(settings['haiku_effort'], 'low')
            self.assertEqual(settings['fable_effort'], 'ultra')
