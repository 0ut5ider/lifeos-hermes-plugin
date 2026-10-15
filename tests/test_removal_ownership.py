# ABOUTME: Checks exact integration ownership before complete software removal preparation.
# ABOUTME: Uses real private mount and release journals to reject changed or foreign programs.
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from optional.lifeos_release_manager.release_programs import ProgramTransaction,publish,fingerprint
from optional.lifeos_release_manager.release_stage import load_bridge


class RemovalOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.home=Path(self.directory.name);self.profile=self.home/'.hermes';self.profile.mkdir(mode=0o700)
        self.installed=self.home/'.claude';self.installed.mkdir(mode=0o700)
        self.bridge=load_bridge(Path(__file__).resolve().parents[1]/'lifeos_hook_bridge')
        self.guard=self.profile/'plugins/lifeos';self.guard.mkdir(parents=True,mode=0o700)
        self.mount=self.profile/'.lifeos-mount';self.mount.mkdir(mode=0o700)
        snapshot=self.mount/('a'*32);snapshot.mkdir(mode=0o700)
        entries=[]
        for index,name in enumerate(('__init__.py','guard.py','plugin.yaml','policy.json')):
            target=self.guard/name;publish(target,('Synthetic guard '+name).encode())
            entries.append({'target':str(target),'before':None,'after':{'digest':hashlib.sha256(target.read_bytes()).hexdigest(),
                'mode':0o600},'copy':index})
        self.manifest={'version':1,'profile':str(self.profile),'installed':str(self.installed),'baseline':str(self.bridge.memory_module('version_drift').default_baseline_path(self.home)),
            'state':'committed','snapshot':str(snapshot),'entries':entries,'absent_directories':[],
            'workspace':str(self.profile/'workspace')}
        publish(self.mount/'operation.json',json.dumps(self.manifest).encode())

    def operation(self):
        from optional.lifeos_release_manager import removal_ownership
        return removal_ownership

    def test_guard_requires_exact_owned_files_and_preserves_unknown_extension(self):
        result=self.operation().guard(self.profile,self.installed,bridge=self.bridge)
        self.assertEqual(result,fingerprint(self.guard))
        extra=self.guard/'owner.py';extra.write_text('# Synthetic owner extension\n')
        with self.assertRaises(ValueError):self.operation().guard(self.profile,self.installed,bridge=self.bridge)
        self.assertTrue(extra.exists())

    def test_guard_refuses_later_edit_pending_mount_or_other_native_binding(self):
        target=self.guard/'guard.py';original=target.read_bytes();target.write_bytes(original+b'changed')
        with self.assertRaises(ValueError):self.operation().guard(self.profile,self.installed,bridge=self.bridge)
        target.write_bytes(original)
        for field,value in [('state','applying'),('installed',str(self.home/'other'))]:
            changed={**self.manifest,field:value};publish(self.mount/'operation.json',json.dumps(changed).encode())
            with self.subTest(field=field),self.assertRaises(ValueError):
                self.operation().guard(self.profile,self.installed,bridge=self.bridge)

    def test_pulse_requires_proven_fresh_creation_and_current_exact_identity(self):
        pulse=self.home/'.config/systemd/user/com.lifeos.pulse.service';pulse.parent.mkdir(parents=True)
        generated=self.home/'generated';generated.mkdir(mode=0o700);source=generated/'pulse';publish(source,b'Synthetic owned Pulse unit')
        job=self.profile/'.lifeos-releases'/('b'*32);job.mkdir(parents=True,mode=0o700);job.parent.chmod(0o700)
        tx=ProgramTransaction(job/'program-snapshot');tx.prepare(directories={},files={pulse:source});tx.apply()
        plan={'fresh':True,'program_entries_sha256':tx.entries_digest()};publish(job/'plan.json',json.dumps(plan).encode())
        publish(job/'request.json',json.dumps({'profile':str(self.profile),'installed':str(self.installed),
            'identifier':job.name,'plan_sha256':hashlib.sha256((job/'plan.json').read_bytes()).hexdigest()}).encode())
        publish(job/'status.json',b'{"state":"applied"}')
        self.assertEqual(self.operation().pulse(self.profile,self.installed),pulse)
        pulse.write_bytes(b'Synthetic later unit edit')
        with self.assertRaises(ValueError):self.operation().pulse(self.profile,self.installed)
        pulse.write_bytes(source.read_bytes())
        publish(job/'plan.json',json.dumps({**plan,'fresh':False}).encode())
        with self.assertRaises(ValueError):self.operation().pulse(self.profile,self.installed)
