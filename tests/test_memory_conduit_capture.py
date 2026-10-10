# ABOUTME: Characterizes native Conduit capture and requires current owner admission for work activity.
# ABOUTME: Runs actual native command processes with synthetic work events and no inference or external adapters.
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import re
import sys
from lifeos_hook_bridge.memory_access import NativeMemory, MemoryUnavailable
from lifeos_hook_bridge.memory_service import MemoryService
from lifeos_hook_bridge import memory_conduit_capture as capture
import unittest

import test_memory_manual_state as fixture


class MemoryConduitCaptureTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.MemoryManualStateTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root
        self.home=self.fixture.fixture.fixture.home
        source=Path(os.environ['LIFEOS_MEMORY_SOURCE'])
        (self.root/'LIFEOS/PULSE').symlink_to(source/'LIFEOS/PULSE',target_is_directory=True)
        self.data=self.root/'LIFEOS/USER/CONDUIT'
        self.data.mkdir(parents=True)
        self.config=self.data/'config.json'
        self.config.write_text(json.dumps({'enabled':True,'pollIntervalSec':120,
            'sources':{'appFocus':False,'git':False,'claudeSession':True,'github':False},
            'repos':[],'retentionDays':30}))
        self.config.chmod(0o600)
        self.work=self.root/'LIFEOS/MEMORY/STATE/work-events.jsonl'
        self.work.parent.mkdir(parents=True,exist_ok=True)
        self.work.write_text(json.dumps({'ts':datetime.now(timezone.utc).isoformat(),
            'slug':'synthetic-hermes-work','type':'work.started'})+'\n')

    def call(self,command='capture',*arguments,original=False,context=True,extra_environment=None):
        source=Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE']) if original else self.root
        environment=dict(os.environ,HOME=str(self.home),CLAUDE_CONFIG_DIR=str(self.root),
            LIFEOS_DIR=str(self.root/'LIFEOS'),BUN_CONFIG_NO_AUTO_INSTALL='1',TZ='UTC')
        for key in ('LIFEOS_MEMORY_INTERNAL','LIFEOS_MEMORY_CONTEXT','LIFEOS_MEMORY_PUBLICATION_JOURNAL'):
            environment.pop(key,None)
        if original:environment['LIFEOS_MEMORY_INTERNAL']='1'
        elif context:environment['LIFEOS_MEMORY_CONTEXT']=json.dumps(asdict(self.fixture.fixture.context))
        if extra_environment:environment.update(extra_environment)
        return subprocess.run(['bun','--no-install',str(source/'LIFEOS/PULSE/Conduit/conduit.ts'),command,*arguments],
            env=environment,capture_output=True,text=True,timeout=40,cwd=self.home)

    def events(self):
        return [json.loads(line) for path in sorted((self.data/'events').glob('*.jsonl'))
            for line in path.read_text().splitlines()]

    def test_original_capture_folds_work_activity_and_repeats_without_duplicate_events(self):
        result=self.call(original=True)
        self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'captured 1 event(s)\n',''))
        rows=self.events()
        self.assertEqual(len(rows),1)
        self.assertEqual({k:v for k,v in rows[0].items() if k!='ts'},
            {'type':'claude-session','source':'claudeSession',
             'detail':{'events':1,'lastSlug':'synthetic-hermes-work'}})
        self.assertEqual(json.loads((self.data/'state.json').read_text())['lastClaudeCursor'],
            json.loads(self.work.read_text())['ts'])
        repeated=self.call(original=True)
        self.assertEqual((repeated.returncode,repeated.stdout,repeated.stderr),(0,'captured 0 event(s)\n',''))
        self.assertEqual(self.events(),rows)

    def test_original_failed_append_advances_cursor_and_loses_activity_known_bug(self):
        blocked=self.data/'events'
        blocked.write_text('Synthetic blocked event directory.\n')
        result=self.call(original=True)
        self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'captured 0 event(s)\n',''))
        state=json.loads((self.data/'state.json').read_text())
        self.assertEqual(state['lastClaudeCursor'],json.loads(self.work.read_text())['ts'])
        blocked.unlink()
        repeated=self.call(original=True)
        self.assertEqual((repeated.returncode,repeated.stdout,repeated.stderr),(0,'captured 0 event(s)\n',''))
        self.assertEqual(self.events(),[])

    def test_unbound_capture_refuses_before_event_or_cursor_publication(self):
        before=self.config.read_bytes()
        result=self.call(context=False)
        self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(self.config.read_bytes(),before)
        self.assertEqual(self.events(),[])
        self.assertFalse((self.data/'state.json').exists())
        self.assertNotIn('synthetic-hermes-work',result.stdout+result.stderr)

    def test_current_owner_capture_keeps_native_event_and_private_publication(self):
        result=self.call()
        self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'captured 1 event(s)\n',''))
        rows=self.events()
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['detail'],{'events':1,'lastSlug':'synthetic-hermes-work'})
        paths=list((self.data/'events').glob('*.jsonl'))+[self.data/'state.json']
        self.assertEqual([path.stat().st_mode & 0o777 for path in paths],[0o600,0o600])

    def test_private_work_event_refuses_capture_and_cursor_publication(self):
        value=json.loads(self.work.read_text())
        value['slug']='<private>Synthetic excluded Hermes activity.</private>'
        self.work.write_text(json.dumps(value)+'\n')
        result=self.call()
        self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertNotIn('Synthetic excluded',result.stdout+result.stderr)
        self.assertEqual(self.events(),[])
        self.assertFalse((self.data/'state.json').exists())

    def test_limited_writer_cannot_publish_capture_or_advance_cursor(self):
        configuration=self.fixture.fixture.configuration
        configuration.update(lambda value:value['destinations']['chat-a:200'].update(write=['project']))
        result=self.call()
        self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(self.events(),[])
        self.assertFalse((self.data/'state.json').exists())

    def test_current_status_and_existing_init_preserve_actual_native_stdout(self):
        for command in ('status','init'):
            with self.subTest(command=command):
                original=self.call(command,original=True)
                current=self.call(command)
                self.assertEqual((original.returncode,original.stderr),(0,''))
                self.assertEqual((current.returncode,current.stdout,current.stderr),
                    (0,original.stdout,''))

    def test_unbound_status_and_rollup_refuse_without_disclosure_or_publication(self):
        for command in ('status','today','rollup','init'):
            with self.subTest(command=command):
                before=self.config.read_bytes()
                result=self.call(command,context=False)
                self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertNotIn('synthetic-hermes-work',result.stdout+result.stderr)
                self.assertEqual(self.config.read_bytes(),before)
                self.assertFalse((self.data/'state.json').exists())
                self.assertFalse((self.data/'daily').exists())

    def seed_event(self,date):
        path=self.data/'events'/(date+'.jsonl')
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps({'ts':date+'T12:00:00Z','type':'app-focus','source':'synthetic',
            'app':'Terminal','detail':{'intervalSec':120}})+'\n')
        return path

    def without_generated_time(self,value):
        return re.sub(r'generated [0-9TZ:.+-]+','generated <native-time>',value)

    def test_current_today_and_selected_rollup_preserve_actual_native_markdown_and_records(self):
        date=datetime.now(timezone.utc).strftime('%Y-%m-%d')
        self.seed_event(date)
        original=self.call('today',original=True)
        current=self.call('today')
        self.assertEqual((original.returncode,original.stderr),(0,''))
        self.assertEqual((current.returncode,current.stderr),(0,''))
        self.assertEqual(self.without_generated_time(current.stdout),self.without_generated_time(original.stdout))
        original=self.call('rollup',date,original=True)
        before=json.loads((self.data/'daily'/(date+'.json')).read_text())
        current=self.call('rollup',date)
        self.assertEqual((current.returncode,current.stderr),(0,''))
        self.assertEqual(self.without_generated_time(current.stdout),self.without_generated_time(original.stdout))
        after=json.loads((self.data/'daily'/(date+'.json')).read_text())
        before.pop('generatedAt');after.pop('generatedAt')
        self.assertEqual(after,before)
        self.assertEqual([(self.data/'daily'/(date+suffix)).stat().st_mode & 0o777 for suffix in ('.json','.md')],
            [0o600,0o600])
        self.assertEqual((self.data/'state.json').stat().st_mode & 0o777,0o600)

    def test_capture_rolls_up_old_events_before_native_retention_removes_them(self):
        old=self.seed_event('2000-01-01')
        original=old.read_bytes()
        result=self.call()
        self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'captured 1 event(s)\n',''))
        self.assertFalse(old.exists())
        record=json.loads((self.data/'daily/2000-01-01.json').read_text())
        self.assertEqual(record['date'],'2000-01-01')
        self.assertTrue((self.data/'daily/2000-01-01.md').exists())
        state=json.loads((self.data/'state.json').read_text())
        self.assertEqual(state['lastRollupDate'],'2000-01-01')
        self.assertEqual(len(self.events()),1)
        self.assertTrue(original)

    def test_disabled_capture_keeps_native_idle_behavior_without_reading_excluded_activity(self):
        value=json.loads(self.config.read_text());value['enabled']=False
        self.config.write_text(json.dumps(value))
        self.work.write_text(json.dumps({'ts':'2026-10-09T12:00:00Z',
            'slug':'<private>Synthetic excluded idle activity.</private>'})+'\n')
        blocked=self.data/'events';blocked.write_text('Synthetic unused event directory.\n')
        before=(self.config.read_bytes(),self.work.read_bytes(),blocked.read_bytes())
        result=self.call()
        self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'captured 0 event(s)\n',''))
        self.assertEqual((self.config.read_bytes(),self.work.read_bytes(),blocked.read_bytes()),before)
        self.assertFalse((self.data/'state.json').exists())

    def test_optional_capture_sources_refuse_before_any_file_or_external_command(self):
        for source in ('appFocus','git','github'):
            with self.subTest(source=source):
                value=json.loads(self.config.read_text());value['sources'][source]=True
                self.config.write_text(json.dumps(value))
                before=self.config.read_bytes()
                result=self.call()
                self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertEqual(self.events(),[])
                self.assertFalse((self.data/'state.json').exists())
                self.assertEqual(self.config.read_bytes(),before)
                value['sources'][source]=False;self.config.write_text(json.dumps(value))

    def test_foreign_claude_root_environment_cannot_redirect_managed_capture(self):
        foreign=self.home/'synthetic-foreign-root'
        result=self.call(extra_environment={'CLAUDE_CONFIG_DIR':str(foreign)})
        self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'captured 1 event(s)\n',''))
        self.assertEqual(len(self.events()),1)
        self.assertFalse(foreign.exists())

    def after_native(self,callback):
        original=capture._execute
        observed=[]
        def execute(*arguments):
            result=original(*arguments)
            observed.append(result)
            callback()
            return result
        capture._execute=execute
        self.addCleanup(setattr,capture,'_execute',original)
        return observed

    def service(self):
        return MemoryService(self.fixture.fixture.configuration).native(self.fixture.fixture.context,
            'conduit_command',{'command':'capture','date':None})

    def test_later_work_change_after_actual_execution_preserves_all_owner_files(self):
        later=self.work.read_bytes()+json.dumps({'ts':'2099-10-09T12:00:00Z',
            'slug':'synthetic-later-work'}).encode()+b'\n'
        observed=self.after_native(lambda:self.work.write_bytes(later))
        result=self.service()
        self.assertFalse(result['ok'],result)
        self.assertEqual(observed,['captured 1 event(s)\n'])
        self.assertEqual(self.work.read_bytes(),later)
        self.assertEqual(self.events(),[])
        self.assertFalse((self.data/'state.json').exists())

    def test_owner_revocation_after_actual_execution_preserves_all_owner_files(self):
        observed=self.after_native(lambda:self.fixture.fixture.configuration.update(
            lambda value:value['accounts'].pop('chat-a:100')))
        result=self.service()
        self.assertFalse(result['ok'],result)
        self.assertEqual(observed,['captured 1 event(s)\n'])
        self.assertEqual(self.events(),[])
        self.assertFalse((self.data/'state.json').exists())

    def test_isolated_native_command_inherits_the_callers_process_group(self):
        original=capture.subprocess.Popen
        observed=[]
        def start(arguments,*values,**options):
            process=original(arguments,*values,**options)
            if isinstance(arguments,list) and any(str(value).endswith('/Conduit/conduit.ts') for value in arguments):
                observed.append((os.getpgid(process.pid),os.getpgrp()))
            return process
        capture.subprocess.Popen=start
        self.addCleanup(setattr,capture.subprocess,'Popen',original)
        result=self.service()
        self.assertTrue(result['ok'],result)
        self.assertEqual(len(observed),1)
        self.assertEqual(observed[0][0],observed[0][1])

    def interrupt(self,phase):
        temporary=self.home/'synthetic-native-temporary'
        temporary.mkdir(exist_ok=True,mode=0o700)
        result=subprocess.run([sys.executable,str(Path(__file__).with_name('memory_conduit_capture_process.py')),
            str(self.fixture.fixture.configuration.path),str(self.root),
            json.dumps(asdict(self.fixture.fixture.context)),phase],capture_output=True,text=True,timeout=40,
            env=dict(os.environ,HOME=str(self.home),TMPDIR=str(temporary)))
        self.assertEqual((result.returncode,result.stdout,result.stderr),(73,'',''))

    def test_actual_exit_after_event_publication_keeps_cursor_unadvanced_and_recovers_event(self):
        work=self.work.read_bytes()
        config=self.config.read_bytes()
        self.interrupt('events')
        self.assertEqual(len(self.events()),1)
        self.assertFalse((self.data/'state.json').exists())
        with NativeMemory(self.root)._transaction():pass
        self.assertEqual(self.events(),[])
        self.assertFalse((self.data/'state.json').exists())
        self.assertEqual(self.config.read_bytes(),config)
        self.assertEqual(self.work.read_bytes(),work)

    def test_actual_exit_after_retention_deletion_restores_all_original_owner_files(self):
        old=self.seed_event('2000-01-01')
        old.chmod(0o640)
        original=old.read_bytes()
        self.interrupt('prune')
        self.assertFalse(old.exists())
        with NativeMemory(self.root)._transaction():pass
        self.assertEqual(old.read_bytes(),original)
        self.assertEqual(old.stat().st_mode & 0o777,0o640)
        self.assertFalse((self.data/'daily/2000-01-01.json').exists())
        self.assertFalse((self.data/'daily/2000-01-01.md').exists())
        self.assertFalse((self.data/'state.json').exists())
        self.assertEqual(len(self.events()),1)

    def test_actual_committed_exit_keeps_native_event_record_and_retention_effects(self):
        old=self.seed_event('2000-01-01')
        self.interrupt('committed')
        self.assertFalse(old.exists())
        before={str(path.relative_to(self.data)):path.read_bytes() for path in self.data.rglob('*') if path.is_file()}
        with NativeMemory(self.root)._transaction():pass
        after={str(path.relative_to(self.data)):path.read_bytes() for path in self.data.rglob('*') if path.is_file()}
        self.assertEqual(after,before)
        self.assertEqual(len(self.events()),1)
        self.assertTrue((self.data/'daily/2000-01-01.json').exists())
        self.assertFalse((self.root/'LIFEOS/MEMORY/STATE/memory-operation.json').exists())

    def test_later_owner_recreation_after_retention_exit_blocks_all_recovery(self):
        old=self.seed_event('2000-01-01')
        self.interrupt('prune')
        later=json.dumps({'ts':'2000-01-01T12:00:01Z','type':'app-focus','source':'synthetic',
            'app':'Synthetic later owner activity','detail':{'intervalSec':60}}).encode()+b'\n'
        old.write_bytes(later)
        daily=(self.data/'daily/2000-01-01.json').read_bytes()
        with self.assertRaises(MemoryUnavailable):
            with NativeMemory(self.root)._transaction():pass
        self.assertEqual(old.read_bytes(),later)
        self.assertEqual((self.data/'daily/2000-01-01.json').read_bytes(),daily)
        self.assertTrue((self.root/'LIFEOS/MEMORY/STATE/memory-operation.json').exists())
