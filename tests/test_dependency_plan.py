# ABOUTME: Checks the comparison of uv locks that decides whether the bridge would change existing packages.
# ABOUTME: Workspace members are excluded; version changes and removals of registry packages are reported.
from pathlib import Path
import tempfile
import unittest

from optional.lifeos_release_manager.dependency_plan import compare, locked_packages


LOCK = '''version = 1
[[package]]
name = "hermes-agent"
version = "0.0.0"
source = { editable = "." }

[[package]]
name = "hermes-plugin-abc"
version = "0.0.0"
source = { virtual = "plugin-deps/abc" }

[[package]]
name = "mcp"
version = "2.0.0"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "numpy"
version = "2.1.0"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "numpy"
version = "1.26.4"
source = { registry = "https://pypi.org/simple" }
'''


class DependencyPlanTests(unittest.TestCase):
    def write(self, text):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / 'uv.lock'
        path.write_text(text)
        return path

    def test_registry_packages_are_listed_and_members_excluded(self):
        self.assertEqual(locked_packages(self.write(LOCK)), {'mcp': ['2.0.0'], 'numpy': ['1.26.4', '2.1.0']})

    def test_additions_are_separate_from_changes_and_removals(self):
        before = {'mcp': ['2.0.0'], 'numpy': ['2.1.0'], 'six': ['1.16.0']}
        after = {'mcp': ['2.0.0'], 'numpy': ['2.2.0'], 'tree-sitter': ['0.26.0']}
        self.assertEqual(compare(before, after), {
            'changed': {'numpy': {'before': ['2.1.0'], 'after': ['2.2.0']},
                        'six': {'before': ['1.16.0'], 'after': None}},
            'added': {'tree-sitter': ['0.26.0']}})

    def test_identical_locks_change_nothing(self):
        packages = locked_packages(self.write(LOCK))
        self.assertEqual(compare(packages, packages), {'changed': {}, 'added': {}})


if __name__ == '__main__':
    unittest.main()
