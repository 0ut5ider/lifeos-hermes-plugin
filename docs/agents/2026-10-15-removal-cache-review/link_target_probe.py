# ABOUTME: Checks whether contained interpreter links also bind their executable target bytes.
# ABOUTME: Uses a private synthetic runtime and a harmless changed executable with an actual child process.
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

import test_removal_runtime as fixture_module
from optional.lifeos_release_manager.removal_workflow import _stock
from optional.lifeos_release_manager.removal_runtime import command,identity

OUTPUT=Path(__file__).parent

class LinkTargetReview(unittest.TestCase):
    def test_contained_interpreter_link_cannot_select_unbound_target_bytes(self):
        fixture=fixture_module.RemovalRuntimeTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        executable=fixture.root/'tools/private-python';executable.parent.mkdir(mode=0o700)
        shutil.copy2(Path(sys.executable).resolve(),executable);executable.chmod(0o700)
        link=fixture.root/'python-environment/bin/python';link.unlink();link.symlink_to(executable)
        plan=fixture.plan();self.assertEqual(_stock(fixture.job,plan),fixture.runtime)
        executable.write_text('#!/bin/sh\nexit 94\n');executable.chmod(0o700)
        observed={'contained_target':executable.resolve().is_relative_to(fixture.root),
            'execution_identity_unchanged':identity(fixture.root)==plan['stock_runtime_execution']}
        try:_stock(fixture.job,plan);observed['changed_interpreter_admitted']=True
        except ValueError as error:observed['refused']=str(error)
        result=subprocess.run(command([fixture.runtime['python'],'-I','-c','print(1)'],fixture.runtime),
            capture_output=True,timeout=10)
        self.assertEqual(result.stdout+result.stderr,b'');observed['selected_command_exit']=result.returncode
        (OUTPUT/'contained-unbound-target.json').write_text(json.dumps(observed,indent=2)+'\n')
        self.assertIn('refused',observed)
