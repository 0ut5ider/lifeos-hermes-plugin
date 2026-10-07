# ABOUTME: Verifies native dynamic context, documentation, settings, and render branches.
# ABOUTME: Runs real installed programs and keeps every effect in disposable filesystem state.
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import unittest

import test_native_lifecycle_branches as lifecycle

SOURCE = os.environ.get('LIFEOS_GUARD_SOURCE')


@unittest.skipUnless(SOURCE and shutil.which('bun'), 'Prepared native startup programs and Bun are required')
class NativeStartupSurfaceTests(unittest.TestCase):
    def fixture(self):
        fixture=lifecycle.NativeLifecycleBranchTests()
        home,root,environment=fixture.fixture()
        self.addCleanup(fixture.doCleanups)
        return home,root,environment

    def call(self, root, environment, relative, payload=None, arguments=()):
        return subprocess.run(['bun',str(Path(SOURCE)/relative),*arguments],
            input=json.dumps(payload or {}),env=environment,cwd=root,text=True,capture_output=True,timeout=20)

    def test_dynamic_work_context_missing_enabled_disabled_and_terminal_phases(self):
        _,root,environment=self.fixture()
        (root/'settings.json').write_text('{}')
        missing=self.call(root,environment,'hooks/LoadContext.hook.ts',{'source':'startup'})
        self.assertEqual(missing.returncode,0,missing.stderr)
        self.assertNotIn('Synthetic Active Fixture Work',missing.stdout)
        environment['LIFEOS_NOTIFICATION_CHANNEL']='desktop'
        work=root/'LIFEOS/MEMORY/WORK'/(datetime.now().strftime('%Y%m%d-%H%M%S')+'_synthetic-work')
        work.mkdir(parents=True)
        isa=work/'ISA.md'
        isa.write_text('---\ntitle: Synthetic Active Fixture Work\nphase: climbing\nprogress: 0/1\nsession_id: synthetic-work\n---\n## Criteria\n- [ ] Fixture criterion\n')
        for source in ('startup','resume'):
            active=self.call(root,environment,'hooks/LoadContext.hook.ts',{'source':source})
            self.assertEqual(active.returncode,0,active.stderr)
            self.assertIn('Synthetic Active Fixture Work',active.stdout)
        (root/'settings.json').write_text(json.dumps({'dynamicContext':{
            'relationshipContext':False,'learningReadback':False,'advisoryReadback':False,'activeWorkSummary':False}}))
        disabled=self.call(root,environment,'hooks/LoadContext.hook.ts')
        self.assertEqual(disabled.returncode,0)
        self.assertNotIn('Synthetic Active Fixture Work',disabled.stdout)
        (root/'settings.json').write_text('{}')
        for phase in ('complete','learn','COMPLETED'):
            isa.write_text('---\ntitle: Synthetic Active Fixture Work\nphase: '+phase+'\n---\n')
            terminal=self.call(root,environment,'hooks/LoadContext.hook.ts')
            self.assertEqual(terminal.returncode,0)
            self.assertNotIn('Synthetic Active Fixture Work',terminal.stdout)

    def test_actual_doc_handler_detects_broken_refs_and_repairs_count_without_teardown_inference(self):
        _,root,environment=self.fixture()
        docs=root/'LIFEOS/DOCUMENTATION/Hooks';docs.mkdir(parents=True)
        document=docs/'HookSystem.md'
        document.write_text('**Status:** Production - 999 hooks active\nMissingFixture.hook.ts\n')
        changed=root/'hooks/HookHealer.hook.ts'
        transcript=root/'transcript.jsonl'
        transcript.write_text(json.dumps({'type':'assistant','message':{'content':[{
            'type':'tool_use','id':'observed-change','name':'Edit','input':{'file_path':str(changed),
                'old_string':'synthetic before','new_string':'synthetic after'}}]}})+'\n')
        driver=root/'doc-control.ts'
        driver.write_text('import {handleDocCrossRefIntegrity} from '+json.dumps(str(Path(SOURCE)/'hooks/handlers/DocCrossRefIntegrity.ts'))+';\n'
            'await handleDocCrossRefIntegrity({} as any,'+json.dumps({'session_id':'docs','hook_event_name':'SessionEnd','transcript_path':str(transcript)})+');\n')
        result=subprocess.run(['bun',str(driver)],env=environment,text=True,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('MissingFixture.hook.ts',result.stderr)
        self.assertIn('[UPDATED] Updated hook count',result.stderr)
        self.assertIn('[INFERENCE] Skipped on SessionEnd',result.stderr)
        count=len(list((Path(SOURCE)/'hooks').rglob('*.hook.ts')))
        self.assertIn(str(count)+' hooks active',document.read_text())
        previous=document.read_bytes()
        with ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(lambda _:subprocess.run(['bun',str(driver)],env=environment,text=True,capture_output=True,timeout=15),range(8)))
        self.assertTrue(all(r.returncode==0 and '[UPDATED]' not in r.stderr for r in results),results)
        self.assertEqual(document.read_bytes(),previous)

    def test_merge_array_ownership_malformed_source_concurrency_and_deleted_live_output(self):
        _,root,environment=self.fixture()
        system=root/'settings.system.json';user=root/'settings.user.json';output=root/'settings.json'
        system.write_text(json.dumps({'env':{'SYSTEM':'retained'},'permissions':{'deny':['Read(./synthetic-secret)']},'items':['system']}))
        user.write_text(json.dumps({'env':{'USER':'overlay'},'permissions':{'deny':[]},
            'items':{'__merge':'append','values':['user']}}))
        args=('--system',str(system),'--user',str(user),'--output',str(output))
        first=self.call(root,environment,'LIFEOS/TOOLS/MergeSettings.ts',arguments=args)
        self.assertEqual(first.returncode,0,first.stderr)
        self.assertIn('no-opinion',first.stderr)
        merged=json.loads(output.read_text())
        self.assertEqual(merged['permissions']['deny'],['Read(./synthetic-secret)'])
        self.assertEqual(merged['items'],['system','user'])
        self.assertEqual(merged['env'],{'SYSTEM':'retained','USER':'overlay'})
        prior=output.read_bytes()
        user.write_text('{invalid')
        invalid=self.call(root,environment,'LIFEOS/TOOLS/MergeSettings.ts',arguments=args)
        self.assertNotEqual(invalid.returncode,0)
        self.assertTrue(invalid.stderr)
        self.assertEqual(output.read_bytes(),prior)
        user.write_text(json.dumps({'env':{'USER':'overlay'},'items':['user']}))
        output.unlink()
        with ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(lambda _:self.call(root,environment,'LIFEOS/TOOLS/MergeSettings.ts',arguments=args),range(8)))
        self.assertTrue(all(r.returncode==0 for r in results),results)
        self.assertEqual(json.loads(output.read_text())['items'],['user'])
        self.assertEqual(json.loads((root/'LIFEOS/MEMORY/STATE/settings-merge-snapshot.json').read_text()),json.loads(output.read_text()))
        self.assertEqual(list(root.glob('settings.json.tmp.*')),[])

    def test_isa_first_authoring_missing_completed_resumed_and_newer_mirror(self):
        _,root,environment=self.fixture()
        state=root/'LIFEOS/MEMORY/STATE/isa-render-debounce';state.mkdir()
        pending=state/'render.json'
        work=root/'LIFEOS/MEMORY/WORK/fixture';work.mkdir(parents=True)
        isa=work/'ISA.md';page=work/'ISA.html'
        payload={'hook_event_name':'Stop','session_id':'render'}
        absent=self.call(root,environment,'hooks/ISARenderOnStop.hook.ts',payload)
        self.assertEqual((absent.returncode,json.loads(absent.stdout)),(0,{'continue':True}))
        for metadata,eligible in [('phase: climbing\niteration: 1',False),('phase: complete',True),('phase: climbing\niteration: 2',True)]:
            isa.write_text('---\ntitle: Synthetic Render Fixture\n'+metadata+'\nprogress: 1/1\n---\n## Criteria\n- [x] Fixture criterion\n')
            page.unlink(missing_ok=True)
            pending.write_text(json.dumps({'edited_isas':[str(isa),str(work/'missing/ISA.md')]}))
            result=self.call(root,environment,'hooks/ISARenderOnStop.hook.ts',payload)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertFalse(pending.exists())
            rows=[json.loads(line) for line in (root/'LIFEOS/MEMORY/OBSERVABILITY/isa-render.jsonl').read_text().splitlines()]
            self.assertIn(str(work/'missing/ISA.md')+':missing',rows[-1]['skipped'])
            if not eligible:
                self.assertIn(str(isa)+':pre-completion',rows[-1]['skipped'])
                self.assertFalse(page.exists())
            else:
                deadline=time.monotonic()+8
                while not page.exists() and time.monotonic()<deadline:time.sleep(.02)
                self.assertTrue(page.exists(),'The actual detached native renderer did not create its mirror')
                self.assertIn('Synthetic Render Fixture',page.read_text())
                self.assertEqual(rows[-1]['rendered'],[str(isa)])
        time.sleep(.1)
        previous=page.read_bytes()
        os.utime(page,(time.time()+60,time.time()+60))
        pending.write_text(json.dumps({'edited_isas':[str(isa)]}))
        newer=self.call(root,environment,'hooks/ISARenderOnStop.hook.ts',payload)
        self.assertEqual(newer.returncode,0)
        time.sleep(.2)
        self.assertEqual(page.read_bytes(),previous)
