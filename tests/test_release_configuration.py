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
    def test_generated_service_definitions_pass_the_actual_systemd_parser(self):
        from optional.lifeos_release_manager.release_services import service_files
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            profile, generated, installed = root / '.hermes', root / 'generated', root / '.claude'
            for path in (profile, generated, installed / 'LIFEOS/PULSE', root / '.local/bin'):
                path.mkdir(parents=True, mode=0o700)
            for name in ('hermes', 'bun'):
                program = root / '.local/bin' / name
                program.write_text('#!/bin/sh\nexit 0\n')
                program.chmod(0o700)
            files = service_files({'account_home': str(root), 'profile': str(profile), 'installed': str(installed)}, generated)
            result = subprocess.run(['systemd-analyze', '--user', 'verify', *map(str, files.values())],
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout + result.stderr, '')

    def test_unsupported_service_paths_refuse_before_generating_files(self):
        from optional.lifeos_release_manager.release_services import service_files
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            generated = root / 'generated'
            generated.mkdir(mode=0o700)
            for key in ('account_home', 'profile', 'installed'):
                for character in (' ', '$', '\\', '"', "'", '\n', ';', '}'):
                    with self.subTest(key=key, character=character):
                        request = {'account_home': str(root), 'profile': str(root / '.hermes'), 'installed': str(root / '.claude')}
                        request[key] += character + 'unsupported'
                        with self.assertRaisesRegex(ValueError, 'service paths'):
                            service_files(request, generated)
                        self.assertEqual(list(generated.iterdir()), [])

    def test_flow_configuration_prepares_native_mount_without_changing_values(self):
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp)
            original = {'model': {'default': 'synthetic', 'provider': 'custom'},
                'approvals': {'mode': 'manual', 'deny': ['keep']},
                'skills': {'external_dirs': ['/synthetic/retain']},
                'plugins': {'enabled': ['retained'], 'entries': {
                    'lifeos-hook-bridge': {'settings': {'fable_effort': 'xhigh'}}}}}
            (profile / 'config.yaml').write_text(json.dumps(original))
            prepared = _yaml_configuration(profile, profile / 'native').decode()
            # Native Mount.ts edits root sections by their block headers.
            for key in ('model', 'approvals', 'skills', 'plugins'):
                self.assertRegex(prepared, '(?m)^' + key + ':\\s*$')
            actual = YAML(typ='safe').load(prepared)
            for key in ('model', 'approvals', 'skills'):
                self.assertEqual(actual[key], original[key])
            self.assertEqual(actual['plugins']['entries']['lifeos-hook-bridge']['settings']['fable_effort'], 'xhigh')
            self.assertEqual(json.loads((profile / 'config.yaml').read_text()), original)

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
            request = {'profile': str(profile), 'account_home': str(root), 'installed': str(root / '.claude'), 'runtime': {'python': sys.executable, 'source': str(Path(__import__('hermes_cli').__file__).resolve().parents[1]), 'hermes': str(job / 'bin/hermes'), 'bun': str(job / 'tools/bun')},
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

    def test_unchanged_native_update_preserves_baseline_time_and_prepared_bytes(self):
        from types import SimpleNamespace
        from lifeos_hook_bridge import update_plan, version_drift
        from optional.lifeos_release_manager.release_programs import ProgramTransaction
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job, profile, package, installed = root / 'job', root / '.hermes', root / 'package', root / '.claude'
            native = package / 'lifeos/LifeOS/install'
            for path in (job, profile, native, installed):
                path.mkdir(parents=True, mode=0o700)
            subprocess.run(['git', 'init', '-q', str(native)], check=True)
            for tree in (native, installed):
                (tree / 'LIFEOS').mkdir()
                (tree / 'hooks').mkdir()
                (tree / 'LIFEOS/VERSION').write_text('7.40.4\n')
                (tree / 'hooks/Test.hook.ts').write_text('synthetic native hook\n')
            subprocess.run(['git', '-C', str(native), 'add', 'LIFEOS/VERSION', 'hooks'], check=True)
            subprocess.run(['git', '-C', str(native), '-c', 'user.name=Test',
                            '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture'], check=True)
            baseline = version_drift.create_baseline(native, installed)
            baseline['created_at'] = 1
            baseline_path = root / 'baseline.json'
            version_drift.save_baseline(baseline, baseline_path)
            (profile / 'config.yaml').write_text('_config_version: 46\nmodel:\n  default: synthetic-model\n')
            (package / 'DAILY-CANDIDATE.json').write_text('{"plugin_files":{}}')
            for name in ('lifeos_hook_bridge', 'optional/lifeos_release_manager'):
                path = package / name
                path.mkdir(parents=True)
                (path / '__init__.py').write_text('# synthetic reviewed program\n')
            tools = job / 'tools'
            tools.mkdir()
            (tools / 'bun').write_text('#!/bin/sh\nexit 0\n')
            (tools / 'bun').chmod(0o700)
            commands = {name: 'bin/' + name for name in ('hermes', 'hermes-agent', 'hermes-acp')}
            (job / 'manifest.json').write_text(json.dumps({'runtime': {'commands': commands}}))
            request = {'profile': str(profile), 'account_home': str(root), 'installed': str(installed),
                'runtime': {'python': sys.executable, 'source': str(Path(__import__('hermes_cli').__file__).resolve().parents[1]),
                            'hermes': str(job / 'bin/hermes'), 'bun': str(tools / 'bun'), 'reference': str(native)},
                'certificate': {'hermes_base': 'synthetic', 'lifeos_base': 'synthetic',
                                'hermes_patch_count': 10, 'lifeos_patch_count': 25},
                'version': '0.4.2-rc.2', 'commit': 'a' * 40, 'package_sha256': 'b' * 64}
            modules = {'version_drift': version_drift, 'update_plan': update_plan}
            selected = {'profile': profile, 'installed': installed, 'package': package,
                'bridge': profile / 'plugins/lifeos-hook-bridge', 'launchers': [root / '.local/bin/hermes'],
                'current': SimpleNamespace(memory_module=modules.__getitem__), 'fresh': False,
                'native_changes': False, 'baseline': baseline_path}
            directories, files, dependencies = _program_plan(job, request, selected)
            prepared = (job / 'generated/baseline.json').read_bytes()
            self.assertEqual(json.loads(prepared)['created_at'], baseline['created_at'])
            transaction = ProgramTransaction(job / 'program-snapshot')
            transaction.prepare(directories=directories, files=files, dependencies=dependencies)
            self.assertEqual(_program_plan(job, request, selected), (directories, files, dependencies))
            self.assertEqual((job / 'generated/baseline.json').read_bytes(), prepared)
            transaction.check_prepared()
            self.assertEqual(version_drift.load_baseline(baseline_path, installed), baseline)
            (installed / 'hooks/Test.hook.ts').write_text('later native edit\n')
            with self.assertRaisesRegex(update_plan.UpdateConflict, 'changed since baseline'):
                _program_plan(job, request, selected)

    def test_fresh_service_files_are_reviewed_without_starting_or_enabling_them(self):
        from optional.lifeos_release_manager.release_services import service_files
        from optional.lifeos_release_manager.release_programs import ProgramTransaction
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            profile, generated = root / '.hermes', root / 'generated'
            profile.mkdir(mode=0o700)
            generated.mkdir(mode=0o700)
            units = root / '.config/systemd/user'
            units.mkdir(parents=True)
            dashboard = units / 'hermes-dashboard.service'
            original = '# Synthetic existing dashboard\n[Service]\nWorkingDirectory=' + str(root) + '\n'
            dashboard.write_text(original)
            files = service_files({'account_home': str(root), 'profile': str(profile), 'installed': str(root / '.claude')}, generated)
            self.assertEqual(files[dashboard], dashboard)
            gateway, pulse = units / 'hermes-gateway.service', units / 'com.lifeos.pulse.service'
            self.assertFalse(gateway.exists())
            self.assertFalse(pulse.exists())
            self.assertIn('WorkingDirectory=' + str(profile) + '\n', files[gateway].read_text())
            self.assertIn('WorkingDirectory=' + str(root / '.claude/LIFEOS/PULSE') + '\n', files[pulse].read_text())
            transaction = ProgramTransaction(root / 'snapshot')
            transaction.prepare(directories={}, files=files)
            self.assertEqual(len(transaction._load()['entries']), 3)
            transaction.apply()
            self.assertEqual(dashboard.read_text(), original)
            self.assertTrue(gateway.is_file() and pulse.is_file())
            self.assertFalse((units / 'default.target.wants').exists())
            transaction.restore()
            self.assertFalse(gateway.exists() or pulse.exists())
            self.assertEqual(dashboard.read_text(), original)

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
