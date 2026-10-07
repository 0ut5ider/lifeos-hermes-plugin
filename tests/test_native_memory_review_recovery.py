# ABOUTME: Checks native review admission across an actual trigger-process interruption.
# ABOUTME: Kills the real Bun publication and verifies that retry does not start another review.
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import time
import unittest

import test_native_lifecycle_branches as lifecycle

SOURCE=os.environ.get('LIFEOS_GUARD_SOURCE')


@unittest.skipUnless(SOURCE and shutil.which('bun'),'Prepared native review programs and Bun are required')
class NativeMemoryReviewRecoveryTests(unittest.TestCase):
    def test_killed_global_publication_does_not_duplicate_an_already_started_review(self):
        fixture=lifecycle.NativeLifecycleBranchTests();home,root,environment=fixture.fixture()
        self.addCleanup(fixture.doCleanups)
        transcript=home/'empty-transcript.jsonl';transcript.write_text('')
        config=root/'LIFEOS/USER/CONFIG/memory-review.json';config.parent.mkdir(parents=True)
        config.write_text(json.dumps({'turn_threshold':1,'min_minutes_between':30}))
        marker=home/'publication-ready'
        global_state=root/'LIFEOS/MEMORY/OBSERVABILITY/review-state.json'
        global_state.parent.mkdir(parents=True)
        global_state.write_text(json.dumps({'last_review_at':'2000-01-01T00:00:00Z'}))
        preload=home/'review-publication-pause.cjs'
        preload.write_text('// ABOUTME: Pauses the actual review cadence rename for a kill control.\n'
            '// ABOUTME: Leaves native review decisions and child execution unchanged.\n'
            "const fs=require('node:fs');const rename=fs.renameSync;fs.renameSync=function(source,target){"
            "if(String(target)===process.env.LIFEOS_REVIEW_TARGET){fs.writeFileSync(process.env.LIFEOS_REVIEW_READY,String(process.pid));"
            "Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,30000);}return rename.call(this,source,target);};\n")
        binaries=home/'bin';binaries.mkdir()
        launcher=binaries/'bun';launcher.write_text('#!/bin/sh\nexec '+shlex.quote(shutil.which('bun'))+
            ' --preload '+shlex.quote(str(preload))+' "$@"\n');launcher.chmod(0o755)
        environment.update(PATH=str(binaries)+os.pathsep+environment['PATH'],
            LIFEOS_REVIEW_TARGET=str(global_state),LIFEOS_REVIEW_READY=str(marker))
        payload=json.dumps({'hook_event_name':'Stop','session_id':'interrupted-review','transcript_path':str(transcript)})
        process=subprocess.Popen([shutil.which('bun'),'--preload',str(preload),
            str(Path(SOURCE)/'hooks/MemoryReviewFire.hook.ts')],env=environment,
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        process.stdin.write(payload);process.stdin.close();process.stdin=None
        try:
            deadline=time.monotonic()+8
            while not marker.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.02)
            self.assertTrue(marker.exists(),'The actual global cadence rename was not reached')
        finally:
            if process.poll() is None:process.kill()
            stdout,stderr=process.communicate(timeout=5)
        self.assertEqual(process.returncode,-signal.SIGKILL,(stdout,stderr))
        environment['PATH']=os.pathsep.join(environment['PATH'].split(os.pathsep)[1:])
        retry=subprocess.run([shutil.which('bun'),str(Path(SOURCE)/'hooks/MemoryReviewFire.hook.ts')],
            input=payload,env=environment,text=True,capture_output=True,timeout=10)
        self.assertEqual((retry.returncode,retry.stdout,retry.stderr),(0,'',''))
        log=root/'LIFEOS/MEMORY/OBSERVABILITY/reviewer-runs.jsonl'
        deadline=time.monotonic()+8
        while not log.exists() and time.monotonic()<deadline:time.sleep(.02)
        self.assertTrue(log.exists(),'The actual admitted reviewer did not complete')
        rows=[json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(len(rows),1,rows)
        self.assertTrue(rows[0]['skipped'] and rows[0]['parse_ok'],rows)
        fires=[json.loads(line) for line in (root/'LIFEOS/MEMORY/OBSERVABILITY/reviewer-fires.jsonl').read_text().splitlines()]
        self.assertEqual(len(fires),1,fires)
