# ABOUTME: Verifies that managed release configuration enables its required plugins and preserves model choices.
# ABOUTME: Uses real YAML files with disabled plugin entries and existing tier settings.
from pathlib import Path
import tempfile
import unittest

from ruamel.yaml import YAML
from optional.lifeos_release_manager.release_worker import _yaml_configuration


class ReleaseConfigurationTests(unittest.TestCase):
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
