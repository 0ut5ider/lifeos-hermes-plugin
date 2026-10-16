# ABOUTME: Checks removal admission against real returned exports and exact private workflow bindings.
# ABOUTME: Uses synthetic verification journals for admission controls, not installed end-to-end acceptance.
import hashlib
import json
from pathlib import Path
import unittest

import test_memory_return as fixture
from optional.lifeos_release_manager.release_programs import publish
from optional.lifeos_release_manager.release_stage import load_bridge


class RemovalPreparationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.MemoryReturnTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.profile=self.fixture.profile;self.configuration=self.fixture.configuration
        self.identifier='c'*32;self.signature='d'*64
        self.source=load_bridge(Path(__file__).resolve().parents[1]/'lifeos_hook_bridge')
        target=self.source.memory_module('memory_import_sources').directory(self.profile,'a'*32)
        target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.fixture.fixture.snapshot.rename(target);self.fixture.fixture.snapshot=target
        self.inner=self.source.memory_module('memory_return').MemoryReturn(self.configuration,operation_id=self.identifier,
            verify_writers=lambda:None)
        self.prepared=self.inner.prepare(self.fixture.fixture.snapshot,self.fixture.export['signature'],
            self.fixture.plan['signature'],prompt='Synthetic reviewed stock prompt.',account='dashboard:owner')
        self.inner.apply(self.fixture.fixture.snapshot,self.prepared['signature'],account='dashboard:owner')
        self.job=self.profile/'.lifeos-portability'/self.identifier;self.job.mkdir(parents=True,mode=0o700)
        self.job.parent.chmod(0o700)
        selected={'kind':'return','identifier':'a'*32,'signature':self.fixture.export['signature'],
            'plan_signature':self.fixture.plan['signature'],'prompt':'Synthetic reviewed stock prompt.'}
        self.request={'version':1,'identifier':self.identifier,'profile':str(self.profile),'owner':'dashboard:owner',
            'bridge':None,'selection':selected}
        publish(self.job/'request.json',json.dumps(self.request).encode())
        self.receipt={'signature':self.signature,'state':'verified','application_verified':True}
        publish(self.job/'review.json',json.dumps({'signature':self.signature,'state':'ready'}).encode())
        publish(self.job/'receipt.json',json.dumps(self.receipt).encode());publish(self.job/'status.json',b'{"state":"verified"}')
        transition=self.profile/'.lifeos-memory-transition';transition.mkdir(mode=0o700)
        units=self.source.memory_module('profile_services').UNITS
        self.plan={'version':1,'profile':str(self.profile),'root':self.configuration.load()['root'],'owner':'dashboard:owner',
            'units':units,'snapshot':str(self.fixture.fixture.snapshot),'return_signature':self.prepared['signature'],
            'services_signature':'e'*64,'original_roles':['gateway','dashboard'],'pulse_enablement':'disabled','operation_id':self.identifier}
        encoded=json.dumps(self.plan,sort_keys=True,separators=(',',':')).encode();self.signature=hashlib.sha256(encoded).hexdigest()
        self.receipt['signature']=self.signature
        publish(self.job/'review.json',json.dumps({'signature':self.signature,'state':'ready'}).encode())
        publish(self.job/'receipt.json',json.dumps(self.receipt).encode())
        publish(transition/'plan.json',encoded)
        publish(transition/'operation.json',json.dumps({'signature':self.signature,'state':'verified'}).encode())

    def returned(self, *, owner='dashboard:owner'):
        from optional.lifeos_release_manager.removal_preparation import returned
        return returned(self.profile,self.identifier,self.signature,owner=owner,source=self.source,configuration=self.configuration)

    def test_verified_return_binds_current_native_export_and_keeps_later_builtin_edits(self):
        path=self.profile/'memories/MEMORY.md';later=path.read_bytes()+b'\nSynthetic later builtin fact.';path.write_bytes(later)
        result=self.returned()
        self.assertEqual(result['native_signature'],self.inner._load(
            self.fixture.fixture.snapshot,self.prepared['signature'],'dashboard:owner')[0]['target_signature'])
        self.assertEqual(path.read_bytes(),later)
        self.assertEqual(result['return_identifier'],self.identifier)

    def test_unverified_or_other_owner_or_changed_signature_refuses(self):
        with self.assertRaises(PermissionError):self.returned(owner='dashboard:other')
        publish(self.job/'status.json',b'{"state":"verification_required"}')
        with self.assertRaises(ValueError):self.returned()
        publish(self.job/'status.json',b'{"state":"verified"}')
        self.receipt['signature']='f'*64;publish(self.job/'receipt.json',json.dumps(self.receipt).encode())
        with self.assertRaises(ValueError):self.returned()

    def test_new_native_fact_requires_a_new_export_before_software_removal(self):
        self.fixture.fixture.native.remember(self.fixture.fixture.scope,category='project',content='Synthetic late native fact.',
            title='Synthetic late fact',project='lab',request_id='late-removal-fact')
        with self.assertRaises(RuntimeError):self.returned()


class RemovalSoftwarePlanTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.home=Path(self.directory.name);self.profile=self.home/'.hermes';self.profile.mkdir(mode=0o700)
        self.installed=self.home/'.claude';self.installed.mkdir(mode=0o700)
        self.generated=self.home/'generated';self.generated.mkdir(mode=0o700)
        self.runtime=self.home/'stock-runtime';(self.runtime/'bin').mkdir(parents=True,mode=0o700)
        self.source=load_bridge(Path(__file__).resolve().parents[1]/'lifeos_hook_bridge')
        publish(self.profile/'config.yaml',b'model: synthetic-model\nmemory: {provider: builtin}\nplugins: {enabled: [lifeos-release-manager]}\n')
        for name,data in [('lifeos-memory.json',b'{}'),('lifeos-installation.json',b'{}'),('integration-release.json',b'{}'),
                          ('memories/MEMORY.md',b'Synthetic later builtin memory'),('SOUL.md',b'Synthetic reviewed prompt')]:
            target=self.profile/name;target.parent.mkdir(parents=True,exist_ok=True,mode=0o700);publish(target,data)
        self.native={'files':{self.installed/'Owned.ts':None},'dependencies':{},'settings':b'{"foreign":"preserved"}\n'}
        publish(self.installed/'Owned.ts',b'Synthetic owned program')
        publish(self.installed/'settings.json',b'{}')
        self.pulse=self.home/'.config/systemd/user/com.lifeos.pulse.service';self.pulse.parent.mkdir(parents=True)
        publish(self.pulse,b'Synthetic owned Pulse service')
        self.generation={'home':self.home,'launchers':{self.home/'.local/bin'/name:None for name in ('hermes','hermes-agent','hermes-acp')},
            'bun':self.home/'.local/bin/bun'}
        for name in ('hermes','hermes-agent','hermes-acp'):publish(self.runtime/'bin'/name,b'#!/bin/sh\nexit 0\n',0o700)
        self.workspace=self.profile/'workspace';self.workspace.mkdir(mode=0o700);publish(self.workspace/'owner.txt',b'Synthetic owner work')
        block=self.source.memory_module('mount_transaction')
        from optional.lifeos_release_manager.removal_configuration import environment_block
        publish(self.profile/'.env',b'SYNTHETIC_KEEP=yes\n'+environment_block(self.profile,self.workspace))

    def plan(self):
        from optional.lifeos_release_manager.removal_preparation import software
        return software(self.profile,self.installed,self.generation,self.native,self.runtime,self.generated,
            workspace=self.workspace,pulse=self.pulse)

    def test_fixed_plan_keeps_data_and_prompt_and_uses_stock_launchers(self):
        directories,files,dependencies,expected=self.plan()
        self.assertEqual(set(directories),{self.profile/'plugins'/name for name in ('lifeos','lifeos-hook-bridge','lifeos-release-manager')})
        self.assertTrue(all(source is None for source in directories.values()))
        self.assertNotIn(self.profile/'SOUL.md',files);self.assertNotIn(self.profile/'memories/MEMORY.md',files)
        self.assertNotIn(self.workspace,files);self.assertNotIn(self.workspace,directories)
        for name in ('lifeos-memory.json','lifeos-installation.json','integration-release.json'):self.assertIsNone(files[self.profile/name])
        self.assertIsNone(files[self.pulse]);self.assertIsNone(files[self.generation['bun']])
        for name in ('hermes','hermes-agent','hermes-acp'):
            text=files[self.home/'.local/bin'/name].read_text()
            self.assertIn(str(self.runtime/'bin'/name),text)
            self.assertEqual(text,'#!/bin/sh\nexec '+str(self.runtime/'bin'/name)+' "$@"\n')
            self.assertEqual(files[self.home/'.local/bin'/name].stat().st_mode & 0o777,0o700)
        self.assertEqual(files[self.profile/'.env'].read_bytes(),b'SYNTHETIC_KEEP=yes\n')
        self.assertEqual((self.profile/'SOUL.md').read_bytes(),b'Synthetic reviewed prompt')
        self.assertEqual((self.workspace/'owner.txt').read_bytes(),b'Synthetic owner work')

    def dependency(self):
        from optional.lifeos_release_manager.release_programs import fingerprint
        root=self.installed/'node_modules';(root/'package').mkdir(parents=True)
        publish(root/'package/tool.js',b'// Synthetic dependency command\n')
        (root/'.bin').mkdir();(root/'.bin/tool').symlink_to('../package/tool.js')
        self.native['dependencies']={root:None}
        self.native['before']={root:fingerprint(root,allow_links=True)}
        return root

    def test_contained_dependency_links_support_actual_removal_and_restore(self):
        from optional.lifeos_release_manager.release_programs import ProgramTransaction,fingerprint
        root=self.dependency();before=fingerprint(root,allow_links=True)
        (self.home/'.local/bin').mkdir(parents=True,mode=0o700)
        memory=self.profile/'memories/MEMORY.md';retained=memory.read_bytes()
        (self.profile/'plugins').mkdir(mode=0o700)
        directories,files,dependencies,expected=self.plan()
        self.assertEqual(expected[root],before)
        tx=ProgramTransaction(self.home/'dependency-transaction')
        tx.prepare(directories=directories,files=files,dependencies=dependencies,expected_before=expected)
        tx.apply();self.assertFalse(root.exists());self.assertEqual(memory.read_bytes(),retained)
        tx.restore();self.assertEqual(fingerprint(root,allow_links=True),before)
        self.assertTrue((root/'.bin/tool').is_symlink());self.assertEqual(memory.read_bytes(),retained)

    def test_dependency_links_outside_selected_tree_still_refuse(self):
        root=self.dependency();link=root/'.bin/tool';link.unlink()
        link.symlink_to(self.workspace/'owner.txt')
        with self.assertRaisesRegex(ValueError,'Dependency links must stay inside'):
            self.plan()
        self.assertEqual((self.workspace/'owner.txt').read_bytes(),b'Synthetic owner work')
        self.assertFalse((self.generated/'config.yaml').exists())

    def test_dependency_edit_after_native_inventory_preserves_later_bytes(self):
        from optional.lifeos_release_manager.release_programs import ProgramTransaction
        root=self.dependency();path=root/'package/tool.js';later=b'// Synthetic later dependency edit\n'
        path.write_bytes(later);(self.profile/'plugins').mkdir(mode=0o700)
        directories,files,dependencies,expected=self.plan()
        tx=ProgramTransaction(self.home/'dependency-conflict')
        with self.assertRaisesRegex(ValueError,'input changes'):
            tx.prepare(directories=directories,files=files,dependencies=dependencies,expected_before=expected)
        self.assertEqual(path.read_bytes(),later);self.assertFalse(tx.journal.exists())

    def test_preparation_requires_explicit_discord_disable_before_any_staging(self):
        from optional.lifeos_release_manager import removal_preparation
        job=self.profile/'.lifeos-portability'/('f'*32)
        for acknowledgement in (False,None,'yes',1):
            with self.subTest(value=acknowledgement),self.assertRaises(ValueError):
                removal_preparation.prepare(self.profile,job,{'kind':'removal','identifier':'a'*32,
                    'signature':'b'*64,'disable_discord':acknowledgement},owner='dashboard:owner',source=self.source,
                    configuration=None)
        self.assertFalse(job.exists())
