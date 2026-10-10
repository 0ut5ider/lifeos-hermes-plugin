# ABOUTME: Checks generated Pulse service files against ownership admission requirements.
# ABOUTME: Uses physical files under permissive umasks to verify safe publication and return.
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lifeos_hook_bridge.profile_services import _definition_file
from lifeos_hook_bridge.selection_worker import SystemdServices


class SelectionServiceFileTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.services = SystemdServices.__new__(SystemdServices)
        self.services.pulse = True
        self.services.dropin = self.home / 'units/pulse.service.d/lifeos-installation.conf'

    def test_generated_definition_is_private_under_a_group_writable_umask(self):
        previous = os.umask(0o002)
        try:
            with patch('lifeos_hook_bridge.selection_worker._systemctl') as manager:
                self.services.point_pulse(self.home / 'selected')
                manager.assert_called_once_with('daemon-reload')
        finally:
            os.umask(previous)
        self.assertEqual(self.services.dropin.stat().st_mode & 0o777, 0o600)
        self.assertIn('HOME=' + str(self.home / 'selected'), self.services.dropin.read_text())
        self.assertEqual(_definition_file(self.services.dropin)['declared'], str(self.services.dropin))

    def test_return_removes_the_generated_override(self):
        with patch('lifeos_hook_bridge.selection_worker._systemctl'):
            self.services.point_pulse(self.home / 'selected')
            self.services.point_pulse(None)
        self.assertFalse(self.services.dropin.exists())


if __name__ == '__main__':
    unittest.main()
