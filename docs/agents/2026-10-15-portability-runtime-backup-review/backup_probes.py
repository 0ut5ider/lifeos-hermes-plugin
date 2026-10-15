# ABOUTME: Checks exact-root portability runtime exclusions in actual profile backup and recovery.
# ABOUTME: Preserves synthetic source artifacts and exercises real archive inspection and symlink boundaries.
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest

from lifeos_hook_bridge.profile_backup import create,inspect
from lifeos_hook_bridge.profile_backup_recovery import recover
from lifeos_hook_bridge.memory_access import MemoryUnavailable
import test_profile_backup as fixtures

OUTPUT=Path(__file__).parent

class PortabilityRuntimeReview(unittest.TestCase):
    def fixture(self):
        fixture=fixtures.ProfileBackupTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        return fixture

    def test_recovery_declares_omitted_runtime_and_preserves_later_source_state_and_owner_files(self):
        fixture=self.fixture();root=fixture.profile/'.lifeos-portability';runtime=root/('a'*32)/'removal/stock-runtime'
        runtime.mkdir(parents=True,mode=0o700);marker=runtime/'synthetic-owned-runtime';marker.write_bytes(b'Synthetic runtime before backup')
        originals={'.lifeos-portability-notes/owner.md':b'Synthetic similar prefix owner file',
            'workspace/.lifeos-portability/owner.md':b'Synthetic nested reserved name owner file',
            'workspace/.lifeos-portability-notes/owner.md':b'Synthetic nested similar prefix owner file'}
        for relative,data in originals.items():
            p=fixture.profile/relative;p.parent.mkdir(parents=True,exist_ok=True,mode=0o700);p.write_bytes(data)
        result,manifest=fixture.snapshot();exclusion={'path':'.lifeos-portability','reason':'runtime'}
        self.assertIn(exclusion,manifest['excluded'])
        self.assertFalse(any(x['path']=='.lifeos-portability' or x['path'].startswith('.lifeos-portability/') for key in ('files','directories','links') for x in manifest[key]))
        later=b'Synthetic later retained runtime state';marker.write_bytes(later)
        self.assertEqual(inspect(fixture.configuration,fixture.destination,result['signature'])['excluded'],manifest['excluded'])
        destination=fixture.fixture.fixture.home/'independent-recovery'
        recovered=recover(fixture.configuration,fixture.destination,result['signature'],destination)
        self.assertFalse((Path(recovered['profile'])/'.lifeos-portability').exists())
        for relative,data in originals.items():self.assertEqual((Path(recovered['profile'])/relative).read_bytes(),data)
        self.assertEqual(marker.read_bytes(),later)
        receipt=json.loads(Path(recovered['recovery_manifest']).read_bytes());self.assertIn(exclusion,receipt['excluded'])
        self.assertFalse(recovered['ownership_enabled']);self.assertFalse(recovered['sharing_enabled'])
        self.assertEqual(fixture.fixture.fixture.memory.get(fixtures.native_fixture.OWNER,fixture.saved['reference'])['content'],'Synthetic coherent profile backup fact')
        (OUTPUT/'recovery-exclusion.json').write_text(json.dumps({'backup_verified':True,'runtime_exclusion_declared_in_backup_and_recovery':True,'runtime_not_claimed_restored':True,'later_live_runtime_retained':True,'three_neighbor_owner_files_recovered':True,'live_native_fact_retained':True,'candidate_ownership_and_sharing_disabled':True},indent=2)+'\n')

    def test_exact_root_external_symlink_is_recorded_without_following_or_rewriting_target(self):
        fixture=self.fixture();outside=fixture.fixture.fixture.home/'external-runtime';outside.mkdir(mode=0o700)
        marker=outside/'synthetic-runtime';marker.write_bytes(b'Synthetic outside runtime');os.mkfifo(outside/'never-read-pipe',0o600)
        link=fixture.profile/'.lifeos-portability';link.symlink_to(outside)
        reads=[]
        def trace(frame,event,arg):
            if event=='call' and frame.f_code.co_name=='_read':reads.append(frame.f_locals.get('path'))
            return trace
        sys.settrace(trace)
        try:result,manifest=fixture.snapshot()
        finally:sys.settrace(None)
        self.assertIn({'path':'.lifeos-portability','reason':'runtime'},manifest['excluded'])
        self.assertTrue(link.is_symlink());self.assertEqual(os.readlink(link),str(outside));self.assertEqual(marker.read_bytes(),b'Synthetic outside runtime')
        self.assertFalse(any(p is not None and Path(p).is_relative_to(outside) for p in reads))
        self.assertFalse(any(x['path']=='.lifeos-portability' for x in manifest['links']))
        (OUTPUT/'root-symlink-exclusion.json').write_text(json.dumps({'excluded_symlink_not_followed':True,'no_target_reads':True,'source_symlink_and_target_retained':True,'exclusion_declared':True,'no_link_copy_claim':True},indent=2)+'\n')

    def test_similarly_named_and_nested_external_links_remain_refused(self):
        fixture=self.fixture();outside=fixture.fixture.fixture.home/'unreviewed-external';outside.mkdir(mode=0o700)
        (outside/'owner.md').write_bytes(b'Synthetic external owner data')
        cases=('.lifeos-portability-notes','workspace/.lifeos-portability')
        for relative in cases:
            path=fixture.profile/relative;path.parent.mkdir(parents=True,exist_ok=True,mode=0o700);path.symlink_to(outside)
            with self.subTest(relative=relative),self.assertRaisesRegex(MemoryUnavailable,'external profile link'):
                create(fixture.configuration,fixture.destination)
            self.assertFalse(fixture.destination.exists());self.assertTrue(path.is_symlink());path.unlink()
        self.assertEqual((outside/'owner.md').read_bytes(),b'Synthetic external owner data')

    def test_inspection_refuses_wrong_reason_and_copied_path_under_exact_exclusion(self):
        fixture=self.fixture();runtime=fixture.profile/'.lifeos-portability';runtime.mkdir(mode=0o700)
        (runtime/'synthetic-state').write_bytes(b'Synthetic retained runtime')
        result,manifest=fixture.snapshot();path=fixture.destination/'manifest.json';original=path.read_bytes()
        for reason in ('dependencies','regenerable','other_profile'):
            modified=json.loads(original)
            next(x for x in modified['excluded'] if x['path']=='.lifeos-portability')['reason']=reason
            path.write_text(json.dumps(modified));path.chmod(0o600)
            with self.subTest(reason=reason),self.assertRaisesRegex(MemoryUnavailable,'invalid exclusion metadata'):inspect(fixture.configuration,fixture.destination)
        modified=json.loads(original);modified['directories'].append({'path':'.lifeos-portability','mode':0o700,'mtime_ns':0})
        path.write_text(json.dumps(modified));path.chmod(0o600)
        with self.assertRaises(MemoryUnavailable):inspect(fixture.configuration,fixture.destination)
        path.write_bytes(original);self.assertEqual(inspect(fixture.configuration,fixture.destination,result['signature'])['excluded'],manifest['excluded'])
