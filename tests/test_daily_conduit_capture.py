# ABOUTME: Verifies selected Conduit capture through the native daily scheduler command path.
# ABOUTME: Checks headless source selection, private events, and repeat activity capture.
import json
import os
import subprocess
import sys
from pathlib import Path
import unittest

import test_daily_pulse_profile as profile_fixture
from test_memory_conduit_capture_job import seed

TEMPLATE = profile_fixture.ROOT / 'docs/deployment/daily-text/CONDUIT.config.json'


class DailyConduitCaptureTests(unittest.TestCase):
    def fixture(self):
        control = profile_fixture.DailyPulseProfileTests()
        fixture, environment = control.owner_fixture()
        self.addCleanup(control.doCleanups)
        return control, fixture, environment

    def test_native_daily_profile_selects_fixed_owner_capture_with_local_output(self):
        control = profile_fixture.DailyPulseProfileTests()
        jobs = control.config()['jobs']
        capture = [job for job in jobs if job['name'] == 'conduit-capture']
        self.assertEqual(len(capture), 1)
        job = capture[0]
        self.assertEqual(job['command'], 'hermes lifeos-job conduit-capture')
        self.assertEqual(job['schedule'], '*/2 * * * *')
        self.assertEqual(job['output'], 'log')
        self.assertEqual(job['type'], 'script')
        self.assertTrue(job['enabled'])
        self.assertNotIn('scheduleError', job)

    def test_selected_native_configuration_uses_only_the_work_event_adapter(self):
        self.assertTrue(TEMPLATE.is_file(), 'The headless capture template must exist')
        config = json.loads(TEMPLATE.read_text())
        self.assertTrue(config['enabled'])
        self.assertEqual(config['pollIntervalSec'], 120)
        self.assertEqual(config['sources'], {'appFocus': False, 'git': False,
            'claudeSession': True, 'github': False})
        self.assertEqual(config['repos'], [])
        self.assertEqual(config['retentionDays'], 30)

    def test_native_spawn_uses_template_and_actual_hermes_parser_without_inference(self):
        self.assertTrue(TEMPLATE.is_file(), 'The headless capture template must exist')
        control, fixture, environment = self.fixture()
        data = seed(fixture.native.root)
        (data / 'config.json').write_bytes(TEMPLATE.read_bytes())
        first = control.call(environment=environment, name='conduit-capture')
        self.assertEqual((first.returncode, first.stderr), (0, ''), first.stdout + first.stderr)
        value = json.loads(json.loads(first.stdout)['output'])
        self.assertEqual(value['status'], 'completed', value)
        self.assertEqual(value['output'], 'captured 1 event(s)\n')
        events = list((data / 'events').glob('*.jsonl'))
        self.assertEqual(len(events), 1)
        before = events[0].read_bytes()
        self.assertEqual(events[0].stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(before)['detail']['lastSlug'], 'synthetic-owner-job-work')
        repeat = control.call(environment=environment, name='conduit-capture')
        self.assertEqual((repeat.returncode, repeat.stderr), (0, ''), repeat.stdout + repeat.stderr)
        value = json.loads(json.loads(repeat.stdout)['output'])
        self.assertEqual(value['status'], 'completed', value)
        self.assertEqual(value['output'], 'captured 0 event(s)\n')
        self.assertEqual(events[0].read_bytes(), before)
        self.assertEqual(fixture.fixture.fixture.received, [])

    def test_native_spawn_refuses_capture_without_current_owner_activation(self):
        self.assertTrue(TEMPLATE.is_file(), 'The headless capture template must exist')
        control, fixture, environment = self.fixture()
        data = seed(fixture.native.root)
        (data / 'config.json').write_bytes(TEMPLATE.read_bytes())
        fixture.configuration.update(lambda value: value.update(ownership_enabled=False))
        result = control.call(environment=environment, name='conduit-capture')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Script exited 1', result.stderr)
        self.assertFalse((data / 'events').exists())
        self.assertFalse((data / 'state.json').exists())
        self.assertEqual(fixture.fixture.fixture.received, [])

    def test_actual_hermes_isa_hook_produces_the_work_events_that_scheduled_capture_consumes(self):
        self.assertTrue(TEMPLATE.is_file(), 'The headless capture template must exist')
        control, fixture, environment = self.fixture()
        root = fixture.native.root
        data = seed(root)
        work = root / 'LIFEOS/MEMORY/STATE/work-events.jsonl'
        work.unlink()
        (data / 'config.json').write_bytes(TEMPLATE.read_bytes())
        source = Path(os.environ['LIFEOS_MEMORY_SOURCE'])
        hooks = root / 'hooks'
        if not hooks.exists():
            hooks.symlink_to(source / 'hooks', target_is_directory=True)
        settings = {'permissions': {'allow': ['Write']}, 'hooks': {'PostToolUse': [{
            'matcher': 'Write', 'hooks': [{'type': 'command',
                'command': 'bun --no-install ' + str(source / 'hooks/ISASync.hook.ts')}]}]}}
        (root / 'settings.json').write_text(json.dumps(settings))
        environment.update(LIFEOS_HERMES_SOURCE=os.environ['LIFEOS_HERMES_SOURCE'],
            LIFEOS_NOTIFICATION_CHANNEL='headless', TERMINAL_CWD=str(fixture.native.home),
            HERMES_WRITE_SAFE_ROOT=str(fixture.native.home))
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('daily_conduit_hermes_work.py'))],
            input=json.dumps({'root': str(root), 'route': fixture.fixture.fixture.route}),
            env=environment, cwd=fixture.native.home, capture_output=True, text=True, timeout=60)
        self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['diagnostics'], '')
        for warning in report['import_warnings']:
            self.assertTrue(warning['filename'].endswith('/pm/shell.py'), warning)
            self.assertEqual(warning['line'], 13, warning)
            self.assertIn('is an invalid escape sequence', warning['message'])
        self.assertTrue(report['events'], report)
        self.assertTrue(all(event['src'] == 'ISASync.hook.ts' for event in report['events']), report)
        self.assertEqual(report['registry']['sessions']['synthetic-conduit-hermes']['sessionUUID'],
            'synthetic-conduit-hermes-work')
        self.assertIn('lifeos-ascent-delta', report['tool_context'])
        capture = control.call(environment=environment, name='conduit-capture')
        self.assertEqual((capture.returncode, capture.stderr), (0, ''), capture.stdout + capture.stderr)
        value = json.loads(json.loads(capture.stdout)['output'])
        self.assertEqual(value['status'], 'completed', value)
        self.assertEqual(value['output'], 'captured 1 event(s)\n')
        events = list((data / 'events').glob('*.jsonl'))
        self.assertEqual(len(events), 1)
        detail = json.loads(events[0].read_bytes())['detail']
        self.assertEqual(detail['events'], len(report['events']))
        self.assertEqual(detail['lastSlug'], 'synthetic-conduit-hermes')
        self.assertEqual(events[0].stat().st_mode & 0o777, 0o600)
        self.assertEqual(fixture.fixture.fixture.received, [])
        evidence = os.environ.get('LIFEOS_DAILY_CONDUIT_EVIDENCE')
        if evidence:
            Path(evidence).write_text(json.dumps({'source_report': report, 'capture_result': value,
                'native_event': json.loads(events[0].read_bytes()), 'event_mode': '0600',
                'model_requests': fixture.fixture.fixture.received}, indent=2) + '\n')
