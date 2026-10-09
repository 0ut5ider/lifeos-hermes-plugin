# ABOUTME: Verifies omitted text-release integrations against native modules and configuration.
# ABOUTME: Uses synthetic files and denied Siri requests without network scans or model turns.
import json
import os
from pathlib import Path
import subprocess
import unittest

import test_daily_pulse_profile as profile_fixture
import test_memory_native as native_fixture


class OptionalTextReleaseTests(unittest.TestCase):
    def test_actual_native_profile_excludes_the_private_bunker_integration(self):
        modules = profile_fixture.DailyPulseProfileTests().config()['modules']
        self.assertFalse(modules['bunker'])
        self.assertTrue(modules['local'])
        self.assertTrue(modules['content'])
        self.assertTrue(modules['conduit'])

    def fixture(self):
        fixture = native_fixture.NativeMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        config = fixture.root / 'LIFEOS/USER/CONFIG'
        config.mkdir()
        (config / 'memory-http.json').write_text('{"version":1,"managed":true}')
        sentinel = fixture.root / 'LIFEOS/USER/TELOS/GOALS.md'
        sentinel.parent.mkdir()
        sentinel.write_text('<private>SyntheticOptionalContextHidden</private>\n')
        os.utime(sentinel, (1, 1))
        return fixture, sentinel

    def run_native(self, fixture, script, environment=None):
        result = subprocess.run(['bun', '--no-install', '-e', script], capture_output=True, text=True, timeout=30,
            env=dict(os.environ, HOME=str(fixture.home), CLAUDE_CONFIG_DIR=str(fixture.root),
                HERMES_HOME=str(fixture.home / 'hermes'), **(environment or {})))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, '')
        return result.stdout.splitlines()

    def test_native_bunker_reports_private_implementation_absence_without_scanning(self):
        fixture, sentinel = self.fixture()
        binary = native_fixture.SOURCE / 'LIFEOS/PULSE/Bunker/bin/bunker.ts'
        self.assertFalse(binary.exists(), 'The selected public package must omit the private implementation')
        script = ('import {health,bunkerAvailable,handleRequest} from ' + json.dumps(str(native_fixture.SOURCE / 'LIFEOS/PULSE/modules/bunker.ts'))
            + ';const response=await handleRequest(new Request("http://localhost/api/bunker"),"/api/bunker");'
            + 'console.log(JSON.stringify({available:bunkerAvailable(),health:health(),board:await response.json()}));')
        lines = self.run_native(fixture, script, {'BUNKER_DIR': str(native_fixture.SOURCE / 'LIFEOS/PULSE/Bunker')})
        self.assertEqual(len(lines), 1)
        body = json.loads(lines[0])
        self.assertFalse(body['available'])
        self.assertEqual(body['health']['status'], 'unavailable')
        self.assertEqual(body['board']['apps'], [])
        self.assertEqual(body['board']['summary']['apps'], 0)
        self.assertEqual(sentinel.stat().st_atime_ns, 1000000000)

    def test_siri_unset_or_incorrect_key_refuses_before_context_or_turn_processing(self):
        fixture, sentinel = self.fixture()
        for key in ('', 'synthetic-not-an-account-key'):
            with self.subTest(configured=bool(key)):
                script = ('import {handleSiriRequest,siriHealth} from ' + json.dumps(str(native_fixture.SOURCE / 'LIFEOS/PULSE/modules/siri.ts'))
                    + ';const request=new Request("http://localhost/api/siri/turn",{method:"POST",headers:{"authorization":"Bearer invalid"},body:JSON.stringify({text:"SyntheticOptionalContextHidden"})});'
                    + 'const response=await handleSiriRequest(request,"/api/siri/turn");console.log(JSON.stringify({status:response.status,body:await response.json(),health:siriHealth()}));')
                lines = self.run_native(fixture, script, {'SIRI_API_KEY': key})
                self.assertEqual(len(lines), 2)
                warning = json.loads(lines[0])
                self.assertEqual((warning['module'], warning['level'], warning['msg']), ('siri', 'warn', 'unauthorized siri request'))
                body = json.loads(lines[1])
                self.assertEqual(body['status'], 401)
                self.assertEqual(body['body'], {'error': 'unauthorized'})
                self.assertEqual(body['health'], {'configured': bool(key), 'turnsServed': 0, 'lastError': None})
                self.assertEqual(sentinel.stat().st_atime_ns, 1000000000)


if __name__ == '__main__': unittest.main()
