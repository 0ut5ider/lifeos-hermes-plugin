# ABOUTME: Measures native reminder refusal and delivery-marker retry behavior.
# ABOUTME: Uses actual missing executables and interrupted state publication in isolated homes.
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import time
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

    def test_actual_interrupted_attempt_remains_retryable_before_acknowledgement(self):
        fixture=lifecycle.NativeLifecycleBranchTests();home,root,environment=fixture.fixture()
        self.addCleanup(fixture.doCleanups)
        work=root/'LIFEOS/USER/WORK';work.mkdir(parents=True)
        (work/'work_repo.json').write_text(json.dumps({'repo':'synthetic-owner/private-fixture',
            'privacy':{'verified_private':True,'verified_at':datetime.now(timezone.utc).isoformat(),'visibility':'PRIVATE'}}))
        binaries=home/'bin';binaries.mkdir();ready=home/'transport-started'
        transport=binaries/'gh'
        transport.write_text('#!'+sys.executable+'\n# ABOUTME: Holds a native issue command before acknowledgement.\n'
            '# ABOUTME: Creates no external issue and exits successfully only for the retry control.\n'
            'import pathlib,time\npathlib.Path('+repr(str(ready))+').touch()\ntime.sleep(30)\n')
        transport.chmod(0o755);environment['PATH']=str(binaries)+os.pathsep+environment['PATH']
        command=[shutil.which('bun'),str(Path(SOURCE)/'hooks/ReminderRouter.hook.ts')]
        payload=json.dumps({'session_id':'interrupted-reminder','prompt':'Remind me to inspect the synthetic fixture tomorrow'})
        process=subprocess.Popen(
            command,env=environment,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
        process.stdin.write(payload);process.stdin.close();process.stdin=None
        try:
            deadline=time.monotonic()+5
            while not ready.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.01)
            self.assertTrue(ready.exists(),'The actual issue command did not start')
        finally:
            if process.poll() is None:os.killpg(process.pid,signal.SIGKILL)
            stdout,stderr=process.communicate(timeout=5)
        self.assertEqual(process.returncode,-signal.SIGKILL,(stdout,stderr))
        seen=root/'LIFEOS/MEMORY/STATE/reminder-router-seen.json'
        self.assertFalse(seen.exists())
        transport.write_text('#!/bin/sh\n# ABOUTME: Acknowledges the native issue-command retry control.\n'
            '# ABOUTME: Exercises local state publication without external delivery.\nexit 0\n')
        retry=subprocess.run(command,input=payload,env=environment,capture_output=True,text=True,timeout=10)
        self.assertEqual(retry.returncode,0,retry.stderr);self.assertIn('routed reminder',retry.stderr)
        self.assertTrue(seen.exists())

    def test_route_kinds_dates_and_unverified_destination_component_contract(self):
        fixture=lifecycle.NativeLifecycleBranchTests();home,root,environment=fixture.fixture()
        self.addCleanup(fixture.doCleanups)
        work=root/'LIFEOS/USER/WORK';work.mkdir(parents=True)
        configuration=work/'work_repo.json'
        value={'repo':'synthetic-owner/private-fixture','privacy':{'verified_private':False,
            'verified_at':datetime.now(timezone.utc).isoformat(),'visibility':'PRIVATE'}}
        configuration.write_text(json.dumps(value))
        binaries=home/'bin';binaries.mkdir();record=home/'arguments.json'
        transport=binaries/'gh';transport.write_text('#!'+sys.executable+'\n'
            '# ABOUTME: Records arguments constructed by the native reminder component.\n'
            '# ABOUTME: Creates no external issue and returns local command acknowledgement.\n'
            'import json,pathlib,sys\npathlib.Path('+repr(str(record))+').write_text(json.dumps(sys.argv[1:]))\n')
        transport.chmod(0o755);environment['PATH']=str(binaries)+os.pathsep+environment['PATH']
        command=[shutil.which('bun'),str(Path(SOURCE)/'hooks/ReminderRouter.hook.ts')]
        result=subprocess.run(command,input=json.dumps({'session_id':'unverified','prompt':'Remind me to inspect tomorrow'}),
            env=environment,capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr);self.assertFalse(record.exists())
        value['privacy']['verified_private']=True;configuration.write_text(json.dumps(value))
        for kind,prompt in [('reminder','Remind me to inspect tomorrow'),('research','Research the synthetic paper'),
                            ('queue','Queue this for later')]:
            with self.subTest(kind=kind):
                result=subprocess.run(command,input=json.dumps({'session_id':kind,'prompt':prompt}),
                    env=environment,capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stderr)
                args=json.loads(record.read_text());self.assertIn('Type:'+kind,args)
                body=args[args.index('--body')+1];self.assertIn(prompt,body)
                self.assertEqual('**Due:**' in body,kind=='reminder')
