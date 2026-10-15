# ABOUTME: Verifies current profile transformation for complete LifeOS software removal.
# ABOUTME: Tests retained model and credential settings and actual stock Discord disable admission.
import io
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from ruamel.yaml import YAML


class RemovalConfigurationTests(unittest.TestCase):
    def operation(self):
        from optional.lifeos_release_manager import removal_configuration
        return removal_configuration

    def test_removal_preserves_current_settings_and_detaches_aliases(self):
        data=b'''# Current owner configuration
model: {default: current-model, base_url: http://127.0.0.1:9}
other_enabled: &selected [lifeos, lifeos-release-manager, other]
other_entry: &entry {enabled: false, value: keep}
memory: {provider: builtin, memory_enabled: true, user_profile_enabled: true}
plugins:
  enabled: *selected
  disabled: [lifeos-hook-bridge, other-disabled]
  entries:
    lifeos: *entry
    other: *entry
skills: {external_dirs: [/account/.claude/skills, /other/skills]}
platforms:
  discord: {enabled: true, token: synthetic-token, extra: {allowed_channels: ['123']}}
  telegram: {enabled: false, token: synthetic-other-token}
custom: keep-current
'''
        result=self.operation().configuration(data,Path('/account/.claude'))
        value=YAML(typ='safe').load(result)
        self.assertIn(b'# Current owner configuration',result)
        self.assertEqual(value['model']['default'],'current-model')
        self.assertEqual(value['other_enabled'],['lifeos','lifeos-release-manager','other'])
        self.assertEqual(value['other_entry'],{'enabled':False,'value':'keep'})
        self.assertEqual(value['plugins']['enabled'],['other'])
        self.assertEqual(value['plugins']['disabled'],['other-disabled'])
        self.assertEqual(value['plugins']['entries'],{'other':{'enabled':False,'value':'keep'}})
        self.assertEqual(value['skills']['external_dirs'],['/other/skills'])
        self.assertFalse(value['platforms']['discord']['enabled'])
        self.assertEqual(value['platforms']['discord']['token'],'synthetic-token')
        self.assertEqual(value['platforms']['telegram']['token'],'synthetic-other-token')
        self.assertEqual(value['memory'],{'memory_enabled':True,'user_profile_enabled':True})
        self.assertEqual(value['custom'],'keep-current')

    def test_native_ownership_or_ambiguous_aliases_refuse(self):
        for data in (b'memory: {provider: lifeos-hook-bridge}\n',b'memory: &shared {provider: builtin}\nother: *shared\n',
                     b'memory: {provider: builtin, memory_enabled: false}\n', b'plugins: {enabled: other}\n'):
            with self.subTest(data=data),self.assertRaises(ValueError):self.operation().configuration(data,Path('/account/.claude'))

    def test_stock_gateway_keeps_discord_disabled_with_env_token(self):
        result=self.operation().configuration(b'memory: {provider: builtin}\n',Path('/account/.claude'))
        with tempfile.TemporaryDirectory() as folder:
            profile=Path(folder);(profile/'config.yaml').write_bytes(result)
            code='''import io,logging,sys
from pathlib import Path
from hermes_constants import set_hermes_home_override
set_hermes_home_override(sys.argv[1])
from gateway.config import load_gateway_config,Platform
capture=io.StringIO();handler=logging.StreamHandler(capture)
logging.getLogger().addHandler(handler)
config=load_gateway_config()
assert config.platforms[Platform.DISCORD].enabled is False
assert Platform.DISCORD not in config.get_connected_platforms()
logging.getLogger().removeHandler(handler)
assert 'explicitly disabled' in capture.getvalue()
'''
            source='/home/outsider/.cache/lifeos-daily-promotion-20261014/upstream-hermes'
            env=dict(os.environ,PYTHONPATH=source,DISCORD_BOT_TOKEN='synthetic-not-a-token',HERMES_HOME=str(profile),HOME=folder)
            child=subprocess.run([sys.executable,'-B','-c',code,str(profile)],env=env,text=True,capture_output=True,timeout=30)
            self.assertEqual(child.returncode,0,child.stdout+child.stderr)
            self.assertEqual(child.stdout+child.stderr,'')

    def test_environment_removes_only_the_exact_owned_block(self):
        operation=self.operation();profile=Path('/account/.hermes');workspace=Path('/account/workspace')
        block=operation.environment_block(profile,workspace)
        data=b'# Keep owner settings\nAPI_TOKEN=synthetic-token\n'+block+b'OTHER=keep\n'
        self.assertEqual(operation.environment(data,profile,workspace),b'# Keep owner settings\nAPI_TOKEN=synthetic-token\nOTHER=keep\n')
        custom=b'HERMES_WRITE_SAFE_ROOT=/owner/custom\nOTHER=keep\n'
        self.assertEqual(operation.environment(custom,profile,workspace),custom)
