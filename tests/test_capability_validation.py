# ABOUTME: Runs the Hermes plugin validator against the runtime package on a prepared host source.
# ABOUTME: Requires the capability probe and every capability declaration to match actual registration.
import importlib.util
from pathlib import Path
import unittest

PACKAGE=Path(__file__).parents[1]/'lifeos_hook_bridge'


@unittest.skipUnless(importlib.util.find_spec('hermes_cli'),'A prepared Hermes source is required')
class CapabilityValidationTests(unittest.TestCase):
    def test_host_validator_accepts_the_probe_and_declared_capabilities(self):
        from hermes_cli.plugin_validate import validate_plugin_dir
        checks={name:(passed,detail) for name,passed,detail in validate_plugin_dir(PACKAGE).checks}
        for name in ('manifest','manifest fields','config schema','loadable','python dependencies',
                     'capability probe','declared tools','declared hooks','declared middleware',
                     'built-in tool collisions'):
            with self.subTest(check=name):
                self.assertIn(name,checks)
                self.assertTrue(checks[name][0],checks[name][1])
