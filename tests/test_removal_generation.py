# ABOUTME: Verifies managed-account admission before removal of account-wide launchers.
# ABOUTME: Refuses other profiles and modified or non-default installation layouts.
from pathlib import Path
import tempfile
import unittest


class RemovalGenerationTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.home=Path(self.directory.name);self.profile=self.home/'.hermes';self.profile.mkdir(mode=0o700)
        self.installed=self.home/'.claude';self.installed.mkdir(mode=0o700)

    def operation(self):
        from optional.lifeos_release_manager.removal_generation import account
        return account

    def test_one_default_profile_is_admitted_without_changing_files(self):
        self.assertEqual(self.operation()(self.profile,self.installed),self.home)
        self.assertEqual(sorted(path.name for path in self.home.iterdir()),['.claude','.hermes'])

    def test_another_profile_refuses_account_wide_software_removal(self):
        (self.profile/'profiles/another').mkdir(parents=True)
        with self.assertRaises(ValueError):self.operation()(self.profile,self.installed)

    def test_named_profile_or_selected_external_home_refuses(self):
        other=self.home/'external/.claude';other.mkdir(parents=True)
        with self.assertRaises(ValueError):self.operation()(self.profile,other)
        named=self.profile/'profiles/testing';named.mkdir(parents=True)
        with self.assertRaises(ValueError):self.operation()(named,self.installed)


class GenerationLauncherTests(unittest.TestCase):
    def setUp(self):
        import json
        from optional.lifeos_release_manager.release_programs import publish
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.home=Path(self.directory.name)/'owner home';self.home.mkdir(mode=0o700)
        self.profile=self.home/'.hermes';self.profile.mkdir(mode=0o700)
        self.installed=self.home/'.claude';self.installed.mkdir(mode=0o700)
        identity={'version':'1.0.0','commit':'a'*40,'package_sha256':'b'*64}
        publish(self.profile/'integration-release.json',json.dumps(identity).encode())
        roots=self.profile/'.lifeos-releases';roots.mkdir(mode=0o700)
        self.job=roots/('c'*32);self.job.mkdir(mode=0o700)
        request={'profile':str(self.profile),'installed':str(self.installed),**identity}
        publish(self.job/'request.json',json.dumps(request).encode())
        publish(self.job/'status.json',json.dumps({'state':'applied'}).encode())
        self.launcher=self.home/'.local/bin/hermes';self.launcher.parent.mkdir(parents=True,mode=0o700)

    def script(self, command):
        return ("#!/bin/sh\nexec '"+str(command)+"' \"$@\"\n").encode()

    def selected(self):
        from optional.lifeos_release_manager.removal_generation import selected
        class Status:
            def status(self, profile, plugin):return {'active':{'verification':'verified'}}
        class Bridge:
            def memory_module(self, name):return Status()
        return selected(self.profile,self.installed,bridge=Bridge())

    def test_wrapper_accepts_only_the_exact_quoted_launcher(self):
        from optional.lifeos_release_manager.removal_generation import _wrapper
        target=self.job/'bin/hermes'
        self.launcher.write_bytes(self.script(target))
        self.assertEqual(_wrapper(self.launcher,target)['type'],'file')
        for variant in (b'#!/bin/sh\nexec '+str(target).encode()+b' "$@"\n',self.script(target)+b'\n'):
            self.launcher.write_bytes(variant)
            with self.assertRaises(ValueError):_wrapper(self.launcher,target)

    def test_generation_is_selected_only_by_its_exact_account_launcher(self):
        self.launcher.write_bytes(self.script(self.job/'bin/hermes'))
        with self.assertRaises(KeyError) as selected:self.selected()
        self.assertEqual(selected.exception.args,('certificate',))
        self.launcher.write_bytes(b'#!/bin/sh\nexec '+str(self.job/'bin/hermes').encode()+b' "$@"\n')
        with self.assertRaisesRegex(ValueError,'Removal requires one exact currently selected complete generation'):
            self.selected()
