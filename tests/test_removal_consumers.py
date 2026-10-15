# ABOUTME: Refuses other account consumers of programs selected for complete software removal.
# ABOUTME: Uses actual owner unit files and a real Bun process without reading personal records.
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest
from uuid import uuid4

from test_profile_services import service_manager_fixture


class RemovalConsumersTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.home=Path(self.directory.name);self.profile=self.home/'.hermes';self.profile.mkdir(mode=0o700)
        self.installed=self.home/'.claude';self.installed.mkdir(mode=0o700)
        self.directory=self.home/'.config/systemd/user';self.directory.mkdir(parents=True)
        self.owned=self.directory/'com.lifeos.pulse.service';self.owned.write_text('ExecStart='+str(self.home/'.local/bin/bun')+' '+str(self.installed/'LIFEOS/PULSE/pulse.ts')+'\n')

    def operation(self):
        from optional.lifeos_release_manager import removal_consumers
        return removal_consumers

    def test_foreign_unit_using_shared_bun_or_native_program_refuses(self):
        self.operation().unit_files(self.profile,self.installed,known={self.owned})
        path=self.directory/'other.service';path.write_text('ExecStart='+str(self.home/'.local/bin/bun')+' /synthetic/other.ts\n')
        with self.assertRaises(ValueError):self.operation().unit_files(self.profile,self.installed,known={self.owned})
        path.write_text('ExecStart=/usr/bin/echo '+str(self.installed/'hooks/Owner.ts')+'\n')
        with self.assertRaises(ValueError):self.operation().unit_files(self.profile,self.installed,known={self.owned})
        path.write_text('ExecStart=/usr/bin/sleep infinity\n')
        self.operation().unit_files(self.profile,self.installed,known={self.owned})

    @unittest.skipUnless(shutil.which('bun'),'Actual Bun is required')
    def test_running_bun_outside_reviewed_service_groups_refuses(self):
        command=self.home/'.local/bin/bun';command.parent.mkdir(parents=True);shutil.copy2(shutil.which('bun'),command)
        with subprocess.Popen([str(command),'-e','setInterval(()=>{},1000)'],stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,stderr=subprocess.PIPE) as process:
            try:
                time.sleep(0.1);self.assertIsNone(process.poll())
                with self.assertRaises(ValueError):self.operation().processes(self.profile,self.installed,groups=set())
                group={line.removeprefix('0::') for line in (Path('/proc')/str(process.pid)/'cgroup').read_text().splitlines() if line.startswith('0::')}
                self.operation().processes(self.profile,self.installed,groups=group)
            finally:
                process.terminate();stdout,stderr=process.communicate(timeout=10)
                self.assertEqual(stdout+stderr,b'')

    def test_retained_foreign_hook_cannot_lose_its_bun_or_native_dependency(self):
        for command in ('bun /synthetic/owner.ts','/usr/bin/env bun /synthetic/owner.ts',
                        str(self.installed/'LIFEOS/TOOLS/Owner.ts')):
            value={'hooks':{'SessionEnd':[{'hooks':[{'type':'command','command':command}]}]}}
            with self.subTest(command=command),self.assertRaises(ValueError):self.operation().hooks(value,self.profile,self.installed)
        value={'hooks':{'SessionEnd':[{'hooks':[{'type':'command','command':'echo synthetic-foreign'}]}]}}
        self.operation().hooks(value,self.profile,self.installed)

    def test_inactive_runtime_linked_foreign_service_refuses_without_changing_it(self):
        with service_manager_fixture():
            unit='lifeos-removal-consumer-'+uuid4().hex+'.service';definition=self.home/unit
            data=('[Service]\nExecStart='+str(self.home/'.local/bin/bun')+' '+
                str(self.installed/'LIFEOS/TOOLS/Owner.ts')+'\n')
            definition.write_text(data)
            def command(*arguments):
                result=subprocess.run(['systemctl','--user',*arguments],capture_output=True,text=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertEqual(result.stderr,'');return result.stdout
            command('--quiet','link','--runtime',str(definition))
            try:
                command('daemon-reload')
                self.assertEqual(command('show',unit,'--property=ActiveState','--value').strip(),'inactive')
                with self.assertRaisesRegex(ValueError,'Another.*service'):
                    self.operation().unit_files(self.profile,self.installed,known={self.owned})
                self.assertEqual(definition.read_text(),data)
            finally:
                command('--quiet','disable','--runtime',unit);command('daemon-reload')
