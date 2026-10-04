# ABOUTME: Changes real synthetic sources and authority after actual native graph view rendering.
# ABOUTME: Verifies the owner response refuses an obsolete snapshot before delivery.
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from lifeos_hook_bridge.memory_access import NativeMemory, MemoryUnavailable
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
import test_memory_delegation as delegation
from test_memory_native import SOURCE


class MemoryGraphViewConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        (self.fixture.root / 'LIFEOS/PULSE').symlink_to(SOURCE / 'LIFEOS/PULSE')
        self.fixture.fixture.remember()
        self.preferences = MemoryPreferences(self.fixture.configuration.path, self.fixture.root,
            self.fixture.fixture.home / 'authorized_keys', Path(sys.executable),
            Path(__file__).parents[1] / 'lifeos_hook_bridge/memory_mcp.py')
        self.path = self.fixture.root / 'LIFEOS/MEMORY/WORK/synthetic-work/ISA.md'
        self.path.parent.mkdir(parents=True)
        self.path.write_text('---\ntitle: "Synthetic current work"\n---\nSynthetic current work body\n')

    def render_then_change(self, change):
        real_native = NativeMemory._native
        rendered = []

        def native(memory, action, **arguments):
            result = real_native(memory, action, **arguments)
            if action == 'memory_graph_view':
                rendered.append(result)
                change()
            return result

        # Instrument the completed native render. The renderer and response are real.
        with patch.object(NativeMemory, '_native', native):
            with self.assertRaises((MemoryUnavailable, PermissionError)) as refused:
                self.preferences.pulse_response('graph', account='chat-a:100')
        self.assertEqual(len(rendered), 1, str(refused.exception))
        self.assertEqual(rendered[0]['status'], 200)
        self.assertEqual(rendered[0]['body']['nodeCount'], 2)

    def test_retained_source_change_after_render_refuses_delivery(self):
        self.render_then_change(lambda: self.path.write_text(self.path.read_text() + '\nSynthetic later edit\n'))

    def test_owner_revocation_after_render_refuses_delivery(self):
        self.render_then_change(lambda: self.fixture.configuration.update(
            lambda config: config['accounts'].pop('chat-a:100')))

    def test_installation_change_after_render_refuses_delivery(self):
        self.render_then_change(lambda: self.fixture.configuration.update(
            lambda config: config.update(root=str(self.fixture.fixture.home / 'foreign-root'))))
