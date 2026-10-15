# ABOUTME: Verifies frozen recovery admission before retained manager code can execute.
# ABOUTME: Rejects changed code, private owner metadata, and cross-workflow marker substitutions.
import json
from pathlib import Path
import unittest

import test_removal_state as fixture
from optional.lifeos_release_manager.release_programs import publish


class RemovalBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.RemovalStateTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)

    def validate(self):
        from optional.lifeos_release_manager.removal_bootstrap import validate
        return validate(self.fixture.profile,self.fixture.job.name)

    def test_exact_retained_code_is_admitted_before_interactive_authentication(self):
        result=self.validate()
        self.assertEqual(result['signature'],self.fixture.signature)
        self.assertEqual(result['worker'],str(self.fixture.stage/'recovery-manager/removal_recovery.py'))

    def test_changed_manager_and_bridge_code_refuse_before_execution(self):
        for relative in ('recovery-manager/removal_recovery.py','recovery-bridge/memory_service.py'):
            path=self.fixture.stage/relative;data=path.read_bytes();path.write_bytes(data+b'\n# Synthetic changed source\n')
            with self.subTest(relative=relative),self.assertRaises(ValueError):self.validate()
            path.write_bytes(data)

    def test_other_workflow_and_public_marker_refuse(self):
        path=self.fixture.profile/'.lifeos-removal.json';data=path.read_bytes()
        marker=json.loads(data);marker['workflow']='b'*32;publish(path,json.dumps(marker).encode())
        with self.assertRaises(ValueError):self.validate()
        publish(path,data);path.chmod(0o644)
        with self.assertRaises(ValueError):self.validate()

    def test_actual_sealed_stock_command_bootstraps_help_without_authentication(self):
        import os
        import subprocess
        runtime=Path(os.environ.get('LIFEOS_STOCK_RUNTIME','/home/outsider/.cache/lifeos-memory-portability-20261015/stock-full-9b204dad/runtime'))
        if not (runtime/'runtime.json').is_file():self.skipTest('Constructed stock runtime is required')
        from optional.lifeos_release_manager.removal_preparation import _recovery_command
        command=self.fixture.stage/'recover'
        publish(command,_recovery_command(self.fixture.profile,self.fixture.job,json.loads((runtime/'runtime.json').read_bytes())),0o700)
        environment={**os.environ,'HERMES_HOME':str(self.fixture.profile),'PYTHONDONTWRITEBYTECODE':'1'}
        result=subprocess.run([str(command),'--help'],env=environment,capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stderr,'')
        self.assertIn('Authenticate and resume or roll back',result.stdout)
        self.assertNotIn('Dashboard password:',result.stdout)
