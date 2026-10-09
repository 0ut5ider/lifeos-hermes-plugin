# ABOUTME: Characterizes complete native Telos template data and governed personal reads.
# ABOUTME: Uses real copied template processes with synthetic Markdown and CSV sources.
from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

import test_memory_manual_state as state_fixture
from test_memory_native import OWNER


class MemoryTelosTemplateTests(unittest.TestCase):
    def setUp(self):
        state_fixture.MemoryManualStateTests.setUp(self)
        source = Path(os.environ['LIFEOS_MEMORY_SOURCE'])
        (self.root / 'skills').symlink_to(source / 'skills', target_is_directory=True)
        self.template = source / 'skills/Telos/DashboardTemplate/lib/telos-data.ts'
        self.directory = self.root / 'LIFEOS/USER/TELOS'
        self.data = self.directory / 'data'
        self.data.mkdir()
        self.goal = self.directory / 'GOALS.md'
        self.goal.write_text('# Goals\nSyntheticTemplateGoal\n')
        (self.directory / 'TELOS.md').write_text('# Telos\nSyntheticTemplateTelos\n')
        (self.directory / 'z-extra.md').write_text('# Extra\nSyntheticTemplateExtra\n')
        (self.data / 'measures.csv').write_text('name,value\nSyntheticTemplateMeasure,12\n')
        (self.data / '.hidden.csv').write_text('SyntheticTemplateHidden\n')
        (self.directory / '.hidden.md').write_text('SyntheticTemplateHidden\n')
        (self.directory / 'ignored.txt').write_text('SyntheticTemplateIgnored\n')
        (self.directory / 'directory.md').mkdir()

    def call(self, *, context=True, original=False, copied=False):
        template = (Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE']) /
            'skills/Telos/DashboardTemplate/lib/telos-data.ts' if original else self.template)
        if copied:
            target = self.fixture.fixture.home / 'copied-telos-project/lib/telos-data.ts'
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(template, target)
            template = target
        environment = dict(os.environ, HOME=str(self.fixture.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1')
        for name in ('LIFEOS_MEMORY_INTERNAL', 'LIFEOS_MEMORY_CONTEXT', 'LIFEOS_MEMORY_PUBLICATION_JOURNAL'):
            environment.pop(name, None)
        if original: environment['LIFEOS_MEMORY_INTERNAL'] = '1'
        elif context: environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        return subprocess.run(['bun', '--no-install', str(Path(__file__).with_name('memory_telos_template_process.ts')), str(template)],
            capture_output=True, text=True, timeout=45, env=environment, cwd=self.fixture.fixture.home)

    def test_native_markdown_csv_core_order_context_list_and_count(self):
        original = self.call(original=True)
        result = self.call()
        self.assertEqual((result.returncode, result.stdout, result.stderr),
            (original.returncode, original.stdout, original.stderr))
        report = json.loads(result.stdout)
        self.assertEqual(report['list'], ['TELOS.md', 'GOALS.md', 'data/measures.csv', 'z-extra.md'])
        self.assertEqual(report['count'], 4)
        self.assertIn('SyntheticTemplateMeasure', report['context'])
        self.assertNotIn('SyntheticTemplateHidden', result.stdout)
        self.assertNotIn('SyntheticTemplateIgnored', result.stdout)

    def test_unbound_and_copied_readers_cannot_disclose_personal_data(self):
        for copied in (False, True):
            with self.subTest(copied=copied):
                result = self.call(context=False, copied=copied)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn('SyntheticTemplate', result.stdout + result.stderr)

    def test_private_and_retired_content_refuse_complete_context(self):
        self.goal.write_text('<private>SyntheticTemplateHiddenGoal</private>\n')
        result = self.call()
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('SyntheticTemplateHiddenGoal', result.stdout + result.stderr)
        self.goal.write_text('# Goals\nSyntheticTemplateGoal\n')
        saved = self.fixture.fixture.memory.remember(OWNER, category='principal', content='RULE: SyntheticTemplateGoal',
            title='', project='', request_id='template-retained')
        self.fixture.fixture.memory.forget(OWNER, saved['reference'], 'template-forget')
        result = self.call()
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('SyntheticTemplateGoal', result.stdout + result.stderr)

    def test_revocation_missing_connector_and_read_only_owner(self):
        self.fixture.configuration.update(lambda config: config['destinations']['chat-a:200'].update(write=[]))
        result = self.call(copied=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('SyntheticTemplateGoal', result.stdout)
        self.fixture.configuration.update(lambda config: config['accounts'].clear())
        self.assertEqual(self.call().returncode, 2)
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.assertEqual(self.call().returncode, 2)

    def test_redirected_invalid_and_excessive_sources_refuse(self):
        raw = self.goal.read_bytes()
        outside = self.fixture.fixture.home / 'outside-template.md'
        outside.write_bytes(raw)
        for mode in ('symlink', 'hardlink', 'utf8', 'oversize'):
            with self.subTest(mode=mode):
                self.goal.unlink()
                if mode == 'symlink': self.goal.symlink_to(outside)
                elif mode == 'hardlink': os.link(outside, self.goal)
                elif mode == 'utf8': self.goal.write_bytes(raw + b'\xff')
                else: self.goal.write_bytes(raw + b'x' * 256 * 1024)
                result = self.call()
                self.assertEqual(result.returncode, 2)
                self.assertNotIn('SyntheticTemplateGoal', result.stdout + result.stderr)

    def test_actual_native_render_rechecks_source_identity_selection_and_authority(self):
        from lifeos_hook_bridge import memory_telos_template as module
        from lifeos_hook_bridge.memory_access import MemoryUnavailable, MemoryConflict
        from lifeos_hook_bridge.memory_service import MemoryService
        memory = self.fixture.fixture.memory
        service = MemoryService(self.fixture.configuration)
        configuration = self.fixture.configuration.path.read_bytes()
        original = memory._native
        added = self.data / 'newly-created.csv'
        for mode in ('bytes', 'inode', 'mtime', 'selection', 'authority'):
            with self.subTest(mode=mode):
                self.fixture.configuration.path.write_bytes(configuration)
                self.goal.write_text('# Goals\nSyntheticTemplateGoal\n')
                added.unlink(missing_ok=True)
                admitted = self.fixture.configuration.load()
                scope = service.scope(self.fixture.context)
                observed = []
                def observe(action, **values):
                    result = original(action, **values)
                    if action == 'telos_template_view':
                        self.assertIn('SyntheticTemplateGoal', json.dumps(result))
                        observed.append(True)
                        if mode == 'bytes': self.goal.write_text('Synthetic changed source\n')
                        elif mode == 'inode':
                            replacement = self.goal.with_suffix('.replacement')
                            replacement.write_bytes(self.goal.read_bytes())
                            os.replace(replacement, self.goal)
                        elif mode == 'mtime':
                            info = self.goal.stat()
                            os.utime(self.goal, ns=(info.st_atime_ns, info.st_mtime_ns + 1000000))
                        elif mode == 'selection': added.write_text('name,value\nSyntheticNewMeasure,13\n')
                        else: self.fixture.configuration.update(lambda config: config['accounts'].clear())
                    return result
                memory._native = observe
                try:
                    with self.assertRaises((MemoryUnavailable, MemoryConflict)):
                        module.view(memory, scope,
                            check_current=lambda: service._check_current_context(admitted, self.fixture.context, scope))
                finally: memory._native = original
                self.assertEqual(observed, [True])

    def test_exact_review_restores_safe_old_markdown_and_csv_without_changes(self):
        from lifeos_hook_bridge.memory_source_review import preview, approve
        from lifeos_hook_bridge.memory_service import MemoryService
        memory = self.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: SyntheticUnrelatedTemplateRetirement',
            title='', project='', request_id='template-review-save')
        memory.forget(OWNER, saved['reference'], 'template-review-forget')
        paths = [self.goal, self.directory / 'TELOS.md', self.directory / 'z-extra.md', self.data / 'measures.csv']
        for path in paths: os.utime(path, (1577836800, 1577836800))
        before = [(path.read_bytes(), path.stat().st_mtime_ns) for path in paths]
        self.assertEqual(self.call().returncode, 2)
        service = MemoryService(self.fixture.configuration)
        admitted = self.fixture.configuration.load()
        scope = service.scope(self.fixture.context)
        relatives = [str(path.relative_to(self.root)) for path in paths]
        snapshot = preview(memory, scope, relatives)
        self.assertTrue(all(row['accepted'] for row in snapshot['sources']), snapshot)
        receipt = approve(memory, scope, relatives, snapshot['signature'],
            check_current=lambda: service._check_current_context(admitted, self.fixture.context, scope))
        self.assertEqual(receipt['status'], 'committed', receipt)
        self.assertEqual(self.call().returncode, 0)
        self.assertEqual([(path.read_bytes(), path.stat().st_mtime_ns) for path in paths], before)

    def test_unconfigured_copied_reader_and_missing_selection_keep_native_output(self):
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        (self.root / 'LIFEOS/USER/CONFIG/memory-http.json').unlink()
        result = self.call(context=False, copied=True)
        original = self.call(original=True)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
            (original.returncode, original.stdout, original.stderr))
        shutil.rmtree(self.directory)
        result = self.call(context=False, copied=True)
        original = self.call(original=True)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
            (original.returncode, original.stdout, original.stderr))
        report = json.loads(result.stdout)
        self.assertEqual((report['files'], report['list'], report['count']), ([], [], 0))

    def test_copied_template_runs_under_actual_node(self):
        project = self.fixture.fixture.home / 'node-template-project'
        project.mkdir()
        source = project / 'telos-data.ts'
        shutil.copyfile(self.template, source)
        built = subprocess.run(['bun', 'build', str(source), '--target=node', '--format=esm', '--outdir', str(project / 'dist')],
            capture_output=True, text=True, timeout=30)
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        self.assertEqual(built.stderr, '')
        self.assertIn('telos-data.js', built.stdout)
        (project / 'package.json').write_text('{"type":"module"}')
        script = 'import * as data from ' + json.dumps((project / 'dist/telos-data.js').as_uri()) + ';\n'
        script += 'console.log(JSON.stringify({files:data.getAllTelosData(),context:data.getTelosContext(),list:data.getTelosFileList(),count:data.getTelosFileCount()}));'
        environment = dict(os.environ, HOME=str(self.fixture.fixture.home), LIFEOS_MEMORY_CONTEXT=json.dumps(asdict(self.fixture.context)))
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        result = subprocess.run(['node', '--input-type=module', '-e', script], capture_output=True, text=True,
            timeout=45, env=environment, cwd=project)
        original = self.call(original=True)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
            (original.returncode, original.stdout, original.stderr))

    def test_private_csv_and_retired_filename_refuse_all_native_views(self):
        csv = self.data / 'measures.csv'
        csv.write_text('name,value\n<private>SyntheticTemplateHiddenMeasure</private>,12\n')
        result = self.call()
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('SyntheticTemplateHiddenMeasure', result.stdout + result.stderr)
        csv.write_text('name,value\nSafeMeasure,12\n')
        named = self.directory / 'SyntheticRetiredTemplateLabel.md'
        named.write_text('Safe public source body\n')
        memory = self.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: SyntheticRetiredTemplateLabel',
            title='', project='', request_id='template-label-save')
        memory.forget(OWNER, saved['reference'], 'template-label-forget')
        result = self.call()
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('SyntheticRetiredTemplateLabel', result.stdout + result.stderr)

    def test_complete_selection_near_directory_limit_retains_all_native_fields(self):
        for index in range(2030):
            (self.directory / f'extra-{index:04}.md').write_text('Safe bounded source\n')
        result = self.call()
        original = self.call(original=True)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
            (original.returncode, original.stdout, original.stderr))
        report = json.loads(result.stdout)
        self.assertEqual(report['count'], 2034)
        self.assertIn('extra-2029.md', report['list'])

    def test_missing_managed_selection_keeps_native_empty_context(self):
        shutil.rmtree(self.directory)
        result = self.call()
        original = self.call(original=True)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
            (original.returncode, original.stdout, original.stderr))
        self.assertEqual(json.loads(result.stdout)['count'], 0)

    def test_partial_reader_and_arbitrary_source_arguments_refuse(self):
        from lifeos_hook_bridge.memory_service import MemoryService
        service = MemoryService(self.fixture.configuration)
        result = service.native(self.fixture.context, 'telos_template', {'root': str(self.fixture.fixture.home)})
        self.assertFalse(result['ok'])
        self.assertNotIn('SyntheticTemplateGoal', json.dumps(result))
        self.fixture.configuration.update(lambda config: config['destinations']['chat-a:200'].update(read=['project']))
        result = self.call()
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('SyntheticTemplateGoal', result.stdout + result.stderr)
