# ABOUTME: Prepares the selected latest stable Hermes release with the complete bridge extension.
# ABOUTME: Verifies the actual prepared source, plugin capabilities, and repeatable patch output.
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from lifeos_hook_bridge.install_source import prepare_supported_hermes, validate_supported_hermes


class LatestHermesTests(unittest.TestCase):
    def test_latest_stable_release_prepares_and_validates_without_changing_upstream(self):
        source = Path(os.environ['LIFEOS_LATEST_HERMES_SOURCE'])
        expected = '71d34bad1045610252eda02ee79549436896e784'
        before = subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
        self.assertEqual(before, expected)
        with tempfile.TemporaryDirectory() as temp:
            prepared = Path(temp)/'hermes'
            result = prepare_supported_hermes(source, prepared)
            self.assertEqual(result['base_commit'], expected)
            self.assertEqual(validate_supported_hermes(prepared), result)
            self.assertEqual(len(result['patches']), 10)
            checks = subprocess.run([os.environ['LIFEOS_TEST_PYTHON'],'-c',
                'from hermes_cli.plugins import VALID_HOOKS\n'
                'from hermes_cli.middleware import REQUIRED_MIDDLEWARE_API_VERSION\n'
                'assert REQUIRED_MIDDLEWARE_API_VERSION == 1\n'
                'assert {"pre_prompt_admission","pre_command_approval","pre_turn_stop","pre_message_delivery","on_turn_result"} <= VALID_HOOKS\n'],
                cwd=prepared,env=dict(os.environ,PYTHONPATH=str(prepared)),capture_output=True,text=True,timeout=30)
            self.assertEqual((checks.returncode,checks.stderr),(0,''),checks.stdout)
        self.assertEqual(subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip(),before)
        self.assertEqual(subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True),'')
