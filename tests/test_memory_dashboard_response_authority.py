# ABOUTME: Checks dashboard preference authority after actual wiki, Knowledge, and Pulse rendering.
# ABOUTME: Uses real native readers and account revocation without replacing renderer responses.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_pulse_auth as auth_fixture


class MemoryDashboardResponseAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.fixture=auth_fixture.MemoryPulseAuthTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def assert_view_withheld(self,view,mode="revoke"):
        expected=mode!="unchanged"
        result=subprocess.run([sys.executable,str(Path(__file__).with_name('memory_dashboard_response_process.py')),
            str(self.fixture.configuration.path),view,mode],capture_output=True,text=True,timeout=40,
            env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1])))
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),{'rendered':True,'withheld':expected})

    def test_wiki_result_is_withheld_after_account_revocation(self):self.assert_view_withheld('wiki')
    def test_knowledge_result_is_withheld_after_account_revocation(self):self.assert_view_withheld('knowledge')
    def test_pulse_result_is_withheld_after_account_revocation(self):self.assert_view_withheld('pulse')

    def test_unchanged_authority_preserves_each_native_response(self):
        for view in ('wiki','knowledge','pulse'):
            with self.subTest(view=view):self.assert_view_withheld(view,'unchanged')

    def test_changed_configuration_with_owner_binding_retained_withholds_response(self):
        self.assert_view_withheld('pulse','configuration')
