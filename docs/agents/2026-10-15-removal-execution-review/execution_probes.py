# ABOUTME: Probes executable bytecode and basename Bun service consumers under removal admission.
# ABOUTME: Uses synthetic runtime inputs, actual Python imports, and a locked real inactive user unit.
import importlib.util
import importlib._bootstrap_external
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from uuid import uuid4

from optional.lifeos_release_manager.removal_workflow import _stock
from optional.lifeos_release_manager import removal_consumers
from test_profile_services import service_manager_fixture
from test_removal_runtime import RemovalRuntimeTests

OUTPUT=Path(__file__).parent

class ExecutedBytecodeReview(unittest.TestCase):
    def test_changed_bytecode_cannot_change_the_admitted_program(self):
        fixture=RemovalRuntimeTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        source=fixture.root/'python-environment/lib/site-packages/synthetic.py'
        source.write_text("VALUE='reviewed-source'\n")
        plan=fixture.plan();self.assertEqual(_stock(fixture.job,plan),fixture.runtime)
        cache=Path(importlib.util.cache_from_source(str(source)));cache.parent.mkdir(mode=0o700,exist_ok=True)
        metadata=source.stat()
        data=importlib._bootstrap_external._code_to_timestamp_pyc(
            compile("VALUE='executed-unreviewed-cache'\n",str(source),'exec'),
            mtime=int(metadata.st_mtime),source_size=metadata.st_size)
        cache.write_bytes(data);cache.chmod(0o600)
        observed={}
        try:_stock(fixture.job,plan);observed['changed_bytecode_admitted']=True
        except ValueError as error:observed['refused']=str(error)
        result=subprocess.run([sys.executable,'-I','-c',
            'import json,sys;sys.path.insert(0,sys.argv[1]);import synthetic;print(json.dumps(synthetic.VALUE))',str(source.parent)],
            capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stderr,'')
        observed['executed_value']=json.loads(result.stdout)
        observed['source_unchanged']=source.read_text()=="VALUE='reviewed-source'\n"
        (OUTPUT/'executed-bytecode.json').write_text(json.dumps(observed,indent=2)+'\n')
        self.assertFalse(observed.get('changed_bytecode_admitted') and observed['executed_value']=='executed-unreviewed-cache')

class BasenameServiceReview(unittest.TestCase):
    def command(self,*args):
        result=subprocess.run(['systemctl','--user',*args],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertEqual(result.stderr,'')
        return result.stdout

    @unittest.skipUnless(shutil.which('bun'),'Actual Bun is required')
    def test_inactive_basename_bun_service_cannot_lose_selected_executable(self):
        with service_manager_fixture(),tempfile.TemporaryDirectory(prefix='removal-basename-review-') as temporary:
            home=Path(temporary);profile=home/'.hermes';profile.mkdir(mode=0o700)
            installed=home/'.claude';installed.mkdir(mode=0o700)
            directory=home/'.local/bin';directory.mkdir(parents=True);bun=directory/'bun';shutil.copy2(shutil.which('bun'),bun)
            recorded=home/'executed-path';script="require('fs').writeFileSync("+json.dumps(str(recorded))+",process.execPath)"
            unit='lifeos-removal-basename-'+uuid4().hex+'.service';definition=home/unit
            definition.write_text('[Unit]\nDescription=Synthetic basename removal consumer\n[Service]\nType=oneshot\n'
                'Environment=PATH='+str(directory)+':/usr/bin:/bin\nExecStart=/usr/bin/env bun -e '+json.dumps(script)+'\n')
            self.command('--quiet','link','--runtime',str(definition))
            try:
                self.command('daemon-reload');self.command('start',unit)
                properties=dict(line.split('=',1) for line in self.command('show',unit,'--property=ActiveState,Result').splitlines())
                self.assertEqual(properties,{'ActiveState':'inactive','Result':'success'})
                self.assertEqual(recorded.read_text(),str(bun))
                observed={'inactive':True,'selected_bun_executed':True}
                try:removal_consumers.unit_files(profile,installed,known=set());observed['foreign_consumer_admitted']=True
                except ValueError as error:observed['refused']=str(error)
                (OUTPUT/'basename-service.json').write_text(json.dumps(observed,indent=2)+'\n')
                self.assertIn('refused',observed)
            finally:
                self.command('stop',unit);self.command('--quiet','disable','--runtime',unit);self.command('daemon-reload')
