# ABOUTME: Verifies frozen native dependencies against real Bun and immutable release locks.
# ABOUTME: Refuses changed package manifests and later lock edits before dependency installation.
from pathlib import Path
import json
import os
import shutil
import tempfile
import unittest


ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'lifeos_hook_bridge/dependency_locks'
SOURCE=Path(os.environ.get('LIFEOS_FRESH_SOURCE',''))


@unittest.skipUnless(shutil.which('bun') and os.environ.get('LIFEOS_FRESH_SOURCE'),
                     'Bun and the full native candidate are required')
class NativeDependenciesTests(unittest.TestCase):
    def fixture(self,root,package='skills/Remotion/Tools'):
        installed=root/'home/.claude'
        target=installed/package
        target.mkdir(parents=True)
        target.joinpath('package.json').write_bytes((SOURCE/'LifeOS/install'/package/'package.json').read_bytes())
        return installed,target

    def run_install(self,installed,target):
        from lifeos_hook_bridge.native_dependencies import dependency_environment
        from lifeos_hook_bridge.install_source import _install_step
        with dependency_environment(installed,Path(shutil.which('bun')),CATALOG) as selected:
            return _install_step(['bun','install'],cwd=target,environment=os.environ|selected,timeout=15)

    def test_native_bun_installs_exact_locked_dependencies(self):
        with tempfile.TemporaryDirectory(prefix='native-dependencies-') as directory:
            installed,target=self.fixture(Path(directory))
            result=self.run_install(installed,target)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            descriptor=json.loads((CATALOG/'catalog.json').read_text())['packages']['skills/Remotion/Tools']
            self.assertEqual((target/'bun.lock').read_bytes(),(CATALOG/descriptor['lock_file']).read_bytes())
            for name,version in (('remotion','4.0.533'),('typescript','5.9.3'),('@types/bun','1.4.2')):
                self.assertEqual(json.loads((target/'node_modules'/name/'package.json').read_text())['version'],version)
            self.assertEqual(list(installed.glob('.dependency-bin-*')),[])

    def test_stale_shipped_dashboard_lock_requires_reviewed_release_lock(self):
        with tempfile.TemporaryDirectory(prefix='native-dependencies-') as directory:
            installed,target=self.fixture(Path(directory),'skills/Telos/DashboardTemplate')
            original=(SOURCE/'LifeOS/install/skills/Telos/DashboardTemplate/bun.lock').read_bytes()
            (target/'bun.lock').write_bytes(original)
            from lifeos_hook_bridge.install_source import _install_step
            result=_install_step([shutil.which('bun'),'install','--frozen-lockfile'],cwd=target,
                environment=os.environ.copy(),timeout=15)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('lockfile had changes, but lockfile is frozen',result.stderr)
            self.assertEqual((target/'bun.lock').read_bytes(),original)

    def test_empty_installation_gets_all_release_locks_before_native_deployment(self):
        from lifeos_hook_bridge.native_dependencies import seed_release_locks
        with tempfile.TemporaryDirectory(prefix='native-dependencies-') as directory:
            installed=Path(directory)/'home/.claude';installed.mkdir(parents=True)
            seed_release_locks(installed,CATALOG)
            value=json.loads((CATALOG/'catalog.json').read_text())
            for name,item in value['packages'].items():
                self.assertEqual((installed/name/'bun.lock').read_bytes(),(CATALOG/item['lock_file']).read_bytes())
                self.assertEqual((installed/name/'bun.lock').stat().st_mode & 0o077,0)
            target=installed/'skills/Telos/DashboardTemplate'
            target.joinpath('package.json').write_bytes((SOURCE/'LifeOS/install/skills/Telos/DashboardTemplate/package.json').read_bytes())
            result=self.run_install(installed,target)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertTrue((target/'node_modules/next/package.json').is_file())
            snapshot={str(path.relative_to(installed)):path.read_bytes() for path in installed.rglob('bun.lock')}
            with self.assertRaises(ValueError):seed_release_locks(installed,CATALOG)
            self.assertEqual({str(path.relative_to(installed)):path.read_bytes() for path in installed.rglob('bun.lock')},snapshot)

    def test_changed_package_and_existing_lock_refuse_before_bun_runs(self):
        with tempfile.TemporaryDirectory(prefix='native-dependencies-') as directory:
            installed,target=self.fixture(Path(directory))
            original=(target/'package.json').read_bytes()
            for change in ('package','lock'):
                with self.subTest(change=change):
                    if change=='package':(target/'package.json').write_text('{"dependencies":{"unreviewed":"latest"}}')
                    else:
                        (target/'package.json').write_bytes(original)
                        (target/'bun.lock').write_text('Later lock edit.')
                    result=self.run_install(installed,target)
                    self.assertNotEqual(result.returncode,0)
                    self.assertNotIn('bun install v',result.stdout+result.stderr)
                    self.assertFalse((target/'node_modules').exists())
            self.assertEqual((target/'bun.lock').read_text(),'Later lock edit.')

    def test_release_catalog_covers_every_source_package_and_refuses_changes(self):
        from lifeos_hook_bridge.native_dependencies import validate_release_dependencies
        from lifeos_hook_bridge.install_source import SUPPORTED_LIFEOS_COMMIT
        value=validate_release_dependencies(SOURCE/'LifeOS/install',CATALOG,SUPPORTED_LIFEOS_COMMIT)
        self.assertEqual(len(value['packages']),12)
        with tempfile.TemporaryDirectory(prefix='native-catalog-') as directory:
            root=Path(directory)
            for name in value['packages']:
                target=root/name/'package.json';target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes((SOURCE/'LifeOS/install'/name/'package.json').read_bytes())
            validate_release_dependencies(root,CATALOG,SUPPORTED_LIFEOS_COMMIT)
            for change in ('revision','manifest','extra','missing'):
                with self.subTest(change=change):
                    if change=='revision':
                        with self.assertRaises(ValueError):validate_release_dependencies(root,CATALOG,'0'*40)
                    elif change=='manifest':
                        original=(root/'package.json').read_bytes()
                        (root/'package.json').write_bytes(original+b'\n')
                        with self.assertRaises(ValueError):validate_release_dependencies(root,CATALOG,SUPPORTED_LIFEOS_COMMIT)
                        (root/'package.json').write_bytes(original)
                    elif change=='extra':
                        (root/'unreviewed').mkdir();(root/'unreviewed/package.json').write_text('{}')
                        with self.assertRaises(ValueError):validate_release_dependencies(root,CATALOG,SUPPORTED_LIFEOS_COMMIT)
                        shutil.rmtree(root/'unreviewed')
                    else:
                        (root/'package.json').unlink()
                        with self.assertRaises(ValueError):validate_release_dependencies(root,CATALOG,SUPPORTED_LIFEOS_COMMIT)


if __name__=='__main__':
    unittest.main()
