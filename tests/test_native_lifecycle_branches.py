# ABOUTME: Checks installed startup and lifecycle branches against isolated native state.
# ABOUTME: Runs actual Bun programs and filesystem operations without model-response substitution.
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import shlex
import tempfile
import time
import unittest

from lifeos_hook_bridge.bridge import HookBridge

SOURCE = os.environ.get('LIFEOS_GUARD_SOURCE')


@unittest.skipUnless(SOURCE and shutil.which('bun'), 'Prepared native lifecycle programs and Bun are required')
class NativeLifecycleBranchTests(unittest.TestCase):
    def fixture(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        home = Path(temporary.name)
        root = home/'.claude'
        (root/'LIFEOS/MEMORY/STATE').mkdir(parents=True)
        (root/'hooks').symlink_to(Path(SOURCE)/'hooks',target_is_directory=True)
        (root/'LIFEOS/TOOLS').symlink_to(Path(SOURCE)/'LIFEOS/TOOLS',target_is_directory=True)
        environment = {**os.environ,'HOME':str(home),'LIFEOS_DIR':str(root/'LIFEOS'),
                       'LIFEOS_NOTIFICATION_CHANNEL':'headless'}
        for key in ('LIFEOS_MEMORY_CONTEXT','LIFEOS_MEMORY_INTERNAL','CLAUDE_CONFIG_DIR','LIFEOS_CONFIG_DIR',
                    'CORTEX_HEALTH_ROOT','CORTEX_HEALTH_REPORT_PATH','CORTEX_HEALTH_NO_WRITE',
                    'CLAUDE_AGENT_TYPE','CLAUDE_CODE_SUBAGENT_NAME','CLAUDE_CODE_SUBAGENT_TYPE',
                    'CLAUDE_AGENT_SDK','CLAUDE_CODE_FORK_SUBAGENT','CLAUDE_PROJECT_DIR'):
            environment.pop(key,None)
        return home, root, environment

    def call(self, root, environment, relative, payload=None, arguments=()):
        return subprocess.run(['bun',str(Path(SOURCE)/relative),*arguments],
            input=json.dumps(payload or {}),env=environment,cwd=root,text=True,capture_output=True,timeout=30)

    def seed_health(self, root):
        now = datetime.now(timezone.utc).isoformat()
        for relative in ('PRINCIPAL/PRINCIPAL_MEMORY.md','DIGITAL_ASSISTANT/DA_MEMORY.md'):
            path = root/'LIFEOS/USER'/relative
            path.parent.mkdir(parents=True)
            path.write_text('<!-- BEGIN ENTRIES -->\n<!-- END ENTRIES -->\n')
        state = root/'LIFEOS/MEMORY/STATE'
        (state/'delta-surface-heartbeat').touch()
        obs = root/'LIFEOS/MEMORY/OBSERVABILITY'
        (obs/'reviewer-runs/synthetic-run').mkdir(parents=True)
        (obs/'review-state.json').write_text(json.dumps({'last_review_at':now,
            'turn_count_since_last_review':0,'pending_review':False}))
        summary = {'total':0,'by_type':{},'succeeded':0,'failed':0,'failures':[],
                   'skipped_guard':0,'skips':[],'proposals_auto_applied':0,'proposals_auto_apply_failed':0}
        (obs/'reviewer-runs.jsonl').write_text(json.dumps({'ts':now,'ok':True,'runId':'synthetic-run',
            'transcript':'synthetic-transcript','exchanges':1,'inference_duration_ms':1,
            'parse_ok':True,'dispatch_summary':summary})+'\n')
        (obs/'memory-retrievals.jsonl').write_text(json.dumps({'ts':now,'query_hash':'synthetic-query',
            'returned_count':0,'duration_ms':1})+'\n')
        (obs/'pending-proposals.jsonl').write_text('')
        (root/'LIFEOS/CORTEX_INDEX_POLICY.json').write_bytes((Path(SOURCE)/'LIFEOS/CORTEX_INDEX_POLICY.json').read_bytes())
        (root/'settings.json').write_text(json.dumps({'hooks':{
            'UserPromptSubmit':[{'hooks':[{'type':'command','command':'bun '+str(root/'hooks/MemoryTurnStart.hook.ts')}]}],
            'Stop':[{'hooks':[{'type':'command','command':'bun '+str(root/'hooks'/name)} for name in
                ('MemoryReviewFire.hook.ts','MemoryHealthGate.hook.ts')]}]}}))

    def test_health_ok_warning_and_missing_tool_follow_both_event_contracts(self):
        home, root, environment = self.fixture()
        self.seed_health(root)
        checker = self.call(root,environment,'LIFEOS/TOOLS/MemoryHealthCheck.ts')
        self.assertEqual(checker.stderr,'')
        report = json.loads(checker.stdout)
        self.assertEqual(report['overall'],'ok', report)
        self.assertEqual(checker.returncode,0)
        hook = 'hooks/MemoryHealthGate.hook.ts'
        for event in ('Stop','SessionEnd'):
            with self.subTest(event=event):
                result = self.call(root,environment,hook,{'hook_event_name':event,'session_id':'healthy'})
                self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'',''))
        state = root/'LIFEOS/MEMORY/OBSERVABILITY/review-state.json'
        state.unlink()
        for event in ('Stop','SessionEnd'):
            with self.subTest(warning_event=event):
                result = self.call(root,environment,hook,{'hook_event_name':event,'session_id':'warning'})
                self.assertEqual((result.returncode,result.stdout),(0,''))
                self.assertIn('Memory health: WARN',result.stderr)
        log = root/'LIFEOS/MEMORY/OBSERVABILITY/memory-health.jsonl'
        reports = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual([row['overall'] for row in reports],['ok','ok','ok','warn','warn'])
        (root/'LIFEOS/TOOLS').unlink()
        prior = log.read_bytes()
        for event in ('Stop','SessionEnd'):
            result = self.call(root,environment,hook,{'hook_event_name':event,'session_id':'missing-tool'})
            self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'',''))
        self.assertEqual(log.read_bytes(),prior)

    def test_concurrent_slash_prompts_and_restart_preserve_session_identity(self):
        home, root, environment = self.fixture()
        settings = root/'settings.json'
        settings.write_text(json.dumps({'hooks':{'UserPromptSubmit':[{'hooks':[{
            'type':'command','command':'bun '+str(root/'hooks/PromptProcessing.hook.ts')}]}]}}))
        bridges = [HookBridge(settings,root,lifeos_home=home) for _ in range(8)]
        for bridge in bridges:
            bridge.environment.update(environment)
            self.addCleanup(bridge.close)
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda index:bridges[index].pre_llm_call('/Research',session_id='prompt-'+str(index)),range(8)))
        names = root/'LIFEOS/MEMORY/STATE/session-names.json'
        recorded = json.loads(names.read_text())
        self.assertEqual(set(recorded),{'prompt-'+str(i) for i in range(8)})
        self.assertTrue(all(name.startswith('Research Skill Run') for name in recorded.values()))
        self.assertEqual(len(set(recorded.values())),8)
        rows = json.loads((root/'LIFEOS/MEMORY/STATE/work.json').read_text())['sessions']
        self.assertEqual({row['sessionUUID'] for row in rows.values()},{'prompt-'+str(i) for i in range(8)})
        prior = names.read_bytes()
        for bridge in bridges:
            bridge.close()
        resumed = HookBridge(settings,root,lifeos_home=home)
        resumed.environment.update(environment)
        self.addCleanup(resumed.close)
        resumed.pre_llm_call('Thanks',session_id='prompt-0',source='resume')
        self.assertEqual(names.read_bytes(),prior)

    def test_healer_contains_repairs_and_preserves_interpreter_arguments(self):
        _, root, environment = self.fixture()
        registered = root/'fixture-hooks'
        registered.mkdir()
        for name, contents, mode in (('valid.sh','#!/bin/sh\nexit 0\n',0o755),
                ('direct.sh','#!/bin/sh\nexit 0\n',0o644),('argument.sh','#!/bin/sh\nexit 0\n',0o644),
                ('noshebang.sh','exit 0\n',0o644),('unsupported.py','print("fixture")\n',0o644),('unregistered.sh','#!/bin/sh\nexit 0\n',0o644)):
            target = registered/name
            target.write_text(contents)
            target.chmod(mode)
        outside = root.parent/'outside.sh'
        outside.write_text('#!/bin/sh\nexit 0\n')
        outside.chmod(0o644)
        (registered/'redirect.sh').symlink_to(outside)
        commands = [str(registered/name) for name in ('valid.sh','direct.sh','missing.sh','redirect.sh','noshebang.sh','unsupported.py')]
        commands.append('bash '+str(registered/'argument.sh'))
        settings = root/'settings.json'
        settings.write_text(json.dumps({'hooks':{'Stop':[{'hooks':[{'command':command} for command in commands]}]}}))
        before = {name:(registered/name).read_bytes() for name in ('valid.sh','direct.sh','argument.sh','unsupported.py','unregistered.sh')}
        result = self.call(root,environment,'hooks/HookHealer.hook.ts',{'hook_event_name':'SessionStart'})
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue((registered/'direct.sh').stat().st_mode & 0o111)
        for name in ('argument.sh','unsupported.py','unregistered.sh'):
            self.assertEqual((registered/name).stat().st_mode & 0o111,0)
        self.assertEqual(outside.stat().st_mode & 0o111,0)
        self.assertFalse((registered/'missing.sh').exists())
        self.assertEqual({name:(registered/name).read_bytes() for name in before},before)
        log = root/'LIFEOS/MEMORY/OBSERVABILITY/hook-healer.jsonl'
        rows = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(sum(row['event']=='healed' for row in rows),2)
        self.assertEqual(sum(row['event']=='missing' for row in rows),1)
        self.assertEqual(sum(row['event']=='containment-refused' for row in rows),1)
        repeated = self.call(root,environment,'hooks/HookHealer.hook.ts')
        self.assertEqual(repeated.returncode,0)
        self.assertEqual(sum(json.loads(line)['event']=='healed' for line in log.read_text().splitlines()),2)

    def test_kitty_absent_terminal_and_child_markers_preserve_desktop_files(self):
        _, root, environment = self.fixture()
        state = root/'LIFEOS/MEMORY/STATE'
        (state/'kitty-env.json').write_text('{"synthetic_prior":true}\n')
        prior = (state/'kitty-env.json').read_bytes()
        for key in ('KITTY_LISTEN_ON','KITTY_WINDOW_ID'):
            environment.pop(key,None)
        result = self.call(root,environment | {'LIFEOS_NOTIFICATION_CHANNEL':'desktop'},
            'hooks/KittyEnvPersist.hook.ts',{'session_id':'absent','source':'startup'})
        self.assertEqual(result.returncode,0)
        self.assertEqual((state/'kitty-env.json').read_bytes(),prior)
        self.assertFalse((state/'kitty-sessions/absent.json').exists())
        desktop = environment | {'LIFEOS_NOTIFICATION_CHANNEL':'desktop','TERM':'xterm-kitty',
            'KITTY_LISTEN_ON':'unix:/tmp/nonexistent-lifeos-fixture','KITTY_WINDOW_ID':'123'}
        for marker in ('CLAUDE_AGENT_TYPE','CLAUDE_CODE_SUBAGENT_NAME','CLAUDE_CODE_SUBAGENT_TYPE',
                       'CLAUDE_AGENT_SDK','CLAUDE_CODE_FORK_SUBAGENT'):
            with self.subTest(marker=marker):
                result = self.call(root,desktop | {marker:'1'},'hooks/KittyEnvPersist.hook.ts',
                    {'session_id':'child','source':'startup'})
                self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'',''))
                self.assertEqual((state/'kitty-env.json').read_bytes(),prior)
                self.assertFalse((state/'kitty-sessions/child.json').exists())

    def test_concurrent_freshness_refresh_replaces_stale_cache_with_valid_current_state(self):
        _, root, environment = self.fixture()
        telos = root/'LIFEOS/USER/TELOS/TELOS.md'
        telos.parent.mkdir(parents=True)
        today = datetime.now(timezone.utc).date().isoformat()
        telos.write_text(f'---\nlast_updated: {today}\nlast_reviewed: {today}\n---\n# Synthetic TELOS\n')
        cache = root/'LIFEOS/USER/CACHE/freshness.json'
        cache.parent.mkdir()
        cache.write_text('{"synthetic_stale":true}\n')
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _:self.call(root,environment,'LIFEOS/TOOLS/FreshnessCache.ts',
                                                       arguments=('--quiet',)),range(8)))
        self.assertTrue(all((result.returncode,result.stdout,result.stderr)==(0,'','') for result in results),results)
        payload = json.loads(cache.read_text())
        self.assertNotIn('synthetic_stale',payload)
        self.assertEqual(payload['total'],len(payload['files']))
        self.assertFalse(next(row for row in payload['files'] if row['slug']=='telos')['stale'])
        self.assertEqual(list(cache.parent.glob('freshness.json.tmp.*')),[])
        telos.unlink()
        missing = self.call(root,environment,'LIFEOS/TOOLS/FreshnessCache.ts',arguments=('--quiet',))
        self.assertEqual((missing.returncode,missing.stdout,missing.stderr),(0,'',''))
        current = json.loads(cache.read_text())
        self.assertTrue(next(row for row in current['files'] if row['slug']=='telos')['stale'])

    def test_interrupted_freshness_rename_preserves_the_prior_cache(self):
        _, root, environment = self.fixture()
        cache = root/'LIFEOS/USER/CACHE/freshness.json'
        cache.parent.mkdir(parents=True)
        previous = b'{"synthetic_prior":true}\n'
        cache.write_bytes(previous)
        marker = root/'rename-ready'
        preload = root/'rename-delay.cjs'
        preload.write_text('''// ABOUTME: Pauses the actual native freshness publication before rename.
// ABOUTME: Preserves native collection and temporary writes for an interruption control.
const fs = require('node:fs');
const rename = fs.renameSync;
fs.renameSync = function(source, target) {
  if (String(target).endsWith('/freshness.json')) {
    fs.writeFileSync(process.env.LIFEOS_RENAME_MARKER, String(source));
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 30000);
  }
  return rename.call(this, source, target);
};
''')
        process = subprocess.Popen(['bun','--preload',str(preload),str(Path(SOURCE)/'LIFEOS/TOOLS/FreshnessCache.ts'),'--quiet'],
            env=environment | {'LIFEOS_RENAME_MARKER':str(marker)},stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic()+10
            while not marker.exists() and process.poll() is None and time.monotonic()<deadline:
                time.sleep(.02)
            self.assertTrue(marker.exists(),'Actual freshness rename was not reached')
        finally:
            if process.poll() is None:
                process.kill()
            output, errors = process.communicate(timeout=5)
        self.assertEqual((process.returncode,output,errors),(-9,b'',b''))
        self.assertEqual(cache.read_bytes(),previous)
        self.assertTrue(Path(marker.read_text()).is_file())

    def test_pinned_async_health_report_survives_parent_kill_and_remains_after_restart(self):
        home, root, environment = self.fixture()
        self.seed_health(root)
        settings = root/'settings.json'
        selected = {'type':'command','command':'bun '+str(root/'hooks/MemoryHealthGate.hook.ts'),
                    'async':True,'timeout':15}
        registered = json.loads(settings.read_text())
        registered['hooks']['Stop'][0]['hooks'][-1] = selected
        settings.write_text(json.dumps(registered))
        binaries = home/'bin'
        binaries.mkdir()
        launcher = binaries/'bun'
        launcher.write_text('#!/bin/sh\nsleep 0.3\nexec '+shlex.quote(shutil.which('bun'))+' "$@"\n')
        launcher.chmod(0o755)
        environment['PATH'] = str(binaries)+os.pathsep+environment['PATH']
        environment.pop('XDG_RUNTIME_DIR',None)
        driver = ('import os,signal\nfrom pathlib import Path\nfrom lifeos_hook_bridge.bridge import HookBridge\n'
            f'b=HookBridge(Path({str(settings)!r}),Path({str(root)!r}),lifeos_home=Path({str(home)!r}))\n'
            f'b.hooks={{"Stop":[{{"hooks":[{selected!r}]}}]}}\n'
            'b.stop("Synthetic completed candidate",session_id="async-health")\n'
            'os.kill(os.getpid(),signal.SIGKILL)\n')
        killed = subprocess.run([sys.executable,'-c',driver],env=environment,timeout=10)
        self.assertEqual(killed.returncode,-9)
        log = root/'LIFEOS/MEMORY/OBSERVABILITY/memory-health.jsonl'
        deadline = time.monotonic()+10
        while not log.exists() and time.monotonic()<deadline:
            time.sleep(.03)
        self.assertTrue(log.exists(),'The actual detached native health check did not publish')
        self.assertEqual(json.loads(log.read_text())['overall'],'ok')
        before = log.read_bytes()
        restarted = HookBridge(settings,root,lifeos_home=home)
        self.addCleanup(restarted.close)
        restarted.hooks = {}
        self.assertIsNone(restarted.pre_llm_call('Restarted synthetic session',session_id='async-health'))
        self.assertEqual(log.read_bytes(),before)
