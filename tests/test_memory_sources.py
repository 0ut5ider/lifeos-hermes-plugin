# ABOUTME: Tests governed native learning readback and retained source exclusions.
# ABOUTME: Uses real native readers and checks permissions before source text reaches their output.
from dataclasses import replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import unittest

from lifeos_hook_bridge.memory_service import MemoryService
import test_memory_delegation as delegation_fixture
import test_memory_native as native_fixture


class MemorySourceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation_fixture.MemoryDelegationTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.memory = self.fixture.fixture.memory
        self.service = MemoryService(self.fixture.configuration)

    def source(self, relative, content):
        path = self.fixture.root / 'LIFEOS/MEMORY' / relative
        path.parent.mkdir(parents=True,exist_ok=True); path.write_text(content)
        return path

    def reader(self, function, *, managed=True, context=True, library='learning-readback.ts'):
        if not managed:
            (self.fixture.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        from dataclasses import asdict
        environment = dict(os.environ,HOME=str(self.fixture.fixture.home),LIFEOS_DIR=str(self.fixture.root/'LIFEOS'),BUN_CONFIG_NO_AUTO_INSTALL='1',TZ='UTC')
        environment.pop('LIFEOS_MEMORY_INTERNAL',None); environment.pop('LIFEOS_MEMORY_CONTEXT',None)
        if context: environment['LIFEOS_MEMORY_CONTEXT']=json.dumps(asdict(self.fixture.context))
        module = self.fixture.root/'hooks/lib'/library
        script = "const m=await import(process.argv[1]);console.log(JSON.stringify(m[process.argv[2]](process.argv[3])))"
        result = subprocess.run(['bun','--no-install','-e',script,str(module),function,str(self.fixture.root/'LIFEOS')],
                                env=environment,capture_output=True,text=True,timeout=45)
        self.assertEqual(result.returncode,0,result.stderr); self.assertEqual(result.stderr,'')
        return json.loads(result.stdout)

    def test_unmanaged_wisdom_reader_keeps_native_behavior(self):
        self.source('WISDOM/FRAMES/synthetic.md','### Synthetic native wisdom marker [CRYSTAL: 95%]\n')
        self.assertIn('Synthetic native wisdom marker',self.reader('loadWisdomFrames',managed=False))

    def startup(self):
        from dataclasses import asdict
        environment = dict(os.environ,HOME=str(self.fixture.fixture.home),LIFEOS_DIR=str(self.fixture.root/'LIFEOS'),
                           LIFEOS_NOTIFICATION_CHANNEL='desktop',LIFEOS_MEMORY_CONTEXT=json.dumps(asdict(self.fixture.context)))
        for name in ('LIFEOS_MEMORY_INTERNAL','CLAUDE_PLUGIN_ROOT','CLAUDE_AGENT_TYPE','CLAUDE_CODE_SUBAGENT_NAME',
                     'CLAUDE_CODE_SUBAGENT_TYPE','CLAUDE_CODE_FORK_SUBAGENT','CLAUDE_AGENT_SDK'):
            environment.pop(name,None)
        result = subprocess.run(['bun','--no-install',str(self.fixture.root/'hooks/LoadContext.hook.ts')],
                                input='{}',env=environment,capture_output=True,text=True,timeout=45)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotIn('Error in LoadContext',result.stderr)
        return result.stdout

    def test_native_startup_keeps_allowed_relationship_and_work_context(self):
        now = datetime.now(timezone.utc)
        self.source('RELATIONSHIP/'+now.strftime('%Y-%m/%Y-%m-%d.md'),'- Synthetic current relationship marker\n')
        self.source('STATE/progress/synthetic-progress.json',json.dumps({'project':'Synthetic current work marker','status':'active',
                    'updated':now.isoformat(),'objectives':['Synthetic current objective'],'next_steps':[], 'handoff_notes':''}))
        output = self.startup()
        self.assertIn('Synthetic current relationship marker',output)
        self.assertIn('Synthetic current work marker',output)

    def test_native_startup_excludes_forgotten_relationship_and_work_text(self):
        marker = 'Synthetic forgotten startup marker'
        saved = self.memory.remember(native_fixture.OWNER,category='principal',content='RULE: '+marker,
                                     title='',project='',request_id='startup-marker')
        self.memory.forget(native_fixture.OWNER,saved['reference'],'forget-startup')
        now = datetime.now(timezone.utc)
        self.source('RELATIONSHIP/'+now.strftime('%Y-%m/%Y-%m-%d.md'),'- '+marker+'\n')
        self.source('STATE/progress/synthetic-progress.json',json.dumps({'project':marker,'status':'active',
                    'updated':now.isoformat(),'objectives':[],'next_steps':[],'handoff_notes':''}))
        output = self.startup()
        self.assertNotIn(marker,output)

    def advisory(self, detail):
        (self.fixture.root/'LIFEOS/MEMORY/STATE/advisory-readback.json').unlink(missing_ok=True)
        event = {'type':'doc.integrity.memory_dir','source':'synthetic','timestamp':datetime.now(timezone.utc).isoformat(),
                 'ok':False,'findings':[{'key':'synthetic-finding','detail':detail}],'finding_count':1}
        self.source('STATE/events.jsonl',json.dumps(event)+'\n')
        return self.reader('loadAdvisoryDigest',library='advisory-readback.ts')

    def test_native_advisory_keeps_valid_findings_without_restoring_forgotten_text(self):
        self.assertIn('Synthetic current advisory marker',self.advisory('Synthetic current advisory marker'))
        saved = self.memory.remember(native_fixture.OWNER,category='principal',content='RULE: Synthetic forgotten advisory marker',
                                     title='',project='',request_id='advisory-marker')
        self.memory.forget(native_fixture.OWNER,saved['reference'],'forget-advisory')
        self.assertIsNone(self.advisory('Synthetic forgotten advisory marker'))

    def test_native_advisory_excludes_private_markup_and_missing_authority(self):
        self.assertIsNone(self.advisory('<private>SYNTHETIC_DENIED_ADVISORY</private>'))
        self.source('STATE/events.jsonl',json.dumps({'type':'doc.integrity.memory_dir','source':'synthetic',
                    'timestamp':datetime.now(timezone.utc).isoformat(),'findings':[{'key':'missing','detail':'Synthetic unbound advisory'}]})+'\n')
        self.assertIsNone(self.reader('loadAdvisoryDigest',library='advisory-readback.ts',context=False))

    def test_work_filename_fallback_cannot_restore_a_forgotten_title(self):
        marker = 'Synthetic forgotten work title marker'
        saved = self.memory.remember(native_fixture.OWNER,category='principal',content='RULE: '+marker,
                                     title='',project='',request_id='work-title')
        self.memory.forget(native_fixture.OWNER,saved['reference'],'forget-work-title')
        self.source('WORK/'+datetime.now().strftime('%Y%m%d-%H%M%S_')+marker.replace(' ','-')+'/ISA.md','phase: build\n')
        self.assertNotIn(marker,self.startup())

    def test_advisory_reader_cannot_follow_a_source_redirect_into_configuration(self):
        marker = 'SYNTHETIC_CONFIG_ONLY_ADVISORY_MARKER'
        secret = self.fixture.root/'LIFEOS/USER/CONFIG/synthetic-secret.jsonl'
        secret.write_text(json.dumps({'type':'doc.integrity.memory_dir','source':'synthetic',
                          'timestamp':datetime.now(timezone.utc).isoformat(),'findings':[{'key':'synthetic','detail':marker}]})+'\n')
        events = self.source('STATE/events.jsonl','')
        events.unlink(); events.symlink_to(secret)
        self.assertIsNone(self.reader('loadAdvisoryDigest',library='advisory-readback.ts'))

    def test_decoded_json_strings_cannot_restore_normalized_forgotten_claims(self):
        marker = 'Synthetic forgotten escaped marker'
        saved = self.memory.remember(native_fixture.OWNER,category='principal',content='RULE: '+marker,
                                     title='',project='',request_id='escaped')
        self.memory.forget(native_fixture.OWNER,saved['reference'],'forget-escaped')
        encoded = marker.replace('forgotten ','forgotten\n')
        self.assertIsNone(self.advisory(encoded))
        self.source('STATE/progress/synthetic-progress.json',json.dumps({'project':encoded,'status':'active',
                    'updated':datetime.now(timezone.utc).isoformat(),'objectives':[],'next_steps':[],'handoff_notes':''}))
        self.assertNotIn(marker,' '.join(self.startup().split()))

    def test_allowed_source_uses_installed_path_and_current_policy(self):
        path = self.source('LEARNING/SYSTEM/2026-09/synthetic.md','Synthetic permitted source marker\n')
        result = self.service.native(self.fixture.context,'read_source',{'path':str(path)})
        self.assertTrue(result['ok'],result)
        self.assertEqual(result['content'],path.read_text())
        self.assertTrue(result['historical'])
        unknown = replace(self.fixture.context,author='unknown')
        denied = self.service.native(unknown,'read_source',{'path':str(path)})
        self.assertFalse(denied['ok'],denied)
        self.assertNotIn('permitted source',str(denied))

    def test_source_paths_cannot_read_credentials_or_intra_user_symlinks(self):
        target = self.fixture.root/'LIFEOS/USER/CONFIG/synthetic-secret.env'
        target.write_text('SYNTHETIC_SOURCE_SECRET=denied\n')
        link = self.source('LEARNING/SYSTEM/2026-09/link.md','')
        link.unlink(); link.symlink_to(target)
        for path in (target,link):
            result = self.service.native(self.fixture.context,'read_source',{'path':str(path)})
            self.assertFalse(result['ok'],result)
            self.assertNotIn('SYNTHETIC_SOURCE_SECRET',str(result))

    def test_native_wisdom_reader_excludes_exact_forgotten_claims(self):
        marker = 'Synthetic forgotten wisdom marker'
        saved = self.memory.remember(native_fixture.OWNER,category='principal',content='RULE: '+marker,
                                     title='',project='',request_id='wisdom')
        self.memory.forget(native_fixture.OWNER,saved['reference'],'forget-wisdom')
        self.source('WISDOM/FRAMES/synthetic.md',f'### {marker} [CRYSTAL: 95%]\n')
        self.assertIsNone(self.reader('loadWisdomFrames'))

    def test_native_wisdom_reader_excludes_private_markup_and_unknown_context(self):
        path = self.source('WISDOM/FRAMES/synthetic.md','### <private>SYNTHETIC_DENIED_WISDOM</private> [CRYSTAL: 95%]\n')
        self.assertIsNone(self.reader('loadWisdomFrames'))
        path.write_text('### Synthetic permitted wisdom [CRYSTAL: 95%]\n')
        self.assertIsNone(self.reader('loadWisdomFrames',context=False))
        self.assertIn('Synthetic permitted wisdom',self.reader('loadWisdomFrames'))

    def test_restricted_project_context_cannot_read_unclassified_source_history(self):
        path = self.source('LEARNING/SYSTEM/2026-09/owner.md','Synthetic owner source history marker\n')
        config = self.fixture.configuration.load()
        config['destinations']['chat-a:200'].update(read=['project'],projects=['lab'])
        self.fixture.configuration.save(config)
        result = self.service.native(self.fixture.context,'read_source',{'path':str(path)})
        self.assertFalse(result['ok'],result)
        self.assertNotIn('owner source history',str(result))

    def test_every_learning_reader_excludes_retained_claims_before_extracting_summaries(self):
        marker = 'Synthetic retained source marker'
        saved = self.memory.remember(native_fixture.OWNER,category='principal',content='RULE: '+marker,
                                     title='',project='',request_id='retained')
        self.memory.forget(native_fixture.OWNER,saved['reference'],'forget-retained')
        now = datetime.now(timezone.utc)
        filename = now.strftime('%Y-%m-%d-%H%M%S_LEARNING_synthetic.md')
        self.source('LEARNING/SYSTEM/'+now.strftime('%Y-%m/')+filename,f'**Feedback:** {marker}\nrating: 9\n')
        self.source('LEARNING/FAILURES/2026-09/synthetic/CONTEXT.md',f'**Summary:** {marker}\n')
        self.source('LEARNING/SYNTHESIS/2026-09/2026-09-30_weekly-patterns.md',f'**Average Rating:** 9/10\n## Top Issues\n1. {marker}\n')
        self.source('STATE/learning-cache.sh',f"today_avg='{marker}'\n")
        for function in ('loadLearningDigest','loadFailurePatterns','loadSynthesisPatterns','loadSignalTrends'):
            with self.subTest(function=function):
                self.assertIsNone(self.reader(function))


if __name__ == '__main__':
    unittest.main()
