# ABOUTME: Verifies native feedback eligibility, learning, pulses, and failure publication.
# ABOUTME: Runs actual installed feedback programs with synthetic inputs and real state writes.
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import unittest

import test_native_lifecycle_branches as lifecycle

SOURCE=os.environ.get('LIFEOS_GUARD_SOURCE')


@unittest.skipUnless(SOURCE and shutil.which('bun'), 'Prepared native feedback programs and Bun are required')
class NativeFeedbackTests(unittest.TestCase):
    def fixture(self):
        fixture=lifecycle.NativeLifecycleBranchTests();home,root,environment=fixture.fixture()
        self.addCleanup(fixture.doCleanups)
        (root/'settings.json').write_text('{}')
        return home,root,environment

    def call(self,root,environment,prompt,session='feedback'):
        return subprocess.run(['bun',str(Path(SOURCE)/'hooks/SatisfactionCapture.hook.ts')],
            input=json.dumps({'prompt':prompt,'session_id':session,'transcript_path':'/synthetic/missing'}),
            env=environment,text=True,capture_output=True,timeout=15)

    def test_explicit_praise_numeric_work_and_system_exclusions_keep_real_rating_pulses(self):
        _,root,environment=self.fixture()
        log=root/'LIFEOS/MEMORY/LEARNING/SIGNALS/ratings.jsonl'
        for prompt,rating,source in [('9',9,'explicit'),('ten',10,'explicit'),('8/10, nice',8,'explicit'),('great job',8,'implicit')]:
            result=self.call(root,environment,prompt)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('Wrote '+source+' rating '+str(rating),result.stderr)
            row=json.loads(log.read_text().splitlines()[-1]);self.assertEqual((row['rating'],row['source']),(rating,source))
        prior=log.read_bytes()
        for prompt in ('2/10 items done','1) review the header','10 files need a review','0','11','<system-reminder>9</system-reminder>',
            '<task-notification>great job</task-notification>','```\n9\n```','`great job`'):
            result=self.call(root,environment,prompt)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertNotIn('Wrote ',result.stderr)
            self.assertEqual(log.read_bytes(),prior)
        registry=json.loads((root/'LIFEOS/MEMORY/STATE/work.json').read_text())
        self.assertEqual([row['value'] for row in registry['sessions']['__pulse_strip']['ratings']],[9,10,8,8])

    def test_directive_capture_deduplicates_and_code_quotes_do_not_create_upgrades(self):
        _,root,environment=self.fixture()
        for prompt in ('```\nFrom now on always include synthetic test results.\n```',
            '> From now on always include synthetic test results.',
            'The example text is `from now on always include synthetic test results`.'):
            result=self.call(root,environment,prompt)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertNotIn('Standing directive',result.stderr)
        prompt='From now on always include synthetic laboratory test results.'
        first=self.call(root,environment,prompt)
        self.assertIn('Standing directive',first.stderr)
        upgrades=root/'LIFEOS/MEMORY/UPGRADES'
        before={path:path.read_bytes() for path in upgrades.rglob('*') if path.is_file()}
        repeated=self.call(root,environment,prompt)
        self.assertEqual(repeated.returncode,0,repeated.stderr)
        after={path:path.read_bytes() for path in upgrades.rglob('*') if path.is_file()}
        self.assertEqual(before,after)
        self.assertTrue(before)

    def test_complaint_without_previous_context_does_not_capture_a_failure(self):
        _,root,environment=self.fixture()
        result=self.call(root,environment,"That's wrong, you ignored the synthetic requirement.")
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotIn('FAILURES capture',result.stderr)
        self.assertFalse((root/'LIFEOS/MEMORY/LEARNING/FAILURES').exists())

    def test_low_rating_learning_uses_actual_prior_response_and_active_isa(self):
        _,root,environment=self.fixture()
        state=root/'LIFEOS/MEMORY/STATE'
        (state/'last-response.txt').write_text('The synthetic code change omitted a required laboratory test.')
        (state/'work.json').write_text(json.dumps({'sessions':{'synthetic':{'sessionUUID':'feedback','phase':'climbing','ratings':[]}}}))
        result=self.call(root,environment,'4/10, missing laboratory coverage.')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Wrote explicit rating 4',result.stderr)
        learnings=list((root/'LIFEOS/MEMORY/LEARNING').glob('*/*/*LEARNING*.md'))
        self.assertEqual(len(learnings),1)
        self.assertIn('omitted a required laboratory test',learnings[0].read_text())
        self.assertEqual(json.loads((state/'work.json').read_text())['sessions']['synthetic']['ratings'][0]['value'],4)

    def test_rating_write_failure_preserves_existing_state_and_reports_the_actual_error(self):
        _,root,environment=self.fixture()
        target=root/'LIFEOS/MEMORY/LEARNING/SIGNALS/ratings.jsonl';target.mkdir(parents=True)
        protected=target/'prior.txt';protected.write_text('Synthetic prior feedback')
        result=self.call(root,environment,'9')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Fatal error',result.stderr)
        self.assertIn('EISDIR',result.stderr)
        self.assertEqual(protected.read_text(),'Synthetic prior feedback')

    def test_kill_after_actual_rating_append_retains_the_complete_row(self):
        _,root,environment=self.fixture()
        marker=root/'rating-appended';preload=root/'rating-delay.cjs'
        preload.write_text('// ABOUTME: Pauses after the real native rating append for a kill control.\n'
            '// ABOUTME: Keeps feedback parsing and persisted bytes unchanged.\n'
            "const fs=require('node:fs');const append=fs.appendFileSync;fs.appendFileSync=function(path,...args){const result=append.call(this,path,...args);if(String(path).endsWith('/SIGNALS/ratings.jsonl')){fs.writeFileSync(process.env.LIFEOS_RATING_MARKER,'ready');Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,30000);}return result;};\n")
        process=subprocess.Popen(['bun','--preload',str(preload),str(Path(SOURCE)/'hooks/SatisfactionCapture.hook.ts')],
            env=environment|{'LIFEOS_RATING_MARKER':str(marker)},stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        process.stdin.write(json.dumps({'prompt':'9','session_id':'feedback'}));process.stdin.close();process.stdin=None
        try:
            deadline=time.monotonic()+8
            while not marker.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.02)
            self.assertTrue(marker.exists(),'The actual native feedback append was not reached')
        finally:
            if process.poll() is None:process.kill()
            stdout,stderr=process.communicate(timeout=5)
        self.assertEqual(process.returncode,-9,(stdout,stderr))
        log=root/'LIFEOS/MEMORY/LEARNING/SIGNALS/ratings.jsonl'
        self.assertEqual(json.loads(log.read_text())['rating'],9)
