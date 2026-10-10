# ABOUTME: Exercises selected owner Content disposal through actual native authenticated HTTP.
# ABOUTME: Requires fixed inbox movement, selected artifact removal, and ledger tombstones.
import json
import os
import importlib
import subprocess
import sys
from lifeos_hook_bridge.memory_access import NativeMemory
from pathlib import Path
import unittest
import httpx
import test_memory_content as fixture


class MemoryContentDisposalTests(unittest.TestCase):
    native_module='content.ts'
    create_fixture=fixture.MemoryContentTests.create_fixture
    stop_dashboard=fixture.MemoryContentTests.stop_dashboard
    stop_pulse=fixture.MemoryContentTests.stop_pulse
    login=fixture.MemoryContentTests.login
    setUp=fixture.MemoryContentTests.setUp
    native_module_name=fixture.MemoryContentTests.native_module_name
    seed=fixture.MemoryContentTests.seed

    def test_owner_delete_moves_fixed_inbox_files_and_removes_selected_artifacts(self):
        path,rows=self.seed(count=1)
        source=self.fixture.home/'Recordings/Inbox/synthetic.wav'
        source.parent.mkdir(parents=True)
        original=b'Synthetic selected content media for owner disposal.'
        source.write_bytes(original)
        sidecar=Path(str(source)+'.md')
        sidecar.write_text('title: Synthetic selected content.\n')
        rows[0]['fields']['path']=str(source)
        path.write_text(json.dumps(rows[0])+'\n')
        artifact=self.root/'LIFEOS/MEMORY/STATE/content-pipeline/artifacts/synthetic0/transcript.md'
        artifact.parent.mkdir(parents=True)
        artifact.write_text('Synthetic derivative.\n')
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.delete(self.native+'/api/content/synthetic0')
            self.assertEqual(result.status_code,200,result.text)
            self.assertEqual(result.json(),{'ok':True,'id':'synthetic0','trashed':2,
                'artifactsRemoved':True,'runnerKicked':False})
            board=client.get(self.native+'/api/content')
            self.assertEqual(board.status_code,200,board.text)
            self.assertEqual(board.json()['items'],[])
        self.assertFalse(source.exists())
        self.assertFalse(sidecar.exists())
        self.assertEqual((source.parent/'.trash'/source.name).read_bytes(),original)
        self.assertFalse(artifact.parent.exists())


    def disposal_fixture(self):
        ledger,rows=self.seed(count=1)
        source=self.fixture.home/'Recordings/Inbox/synthetic.wav'
        source.parent.mkdir(parents=True)
        source.write_bytes(b'Synthetic governed media bytes.\n')
        sidecar=Path(str(source)+'.md')
        sidecar.write_text('Synthetic governed sidecar.\n')
        rows[0]['fields']['path']=str(source)
        ledger.write_text(json.dumps(rows[0])+'\n')
        artifact=self.root/'LIFEOS/MEMORY/STATE/content-pipeline/artifacts/synthetic0/transcript.md'
        artifact.parent.mkdir(parents=True)
        artifact.write_text('Synthetic governed derivative.\n')
        return ledger,rows,source,sidecar,artifact

    def delete(self,id='synthetic0'):
        with httpx.Client(timeout=45) as client:
            self.login(client)
            return client.delete(self.native+'/api/content/'+id)

    def test_repeat_delete_returns_missing_without_appending_or_touching_other_items(self):
        ledger,rows,source,sidecar,artifact=self.disposal_fixture()
        before=ledger.read_bytes()
        result=self.delete()
        self.assertEqual(result.status_code,200,result.text)
        after=ledger.read_bytes()
        self.assertTrue(after.startswith(before))
        event=json.loads(after[len(before):])
        self.assertEqual({k:v for k,v in event.items() if k!='ts'},
            {'v':1,'id':'synthetic0','op':'delete','src':'dashboard'})
        repeated=self.delete()
        self.assertEqual(repeated.status_code,404,repeated.text)
        self.assertEqual(repeated.json(),{'error':'no item synthetic0'})
        self.assertEqual(ledger.read_bytes(),after)

    def test_existing_trash_preserves_every_file_and_ledger_before_tombstone(self):
        ledger,rows,source,sidecar,artifact=self.disposal_fixture()
        trash=source.parent/'.trash'/source.name
        trash.parent.mkdir()
        trash.write_bytes(b'Synthetic earlier owner trash.\n')
        before=[path.read_bytes() for path in (ledger,source,sidecar,artifact,trash)]
        result=self.delete()
        self.assertEqual(result.status_code,503,result.text)
        self.assertEqual([path.read_bytes() for path in (ledger,source,sidecar,artifact,trash)],before)

    def test_external_source_path_refuses_before_any_effect(self):
        ledger,rows,source,sidecar,artifact=self.disposal_fixture()
        external=self.fixture.home/'synthetic-external.wav'
        external.write_bytes(b'Synthetic external owner media.\n')
        rows[0]['fields']['path']=str(external)
        ledger.write_text(json.dumps(rows[0])+'\n')
        before=ledger.read_bytes()
        result=self.delete()
        self.assertEqual(result.status_code,503,result.text)
        self.assertEqual(ledger.read_bytes(),before)
        self.assertTrue(external.exists())
        self.assertTrue(source.exists())
        self.assertTrue(artifact.exists())

    def test_symlink_or_hardlink_source_refuses_before_tombstone(self):
        for kind in ('symlink','hardlink'):
            with self.subTest(kind=kind):
                if kind=='symlink':ledger,rows,source,sidecar,artifact=self.disposal_fixture()
                else:source.unlink()
                external=self.fixture.home/('synthetic-'+kind+'.wav')
                external.write_bytes(b'Synthetic alias owner media.\n')
                if kind=='symlink':
                    source.unlink()
                    source.symlink_to(external)
                else:os.link(external,source)
                before=ledger.read_bytes()
                result=self.delete()
                self.assertEqual(result.status_code,503,result.text)
                self.assertEqual(ledger.read_bytes(),before)
                self.assertTrue(source.exists())
                self.assertTrue(artifact.exists())

    def test_artifact_symlink_refuses_before_tombstone_or_source_movement(self):
        ledger,rows,source,sidecar,artifact=self.disposal_fixture()
        external=self.fixture.home/'synthetic-external.md'
        external.write_text('Synthetic external artifact.\n')
        artifact.unlink()
        artifact.symlink_to(external)
        before=ledger.read_bytes()
        result=self.delete()
        self.assertEqual(result.status_code,503,result.text)
        self.assertEqual(ledger.read_bytes(),before)
        self.assertTrue(source.exists())
        self.assertEqual(external.read_text(),'Synthetic external artifact.\n')

    def test_excluded_ledger_refuses_disposal_without_revealing_or_moving_media(self):
        ledger,rows,source,sidecar,artifact=self.disposal_fixture()
        rows[0]['fields']['title']='<private>Synthetic excluded Content disposal.</private>'
        ledger.write_text(json.dumps(rows[0])+'\n')
        before=ledger.read_bytes()
        result=self.delete()
        self.assertEqual(result.status_code,503,result.text)
        self.assertNotIn('Synthetic excluded',result.text)
        self.assertEqual(ledger.read_bytes(),before)
        self.assertTrue(source.exists())
        self.assertTrue(artifact.exists())

    def test_missing_media_still_disposes_current_item_and_artifacts(self):
        ledger,rows,source,sidecar,artifact=self.disposal_fixture()
        source.unlink()
        sidecar.unlink()
        result=self.delete()
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json(),{'ok':True,'id':'synthetic0','trashed':0,
            'artifactsRemoved':True,'runnerKicked':False})
        self.assertFalse(artifact.parent.exists())

    def interrupt(self,phase):
        result=subprocess.run([sys.executable,str(Path(__file__).with_name('memory_content_disposal_process.py')),
            str(self.fixture.configuration.path),str(self.root),phase],capture_output=True,text=True,timeout=40,
            env=dict(os.environ,HOME=str(self.fixture.home),HERMES_HOME=str(self.fixture.profile)))
        self.assertEqual((result.returncode,result.stdout,result.stderr),(73,'',''))

    def test_actual_process_exit_after_tombstone_restores_exact_ledger_and_permissions(self):
        ledger,rows,source,sidecar,artifact=self.disposal_fixture()
        ledger.chmod(0o640)
        before=ledger.read_bytes()
        self.interrupt('append')
        self.assertNotEqual(ledger.read_bytes(),before)
        with NativeMemory(self.root)._transaction():pass
        self.assertEqual(ledger.read_bytes(),before)
        self.assertEqual(ledger.stat().st_mode & 0o777,0o640)
        self.assertTrue(source.exists())
        self.assertTrue(sidecar.exists())
        self.assertTrue(artifact.exists())

    def test_actual_process_exit_after_first_move_restores_all_original_bytes(self):
        ledger,rows,source,sidecar,artifact=self.disposal_fixture()
        originals=[p.read_bytes() for p in (ledger,source,sidecar,artifact)]
        self.interrupt('1')
        self.assertFalse(source.exists())
        self.assertTrue(sidecar.exists())
        with NativeMemory(self.root)._transaction():pass
        self.assertEqual([p.read_bytes() for p in (ledger,source,sidecar,artifact)],originals)
        self.assertFalse((source.parent/'.trash'/source.name).exists())

    def test_actual_process_exit_after_all_moves_restores_artifacts_and_source(self):
        ledger,rows,source,sidecar,artifact=self.disposal_fixture()
        originals=[p.read_bytes() for p in (ledger,source,sidecar,artifact)]
        self.interrupt('3')
        self.assertFalse(source.exists())
        self.assertFalse(artifact.parent.exists())
        with NativeMemory(self.root)._transaction():pass
        self.assertEqual([p.read_bytes() for p in (ledger,source,sidecar,artifact)],originals)

    def test_actual_committed_exit_finishes_artifact_cleanup_and_keeps_native_trash(self):
        ledger,rows,source,sidecar,artifact=self.disposal_fixture()
        original=source.read_bytes()
        self.interrupt('committed')
        tombstone=ledger.read_bytes()
        quarantine=ledger.parent/'.disposal'
        self.assertTrue(any(quarantine.iterdir()))
        with NativeMemory(self.root)._transaction():pass
        self.assertEqual(ledger.read_bytes(),tombstone)
        self.assertFalse(source.exists())
        self.assertFalse(artifact.exists())
        self.assertEqual((source.parent/'.trash'/source.name).read_bytes(),original)
        self.assertEqual(list(quarantine.iterdir()),[])

    def test_actual_interruption_preserves_later_ledger_before_any_move_recovery(self):
        from lifeos_hook_bridge.memory_access import MemoryUnavailable
        ledger,rows,source,sidecar,artifact=self.disposal_fixture()
        self.interrupt('3')
        later=ledger.read_bytes()+json.dumps({'v':1,'ts':'2026-10-09T12:00:01Z','id':'synthetic1',
            'op':'upsert','src':'synthetic','fields':{'title':'Synthetic later owner item.'}}).encode()+b'\n'
        ledger.write_bytes(later)
        with self.assertRaises(MemoryUnavailable):
            with NativeMemory(self.root)._transaction():pass
        self.assertEqual(ledger.read_bytes(),later)
        self.assertFalse(source.exists())
        self.assertFalse(artifact.exists())
        self.assertTrue((source.parent/'.trash'/source.name).exists())
        self.assertTrue((ledger.parent.parent/'memory-operation.json').exists())

    def instrument_plan(self,callback):
        self.fixture.login()
        self.fixture.client.get('/api/plugins/lifeos-hook-bridge/memory/pulse/state')
        module=importlib.import_module('lifeos_memory_settings.memory_access')
        original=module.NativeMemory._native
        seen=[]
        def native(memory,action,**values):
            result=original(memory,action,**values)
            if action=='content_delete_plan':
                seen.append(result['status'])
                callback()
            return result
        module.NativeMemory._native=native
        self.addCleanup(setattr,module.NativeMemory,'_native',original)
        return seen

    def test_ledger_change_after_real_native_plan_preserves_all_media(self):
        ledger,rows,source,sidecar,artifact=self.disposal_fixture()
        later=ledger.read_bytes()+json.dumps({'v':1,'ts':'2026-10-09T12:00:01Z','id':'synthetic0',
            'op':'upsert','src':'synthetic','fields':{'title':'Synthetic later disposal item.'}}).encode()+b'\n'
        seen=self.instrument_plan(lambda:ledger.write_bytes(later))
        result=self.delete()
        self.assertEqual(result.status_code,503,result.text)
        self.assertEqual(seen,[200])
        self.assertEqual(ledger.read_bytes(),later)
        self.assertTrue(source.exists())
        self.assertTrue(artifact.exists())

    def test_owner_revocation_after_real_native_plan_refuses_before_tombstone(self):
        ledger,rows,source,sidecar,artifact=self.disposal_fixture()
        before=ledger.read_bytes()
        seen=self.instrument_plan(lambda:self.fixture.configuration.update(
            lambda value:value['accounts'].pop('dashboard:basic:synthetic-owner')))
        result=self.delete()
        self.assertEqual(result.status_code,403,result.text)
        self.assertEqual(seen,[200])
        self.assertEqual(ledger.read_bytes(),before)
        self.assertTrue(source.exists())
        self.assertTrue(artifact.exists())

    def test_live_item_refuses_before_any_effect_until_runner_control_is_governed(self):
        ledger,rows,source,sidecar,artifact=self.disposal_fixture()
        rows[0]['fields'].update(stage_status='running',lease_expires='2099-10-09T12:00:00Z')
        ledger.write_text(json.dumps(rows[0])+'\n')
        before=ledger.read_bytes()
        result=self.delete()
        self.assertEqual(result.status_code,503,result.text)
        self.assertEqual(ledger.read_bytes(),before)
        self.assertTrue(source.exists())
        self.assertTrue(artifact.exists())

    def test_actual_process_exit_during_cleanup_finishes_only_original_remaining_artifacts(self):
        ledger,rows,source,sidecar,artifact=self.disposal_fixture()
        second=artifact.parent/'second.md'
        second.write_text('Synthetic second owner derivative.\n')
        self.interrupt('partial')
        tombstone=ledger.read_bytes()
        directories=list((ledger.parent/'.disposal').iterdir())
        self.assertEqual(len(directories),1)
        self.assertFalse((directories[0]/'transcript.md').exists())
        self.assertTrue((directories[0]/'second.md').exists())
        with NativeMemory(self.root)._transaction():pass
        self.assertFalse(directories[0].exists())
        self.assertEqual(ledger.read_bytes(),tombstone)
        self.assertTrue((source.parent/'.trash'/source.name).exists())
