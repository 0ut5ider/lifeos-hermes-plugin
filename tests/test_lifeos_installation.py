# ABOUTME: Checks the profile setting that selects which LifeOS home a Hermes profile uses.
# ABOUTME: Covers the account-home default, validation, publication, and removal.
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lifeos_hook_bridge import lifeos_installation as setting


class LifeOSInstallationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.account = self.root / 'account'
        self.profile = self.account / '.hermes'
        self.profile.mkdir(parents=True, mode=0o700)
        self.store = self.root / 'store/home'
        (self.store / '.claude').mkdir(parents=True, mode=0o700)
        environment = patch.dict(os.environ, {'HOME': str(self.account)})
        environment.start()
        self.addCleanup(environment.stop)

    def test_profile_without_a_setting_uses_the_account_home(self):
        selected = setting.selection(self.profile)
        self.assertEqual(selected.home, self.account)
        self.assertEqual(selected.installed, self.account / '.claude')
        self.assertEqual(selected.workspace, self.account / 'HermesWorkspace')
        self.assertFalse(selected.configured)

    def test_published_setting_selects_another_home_and_keeps_the_workspace(self):
        setting.publish(self.profile, self.store, self.account / 'HermesWorkspace')
        path = self.profile / setting.SETTING
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(path.read_text()), {'version': 1, 'home': str(self.store),
                                                        'workspace': str(self.account / 'HermesWorkspace')})
        selected = setting.selection(self.profile)
        self.assertEqual(selected.installed, self.store / '.claude')
        self.assertEqual(selected.user_data, self.store / '.config/LIFEOS/USER')
        self.assertEqual(selected.workspace, self.account / 'HermesWorkspace')
        self.assertTrue(selected.configured)
        setting.clear(self.profile)
        self.assertEqual(setting.selection(self.profile).home, self.account)

    def test_invalid_settings_are_refused(self):
        path = self.profile / setting.SETTING
        cases = {
            'relative home': {'version': 1, 'home': 'store/home', 'workspace': str(self.account)},
            'missing installation': {'version': 1, 'home': str(self.root), 'workspace': str(self.account)},
            'unknown version': {'version': 2, 'home': str(self.store), 'workspace': str(self.account)},
            'extra field': {'version': 1, 'home': str(self.store), 'workspace': str(self.account), 'root': '/'},
        }
        for name, value in cases.items():
            with self.subTest(name):
                path.write_text(json.dumps(value))
                path.chmod(0o600)
                with self.assertRaises(ValueError):
                    setting.selection(self.profile)
        path.write_text(json.dumps({'version': 1, 'home': str(self.store), 'workspace': str(self.account)}))
        path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'private'):
            setting.selection(self.profile)
        path.unlink()
        path.symlink_to(self.root / 'elsewhere.json')
        with self.assertRaisesRegex(ValueError, 'regular'):
            setting.selection(self.profile)


if __name__ == '__main__':
    unittest.main()


class SelectedHomeRegistrationTests(unittest.TestCase):
    def test_registered_hooks_run_in_the_selected_lifeos_home(self):
        import sys
        import types
        from lifeos_hook_bridge import register, PATCHED_HOOKS
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            account, store = root / 'account', root / 'store/home'
            profile = account / '.hermes'
            profile.mkdir(parents=True, mode=0o700)
            (store / '.claude').mkdir(parents=True)
            record = root / 'record.json'
            hook = store / '.claude/record.py'
            hook.write_text('import json,os,sys\njson.load(sys.stdin)\n'
                            f'open({str(record)!r},"w").write(json.dumps({{"home":os.environ["HOME"],'
                            '"lifeos":os.environ["LIFEOS_DIR"],"hermes":os.environ["HERMES_HOME"],'
                            '"account":os.environ["LIFEOS_ACCOUNT_HOME"],'
                            '"git":os.environ["GIT_CONFIG_GLOBAL"]}))\n')
            (account / '.gitconfig').write_text('[user]\n\tname = Synthetic Owner\n')
            (store / '.claude/settings.json').write_text(json.dumps({
                'env': {'LIFEOS_DIR': '$HOME/.claude/LIFEOS'},
                'hooks': {'UserPromptSubmit': [{'hooks': [{'type': 'command',
                    'command': f'{sys.executable} $HOME/.claude/record.py'}]}]}}))
            setting.publish(profile, store, account / 'HermesWorkspace')

            class Context:
                def __init__(self):
                    self.hooks, self.unload = {}, []
                def register_cli_command(self, name, **entry): pass
                def get_config(self, name, default=None): return default
                def register_hook(self, name, callback): self.hooks.setdefault(name, []).append(callback)
                def on_unload(self, callback): self.unload.append(callback)

            host = types.ModuleType('hermes_cli.plugins')
            host.VALID_HOOKS = set(PATCHED_HOOKS) | {'pre_tool_call', 'post_tool_call', 'on_session_finalize',
                                                     'api_request_error'}
            constants = types.ModuleType('hermes_constants')
            constants.get_hermes_home = lambda: profile
            ctx = Context()
            environment = {key: value for key, value in os.environ.items() if key != 'LIFEOS_HOOK_SETTINGS'}
            with patch.dict(sys.modules, {'hermes_cli': types.ModuleType('hermes_cli'), 'hermes_cli.plugins': host,
                                          'hermes_constants': constants}), \
                    patch.dict(os.environ, {**environment, 'HOME': str(account)}, clear=True):
                register(ctx)
                self.addCleanup(lambda: [callback() for callback in ctx.unload])
                ctx.hooks['pre_prompt_admission'][0](user_message='hello', session_id='session')
                for callback in ctx.hooks.get('on_turn_result', []):
                    callback(session_id='session')
            self.assertEqual(json.loads(record.read_text()),
                             {'home': str(store), 'lifeos': str(store / '.claude/LIFEOS'), 'hermes': str(profile),
                              'account': str(account), 'git': str(account / '.gitconfig')})
