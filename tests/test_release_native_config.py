# ABOUTME: Verifies native configuration migration before a mount publishes its expected output.
# ABOUTME: Uses the real installed migration code and keeps the live profile unchanged during staging.
import os
from pathlib import Path
import tempfile
import unittest

from ruamel.yaml import YAML
from lifeos_hook_bridge.mount_transaction import _check_prepared_config


class ReleaseNativeConfigurationTests(unittest.TestCase):
    def test_staged_configuration_migrates_without_changing_the_live_profile(self):
        from hermes_cli.config_defaults import DEFAULT_CONFIG
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            live, stage, installed = root / 'live', root / 'stage', root / '.claude'
            for folder in (live, stage, installed):
                folder.mkdir(mode=0o700)
            data = b'_config_version: 46\nmodel:\n  default: synthetic-model\n'
            (live / 'config.yaml').write_bytes(data)
            (stage / 'config.yaml').write_bytes(data)
            _check_prepared_config(installed, dict(os.environ, HOME=str(root), HERMES_HOME=str(live)), stage)
            migrated = YAML(typ='safe').load((stage / 'config.yaml').read_bytes())
            self.assertEqual(migrated['_config_version'], DEFAULT_CONFIG['_config_version'])
            self.assertEqual(migrated['model'], {'default': 'synthetic-model'})
            self.assertEqual((live / 'config.yaml').read_bytes(), data)
