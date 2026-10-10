# ABOUTME: Requires Conduit capture through the actual owner job and Hermes command parser.
# ABOUTME: Uses synthetic work events and verifies private output without a model request.
from datetime import datetime, timezone
import json
from pathlib import Path
import os
import unittest

import test_memory_owner_jobs as jobs_fixture
import test_memory_owner_job_command as command_fixture


def seed(root):
    pulse=root/'LIFEOS/PULSE'
    if not pulse.exists():pulse.symlink_to(Path(os.environ['LIFEOS_MEMORY_SOURCE'])/'LIFEOS/PULSE',target_is_directory=True)
    data=root/'LIFEOS/USER/CONDUIT'
    data.mkdir(parents=True,exist_ok=True)
    config=data/'config.json'
    config.write_text(json.dumps({'enabled':True,'pollIntervalSec':120,'sources':{
        'appFocus':False,'git':False,'claudeSession':True,'github':False},'repos':[],'retentionDays':30}))
    config.chmod(0o600)
    work=root/'LIFEOS/MEMORY/STATE/work-events.jsonl'
    work.parent.mkdir(parents=True,exist_ok=True)
    work.write_text(json.dumps({'ts':datetime.now(timezone.utc).isoformat(),'slug':'synthetic-owner-job-work'})+'\n')
    return data


class ConduitCaptureOwnerJobTests(unittest.TestCase):
    def test_actual_owner_job_captures_work_once_and_repeats_without_duplicate_activity(self):
        owner=jobs_fixture.MemoryOwnerJobsTests();owner.setUp()
        self.addCleanup(owner.doCleanups)
        root=Path(owner.configuration.load()['root'])
        data=seed(root)
        result=owner.run_job('conduit-capture')
        self.assertEqual(result['status'],'completed',result)
        self.assertEqual(result['output'],'captured 1 event(s)\n')
        events=list((data/'events').glob('*.jsonl'))
        self.assertEqual(len(events),1)
        before=events[0].read_bytes()
        self.assertEqual(json.loads(before)['detail']['lastSlug'],'synthetic-owner-job-work')
        self.assertEqual(events[0].stat().st_mode & 0o777,0o600)
        repeat=owner.run_job('conduit-capture')
        self.assertEqual(repeat['status'],'completed',repeat)
        self.assertEqual(repeat['output'],'captured 0 event(s)\n')
        self.assertEqual(events[0].read_bytes(),before)

    def test_actual_hermes_parser_runs_selected_owner_capture_without_inference(self):
        owner=command_fixture.MemoryOwnerJobCommandTests();owner.setUp()
        self.addCleanup(owner.doCleanups)
        data=seed(owner.native.root)
        result=owner.call('conduit-capture')
        self.assertEqual((result.returncode,result.stderr),(0,''),result.stdout+result.stderr)
        value=json.loads(result.stdout)
        self.assertEqual(value['status'],'completed',value)
        self.assertEqual(value['output'],'captured 1 event(s)\n')
        self.assertEqual(len(list((data/'events').glob('*.jsonl'))),1)
        self.assertEqual(owner.fixture.fixture.received,[])
