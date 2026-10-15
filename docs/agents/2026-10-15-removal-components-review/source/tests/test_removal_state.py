# ABOUTME: Checks retained owner authority after complete software removal deletes active configuration.
# ABOUTME: Rejects changed recovery sources and preserves a later live owner revocation.
import hashlib
import json
from pathlib import Path
import shutil
import unittest

import test_memory_export as fixture

from optional.lifeos_release_manager.release_programs import publish


class RemovalStateTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.MemoryExportTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.profile=self.fixture.profile;self.configuration=self.fixture.configuration
        self.configuration.update(lambda value:value.update(ownership_enabled=False))
        self.job=self.profile/'.lifeos-portability'/('a'*32);self.stage=self.job/'removal'
        self.stage.mkdir(parents=True,mode=0o700)
        self.job.chmod(0o700);self.job.parent.chmod(0o700)
        repo=Path(__file__).resolve().parents[1]
        for name,source in [('recovery-bridge',repo/'lifeos_hook_bridge'),('recovery-manager',repo/'optional/lifeos_release_manager')]:
            shutil.copytree(source,self.stage/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        def files(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
        self.policy=json.dumps(self.configuration.load(),sort_keys=True,separators=(',',':')).encode();publish(self.stage/'owner-policy.json',self.policy)
        self.plan={'format':1,'profile':str(self.profile),'identifier':self.job.name,'root':self.configuration.load()['root'],
            'owner':'dashboard:owner','owner_policy_sha256':hashlib.sha256(self.policy).hexdigest(),
            'bridge_files':files(self.stage/'recovery-bridge'),'manager_files':files(self.stage/'recovery-manager')}
        data=json.dumps(self.plan,sort_keys=True,separators=(',',':')).encode();self.signature=hashlib.sha256(data).hexdigest()
        publish(self.stage/'plan.json',data)
        publish(self.profile/'.lifeos-removal.json',json.dumps({'format':1,'workflow':self.job.name,'signature':self.signature}).encode())

    def operation(self):
        from optional.lifeos_release_manager.removal_state import retained
        return retained

    def test_missing_active_configuration_retains_exact_owner_for_recovery_only(self):
        self.configuration.path.unlink()
        source,configuration,job,plan=self.operation()(self.profile)
        self.assertEqual(configuration.path,self.configuration.path)
        self.assertEqual(job,self.job)
        self.assertEqual(plan['signature'],self.signature)
        value=configuration.load();configuration.check_owner(value,'dashboard:owner')
        with self.assertRaises(PermissionError):configuration.check_owner(value,'dashboard:other')
        with self.assertRaises(ValueError):configuration.save(value)
        self.assertFalse(self.configuration.path.exists())

    def test_live_owner_revocation_wins_over_retained_authority(self):
        self.configuration.update(lambda value:value['accounts'].pop('dashboard:owner'))
        _,configuration,_,_=self.operation()(self.profile)
        with self.assertRaises(PermissionError):configuration.check_owner(configuration.load(),'dashboard:owner')

    def test_changed_source_policy_and_marker_refuse(self):
        self.configuration.path.unlink()
        path=self.stage/'recovery-bridge/memory_service.py';original=path.read_bytes();path.write_bytes(original+b'\n# Changed\n')
        with self.assertRaises(ValueError):self.operation()(self.profile)
        path.write_bytes(original)
        publish(self.stage/'owner-policy.json',b'{}')
        with self.assertRaises(ValueError):self.operation()(self.profile)
