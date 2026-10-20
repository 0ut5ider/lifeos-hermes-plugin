# ABOUTME: Exercises removal admission from the actual detached owner coordinator unit.
# ABOUTME: Keeps foreign services and mismatched coordinator receipts outside the admitted service set.
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from uuid import uuid4

import test_profile_services as service_fixture


class RemovalCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.fixture=service_fixture.ProfileServicesTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.profile=self.fixture.profile;self.installed=self.fixture.installed
        self.job=self.profile/'.lifeos-portability'/uuid4().hex;self.job.mkdir(parents=True,mode=0o700)
        self.unit='lifeos-memory-'+self.job.name+'-'+uuid4().hex[:8]
        from optional.lifeos_release_manager.release_programs import publish
        request={'version':1,'identifier':self.job.name,'profile':str(self.profile),'owner':'dashboard:owner',
            'bridge':{},'selection':{'kind':'removal','identifier':'a'*32,'signature':'b'*64,'disable_discord':True}}
        publish(self.job/'request.json',json.dumps(request).encode())
        publish(self.job/'launch.json',json.dumps({'unit':self.unit}).encode())

    def run_coordinator(self,*,forged=False,edit_override=False):
        override=None
        if edit_override:
            directory=Path('/run/user')/str(os.getuid())/'systemd/user'/(self.unit+'.service.d')
            directory.mkdir(mode=0o700);override=directory/'override.conf'
            override.write_text('[Service]\nTimeoutStopSec=30\n');override.chmod(0o600)
            def cleanup():
                override.unlink();directory.rmdir();self.fixture.command('systemctl','--user','daemon-reload')
            self.addCleanup(cleanup);self.fixture.command('systemctl','--user','daemon-reload')
        settings={'profile':str(self.profile),'installed':str(self.installed),'units':self.fixture.units,
            'job':str(self.job),'forged':forged,'override':str(override) if override is not None else None}
        code='''import json,sys,os
from pathlib import Path
from lifeos_hook_bridge.profile_services import ProfileServices
from optional.lifeos_release_manager.removal_preparation import check_consumers
from optional.lifeos_release_manager.release_programs import publish
s=json.loads(sys.argv[1]);p=Path(s['profile']);job=Path(s['job'])
if s['forged']:publish(job/'launch.json',json.dumps({'unit':'lifeos-memory-'+job.name+'-ffffffff'}).encode())
services=ProfileServices(p,Path(s['installed']),units=s['units'])
diagnostics={}
edited=False
def trace(frame,event,arg):
 global edited
 if event=='return' and frame.f_code.co_name=='coordinator' and arg is not None and s['override'] and not edited:
  edited=True;target=Path(s['override']);before=target.stat();target.write_bytes(target.read_bytes().replace(b'30',b'31'))
  os.utime(target,ns=(before.st_atime_ns,before.st_mtime_ns))
 if event=='exception' and frame.f_code.co_name=='coordinator':
  diagnostics.update(values=frame.f_locals.get('values'),groups=sorted(frame.f_locals.get('groups',[])),pid=__import__('os').getpid())
 if event=='exception' and frame.f_code.co_name=='processes':
  process=frame.f_locals.get('process')
  if process is not None:diagnostics.update(refused_process=(process/'comm').read_text().strip(),refused_groups=sorted(frame.f_locals.get('current',[])))
 return trace
sys.settrace(trace)
try:
 check_consumers(p,Path(s['installed']),services,workflow=job)
 receipt={'admitted':True}
except ValueError as error:
 import traceback
 diagnostics['trace']=[(Path(item.filename).name,item.lineno,item.name) for item in traceback.extract_tb(error.__traceback__)]
 receipt={'admitted':False,'reason':str(error),'diagnostics':diagnostics}
finally:sys.settrace(None)
(job/'coordinator-test-result.json').write_text(json.dumps(receipt))
'''
        command=['systemd-run','--user','--collect','--quiet','--unit='+self.unit,
            '--property=UMask=0077','--property=StandardOutput=null','--property=StandardError=null',
            '--setenv=PYTHONPATH='+os.environ['PYTHONPATH'],sys.executable,'-B','-c',code,json.dumps(settings)]
        result=subprocess.run(command,capture_output=True,text=True,timeout=45)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(result.stderr,'')
        receipt=self.job/'coordinator-test-result.json';deadline=time.monotonic()+15
        while not receipt.exists() and time.monotonic()<deadline:time.sleep(0.02)
        self.assertTrue(receipt.is_file(),'The actual coordinator does not save its result')
        return json.loads(receipt.read_bytes())

    def test_exact_running_coordinator_is_admitted(self):
        result=self.run_coordinator();self.assertTrue(result['admitted'],result)

    def test_foreign_profile_consumer_still_refuses(self):
        unit='lifeos-foreign-removal-'+uuid4().hex
        result=subprocess.run(['systemd-run','--user','--collect','--quiet','--unit='+unit,
            '--property=WorkingDirectory='+str(self.profile),'/usr/bin/sleep','infinity'],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        try:self.assertFalse(self.run_coordinator()['admitted'])
        finally:self.fixture.command('systemctl','--user','stop',unit)

    def test_other_coordinator_receipt_is_not_admitted(self):
        self.assertFalse(self.run_coordinator(forged=True)['admitted'])

    def test_later_override_bytes_are_not_hidden_by_restored_timestamps(self):
        result=self.run_coordinator(edit_override=True);self.assertFalse(result['admitted'],result)
