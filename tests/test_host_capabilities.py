# ABOUTME: Checks the fresh-process host capability probe against real Hermes sources and small real modules.
# ABOUTME: Runs the probe as a real subprocess; the patched and stock Hermes trees come from the test environment.
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

from optional.lifeos_release_manager.release_catalog import ReleaseRejected


PYTHON = '%d.%d' % sys.version_info[:2]


def entry(hooks=('pre_turn_stop',), middleware_api=1, python=PYTHON):
    return {'label': 'v0.0.1', 'python': python, 'capabilities': {'hooks': list(hooks), 'middleware_api': middleware_api}}


class SmallSourceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.source = Path(self.folder.name) / 'hermes-agent'
        (self.source / 'hermes_cli').mkdir(parents=True)
        (self.source / 'hermes_cli/__init__.py').write_text('')
        self.write("VALID_HOOKS = {'pre_tool_call', 'pre_turn_stop'}\n", 'REQUIRED_MIDDLEWARE_API_VERSION = 1\n')

    def write(self, plugins, middleware):
        (self.source / 'hermes_cli/plugins.py').write_text(plugins)
        (self.source / 'hermes_cli/middleware.py').write_text(middleware)

    def probe(self, value):
        from optional.lifeos_release_manager.host_capabilities import probe_capabilities
        return probe_capabilities(sys.executable, self.source, value)

    def test_patched_source_passes_and_reports_what_it_found(self):
        result = self.probe(entry())
        self.assertEqual(result['python'], PYTHON)
        self.assertEqual(result['middleware_api'], 1)
        self.assertIn('pre_turn_stop', result['hooks'])
        self.assertFalse(list(self.source.rglob('__pycache__')), 'The probe must not write bytecode into the source')

    def test_missing_patched_hook_is_refused_with_its_name(self):
        with self.assertRaisesRegex(ReleaseRejected, 'on_turn_result'):
            self.probe(entry(hooks=('pre_turn_stop', 'on_turn_result')))

    def test_other_middleware_api_version_is_refused(self):
        self.write("VALID_HOOKS = {'pre_turn_stop'}\n", 'REQUIRED_MIDDLEWARE_API_VERSION = 2\n')
        with self.assertRaisesRegex(ReleaseRejected, 'middleware API'):
            self.probe(entry())

    def test_source_without_the_middleware_version_is_refused(self):
        self.write("VALID_HOOKS = {'pre_turn_stop'}\n", '')
        with self.assertRaisesRegex(ReleaseRejected, 'middleware API'):
            self.probe(entry())

    def test_source_that_cannot_import_its_hooks_is_refused(self):
        self.write("raise RuntimeError('broken host')\n", 'REQUIRED_MIDDLEWARE_API_VERSION = 1\n')
        with self.assertRaisesRegex(ReleaseRejected, 'hook'):
            self.probe(entry())

    def test_other_interpreter_version_is_refused(self):
        with self.assertRaisesRegex(ReleaseRejected, 'Python 2.7'):
            self.probe(entry(python='2.7'))

    def test_probe_ignores_an_inherited_python_path(self):
        shadow = Path(self.folder.name) / 'shadow/hermes_cli'
        shadow.mkdir(parents=True)
        (shadow / '__init__.py').write_text('')
        (shadow / 'plugins.py').write_text('VALID_HOOKS = set()\n')
        previous = os.environ.get('PYTHONPATH')
        os.environ['PYTHONPATH'] = str(shadow.parent)
        self.addCleanup(lambda: os.environ.pop('PYTHONPATH') if previous is None else os.environ.update(PYTHONPATH=previous))
        self.assertIn('pre_turn_stop', self.probe(entry())['hooks'])


class RealHermesTests(unittest.TestCase):
    def test_patched_test_environment_hermes_exposes_the_bridge_capabilities(self):
        import hermes_cli
        from optional.lifeos_release_manager.host_capabilities import probe_capabilities
        from scripts.build_host_compatibility import bridge_capabilities
        source = Path(hermes_cli.__file__).resolve().parents[1]
        if not (source / 'hermes_cli/middleware.py').is_file():
            self.skipTest('The test environment Hermes has no middleware module')
        result = probe_capabilities(sys.executable, source, {'label': 'test', 'python': PYTHON,
                                                             'capabilities': bridge_capabilities()})
        self.assertEqual(result['middleware_api'], 1)

    def test_stock_hermes_is_refused(self):
        archive = os.environ.get('LIFEOS_STOCK_HERMES_ARCHIVE')
        if not archive:
            self.skipTest('Set LIFEOS_STOCK_HERMES_ARCHIVE to the qualified stock-hermes.tgz')
        from optional.lifeos_release_manager.host_capabilities import probe_capabilities
        from scripts.build_host_compatibility import bridge_capabilities
        with tempfile.TemporaryDirectory() as directory:
            with tarfile.open(archive) as stream:
                stream.extractall(directory, filter='data')
            with self.assertRaisesRegex(ReleaseRejected, 'patched plugin hooks: augment_tool_result'):
                probe_capabilities(sys.executable, Path(directory), {'label': 'v0.21.7', 'python': PYTHON,
                                                                     'capabilities': bridge_capabilities()})


if __name__ == '__main__':
    unittest.main()
