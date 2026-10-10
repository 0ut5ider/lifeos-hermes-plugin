# ABOUTME: Characterizes native Conduit insight decisions and governed publication.
# ABOUTME: Runs actual native processes with synthetic events and no model for idle or cached days.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest
import sqlite3
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import test_memory_manual_state as state_fixture
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_service import MemoryService
from lifeos_hook_bridge.memory_runtime import MemoryRuntime
from lifeos_hook_bridge.memory_context import route_identity


class MemoryConduitInsightTests(unittest.TestCase):
    date = '2026-10-08'

    def setUp(self):
        state_fixture.MemoryManualStateTests.setUp(self)
        source = Path(os.environ['LIFEOS_MEMORY_SOURCE'])
        (self.root / 'LIFEOS/PULSE').symlink_to(source / 'LIFEOS/PULSE', target_is_directory=True)
        self.directory = self.root / 'LIFEOS/USER/CONDUIT'
        self.events = self.directory / 'events' / (self.date + '.jsonl')
        self.insight = self.directory / 'insights' / (self.date + '.json')
        self.config = self.directory / 'config.json'
        self.inference_environment = {}

    def seed(self, marker='SyntheticInsightCurrent'):
        self.events.parent.mkdir(parents=True, exist_ok=True)
        event = {'ts': self.date + 'T12:00:00Z', 'type': 'app-focus', 'source': 'synthetic',
                 'app': marker, 'detail': {'intervalSec': 120}}
        self.events.write_text(json.dumps(event) + '\n')
        value = {'date': self.date, 'generatedAt': self.date + 'T12:01:00Z', 'conduitVersion': 'synthetic',
                 'level': 'low', 'model': 'haiku-tier', 'since': event['ts'], 'eventsConsidered': 1,
                 'narrative': marker, 'contentTypes': [{'label': marker, 'share': 1, 'evidence': marker}]}
        self.insight.parent.mkdir(parents=True, exist_ok=True)
        self.insight.write_text(json.dumps(value, indent=2))
        return value

    def call(self, *, context=True, original=False, exported=False, date=None):
        tool = (Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE']) if original else self.root) / 'LIFEOS/PULSE/Conduit/BuildInsight.ts'
        environment = dict(os.environ, HOME=str(self.fixture.fixture.home), CLAUDE_CONFIG_DIR=str(self.root),
                           BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.update(self.inference_environment)
        for name in ('LIFEOS_MEMORY_INTERNAL', 'LIFEOS_MEMORY_CONTEXT', 'LIFEOS_MEMORY_PUBLICATION_JOURNAL'):
            environment.pop(name, None)
        if original: environment['LIFEOS_MEMORY_INTERNAL'] = '1'
        elif context: environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        selected = self.date if date is None else date
        command = ['bun', '--no-install', str(tool), selected]
        if exported:
            script = ('import {buildInsight} from ' + json.dumps(str(tool)) + ';try {console.log(JSON.stringify(await buildInsight('
                + json.dumps(selected) + ')))} catch {console.error("Conduit insight unavailable");process.exit(2)}')
            command = ['bun', '--no-install', '-e', script]
        return subprocess.run(command, capture_output=True, text=True, timeout=45,
                              env=environment, cwd=self.fixture.fixture.home)

    def test_original_empty_cli_and_exported_initialization_characterization(self):
        result = self.call(original=True, exported=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertFalse(self.config.exists())
        value = json.loads(self.insight.read_text())
        self.assertEqual(value['eventsConsidered'], 0)
        self.assertEqual(value['model'], '(none)')
        self.assertTrue(value['skipped'])
        result = self.call(original=True)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '[]\n', ''))
        self.assertEqual(json.loads(self.config.read_text())['pollIntervalSec'], 120)

    def test_original_cached_insight_preserves_bytes_without_model_call(self):
        expected = self.seed()
        before = (self.insight.read_bytes(), self.insight.stat().st_mtime_ns)
        result = self.call(original=True, exported=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertIn('no new events', result.stdout)
        self.assertEqual(json.loads(result.stdout.splitlines()[-1]), expected)
        self.assertEqual((self.insight.read_bytes(), self.insight.stat().st_mtime_ns), before)

    def test_unbound_cli_refuses_before_config_or_insight_creation(self):
        result = self.call(context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.config.exists())
        self.assertFalse(self.insight.exists())

    def test_unbound_exported_reader_cannot_disclose_cached_insight(self):
        self.seed()
        before = self.insight.read_bytes()
        result = self.call(context=False, exported=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('SyntheticInsightCurrent', result.stdout + result.stderr)
        self.assertEqual(self.insight.read_bytes(), before)

    def test_owner_empty_publication_and_cached_native_result(self):
        result = self.call()
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '[]\n', ''))
        self.assertEqual(self.insight.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(self.insight.read_text())['model'], '(none)')
        expected = self.seed()
        before = (self.insight.read_bytes(), self.insight.stat().st_mtime_ns)
        result = self.call(exported=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout.splitlines()[-1]), expected)
        self.assertEqual((self.insight.read_bytes(), self.insight.stat().st_mtime_ns), before)

    def test_private_retired_and_read_only_sources_refuse_without_publication(self):
        self.seed('<private>SyntheticInsightHidden</private>')
        before = self.insight.read_bytes()
        result = self.call()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('SyntheticInsightHidden', result.stdout + result.stderr)
        self.assertEqual(self.insight.read_bytes(), before)
        self.assertFalse(self.config.exists())
        self.seed()
        saved = self.fixture.fixture.memory.remember(OWNER, category='principal', content='RULE: SyntheticInsightCurrent',
            title='', project='', request_id='insight-retained')
        self.fixture.fixture.memory.forget(OWNER, saved['reference'], 'insight-forget')
        self.assertNotEqual(self.call().returncode, 0)
        self.assertFalse(self.config.exists())
        self.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=[]))
        self.assertNotEqual(self.call().returncode, 0)

    def test_missing_connector_and_revocation_do_not_use_raw_reader(self):
        self.seed()
        before = self.insight.read_bytes()
        self.fixture.configuration.update(lambda value: value['accounts'].clear())
        self.assertNotEqual(self.call().returncode, 0)
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        result = self.call(exported=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('SyntheticInsightCurrent', result.stdout + result.stderr)
        self.assertEqual(self.insight.read_bytes(), before)

    def test_fixed_date_and_linked_destinations_refuse(self):
        for date in ('../outside', '2026-99-01', '2026-02-30', '', '2026-10-08/../../other'):
            with self.subTest(date=date):
                result = self.call(date=date)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.config.exists())
        self.seed()
        outside = self.fixture.fixture.home / 'outside-insight.json'
        outside.write_bytes(self.insight.read_bytes())
        for mode in ('symlink', 'hardlink'):
            with self.subTest(mode=mode):
                self.insight.unlink()
                if mode == 'symlink': self.insight.symlink_to(outside)
                else: os.link(outside, self.insight)
                result = self.call()
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.config.exists())
                self.assertNotIn('SyntheticInsightCurrent', result.stdout + result.stderr)

    def test_requested_day_does_not_reuse_another_days_insight(self):
        self.seed()
        other = self.insight.with_name('2026-10-07.json')
        self.insight.rename(other)
        self.events.unlink()
        before = other.read_bytes()
        result = self.call()
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '[]\n', ''))
        self.assertEqual(json.loads(self.insight.read_text())['model'], '(none)')
        self.assertEqual(other.read_bytes(), before)

    def test_unconfigured_native_idle_behavior_remains_characterized(self):
        for name in ('memory-access.json', 'memory-http.json'):
            (self.root / 'LIFEOS/USER/CONFIG' / name).unlink()
        result = self.call(context=False)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '[]\n', ''))
        self.assertTrue(self.config.exists())
        self.assertEqual(json.loads(self.insight.read_text())['narrative'], 'No activity captured yet today.')

    def test_original_malformed_existing_object_is_a_known_native_failure(self):
        # The original cast accepts an object without contentTypes and then throws on length.
        self.seed()
        self.insight.write_text('{}')
        result = self.call(original=True, exported=True)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (2, '', 'Conduit insight unavailable\n'))
        before = self.insight.read_bytes()
        result = self.call()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.insight.read_bytes(), before)
        self.assertFalse(self.config.exists())

    def prepare(self, initialize=False):
        result = MemoryService(self.fixture.configuration).native(self.fixture.context, 'conduit_prepare',
            {'date': self.date, 'initialize': initialize})
        self.assertTrue(result['ok'], result)
        return result

    def test_event_change_after_insight_write_retains_recovery_and_later_events(self):
        from lifeos_hook_bridge import memory_conduit_insight as module
        prepared = self.prepare(initialize=True)
        value = {'date':self.date, 'generatedAt':'2026-10-09T12:00:00Z', 'conduitVersion':'1.0.0',
            'level':'low', 'model':'(none)', 'since':None, 'eventsConsidered':0, 'skipped':True,
            'narrative':'No activity captured yet today.', 'contentTypes':[]}
        later = (json.dumps({'ts':self.date+'T12:00:00Z', 'type':'app-focus', 'source':'synthetic',
            'app':'Synthetic later application'}) + '\n').encode()
        original = module.publish
        seen = []
        def observed(path, content):
            original(path, content)
            if path == self.insight:
                self.events.parent.mkdir(parents=True, exist_ok=True)
                self.events.write_bytes(later)
                seen.append(path)
        module.publish = observed
        try:
            result = MemoryService(self.fixture.configuration).native(self.fixture.context, 'conduit_publish',
                {'date':self.date, 'initialize':True, 'signature':prepared['signature'], 'value':value, 'reuse':False})
        finally:
            module.publish = original
        self.assertFalse(result['ok'], result)
        self.assertEqual(seen, [self.insight])
        memory = self.fixture.fixture.memory
        self.assertTrue(memory.transaction.journal.exists())
        with closing(sqlite3.connect(memory.database)) as connection:
            receipt = json.loads(connection.execute("SELECT receipt FROM operations WHERE request_id LIKE 'conduit-insight-%'").fetchone()[0])
        self.assertEqual(receipt['status'], 'unknown')
        with memory._transaction(): pass
        self.assertFalse(self.insight.exists())
        self.assertFalse(self.config.exists())
        self.assertEqual(self.events.read_bytes(), later)

    def check(self, prepared, initialize=False):
        return MemoryService(self.fixture.configuration).native(self.fixture.context, 'conduit_check',
            {'date': self.date, 'initialize': initialize, 'signature': prepared['signature']})

    def test_prepared_sources_bind_bytes_inode_mtime_and_configuration(self):
        self.seed()
        for mode in ('bytes', 'inode', 'mtime', 'configuration'):
            with self.subTest(mode=mode):
                prepared = self.prepare()
                if mode == 'bytes': self.events.write_text(self.events.read_text() + '\n')
                elif mode == 'inode':
                    replacement = self.events.with_suffix('.replacement')
                    replacement.write_bytes(self.events.read_bytes())
                    os.replace(replacement, self.events)
                elif mode == 'mtime': os.utime(self.insight, ns=(self.insight.stat().st_atime_ns, self.insight.stat().st_mtime_ns + 1_000_000))
                else: self.fixture.configuration.update(lambda value: value.update(synthetic_revision='later'))
                self.assertFalse(self.check(prepared)['ok'])
                self.assertFalse(self.config.exists())

    def test_complete_large_history_and_torn_line_preserve_native_summary(self):
        self.seed()
        row = json.loads(self.events.read_text())
        row['detail']['unused'] = 'synthetic padding ' * 20
        self.events.write_text((json.dumps(row) + '\n') * 8001 + '{torn\n' + json.dumps(row))
        self.assertGreater(self.events.stat().st_size, 3 * 1024 * 1024)
        prepared = self.prepare()
        self.assertEqual(prepared['plan']['eventsConsidered'], 8002)
        self.assertIn('SyntheticInsightCurrent 16004min', prepared['plan']['text'])
        self.assertEqual(prepared['plan']['since'], row['ts'])

    def test_generated_output_cannot_change_native_metadata_or_disclose_private_text(self):
        prepared = self.prepare()
        empty = {'date': self.date, 'generatedAt': '2026-10-09T12:00:00Z', 'conduitVersion': '1.0.0',
            'level': 'low', 'model': '(none)', 'since': None, 'eventsConsidered': 0, 'skipped': True,
            'narrative': 'No activity captured yet today.', 'contentTypes': []}
        for change in ({'date': '2026-10-07'}, {'eventsConsidered': True}, {'level': 'max'},
                {'narrative': '<private>SyntheticInsightHidden</private>'}, {'contentTypes': [{'label': 'Injected'}]}):
            with self.subTest(change=change):
                result = MemoryService(self.fixture.configuration).native(self.fixture.context, 'conduit_publish',
                    {'date': self.date, 'initialize': False, 'signature': prepared['signature'], 'value': {**empty, **change}, 'reuse': False})
                self.assertFalse(result['ok'], result)
                self.assertFalse(self.insight.exists())
                self.assertFalse(self.config.exists())

    def test_actual_post_render_edits_and_interruption_preserve_recovery(self):
        for mode in ('source', 'destination', 'authority', 'interrupt'):
            with self.subTest(mode=mode):
                result = subprocess.run([os.environ.get('PYTHON', '/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python'),
                    str(Path(__file__).with_name('memory_conduit_insight_process.py')), str(self.fixture.configuration.path),
                    mode, json.dumps(asdict(self.fixture.context))], capture_output=True, text=True, timeout=45)
                self.assertEqual(result.stderr, '')
                if mode == 'interrupt':
                    self.assertEqual(result.returncode, 73, result.stdout)
                    self.assertTrue(self.insight.exists())
                    recovered = self.prepare()
                    self.assertFalse(self.insight.exists(), recovered)
                    self.assertFalse(self.config.exists())
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(json.loads(result.stdout)['ok'])
                    if mode == 'destination':
                        self.assertEqual(self.insight.read_text(), '{"synthetic_later":true}')
                        self.insight.unlink()
                    else: self.assertFalse(self.insight.exists())
                if self.events.exists(): self.events.unlink()
                if mode == 'authority': self.fixture.configuration.update(lambda value: value['accounts'].update({'chat-a:100': 'owner'}))

    def failure_gateway(self):
        self.received = []
        self.on_request = lambda: None
        owner = self

        class Gateway(BaseHTTPRequestHandler):
            def do_POST(self):
                owner.received.append({'path': self.path, 'body': json.loads(self.rfile.read(int(self.headers['Content-Length'])))})
                owner.on_request()
                self.send_response(401)
                self.send_header('Content-Length', '0')
                self.end_headers()

            def log_message(self, *_): pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Gateway)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        parent = {'provider': 'synthetic', 'model': 'synthetic-parent',
            'base_url': 'http://127.0.0.1/v1', 'api_mode': 'chat_completions'}
        child = {'provider': 'lifeos-local-gateway', 'model': 'synthetic-flashnext',
            'base_url': f'http://127.0.0.1:{server.server_port}', 'api_mode': 'anthropic'}
        def configure(value):
            value['ownership_enabled'] = True
            value['destinations']['chat-a:200']['model_routes'] = [route_identity(**parent), route_identity(**child)]
        self.fixture.configuration.update(configure)
        self.runtime = MemoryRuntime(self.fixture.configuration.path)
        self.addCleanup(self.runtime.clear)
        self.runtime.admit({'HERMES_SESSION_PLATFORM': 'chat-a', 'HERMES_SESSION_USER_ID': '100',
            'HERMES_SESSION_CHAT_ID': '200', 'HERMES_SESSION_CHAT_TYPE': 'dm', 'HERMES_SESSION_ID': 'native-session'},
            **parent, is_first_turn=True)
        self.fixture.context = self.runtime.context()
        environment = self.fixture.fixture.home / 'model.env'
        environment.write_text('ANTHROPIC_BASE_URL=' + child['base_url'] + '\n'
            'ANTHROPIC_AUTH_TOKEN=synthetic-token\nLIFEOS_CHILD_INFERENCE_DIRECT=1\n'
            "LIFEOS_MODEL_TIER_MAP='" + json.dumps({'haiku': {'model': child['model'], 'effort': 'low'}}) + "'\n")
        environment.chmod(0o600)
        plugin = Path(__file__).resolve().parents[1]
        self.inference_environment = {'HERMES_HOME': str(self.fixture.configuration.path.parent),
            'LIFEOS_MEMORY_CONFIGURATION': str(self.fixture.configuration.path), 'LIFEOS_MEMORY_SESSION': 'native-session',
            'LIFEOS_CHILD_PROVIDER': '', 'LIFEOS_HOOK_MODEL_ENV': str(environment),
            'PATH': os.pathsep.join([str(plugin / 'lifeos_hook_bridge/bin'), str(Path(sys.executable).parent),
                                   str(Path.home() / '.bun/bin'), '/usr/bin', '/bin'])}

    def test_actual_plan_validation_rechecks_source_and_authority_before_disclosure(self):
        for mode in ('projection-source', 'projection-authority'):
            with self.subTest(mode=mode):
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_conduit_insight_process.py')),
                    str(self.fixture.configuration.path), mode, json.dumps(asdict(self.fixture.context))],
                    capture_output=True, text=True, timeout=45)
                self.assertEqual((result.returncode, result.stderr), (0, ''))
                self.assertFalse(json.loads(result.stdout)['ok'])
                self.assertFalse(self.insight.exists())
                self.assertFalse(self.config.exists())
                if self.events.exists(): self.events.unlink()
                if mode == 'projection-authority': self.fixture.configuration.update(lambda value: value['accounts'].update({'chat-a:100': 'owner'}))

    def test_actual_inference_transport_failure_keeps_prior_good_insight(self):
        self.failure_gateway()
        expected = self.seed()
        prior = self.insight.read_bytes()
        row = json.loads(self.events.read_text())
        row['ts'] = self.date + 'T13:00:00Z'
        with self.events.open('a') as stream: stream.write(json.dumps(row) + '\n')
        result = self.call(exported=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout.splitlines()[-1]), expected)
        self.assertEqual(self.insight.read_bytes(), prior)
        self.assertEqual(len(self.received), 1)
        self.assertEqual(self.received[0]['path'], '/v1/messages')
        self.assertEqual(self.received[0]['body']['model'], 'synthetic-flashnext')
        self.assertEqual(self.received[0]['body']['output_config'], {'effort': 'low'})
        self.assertIn('SyntheticInsightCurrent 4min', self.received[0]['body']['messages'][0]['content'])

    def test_actual_inference_transport_failure_publishes_native_fallback(self):
        self.failure_gateway()
        self.seed()
        self.insight.unlink()
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(len(self.received), 1)
        value = json.loads(self.insight.read_text())
        self.assertEqual(value['model'], '(failed)')
        self.assertEqual(value['contentTypes'], [])
        self.assertEqual(value['eventsConsidered'], 1)
        self.assertEqual(self.insight.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)

    def test_source_and_authority_changes_during_actual_http_refuse_artifacts(self):
        self.failure_gateway()
        self.seed()
        self.insight.unlink()
        self.on_request = lambda: self.events.write_text(self.events.read_text() + '\n')
        result = self.call()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.received), 1)
        self.assertNotIn('SyntheticInsightCurrent', result.stdout + result.stderr)
        self.assertFalse(self.insight.exists())
        self.assertFalse(self.config.exists())

    def test_revocation_during_actual_http_refuses_artifacts(self):
        self.failure_gateway()
        self.seed()
        self.insight.unlink()
        self.on_request = lambda: self.fixture.configuration.update(lambda value: value['accounts'].clear())
        result = self.call()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.received), 1)
        self.assertFalse(self.insight.exists())
        self.assertFalse(self.config.exists())

    def test_connector_loss_after_actual_preparation_refuses_before_model(self):
        self.failure_gateway()
        self.seed()
        self.insight.unlink()
        connector = self.root / 'LIFEOS/USER/CONFIG/memory-access.json'
        original = json.loads(connector.read_text())['command']
        observer = self.fixture.fixture.home / 'conduit-connector-observer.py'
        observer.write_text('# ABOUTME: Runs the installed memory command before observing prepared connector loss.\n'
            '# ABOUTME: Preserves the real service response while changing only disposable control files.\n'
            'import json,os,subprocess,sys\nfrom pathlib import Path\n'
            'wire=sys.stdin.buffer.read()\nresult=subprocess.run(' + repr(original) + ',input=wire,capture_output=True)\n'
            'if json.loads(wire)["operation"]=="conduit_prepare" and result.returncode==0 and json.loads(result.stdout).get("ok"):\n'
            '    directory=Path(os.environ["HOME"])/".claude/LIFEOS/USER/CONFIG"\n'
            '    for name in ("memory-access.json","memory-http.json"): (directory/name).unlink()\n'
            'sys.stdout.buffer.write(result.stdout)\nsys.stderr.buffer.write(result.stderr)\nsys.exit(result.returncode)\n')
        connector.write_text(json.dumps({'version': 1, 'command': [sys.executable, str(observer)]}))
        result = self.call()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.received, [])
        self.assertFalse(self.insight.exists())
        self.assertFalse(self.config.exists())

    def test_retained_context_cannot_become_unconfigured_after_connector_loss(self):
        self.seed()
        for name in ('memory-access.json', 'memory-http.json'):
            (self.root / 'LIFEOS/USER/CONFIG' / name).unlink()
        before = self.insight.read_bytes()
        result = self.call(exported=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('SyntheticInsightCurrent', result.stdout + result.stderr)
        self.assertEqual(self.insight.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
