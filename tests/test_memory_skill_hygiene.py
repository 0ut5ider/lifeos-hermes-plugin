# ABOUTME: Characterizes native skill hygiene findings and owner admission with real scans.
# ABOUTME: Uses disposable skill files and security controls without changing an installed profile.
import json
import os
from pathlib import Path
import subprocess
import shutil
import unittest

import test_memory_manual_state as state_fixture
from test_memory_native import OWNER


class MemorySkillHygieneTests(unittest.TestCase):
    setUp = state_fixture.MemoryManualStateTests.setUp
    call = state_fixture.MemoryManualStateTests.call

    def seed(self):
        self.skills = self.root / 'skills'
        self.skills.mkdir(exist_ok=True)
        security = self.root / 'LIFEOS/USER/SECURITY'
        security.mkdir(exist_ok=True)
        self.deny = security / 'DENY_LIST.txt'
        self.hashes = security / 'DENY_HASHES.json'
        self.allow = self.root / 'LIFEOS/USER/CONFIG/skill-hygiene-allowlist.json'
        self.deny.write_text('\n'.join('SyntheticDenyToken' + str(index) for index in range(20)) + '\n')
        self.allow.write_text('[]')
        self.code = self.skills / 'SyntheticSkill/SKILL.md'
        self.code.parent.mkdir(exist_ok=True)
        self.code.write_text('# Synthetic skill\nSafe public instructions\n')

    def scan(self, *args, context=True):
        return self.call('SkillHygieneGate.ts', *args, context=context)

    def original(self, *args):
        tool = Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE']) / 'LIFEOS/TOOLS/SkillHygieneGate.ts'
        return subprocess.run(['bun', '--no-install', str(tool), *args], capture_output=True, text=True,
            timeout=40, cwd=self.fixture.fixture.home, env=dict(os.environ, HOME=str(self.fixture.fixture.home),
            LIFEOS_MEMORY_INTERNAL='1', BUN_CONFIG_NO_AUTO_INSTALL='1'))

    def same(self, *args):
        original = self.original(*args)
        result = self.scan(*args)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
            (original.returncode, original.stdout, original.stderr))
        return result

    def test_native_clean_findings_allowlist_filter_and_detail(self):
        self.seed()
        self.same('--json')
        self.code.write_text('SyntheticDenyToken0\nSyntheticDenyToken1\n')
        report = json.loads(self.same('--json', '--max-detail', '1').stdout)
        self.assertEqual(report['totalViolations'], 2)
        self.assertEqual(len(report['skills'][0]['detail']), 1)
        for excluded in ('node_modules/package/a.ts', '.cache/a.txt', 'image.png'):
            path = self.code.parent / excluded
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('SyntheticDenyToken2\n')
        self.assertEqual(json.loads(self.same('--json', '--skill', 'SyntheticSkill').stdout)['totalViolations'], 2)
        self.allow.write_text(json.dumps([{'path': 'skills/SyntheticSkill/', 'reason': 'Synthetic pattern detector', 'added': '2026-10-09'}]))
        report = json.loads(self.same('--json').stdout)
        self.assertEqual((report['totalViolations'], report['allowedHits']), (0, 2))
        self.same('--skill', 'SyntheticSkill')

    def test_native_missing_hash_only_short_list_and_malformed_allowlist(self):
        self.seed()
        self.deny.unlink()
        self.assertTrue(json.loads(self.same('--json').stdout)['skipped'])
        self.hashes.write_text('{}')
        self.assertEqual(self.same('--json').returncode, 1)
        self.hashes.unlink()
        self.deny.write_text('SyntheticDenyToken0\n')
        self.assertEqual(self.same('--json').returncode, 2)
        self.seed()
        for content in ('{', '{}'):
            self.allow.write_text(content)
            self.assertEqual(self.same('--json').returncode, 2)

    def test_unbound_reader_cannot_disclose_findings_or_controls(self):
        self.seed()
        self.code.write_text('SyntheticDenyToken0\n')
        result = self.scan('--json', context=False)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('SyntheticDenyToken', result.stdout + result.stderr)

    def test_private_code_and_decoded_allowlist_refuse_without_clean_verdict(self):
        self.seed()
        self.code.write_text('<private>SyntheticHygieneHidden</private>\n')
        result = self.scan('--json')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('SyntheticHygieneHidden', result.stdout + result.stderr)
        self.code.write_text('Safe public code\n')
        self.allow.write_text('[{"path":"skills/SyntheticSkill/","reason":"\\u003cprivate\\u003eSyntheticHygieneHidden\\u003c/private\\u003e"}]')
        result = self.scan('--json')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('SyntheticHygieneHidden', result.stdout + result.stderr)

    def test_actual_retirement_refuses_retained_security_control(self):
        self.seed()
        saved = self.fixture.fixture.memory.remember(OWNER, category='principal', content='RULE: SyntheticDenyToken0',
            title='', project='', request_id='hygiene-retained')
        self.fixture.fixture.memory.forget(OWNER, saved['reference'], 'hygiene-forget')
        result = self.scan('--json')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('SyntheticDenyToken', result.stdout + result.stderr)

    def test_complete_scan_exceeds_transport_batch_and_keeps_late_findings(self):
        self.seed()
        for index in range(30):
            (self.code.parent / f'part-{index:02}.txt').write_text('Safe code\n' * 20000)
        (self.code.parent / 'z-final.txt').write_text('SyntheticDenyToken19\n')
        report = json.loads(self.same('--json').stdout)
        self.assertEqual(report['totalViolations'], 1)
        self.assertEqual(report['skills'][0]['detail'][0]['file'], 'SyntheticSkill/z-final.txt')

    def test_redirected_invalid_excessive_sources_and_arbitrary_roots_refuse(self):
        self.seed()
        raw = self.code.read_bytes()
        outside = self.fixture.fixture.home / 'hygiene-outside.txt'
        outside.write_bytes(raw)
        for mode in ('symlink', 'hardlink', 'utf8', 'oversize'):
            with self.subTest(mode=mode):
                self.code.unlink()
                if mode == 'symlink': self.code.symlink_to(outside)
                elif mode == 'hardlink': os.link(outside, self.code)
                elif mode == 'utf8': self.code.write_bytes(raw + b'\xff')
                else: self.code.write_bytes(b'x' * (256 * 1024 + 1))
                self.assertEqual(self.scan('--json').returncode, 2)
        self.code.unlink()
        self.code.write_bytes(raw)
        self.assertEqual(self.scan('--json', '--root', str(self.fixture.fixture.home)).returncode, 2)

    def test_revoked_owner_and_missing_connector_refuse(self):
        self.seed()
        self.code.write_text('SyntheticDenyToken0\n')
        self.fixture.configuration.update(lambda config: config['accounts'].clear())
        self.assertEqual(self.scan('--json').returncode, 2)
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.assertEqual(self.scan('--json').returncode, 2)

    def test_actual_native_scan_rechecks_bytes_inode_mtime_selection_hashes_and_authority(self):
        from lifeos_hook_bridge import memory_skill_hygiene as module
        from lifeos_hook_bridge.memory_access import MemoryUnavailable, MemoryConflict
        from lifeos_hook_bridge.memory_service import MemoryService
        self.seed()
        memory = self.fixture.fixture.memory
        service = MemoryService(self.fixture.configuration)
        configuration = self.fixture.configuration.path.read_bytes()
        original = module.render
        added = self.code.parent / 'newly-selected.txt'
        for mode in ('bytes', 'inode', 'mtime', 'selection', 'hashes', 'deny', 'authority'):
            with self.subTest(mode=mode):
                self.fixture.configuration.path.write_bytes(configuration)
                self.seed()
                added.unlink(missing_ok=True)
                self.hashes.unlink(missing_ok=True)
                admitted = self.fixture.configuration.load()
                scope = service.scope(self.fixture.context)
                observed = []
                def observe(memory, args, root):
                    for path in root.rglob('*'):
                        if path.is_file(): self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                    result = original(memory, args, root)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    observed.append(True)
                    if mode == 'bytes': self.code.write_text('Synthetic changed code\n')
                    elif mode == 'inode':
                        replacement = self.code.with_suffix('.replacement')
                        replacement.write_bytes(self.code.read_bytes())
                        os.replace(replacement, self.code)
                    elif mode == 'mtime':
                        info = self.code.stat()
                        os.utime(self.code, ns=(info.st_atime_ns, info.st_mtime_ns + 1000000))
                    elif mode == 'selection': added.write_text('Safe newly selected source\n')
                    elif mode == 'hashes': self.hashes.write_text('{}')
                    elif mode == 'deny': self.deny.write_text(self.deny.read_text() + 'SyntheticAddedDeny\n')
                    else: self.fixture.configuration.update(lambda config: config['accounts'].clear())
                    return result
                module.render = observe
                try:
                    with self.assertRaises((MemoryUnavailable, MemoryConflict)):
                        module.run(memory, scope, args=['--json'],
                            check_current=lambda: service._check_current_context(admitted, self.fixture.context, scope))
                finally: module.render = original
                self.assertEqual(observed, [True])

    def test_exact_review_preserves_safe_old_security_and_skill_sources(self):
        from lifeos_hook_bridge.memory_source_review import preview, approve
        from lifeos_hook_bridge.memory_service import MemoryService
        self.seed()
        memory = self.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: SyntheticUnrelatedHygieneRetirement',
            title='', project='', request_id='hygiene-review-save')
        memory.forget(OWNER, saved['reference'], 'hygiene-review-forget')
        paths = [self.deny, self.allow, self.code]
        for path in paths: os.utime(path, (1577836800, 1577836800))
        before = [(path.read_bytes(), path.stat().st_mtime_ns) for path in paths]
        self.assertEqual(self.scan('--json').returncode, 2)
        service = MemoryService(self.fixture.configuration)
        admitted = self.fixture.configuration.load()
        scope = service.scope(self.fixture.context)
        relatives = [str(path.relative_to(self.root)) for path in paths]
        snapshot = preview(memory, scope, relatives)
        self.assertTrue(all(row['accepted'] for row in snapshot['sources']), snapshot)
        receipt = approve(memory, scope, relatives, snapshot['signature'],
            check_current=lambda: service._check_current_context(admitted, self.fixture.context, scope))
        self.assertEqual(receipt['status'], 'committed', receipt)
        self.assertEqual(self.scan('--json').returncode, 0)
        self.assertEqual([(path.read_bytes(), path.stat().st_mtime_ns) for path in paths], before)

    def test_read_only_owner_and_unconfigured_behavior_preserve_native_scan(self):
        self.seed()
        self.fixture.configuration.update(lambda config: config['destinations']['chat-a:200'].update(write=[]))
        self.same('--json')
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        (self.root / 'LIFEOS/USER/CONFIG/memory-http.json').unlink()
        result = self.scan('--json', context=False)
        original = self.original('--json')
        self.assertEqual((result.returncode, result.stdout, result.stderr),
            (original.returncode, original.stdout, original.stderr))

    def test_full_public_native_skill_tree_keeps_complete_findings(self):
        self.seed()
        prepared = Path(os.environ['LIFEOS_MEMORY_SOURCE']) / 'skills'
        shutil.copytree(prepared, self.skills, dirs_exist_ok=True)
        original = self.original('--json')
        current = self.scan('--json')
        self.assertEqual(current.returncode, original.returncode, current.stderr + current.stdout)
        self.assertEqual(current.stderr, original.stderr)
        # Native ripgrep may visit equal-count skills in a different directory order after copying.
        original_report, current_report = json.loads(original.stdout), json.loads(current.stdout)
        for report in (original_report, current_report):
            report['skills'].sort(key=lambda row: row['skill'])
            for row in report['skills']: row['detail'].sort(key=lambda item: (item['file'], item['line']))
        self.assertEqual(current_report, original_report)

    def test_actual_git_index_retains_tracked_vendored_dependency_findings(self):
        self.seed()
        source = os.environ['LIFEOS_PREPARE_LIFEOS_REPO']
        repository = self.fixture.fixture.home / 'synthetic-git-repository'
        commands = [['git', 'clone', '--quiet', '--no-checkout', '--no-hardlinks', source, str(repository)],
            ['git', '-C', str(repository), 'config', 'core.worktree', str(self.root)]]
        for command in commands:
            result = subprocess.run(command, capture_output=True, text=True, timeout=40)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout + result.stderr, '')
        (self.root / '.git').write_text('gitdir: ' + str(repository / '.git') + '\n')
        vendor = self.code.parent / 'node_modules/package/index.js'
        vendor.parent.mkdir(parents=True)
        vendor.write_text('Synthetic vendored dependency\n')
        result = subprocess.run(['git', '-C', str(self.root), 'add', '-f', 'skills/SyntheticSkill/node_modules/package/index.js'],
            capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout + result.stderr, '')
        report = json.loads(self.same('--json').stdout)
        self.assertEqual(report['vendoredDeps'], ['skills/SyntheticSkill/node_modules'])
        self.assertEqual(report['totalViolations'], 0)
        self.assertFalse(report['ok'])
        self.same('--json', '--skill', 'SyntheticSkill')

    def test_import_does_not_scan_or_disclose_security_controls(self):
        self.seed()
        self.deny.write_text('<private>SyntheticImportHidden</private>\n')
        script = 'await import(' + json.dumps(str(self.root / 'LIFEOS/TOOLS/SkillHygieneGate.ts')) + ');'
        result = subprocess.run(['bun', '--no-install', '-e', script], capture_output=True, text=True, timeout=30,
            env=dict(os.environ, HOME=str(self.fixture.fixture.home), LIFEOS_MEMORY_INTERNAL='1', BUN_CONFIG_NO_AUTO_INSTALL='1'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout + result.stderr, '')

    def test_native_invalid_pattern_returns_scan_error(self):
        self.seed()
        self.deny.write_text(self.deny.read_text() + '[\n')
        for result in (self.original('--json'), self.scan('--json')):
            self.assertEqual(result.returncode, 2)
            body = json.loads(result.stdout)
            self.assertFalse(body['ok'])
            self.assertEqual(body['exitCode'], 2)
            self.assertIn('rg failed:', body['error'])
            self.assertIn('unclosed character class', body['error'])
            self.assertIn('regex parse error:', result.stderr)
            self.assertIn('unclosed character class', result.stderr)
