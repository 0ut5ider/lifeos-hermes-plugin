# ABOUTME: Probes receipt removal, later fragment and drop-in edits, and coordinator child identity.
# ABOUTME: Uses unique actual transient units under the existing service fixture serialization.
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

import test_removal_coordinator as fixtures

OUTPUT=Path(__file__).parent

class CoordinatorBoundaryReview(unittest.TestCase):
    def run_mode(self,mode):
        fixture=fixtures.RemovalCoordinatorTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        override=None
        if mode=='dropin_symlink':
            directory=Path('/run/user')/str(os.getuid())/'systemd/user'/(fixture.unit+'.service.d')
            directory.mkdir(mode=0o700);override=directory/'override.conf'
            override.write_text('[Service]\nTimeoutStopSec=30\n');override.chmod(0o600)
            def cleanup():
                override.unlink(missing_ok=True);directory.rmdir();fixture.fixture.command('systemctl','--user','daemon-reload')
            self.addCleanup(cleanup);fixture.fixture.command('systemctl','--user','daemon-reload')
        settings={'profile':str(fixture.profile),'installed':str(fixture.installed),'units':fixture.fixture.units,
            'job':str(fixture.job),'mode':mode,'override':str(override) if override else None}
        code='''import json,sys,os
from pathlib import Path
from lifeos_hook_bridge.profile_services import ProfileServices
from optional.lifeos_release_manager.removal_preparation import _consumers
s=json.loads(sys.argv[1]);p=Path(s['profile']);job=Path(s['job']);mode=s['mode']
if mode=='no_receipt':(job/'launch.json').unlink()
if mode=='child_pid':
 pid=os.fork()
 if pid:
  os.waitpid(pid,0);raise SystemExit(0)
services=ProfileServices(p,Path(s['installed']),units=s['units'])
injected=False
def trace(frame,event,arg):
 global injected
 if event=='return' and frame.f_code.co_name=='coordinator' and arg is not None and not injected:
  if mode=='fragment_bytes':
   injected=True;path=arg['fragment'];before=path.stat();path.write_bytes(path.read_bytes()+b'\\n# Synthetic later fragment edit\\n')
   os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns))
  if mode=='dropin_symlink':
   injected=True;path=Path(s['override']);target=job/'later-override.conf';target.write_bytes(path.read_bytes());target.chmod(0o600)
   path.unlink();path.symlink_to(target)
 return trace
sys.settrace(trace)
try:
 _consumers(p,Path(s['installed']),services,workflow=job);result={'admitted':True}
except (ValueError,RuntimeError,OSError) as error:
 result={'admitted':False,'exception':type(error).__name__,'reason':str(error)}
finally:sys.settrace(None)
result['fault_injected']=injected or mode in {'no_receipt','child_pid'}
(job/'review-coordinator-result.json').write_text(json.dumps(result))
'''
        run=['systemd-run','--user','--collect','--quiet','--unit='+fixture.unit,
            '--property=UMask=0077','--property=StandardOutput=null','--property=StandardError=null',
            '--setenv=PYTHONPATH='+os.environ['PYTHONPATH'],sys.executable,'-B','-c',code,json.dumps(settings)]
        started=subprocess.run(run,capture_output=True,text=True,timeout=30)
        self.assertEqual(started.returncode,0,started.stdout+started.stderr);self.assertEqual(started.stderr,'')
        receipt=fixture.job/'review-coordinator-result.json';deadline=time.monotonic()+20
        while not receipt.exists() and time.monotonic()<deadline:time.sleep(0.02)
        self.assertTrue(receipt.is_file(),'The actual coordinator did not save its bounded result')
        observed=json.loads(receipt.read_bytes());(OUTPUT/(mode+'.json')).write_text(json.dumps(observed,indent=2)+'\n')
        self.assertTrue(observed['fault_injected']);self.assertFalse(observed['admitted'],observed)
        return observed

    def test_missing_launch_receipt_does_not_exempt_own_transient_unit(self):
        self.run_mode('no_receipt')

    def test_later_fragment_bytes_refuse_even_with_restored_timestamp(self):
        observed=self.run_mode('fragment_bytes');self.assertIn('coordinator changes',observed['reason'])

    def test_later_dropin_symlink_target_refuses(self):
        observed=self.run_mode('dropin_symlink');self.assertIn('coordinator changes',observed['reason'])

    def test_child_process_in_same_group_cannot_claim_main_coordinator(self):
        observed=self.run_mode('child_pid');self.assertIn('does not own',observed['reason'])
