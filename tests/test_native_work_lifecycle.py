# ABOUTME: Measures work-learning eligibility and concurrent session cleanup in real native programs.
# ABOUTME: Uses isolated work registries and actual hook processes without inference substitution.
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import shlex
import tempfile
import time
import unittest

from lifeos_hook_bridge.bridge import HookBridge

SOURCE = os.environ.get('LIFEOS_GUARD_SOURCE')


@unittest.skipUnless(SOURCE and shutil.which('bun'), 'Prepared native lifecycle programs and Bun are required')
class NativeWorkLifecycleTests(unittest.TestCase):
    def fixture(self, home, count=1, closed=True):
        root = home / '.claude'
        state = root / 'LIFEOS/MEMORY/STATE'
        state.mkdir(parents=True)
        (root/'hooks').symlink_to(Path(SOURCE)/'hooks', target_is_directory=True)
        sessions = {}
        now = datetime.now(timezone.utc).isoformat()
        for index in range(count):
            slug = 'work-' + str(index)
            session = 'session-' + str(index)
            work = root / 'LIFEOS/MEMORY/WORK' / slug
            work.mkdir(parents=True)
            sessions[slug] = {'sessionUUID':session, 'phase':'execute', 'task':'Same fixture task',
                              'updatedAt':now, 'started':now, 'progress':'1/1' if closed else '0/1', 'isa':True}
            (work/'ISA.md').write_text(f'---\ntask: Same fixture task\nphase: execute\nstatus: ACTIVE\n'
                f'created_at: {now}\ncompleted_at: null\nupdated: {now}\n---\n# Work\n\n## Claims\n'
                + ('- [x] Durable fixture result\n' if closed else '- [ ] Unfinished fixture result\n'))
        (state/'work.json').write_text(json.dumps({'sessions':sessions}))
        (state/'session-names.json').write_text(json.dumps({row['sessionUUID']:'Same fixture task' for row in sessions.values()}))
        settings = root/'settings.json'
        settings.write_text(json.dumps({'hooks':{'SessionEnd':[{'hooks':[
            {'type':'command','command':'bun '+str(Path(SOURCE)/'hooks'/name)}
            for name in ('WorkCompletionLearning.hook.ts','SessionCleanup.hook.ts')]}]}}))
        bridge = HookBridge(settings, root, lifeos_home=home)
        bridge.environment['LIFEOS_NOTIFICATION_CHANNEL'] = 'headless'
        self.addCleanup(bridge.close)
        return root, bridge

    def test_same_title_concurrent_sessions_retain_one_learning_each(self):
        with tempfile.TemporaryDirectory() as directory:
            root, bridge = self.fixture(Path(directory), count=8)
            preload = root/'name-write-delay.cjs'
            preload.write_text('''// ABOUTME: Widens the native session-name mutation interval.
// ABOUTME: Leaves each actual read and write with the native hook process.
const fs = require('node:fs');
const original = fs.writeFileSync;
fs.writeFileSync = function(path, ...args) {
  if (String(path).endsWith('/session-names.json')) {
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 100);
  }
  return original.call(this, path, ...args);
};
''')
            binaries = root/'fixture-bin'
            binaries.mkdir()
            interpreter = binaries/'bun'
            interpreter.write_text('#!/bin/sh\nexec '+shlex.join([shutil.which('bun'),'--preload',str(preload)])+' "$@"\n')
            interpreter.chmod(0o755)
            bridge.environment['PATH'] = str(binaries)+os.pathsep+bridge.environment['PATH']
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(lambda index: bridge.session_end(session_id='session-'+str(index)), range(8)))
            learnings = list((root/'LIFEOS/MEMORY/LEARNING').rglob('*_work_*.md'))
            rows = json.loads((root/'LIFEOS/MEMORY/STATE/work.json').read_text())['sessions']
            names = json.loads((root/'LIFEOS/MEMORY/STATE/session-names.json').read_text())
            if os.environ.get('LIFEOS_WORK_LIFECYCLE_EVIDENCE'):
                Path(os.environ['LIFEOS_WORK_LIFECYCLE_EVIDENCE']).write_text(json.dumps({
                    'learning_count':len(learnings), 'learning_sessions': [path.read_text().split('**Session:** ')[1].splitlines()[0] for path in learnings],
                    'work_phases':{key:row['phase'] for key,row in rows.items()}, 'remaining_session_names':names},indent=2)+'\n')
            self.assertEqual(len(learnings), 8)
            self.assertEqual({text.split('**Session:** ')[1].splitlines()[0] for text in map(Path.read_text, learnings)},
                             {'session-'+str(index) for index in range(8)})
            self.assertEqual(len(rows), 8)
            self.assertTrue(all(row['phase']=='complete' for row in rows.values()))
            self.assertEqual(names, {})

    def test_learning_finishes_first_and_cleanup_preserves_its_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root, bridge = self.fixture(Path(directory))
            hooks = bridge.hooks['SessionEnd'][0]['hooks']
            bridge.hooks['SessionEnd'][0]['hooks'] = hooks[:1]
            bridge.session_end(session_id='session-0')
            prior = {str(path):path.read_bytes() for path in (root/'LIFEOS/MEMORY/LEARNING').rglob('*_work_*.md')}
            self.assertEqual(len(prior), 1)
            bridge.hooks['SessionEnd'][0]['hooks'] = hooks[1:]
            bridge.session_end(session_id='session-0')
            self.assertEqual({str(path):path.read_bytes() for path in (root/'LIFEOS/MEMORY/LEARNING').rglob('*_work_*.md')}, prior)
            self.assertEqual(json.loads((root/'LIFEOS/MEMORY/STATE/work.json').read_text())['sessions']['work-0']['phase'], 'complete')

    def test_detached_sessions_preserve_learning_and_cleanup_after_parent_closes(self):
        with tempfile.TemporaryDirectory() as directory:
            root, bridge = self.fixture(Path(directory), count=8)
            marker = root/'native-exits.txt'
            preload = root/'detached-write-delay.cjs'
            preload.write_text('''// ABOUTME: Widens actual native cleanup writes and records process completion.
// ABOUTME: Measures detached lifecycle execution without replacing native effects.
const fs = require('node:fs');
const original = fs.writeFileSync;
fs.writeFileSync = function(path, ...args) {
  if (String(path).endsWith('/session-names.json')) {
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 100);
  }
  return original.call(this, path, ...args);
};
process.on('exit', () => fs.appendFileSync(process.env.LIFEOS_NATIVE_EXIT_MARKER, process.pid + '\\n'));
''')
            binaries = root/'fixture-bin'
            binaries.mkdir()
            interpreter = binaries/'bun'
            interpreter.write_text('#!/bin/sh\nexec '+shlex.join([shutil.which('bun'),'--preload',str(preload)])+' "$@"\n')
            interpreter.chmod(0o755)
            bridge.environment['PATH'] = str(binaries)+os.pathsep+bridge.environment['PATH']
            bridge.environment['LIFEOS_NATIVE_EXIT_MARKER'] = str(marker)
            for hook in bridge.hooks['SessionEnd'][0]['hooks']:
                hook['async'] = True
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(lambda index: bridge.session_end(session_id='session-'+str(index)), range(8)))
            bridge.close()
            deadline = time.monotonic()+20
            while time.monotonic() < deadline:
                if marker.exists() and len(marker.read_text().splitlines()) == 16:
                    break
                time.sleep(0.05)
            self.assertTrue(marker.exists(), 'Actual native hook processes did not finish')
            self.assertEqual(len(set(marker.read_text().splitlines())), 16)
            learnings = list((root/'LIFEOS/MEMORY/LEARNING').rglob('*_work_*.md'))
            self.assertEqual(len(learnings), 8)
            self.assertEqual({path.read_text().split('**Session:** ')[1].splitlines()[0] for path in learnings},
                             {'session-'+str(index) for index in range(8)})
            rows = json.loads((root/'LIFEOS/MEMORY/STATE/work.json').read_text())['sessions']
            self.assertTrue(all(row['phase']=='complete' for row in rows.values()))
            self.assertEqual(json.loads((root/'LIFEOS/MEMORY/STATE/session-names.json').read_text()), {})

    def test_unfinished_work_without_closed_claims_produces_no_learning(self):
        with tempfile.TemporaryDirectory() as directory:
            root, bridge = self.fixture(Path(directory), closed=False)
            bridge.session_end(session_id='session-0')
            self.assertEqual(list((root/'LIFEOS/MEMORY/LEARNING').rglob('*_work_*.md')), [])

    def test_repeat_finalization_does_not_duplicate_eligible_learning(self):
        with tempfile.TemporaryDirectory() as directory:
            root, bridge = self.fixture(Path(directory))
            isa = root/'LIFEOS/MEMORY/WORK/work-0/ISA.md'
            isa.write_text('\n'.join(line for line in isa.read_text().splitlines() if not line.startswith('created_at:'))+'\n')
            bridge.session_end(session_id='session-0')
            initial = {str(path):path.read_bytes() for path in (root/'LIFEOS/MEMORY/LEARNING').rglob('*_work_*.md')}
            self.assertEqual(len(initial), 1)
            bridge.session_end(session_id='session-0', reason='resume')
            self.assertEqual({str(path):path.read_bytes() for path in (root/'LIFEOS/MEMORY/LEARNING').rglob('*_work_*.md')}, initial)

            preload = root/'next-day.cjs'
            preload.write_text('''// ABOUTME: Advances the capture clock for a repeated native learning control.
// ABOUTME: Preserves the recorded work origin and actual native publication path.
const OriginalDate = Date;
const tomorrow = OriginalDate.now() + 86400000;
globalThis.Date = class extends OriginalDate {
  constructor(...args) { super(...(args.length ? args : [tomorrow])); }
  static now() { return tomorrow; }
};
''')
            bridge.hooks['SessionEnd'][0]['hooks'] = [{'type':'command', 'command':shlex.join([
                'bun','--preload',str(preload),str(Path(SOURCE)/'hooks/WorkCompletionLearning.hook.ts')])}]
            bridge.session_end(session_id='session-0')
            self.assertEqual({str(path):path.read_bytes() for path in (root/'LIFEOS/MEMORY/LEARNING').rglob('*_work_*.md')}, initial)

    def test_concurrent_repeated_finalization_preserves_one_learning(self):
        with tempfile.TemporaryDirectory() as directory:
            root, bridge = self.fixture(Path(directory))
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(lambda _: bridge.session_end(session_id='session-0'), range(8)))
            self.assertEqual(len(list((root/'LIFEOS/MEMORY/LEARNING').rglob('*_work_*.md'))), 1)
            self.assertEqual(json.loads((root/'LIFEOS/MEMORY/STATE/work.json').read_text())['sessions']['work-0']['phase'], 'complete')

    def test_finalization_preserves_another_sessions_active_work_and_name(self):
        for reason in ('prompt_input_exit', 'resume', 'upstream_failure', 'interrupt'):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as directory:
                root, bridge = self.fixture(Path(directory), count=2)
                other = root/'LIFEOS/MEMORY/WORK/work-1/ISA.md'
                prior = other.read_bytes()
                bridge.session_end(session_id='session-0', reason=reason)
                self.assertEqual(other.read_bytes(), prior)
                rows = json.loads((root/'LIFEOS/MEMORY/STATE/work.json').read_text())['sessions']
                self.assertEqual(rows['work-0']['phase'], 'complete')
                self.assertEqual(rows['work-1']['phase'], 'execute')
                self.assertEqual(json.loads((root/'LIFEOS/MEMORY/STATE/session-names.json').read_text()),
                                 {'session-1':'Same fixture task'})

    def test_partial_work_with_one_closed_claim_preserves_native_eligibility(self):
        with tempfile.TemporaryDirectory() as directory:
            root, bridge = self.fixture(Path(directory))
            isa = root/'LIFEOS/MEMORY/WORK/work-0/ISA.md'
            isa.write_text(isa.read_text()+'- [ ] Another unfinished claim\n')
            bridge.session_end(session_id='session-0')
            files = list((root/'LIFEOS/MEMORY/LEARNING').rglob('*_work_*.md'))
            self.assertEqual(len(files), 1)
            self.assertIn('1/2 closed', files[0].read_text())

    def test_absent_work_produces_no_learning(self):
        with tempfile.TemporaryDirectory() as directory:
            root, bridge = self.fixture(Path(directory))
            bridge.session_end(session_id='absent')
            self.assertEqual(list((root/'LIFEOS/MEMORY/LEARNING').rglob('*_work_*.md')), [])
