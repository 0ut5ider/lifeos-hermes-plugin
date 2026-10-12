# ABOUTME: Verifies that managed release configuration enables its required plugins and preserves model choices.
# ABOUTME: Uses real YAML files with disabled plugin entries and existing tier settings.
from pathlib import Path
import tempfile
import json
import os
import sys
import subprocess
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
            (profile / 'config.yaml').write_text('_config_version: 46\nmodel:\n  default: synthetic-model\n')
            (package / 'DAILY-CANDIDATE.json').write_text('{"plugin_files":{}}')
            commands = {name: 'bin/' + name for name in ('hermes', 'hermes-agent', 'hermes-acp')}
            (job / 'manifest.json').write_text(json.dumps({'runtime': {'commands': commands}}))
            (job / 'manifest.json').chmod(0o644)
            request = {'profile': str(profile), 'account_home': str(root), 'runtime': {'python': sys.executable, 'source': str(Path(__import__('hermes_cli').__file__).resolve().parents[1]), 'hermes': str(job / 'bin/hermes'), 'bun': str(job / 'tools/bun')},
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
            for name in commands:
                target = root / '.local/bin' / name
                self.assertIn(target, first[1])
                self.assertEqual(first[1][target].read_text(), '#!/bin/sh\nexec ' + str(job / commands[name]) + ' "$@"\n')
            from hermes_cli.config_defaults import DEFAULT_CONFIG
            yaml = YAML(typ='safe')
            staged = yaml.load((job / 'generated/config.yaml').read_bytes())
            self.assertEqual(staged['_config_version'], DEFAULT_CONFIG['_config_version'])
            before = (job / 'generated/config.yaml').read_bytes()
            checked = subprocess.run([sys.executable, '-B', '-m', 'hermes_cli.main', 'config', 'check'],
                env=dict(os.environ, HOME=str(job), HERMES_HOME=str(job / 'generated'),
                         PYTHONPATH=str(Path(__import__('hermes_cli').__file__).resolve().parents[1]), PYTHONDONTWRITEBYTECODE='1'),
                capture_output=True, text=True, timeout=120)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertEqual((job / 'generated/config.yaml').read_bytes(), before)
            self.assertEqual(yaml.load((profile / 'config.yaml').read_bytes())['_config_version'], 46)

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
