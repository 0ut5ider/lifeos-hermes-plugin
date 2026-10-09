# ABOUTME: Exercises the native fill failure through the actual selected child command.
# ABOUTME: Requires rejected research errors in digest metadata without a model request.
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import unittest
import test_memory_local_refresh_jobs as fixture


class NativeLocalFillTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.MemoryLocalRefreshJobCommandTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_actual_rejected_child_error_is_retained_in_digest(self):
        command = self.fixture.fixture.fixture
        profile = command.fixture.home
        root = command.native.root
        launcher = command.native.home / '.local/bin/hermes'
        launcher.parent.mkdir(parents=True, exist_ok=True)
        launcher.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' -m hermes_cli.main "$@"\n')
        launcher.chmod(0o700)
        tools = Path(__file__).resolve().parents[1] / 'lifeos_hook_bridge/bin'
        environment = {key: os.environ[key] for key in ('LANG', 'TZ') if key in os.environ}
        environment.update(HOME=str(command.native.home), HERMES_HOME=str(profile),
            PATH=os.pathsep.join([str(tools), str(launcher.parent), str(Path(sys.executable).parent), os.environ['PATH']]),
            PYTHONPATH=os.environ['LIFEOS_HERMES_SOURCE'], LIFEOS_MEMORY_CONFIGURATION_REVISION='0' * 64,
            LIFEOS_MODEL_TIER_MAP=json.dumps({'sonnet': {'provider': 'custom', 'model': 'synthetic-model', 'effort': 'medium'}}),
            BUN_CONFIG_NO_AUTO_INSTALL='1')
        value = {'meta': {'city': 'SyntheticCity', 'state': 'TX', 'county': 'Synthetic', 'zip': '78701',
            'generated_at': datetime.now(timezone.utc).isoformat(), 'sources_used': [], 'sources_failed': [], 'errors': []}}
        value.update({key: {'source_status': 'empty', 'items': []} for key in
            ('construction','crime','business','officials','legislation','elections','arrests','news')})
        source = root / 'skills/LocalIntelligence/Tools/ClaudeFill.ts'
        program = 'import {claudeFill} from ' + json.dumps(str(source)) + ';console.log(JSON.stringify(await claudeFill('
        program += json.dumps(value) + ',{city:"SyntheticCity",state:"TX",stateSlug:"tx",citySlug:"syntheticcity"}, {timeoutMs:10000})));'
        result = subprocess.run(['bun', '--no-install', '-e', program], env=environment,
            capture_output=True, text=True, timeout=20)
        self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout)
        outcome = json.loads(result.stdout)
        self.assertEqual(len(outcome['errors']), 1)
        self.assertIn('claude-fill:', outcome['errors'][0])
        self.assertEqual(outcome['digest']['meta']['errors'], outcome['errors'])
        self.assertEqual(command.fixture.fixture.received, [])

    def test_actual_researched_section_lists_report_invalid_shape_without_becoming_items(self):
        source = Path(os.environ['LIFEOS_MEMORY_SOURCE']) / 'skills/LocalIntelligence/Tools/ClaudeFill.ts'
        capture = Path(__file__).resolve().parents[1] / 'docs/verification/2026-10-08-remaining-reader-audit/local-research-invalid-sections.json'
        program = 'import {validateSection} from ' + json.dumps(str(source)) + ';'
        program += 'const recorded=await Bun.file(' + json.dumps(str(capture)) + ').json();'
        program += 'console.log(JSON.stringify({recorded:Object.fromEntries(Object.entries(recorded).map(([key,value])=>[key,validateSection(value)])),'
        program += 'empty:validateSection({items:[]}),missing:validateSection({}),wrong:validateSection({items:"invalid"})}));'
        result = subprocess.run(['bun', '--no-install', '-e', program], capture_output=True, text=True, timeout=10)
        self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout)
        observed = json.loads(result.stdout)
        self.assertEqual(len(observed['recorded']), 8)
        for section in observed['recorded'].values():
            self.assertEqual(section, {'items': [], 'dropped': 1})
        self.assertEqual(observed['empty'], {'items': [], 'dropped': 0})
        self.assertEqual(observed['missing'], {'items': [], 'dropped': 1})
        self.assertEqual(observed['wrong'], {'items': [], 'dropped': 1})
