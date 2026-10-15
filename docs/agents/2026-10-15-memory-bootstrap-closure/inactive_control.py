# ABOUTME: Checks retention and isolation of an incomplete private return preparation.
# ABOUTME: Uses an actual crash control and verifies that inactive copies cannot change the active plan.
import hashlib
import importlib
import json
from pathlib import Path

from optional.lifeos_release_manager import memory_workflow as workflow

controls=importlib.import_module(__package__+'.adapted_bootstrap_controls')
OUTPUT=Path(__file__).parent


class InactivePreparationControl(controls.WriteBoundaryReview):
    def test_inactive_inner_artifacts_remain_private_and_do_not_select_memory(self):
        self.crash('inner_copy')
        source,configuration=workflow._source(self.profile)
        snapshot=source.memory_module('memory_import_sources').directory(self.profile,'a'*32)
        stages=list(snapshot.glob('.return-preparing-*'))
        self.assertEqual(len(stages),1)
        retained=stages[0]
        document=json.loads((retained/'preparation.json').read_text())
        self.assertEqual(document['writer'],'dashboard:owner')
        self.assertEqual(len(document['operation_id']),32)
        for path in (retained,*retained.rglob('*')):self.assertEqual(path.stat().st_mode & 0o077,0)
        current=snapshot/'return/plan.json';before=current.read_bytes()
        copy=retained/'before/0'
        self.assertTrue(copy.is_file())
        copy.write_bytes(b'Synthetic later edit to retained inactive preparation.')
        signature=hashlib.sha256(before).hexdigest()
        returned=source.memory_module('memory_return').MemoryReturn(configuration)
        plan,state,_=returned._load(snapshot,signature,'dashboard:owner')
        self.assertEqual(state['state'],'ready')
        self.assertEqual(current.read_bytes(),before)
        (OUTPUT/'inactive-artifacts.json').write_text(json.dumps({'retained_preparations':len(stages),
            'private_permissions_verified':True,'owner_binding_verified':True,'active_plan_unchanged':True,
            'active_plan_verified_after_inactive_edit':True},indent=2)+'\n')
