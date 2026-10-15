# ABOUTME: Probes exact stock launcher binding and loaded foreign unit admission for removal.
# ABOUTME: Uses synthetic files, copied stock source, and one locked inactive actual user unit.
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from uuid import uuid4

from optional.lifeos_release_manager.removal_workflow import _stock
from optional.lifeos_release_manager.release_stage import runtime_source_fingerprint,sha
from optional.lifeos_release_manager import removal_consumers
from test_profile_services import service_manager_fixture

OUTPUT=Path(__file__).parent
STOCK=Path('/home/outsider/.cache/lifeos-memory-portability-20261015/stock-full-9b204dad/runtime')

class StockBindingReview(unittest.TestCase):
    @unittest.skipUnless((STOCK/'runtime.json').is_file(),'Actual constructed stock runtime is required')
    def test_later_stock_launcher_edit_refuses_exact_runtime_admission(self):
        with tempfile.TemporaryDirectory(prefix='removal-stock-review-') as temporary:
            job=Path(temporary);root=job/'stock-runtime';root.mkdir(mode=0o700)
            shutil.copytree(STOCK/'hermes',root/'hermes')
            (root/'bin').mkdir();shutil.copy2(STOCK/'bin/hermes',root/'bin/hermes')
            shutil.copy2(STOCK/'manifest.json',root/'manifest.json')
            runtime=json.loads((STOCK/'runtime.json').read_bytes())
            runtime.update(python=str(root/'python-environment/bin/python'),source=str(root/'hermes'),hermes=str(root/'bin/hermes'))
            plan={'stock_runtime':runtime,'stock_runtime_source':runtime_source_fingerprint(root/'hermes'),
                'stock_runtime_manifest_sha256':sha(root/'manifest.json')}
            self.assertEqual(_stock(job,plan),runtime)
            (root/'bin/hermes').write_text('#!/bin/sh\nexit 91\n');(root/'bin/hermes').chmod(0o700)
            observed={}
            try:_stock(job,plan);observed['changed_launcher_admitted']=True
            except ValueError as error:observed['refused']=str(error)
            observed.update(source_unchanged=runtime_source_fingerprint(root/'hermes')==plan['stock_runtime_source'],
                manifest_unchanged=sha(root/'manifest.json')==plan['stock_runtime_manifest_sha256'])
            command=subprocess.run([str(root/'bin/hermes'),'--version'],capture_output=True,timeout=10)
            self.assertEqual(command.stdout+command.stderr,b'');observed['selected_command_exit']=command.returncode
            (OUTPUT/'changed-stock-launcher.json').write_text(json.dumps(observed,indent=2)+'\n')
            self.assertIn('refused',observed)

class ForeignServiceReview(unittest.TestCase):
    def command(self,*args):
        result=subprocess.run(args,capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertEqual(result.stderr,'')
        return result.stdout

    def test_runtime_linked_foreign_consumer_refuses(self):
        with service_manager_fixture(),tempfile.TemporaryDirectory(prefix='removal-unit-review-') as temporary:
            home=Path(temporary);profile=home/'.hermes';profile.mkdir(mode=0o700)
            installed=home/'.claude';installed.mkdir(mode=0o700)
            (home/'.config/systemd/user').mkdir(parents=True)
            unit='lifeos-removal-review-'+uuid4().hex+'.service';definition=home/unit
            definition.write_text('[Unit]\nDescription=Synthetic inactive removal consumer\n[Service]\n'
                'ExecStart='+str(home/'.local/bin/bun')+' '+str(installed/'LIFEOS/TOOLS/Owner.ts')+'\n')
            self.command('systemctl','--user','--quiet','link','--runtime',str(definition))
            try:
                self.command('systemctl','--user','daemon-reload')
                properties=dict(line.split('=',1) for line in self.command('systemctl','--user','show',unit,
                    '--property=LoadState,ActiveState,FragmentPath,ExecStart,UnitFileState').splitlines())
                self.assertEqual(properties['LoadState'],'loaded');self.assertEqual(properties['ActiveState'],'inactive')
                self.assertIn(str(home/'.local/bin/bun'),properties['ExecStart'])
                observed={'loaded':True,'inactive':True,'runtime_linked':properties['UnitFileState']=='linked-runtime'}
                try:removal_consumers.unit_files(profile,installed,known=set());observed['foreign_consumer_admitted']=True
                except ValueError as error:observed['refused']=str(error)
                (OUTPUT/'runtime-linked-consumer.json').write_text(json.dumps(observed,indent=2)+'\n')
                self.assertIn('refused',observed)
            finally:
                self.command('systemctl','--user','--quiet','disable','--runtime',unit)
                self.command('systemctl','--user','daemon-reload')
