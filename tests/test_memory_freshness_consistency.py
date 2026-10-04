# ABOUTME: Changes sources and owner authority after actual native freshness rendering.
# ABOUTME: Verifies read and HTTP delivery refuse snapshots that become obsolete during rendering.
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from lifeos_hook_bridge.memory_access import NativeMemory, MemoryUnavailable
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from lifeos_hook_bridge.memory_service import MemoryService
import test_memory_freshness as freshness_fixture
from test_memory_native import SOURCE


class MemoryFreshnessConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = freshness_fixture.MemoryFreshnessTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        (self.root / 'LIFEOS/PULSE').symlink_to(SOURCE / 'LIFEOS/PULSE')
        self.preferences = MemoryPreferences(self.fixture.fixture.configuration.path, self.root,
            self.fixture.fixture.fixture.home / 'authorized_keys', Path(sys.executable),
            Path(__file__).parents[1] / 'lifeos_hook_bridge/memory_mcp.py')
        self.path = self.root / 'LIFEOS/USER/TELOS/TELOS.md'

    def render_then_change(self, change, *, http=False):
        real_native = NativeMemory._native
        rendered = []

        def native(memory, action, **arguments):
            result = real_native(memory, action, **arguments)
            if action == ('freshness_view' if http else 'read_freshness'):
                rendered.append(result)
                change()
            return result

        # The instrumentation runs after the actual renderer returns its native result.
        with patch.object(NativeMemory, '_native', native):
            if http:
                with self.assertRaises((MemoryUnavailable, PermissionError)):
                    self.preferences.pulse_response('telos_freshness', account='chat-a:100')
            else:
                result = MemoryService(self.fixture.fixture.configuration).native(
                    self.fixture.fixture.context, 'read_freshness',
                    {'view': 'telos', 'path': str(self.path), 'slug': None})
                self.assertFalse(result['ok'], result)
                self.assertNotIn('Synthetic freshness mission', str(result))
        self.assertEqual(len(rendered), 1)
        original = rendered[0]['body' if http else 'value']
        self.assertEqual(original['totalSections'], 2)
        self.assertEqual(original['sections'][0]['preview'], 'Synthetic freshness mission')

    def change_source(self):
        self.path.write_text(self.path.read_text() + '\n## Wisdom\nSynthetic later freshness\n')

    def revoke_owner(self):
        self.fixture.fixture.configuration.update(lambda config: config['accounts'].pop('chat-a:100'))

    def change_installation(self):
        self.fixture.fixture.configuration.update(lambda config: config.update(
            root=str(self.fixture.fixture.fixture.home / 'foreign-root')))

    def test_cli_read_source_change_after_render_refuses_delivery(self):
        self.render_then_change(self.change_source)

    def test_cli_read_owner_change_after_render_refuses_delivery(self):
        self.render_then_change(self.revoke_owner)

    def test_http_source_change_after_render_refuses_delivery(self):
        self.render_then_change(self.change_source, http=True)

    def test_http_owner_change_after_render_refuses_delivery(self):
        self.render_then_change(self.revoke_owner, http=True)

    def test_http_installation_change_after_render_refuses_delivery(self):
        self.render_then_change(self.change_installation, http=True)
