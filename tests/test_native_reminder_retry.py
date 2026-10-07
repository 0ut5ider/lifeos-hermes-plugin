# ABOUTME: Measures native reminder refusal and delivery-marker retry behavior.
# ABOUTME: Uses actual missing executables and interrupted state publication in isolated homes.
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

import test_native_lifecycle_branches as lifecycle

SOURCE=os.environ.get('LIFEOS_GUARD_SOURCE')


@unittest.skipUnless(SOURCE and shutil.which('bun'), 'Prepared native reminder programs and Bun are required')
class NativeReminderRetryTests(unittest.TestCase):
    def test_unavailable_destination_does_not_mark_the_request_delivered(self):
        fixture=lifecycle.NativeLifecycleBranchTests();home,root,environment=fixture.fixture()
        self.addCleanup(fixture.doCleanups)
        work=root/'LIFEOS/USER/WORK';work.mkdir(parents=True)
        (work/'work_repo.json').write_text(json.dumps({'repo':'synthetic-owner/private-fixture',
            'privacy':{'verified_private':True,'verified_at':datetime.now(timezone.utc).isoformat(),'visibility':'PRIVATE'}}))
        empty=home/'empty-bin';empty.mkdir();environment['PATH']=str(empty)
        command=[shutil.which('bun'),str(Path(SOURCE)/'hooks/ReminderRouter.hook.ts')]
        for _ in range(2):
            result=subprocess.run(command,input=json.dumps({'session_id':'reminder','prompt':'Remind me to inspect the synthetic fixture tomorrow'}),
                env=environment,text=True,capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('ReminderRouter',result.stderr)
            self.assertFalse((root/'LIFEOS/MEMORY/STATE/reminder-router-seen.json').exists())
