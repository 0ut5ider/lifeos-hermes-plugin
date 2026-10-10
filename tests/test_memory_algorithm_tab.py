# ABOUTME: Characterizes native Algorithm chain files and a warm-cache composition without inference.
# ABOUTME: Requires current owner admission before personal file reads and automatic generation.
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import unittest

import httpx
import test_memory_pulse_relay as relay_fixture
from test_memory_native import OWNER

RULES = 'LIFEOS/USER/CONFIG/OPERATIONAL_RULES.md'
EXPANDED = 'LIFEOS/USER/CONFIG/OperationalRulesExpanded.md'
STYLE = 'LIFEOS/USER/DIGITAL_ASSISTANT/REFERENCE/WritingStyleBackstop.md'
INCIDENTS = 'LIFEOS/MEMORY/LEARNING/INCIDENTS/README.md'
CACHE = 'LIFEOS/MEMORY/STATE/algorithm-tab-summary.json'
DIRECTORY = 'LIFEOS/ALGORITHM'


class MemoryAlgorithmTabTests(unittest.TestCase):
    native_module = 'algorithm-tab.ts'
    create_fixture = relay_fixture.MemoryPulseRelayTests.create_fixture
    stop_dashboard = relay_fixture.MemoryPulseRelayTests.stop_dashboard
    stop_pulse = relay_fixture.MemoryPulseRelayTests.stop_pulse
    login = relay_fixture.MemoryPulseRelayTests.login

    def native_module_name(self): return 'memory.ts'

    def setUp(self):
        relay_fixture.MemoryPulseRelayTests.setUp(self)
        # A misplaced inference call must fail locally instead of reaching a model service.
        tools = self.root / 'LIFEOS/TOOLS'
        public = tools.resolve()
        tools.unlink()
        tools.mkdir()
        for entry in public.iterdir():
            if entry.name != 'Inference.ts': (tools / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
        self.assertFalse((tools / 'Inference.ts').exists())
        # Read fixtures need physical hook files, as the installed source boundary requires.
        hooks = self.root / 'hooks'
        public = hooks.resolve()
        hooks.unlink()
        shutil.copytree(public, hooks)
        algorithm = self.root / 'LIFEOS/ALGORITHM'
        algorithm.mkdir()
        (algorithm / 'LATEST').write_text('3.2.1\n')
        (algorithm / 'v3.2.1.md').write_text('# The Algorithm 3.2.1\n\n## A run is complete when\n1. Synthetic hook (HOOK)\n2. Synthetic check (CHECK)\n3. Synthetic self (SELF)\n\n## Next\n')
        (algorithm / 'changelog.md').write_text('# Synthetic algorithm history\n')

    def seed(self, marker='SyntheticAlgorithmCurrent'):
        for relative in (RULES, EXPANDED, STYLE, INCIDENTS):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('# Synthetic Algorithm source\n\n' + marker + '\n')
        return self.root / RULES

    def original(self, target='/api/algorithm-tab'):
        control = Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE']) / 'LIFEOS/PULSE/modules/algorithm-tab.ts'
        program = self.fixture.home / 'algorithm-characterization.ts'
        # The actual native parser, hash, store, and handler stay intact in this instrumented copy.
        # Its native hash and catalog prepare a warm cache before a read can trigger generation.
        program.write_text(control.read_text() + '\n' + '''
const fixtureStore: SummaryStore = {overview: {generated_at: "2000-01-01T00:00:00.000Z",
  chain_hash: await chainHash(), level: "high", markdown: "SyntheticAlgorithmWarmOverview"}, files: {}};
for (const spec of CHAIN) {
  let text = "";
  try { text = await Bun.file(chainPath(spec)).text(); } catch {}
  fixtureStore.files[spec.id] = {hash: contentHash(text), generated_at: "2000-01-01T00:00:00.000Z",
    markdown: "SyntheticAlgorithmWarmCard"};
}
await writeStore(fixtureStore);
const before = await Bun.file(STATE_PATH).text();
const request = new Request("http://localhost" + process.argv[2]);
const response = await handleRequest(request, new URL(request.url).pathname);
console.log(JSON.stringify({status: response?.status, body: response ? await response.json() : null,
  generating: state.generating, cache_unchanged: before === await Bun.file(STATE_PATH).text()}));
''')
        (self.root / CACHE).parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(['bun', '--no-install', str(program), target], capture_output=True, text=True, timeout=30,
            env=dict(os.environ, HOME=str(self.fixture.home), CLAUDE_CONFIG_DIR=str(self.root)))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(len(result.stdout.splitlines()), 1, result.stdout[:300])
        body = json.loads(result.stdout)
        self.assertFalse(body['generating'])
        self.assertTrue(body['cache_unchanged'])
        return body

    @staticmethod
    def stable(body): return {key: value for key, value in body.items() if key != 'generated_at'}

    def test_original_native_file_fields_missing_and_version_selection_characterization(self):
        path = self.seed()
        body = self.original('/api/algorithm-tab/file?id=operational-rules')
        self.assertEqual(body['status'], 200)
        self.assertEqual(body['body']['content'], path.read_text())
        self.assertTrue(body['body']['editable'])
        doctrine = self.original('/api/algorithm-tab/file?id=doctrine&version=3.2.1')
        self.assertEqual(doctrine['status'], 200)
        self.assertFalse(doctrine['body']['editable'])
        self.assertEqual(self.original('/api/algorithm-tab/file?id=doctrine&version=../other')['status'], 400)
        self.assertEqual(self.original('/api/algorithm-tab/file?id=unknown')['status'], 404)
        path.unlink()
        self.assertEqual(self.original('/api/algorithm-tab/file?id=operational-rules')['status'], 404)

    def test_original_warm_cache_composition_characterization_has_no_generation(self):
        self.seed()
        body = self.original()['body']
        self.assertEqual(body['version'], '3.2.1')
        self.assertEqual(body['claims'], {'total': 3, 'hook': 1, 'check': 1, 'self': 1})
        self.assertEqual(body['summary'], {'generated_at': '2000-01-01T00:00:00.000Z', 'level': 'high',
            'stale': False, 'markdown': 'SyntheticAlgorithmWarmOverview'})
        self.assertFalse(body['generating'])
        self.assertTrue(any(row['id'] == 'operational-rules' for row in body['chain']))

    def test_anonymous_chain_and_personal_files_require_current_owner(self):
        self.seed()
        self.original()
        for target in ('', '/file?id=operational-rules', '/file?id=operational-rules-expanded',
                '/file?id=writing-style-backstop', '/file?id=incidents'):
            with self.subTest(target=target):
                response = httpx.get(self.native + '/api/algorithm-tab' + target)
                self.assertEqual(response.status_code, 401, response.text[:250])
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
                self.assertNotIn('SyntheticAlgorithm', response.text)

    def test_admitted_personal_file_views_preserve_actual_native_content_and_metadata(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for identifier in ('operational-rules', 'operational-rules-expanded', 'writing-style-backstop', 'incidents'):
                with self.subTest(identifier=identifier):
                    target = '/api/algorithm-tab/file?id=' + identifier
                    response = client.get(self.native + target)
                    self.assertEqual(response.status_code, 200, response.text[:250])
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')
                    self.assertEqual(response.json(), self.original(target)['body'])

    def test_private_personal_chain_file_refuses(self):
        self.seed('<private>SyntheticAlgorithmHidden</private>')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/algorithm-tab/file?id=operational-rules')
            self.assertEqual(response.status_code, 503, response.text[:250])
            self.assertNotIn('SyntheticAlgorithmHidden', response.text)

    def test_owner_warm_composition_preserves_actual_native_chain_and_claims(self):
        self.seed()
        expected = self.original()['body']
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for suffix in ('', '/'):
                response = client.get(self.native + '/api/algorithm-tab' + suffix)
                self.assertEqual(response.status_code, 200, response.text[:250])
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
                self.assertEqual(self.stable(response.json()), self.stable(expected))

    def test_private_summary_refuses_composition_without_blocking_an_independent_file(self):
        self.seed()
        self.original()
        cache = self.root / CACHE
        value = json.loads(cache.read_text())
        value['overview']['markdown'] = '<private>SyntheticAlgorithmSummaryHidden</private>'
        cache.write_text(json.dumps(value))
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/algorithm-tab')
            self.assertEqual(response.status_code, 503, response.text[:250])
            self.assertNotIn('SyntheticAlgorithmSummaryHidden', response.text)
            response = client.get(self.native + '/api/algorithm-tab/file?id=operational-rules')
            self.assertEqual(response.status_code, 200, response.text[:250])
            self.assertEqual(response.headers.get('cache-control'), 'no-store')

    def test_current_owner_origin_bearer_and_connector_govern_delivery(self):
        self.seed()
        target = '/api/algorithm-tab/file?id=operational-rules'
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + target).status_code, 200)
            self.assertEqual(client.get(self.native + target, headers={'Origin': 'https://untrusted.invalid'}).status_code, 403)
            self.assertEqual(client.get(self.native + target, headers={'Authorization': 'Bearer invalid'}).status_code, 401)
            self.fixture.configuration.update(lambda value: value['accounts'].clear())
            self.assertEqual(client.get(self.native + target).status_code, 403)
            (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            self.assertEqual(client.get(self.native + target).status_code, 503)

    def test_actions_refuse_before_writes_commits_or_inference(self):
        path = self.seed()
        before = path.read_bytes()
        with httpx.Client(timeout=30) as client:
            # Owner admission precedes field validation and generation authority.
            self.assertEqual(client.get(self.native + '/api/algorithm-tab/file?id=operational-rules').status_code, 401)
            for target in ('/file', '/doctrine', '/summary/regenerate'):
                self.assertEqual(client.post(self.native + '/api/algorithm-tab' + target, json={}).status_code, 401)
            self.login(client)
            for target, expected in (('/file', 400), ('/doctrine', 400), ('/summary/regenerate', 503)):
                response = client.post(self.native + '/api/algorithm-tab' + target, json={})
                self.assertEqual(response.status_code, expected, response.text[:250])
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
            for target, code in (('/file?id=unknown', 404), ('/file?id=doctrine&version=../outside', 400),
                    ('/file?id=operational-rules&path=other', 400), ('?source=other', 400), ('/unsupported/path', 404)):
                response = client.get(self.native + '/api/algorithm-tab' + target)
                self.assertEqual(response.status_code, code, response.text[:250])
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse((self.root / CACHE).exists())

    def test_redirected_invalid_and_excessive_selected_file_refuses(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for mode in ('symlink', 'hardlink', 'utf8', 'oversize'):
                with self.subTest(mode=mode):
                    path = self.root / RULES
                    path.unlink(missing_ok=True)
                    path = self.seed()
                    if mode in ('symlink', 'hardlink'):
                        outside = self.fixture.home / 'synthetic-algorithm-outside'
                        outside.write_bytes(path.read_bytes())
                        path.unlink()
                        if mode == 'symlink': path.symlink_to(outside)
                        else: os.link(outside, path)
                    elif mode == 'utf8': path.write_bytes(b'\xff')
                    else: path.write_bytes(b'x' * (256 * 1024 + 1))
                    self.assertEqual(client.get(self.native + '/api/algorithm-tab/file?id=operational-rules').status_code, 503)

    def test_actual_native_render_rechecks_source_inode_creation_authority_and_selected_latest(self):
        configuration = self.fixture.configuration.path.read_bytes()
        for mode in ('source', 'metadata', 'created', 'authority', 'latest'):
            with self.subTest(mode=mode):
                self.fixture.configuration.path.write_bytes(configuration)
                path = self.seed()
                if mode == 'created': path.unlink()
                target = '/api/algorithm-tab/file?id=doctrine' if mode == 'latest' else '/api/algorithm-tab/file?id=operational-rules'
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_algorithm_tab_process.py')),
                    str(self.fixture.configuration.path), target, mode], capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})

    def test_retired_selected_file_refuses_and_exact_review_preserves_safe_old_file(self):
        from lifeos_hook_bridge.memory_source_review import preview, approve
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        path = self.seed('SyntheticAlgorithmRetired')
        saved = memory.remember(OWNER, category='principal', content='RULE: SyntheticAlgorithmRetired', title='', project='', request_id='algorithm-retired-save')
        memory.forget(OWNER, saved['reference'], 'algorithm-retired-forget')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            target = '/api/algorithm-tab/file?id=operational-rules'
            self.assertEqual(client.get(self.native + target).status_code, 503)
            path = self.seed('SyntheticAlgorithmReviewed')
            os.utime(path, (1, 1))
            before = (path.read_bytes(), path.stat().st_mtime_ns)
            self.assertEqual(client.get(self.native + target).status_code, 503)
            selected = preview(memory, OWNER, [RULES])
            self.assertTrue(selected['sources'][0]['accepted'], selected)
            self.assertEqual(approve(memory, OWNER, [RULES], selected['signature'])['status'], 'committed')
            response = client.get(self.native + target)
            self.assertEqual(response.status_code, 200, response.text[:250])
            self.assertEqual(response.json()['content'], before[0].decode())
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_original_summary_store_migration_and_empty_parser_characterization(self):
        control = Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE']) / 'LIFEOS/PULSE/modules/algorithm-tab.ts'
        program = self.fixture.home / 'algorithm-store-characterization.ts'
        program.write_text(control.read_text() + '\nconsole.log(JSON.stringify(await readStore()));\n')
        cache = self.root / CACHE
        cache.parent.mkdir(parents=True, exist_ok=True)
        cases = [('{', {'overview': None, 'files': {}}),
            (json.dumps({'markdown': 'SyntheticAlgorithmPriorSchema', 'generated_at': '2000-01-01', 'chain_hash': 'synthetic'}),
             {'overview': {'generated_at': '2000-01-01', 'chain_hash': 'synthetic', 'level': 'high', 'markdown': 'SyntheticAlgorithmPriorSchema'}, 'files': {}}),
            (json.dumps({'overview': None, 'files': {}}), {'overview': None, 'files': {}})]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                cache.write_text(raw)
                result = subprocess.run(['bun', '--no-install', str(program)], capture_output=True, text=True, timeout=30,
                    env=dict(os.environ, HOME=str(self.fixture.home), CLAUDE_CONFIG_DIR=str(self.root)))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), expected)

    def test_version_metadata_matches_native_order_without_reading_unselected_history_text(self):
        self.seed()
        directory = self.root / 'LIFEOS/ALGORITHM'
        historical = directory / 'v0.0.9.md'
        historical.write_text('<private>SyntheticAlgorithmHistoricalHidden</private>\n')
        os.utime(historical, (1, 1))
        (directory / 'v03.2.1.md').write_text('# Synthetic equal numeric version\n')
        expected = self.original()['body']
        self.assertEqual(historical.stat().st_atime_ns, 1000000000)
        self.assertEqual([row['version'] for row in expected['versions']][-1], '0.0.9')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/algorithm-tab')
            self.assertEqual(response.status_code, 200, response.text[:250])
            self.assertEqual(response.headers.get('cache-control'), 'no-store')
            self.assertEqual(self.stable(response.json()), self.stable(expected))
            self.assertEqual(historical.stat().st_atime_ns, 1000000000)
            response = client.get(self.native + '/api/algorithm-tab/file?id=doctrine&version=0.0.9')
            self.assertEqual(response.status_code, 503, response.text[:250])
            self.assertNotIn('SyntheticAlgorithmHistoricalHidden', response.text)


    def test_unconfigured_file_error_preserves_original_native_failure_response(self):
        self.seed()
        home = self.fixture.home / 'synthetic-unmanaged-algorithm'
        rules = home / '.claude' / RULES
        rules.mkdir(parents=True)
        body = '\nconst req = new Request("http://localhost/api/algorithm-tab/file?id=operational-rules");\nconst res = await handleRequest(req, new URL(req.url).pathname);\nconsole.log(JSON.stringify({status: res?.status, body: res ? await res.json() : null}));\n'
        expected = None
        for kind in ('original', 'candidate'):
            program = home / (kind + '.ts')
            source = Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE']) / 'LIFEOS/PULSE/modules/algorithm-tab.ts'
            if kind == 'original': program.write_text(source.read_text() + body)
            else:
                source = Path(os.environ['LIFEOS_MEMORY_SOURCE']) / 'LIFEOS/PULSE/modules/algorithm-tab.ts'
                program.write_text('import {handleRequest} from ' + json.dumps(str(source)) + ';\n' + body)
            result = subprocess.run(['bun', '--no-install', str(program)], capture_output=True, text=True, timeout=30,
                env=dict(os.environ, HOME=str(home), CLAUDE_CONFIG_DIR=str(home / '.claude')))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stderr, '')
            value = json.loads(result.stdout)
            if kind == 'original':
                expected = value
                self.assertEqual(value['status'], 500)
                self.assertEqual(value['body']['error'], 'Directories cannot be read like files')
            else: self.assertEqual(value, expected)

    def test_managed_stale_and_prior_summary_views_do_not_start_ungoverned_generation(self):
        self.seed()
        cache = self.root / CACHE
        cache.parent.mkdir(parents=True, exist_ok=True)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for raw in (None, '{', json.dumps({'overview': None, 'files': {}}),
                    json.dumps({'markdown': 'SyntheticAlgorithmPriorOverview', 'generated_at': '2000-01-01', 'chain_hash': 'synthetic'})):
                with self.subTest(raw=raw):
                    cache.unlink(missing_ok=True)
                    if raw is not None: cache.write_text(raw)
                    response = client.get(self.native + '/api/algorithm-tab')
                    self.assertEqual(response.status_code, 200, response.text[:250])
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')
                    self.assertFalse(response.json()['generating'])
                    self.assertEqual(response.json()['claims'], {'total': 3, 'hook': 1, 'check': 1, 'self': 1})
                    if raw and 'PriorOverview' in raw:
                        self.assertEqual(response.json()['summary'], {'generated_at': '2000-01-01', 'level': 'high',
                            'stale': True, 'markdown': 'SyntheticAlgorithmPriorOverview'})
                    else: self.assertIsNone(response.json()['summary'])
                    self.assertEqual(cache.read_text() if cache.exists() else None, raw)

    def test_version_discovery_is_bounded_and_checks_redirected_metadata(self):
        self.seed()
        self.original()
        directory = self.root / DIRECTORY
        with httpx.Client(timeout=30) as client:
            self.login(client)
            target = directory / 'v0.0.1.md'
            outside = self.fixture.home / 'synthetic-historical-version'
            outside.write_text('Synthetic historical metadata')
            target.symlink_to(outside)
            self.assertEqual(client.get(self.native + '/api/algorithm-tab').status_code, 503)
            target.unlink()
            for index in range(2049): (directory / ('synthetic-entry-' + str(index))).touch()
            self.assertEqual(client.get(self.native + '/api/algorithm-tab').status_code, 503)

    def test_missing_current_doctrine_preserves_native_composition_error_fields(self):
        self.seed()
        (self.root / DIRECTORY / 'v3.2.1.md').unlink()
        expected = self.original()['body']
        self.assertIn('doctrine', expected['errors'])
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/algorithm-tab')
            self.assertEqual(response.status_code, 200, response.text[:250])
            self.assertEqual(response.headers.get('cache-control'), 'no-store')
            self.assertEqual(self.stable(response.json()), self.stable(expected))


if __name__ == '__main__': unittest.main()
