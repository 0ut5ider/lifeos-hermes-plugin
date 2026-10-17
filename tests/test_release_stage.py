# ABOUTME: Verifies complete package identities before staging dependencies or native programs.
# ABOUTME: Uses regular synthetic package files to exercise refusal before candidate code runs.
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

from optional.lifeos_release_manager.release_stage import validate_files, validate_package, runtime_source_fingerprint
from optional.lifeos_release_manager.release_catalog import ReleaseRejected


class ReleaseStageTests(unittest.TestCase):
    def test_stage_subprocess_creates_private_files_with_a_permissive_caller(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = ("import os, sys, json\nfrom pathlib import Path\n"
                "from optional.lifeos_release_manager.release_stage import run_stage\n"
                "os.umask(0o002)\nroot=Path(sys.argv[1])\n"
                "child=\"from pathlib import Path; Path('directory').mkdir(); Path('directory/file').write_text('synthetic')\"\n"
                "run_stage([sys.executable, '-B', '-c', child], root, 'permissions', environment=dict(os.environ))\n"
                "print(json.dumps({'directory': (root/'directory').stat().st_mode & 0o777,"
                " 'file': (root/'directory/file').stat().st_mode & 0o777, 'caller': os.umask(0o002)}))\n")
            result = subprocess.run([sys.executable, '-B', '-c', script, str(root)],
                capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stderr, '')
            self.assertEqual(json.loads(result.stdout), {'directory': 0o700, 'file': 0o600, 'caller': 0o002})
            self.assertEqual((root / 'permissions.stdout').read_bytes(), b'')
            self.assertEqual((root / 'permissions.stderr').read_bytes(), b'')

    def test_authenticated_archive_refuses_coordinated_program_and_manifest_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package, certificate, marker, archive = self.package(root)
            program = package / 'lifeos_hook_bridge/install_source.py'
            program.write_text(program.read_text() + '\nchanged = True\n')
            manifest = json.loads((package / 'DAILY-CANDIDATE.json').read_bytes())
            manifest['plugin_files']['lifeos_hook_bridge/install_source.py'] = hashlib.sha256(program.read_bytes()).hexdigest()
            (package / 'DAILY-CANDIDATE.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ReleaseRejected, 'authenticated archive'):
                validate_package(package, certificate)
            self.assertFalse(marker.exists())
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), certificate['archive_sha256'])

    def test_authenticated_archive_is_required_before_candidate_execution(self):
        for change in ('missing', 'changed', 'symlink', 'fifo'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temp:
                package, certificate, marker, archive = self.package(Path(temp))
                if change == 'missing':
                    archive.unlink()
                elif change == 'changed':
                    archive.write_bytes(b'changed')
                elif change == 'symlink':
                    retained = archive.with_suffix('.retained')
                    archive.rename(retained)
                    archive.symlink_to(retained)
                else:
                    archive.unlink()
                    os.mkfifo(archive)
                with self.assertRaisesRegex(ReleaseRejected, 'authenticated archive'):
                    validate_package(package, certificate)
                self.assertFalse(marker.exists())

    def test_authenticated_archive_accepts_its_exact_extracted_program_map(self):
        with tempfile.TemporaryDirectory() as temp:
            package, certificate, marker, _ = self.package(Path(temp))
            self.assertEqual(validate_package(package, certificate)['head'], certificate['program_commit'])
            self.assertTrue(marker.exists())

    def stock_package(self, root):
        package,certificate,marker,archive=self.package(root)
        source=package/'lifeos_hook_bridge/install_source.py'
        source.write_text(source.read_text().replace('"base_commit": "hermes"','"base_commit": "'+'b'*40+'"'))
        manifest=json.loads((package/'DAILY-CANDIDATE.json').read_bytes())
        manifest['plugin_files']['lifeos_hook_bridge/install_source.py']=hashlib.sha256(source.read_bytes()).hexdigest()
        stock=package/'stock-hermes.tgz'
        with tarfile.open(stock,'w:gz') as output:
            data=b'# Synthetic stock source\n';member=tarfile.TarInfo('run_agent.py');member.size=len(data)
            output.addfile(member,io.BytesIO(data))
        manifest['stock_hermes']={'format':1,'commit':'b'*40,'path':'stock-hermes.tgz',
            'sha256':hashlib.sha256(stock.read_bytes()).hexdigest(),'bytes':stock.stat().st_size}
        (package/'DAILY-CANDIDATE.json').write_text(json.dumps(manifest))
        with tarfile.open(archive,'w:gz') as output:
            for path in sorted(package.iterdir()):output.add(path,arcname=path.name)
        certificate.update(hermes_base='b'*40,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
            archive_bytes=archive.stat().st_size)
        return package,certificate,marker

    def test_stock_archive_is_authenticated_before_candidate_execution(self):
        for change in ('bytes','symlink','fifo'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as temp:
                package,certificate,marker=self.stock_package(Path(temp))
                stock=package/'stock-hermes.tgz'
                if change=='bytes':stock.write_bytes(stock.read_bytes()+b'changed')
                elif change=='symlink':
                    retained=stock.with_suffix('.retained');stock.rename(retained);stock.symlink_to(retained)
                else:stock.unlink();os.mkfifo(stock)
                with self.assertRaisesRegex(ReleaseRejected,'stock source archive'):
                    validate_package(package,certificate)
                self.assertFalse(marker.exists())

    def test_exact_stock_archive_matches_qualified_base(self):
        with tempfile.TemporaryDirectory() as temp:
            package,certificate,marker=self.stock_package(Path(temp))
            result=validate_package(package,certificate)
            self.assertEqual(result['stock_hermes']['commit'],certificate['hermes_base'])
            self.assertTrue(marker.exists())

    def test_extracted_manifest_requires_bounded_regular_owner_storage(self):
        for change in ('symlink', 'oversized', 'fifo'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                package, certificate, marker, _ = self.package(root)
                manifest = package / 'DAILY-CANDIDATE.json'
                if change == 'symlink':
                    outside = root / 'outside-manifest'
                    manifest.rename(outside)
                    manifest.symlink_to(outside)
                elif change == 'oversized':
                    manifest.write_bytes(b' ' * (512 * 1024 + 1))
                else:
                    manifest.unlink()
                    os.mkfifo(manifest)
                with self.assertRaisesRegex(ReleaseRejected, 'bounded regular owner manifest'):
                    validate_package(package, certificate)
                self.assertFalse(marker.exists())

    def test_native_source_manifests_match_the_authenticated_program_map(self):
        for name in ('hermes/hermes-source-manifest.json', 'lifeos/lifeos-source-manifest.json'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                package, certificate, marker, _ = self.package(Path(temp))
                (package / name).write_text('{"tree_sha256":"changed"}')
                with self.assertRaisesRegex(ReleaseRejected, 'native source manifest'):
                    validate_package(package, certificate)
                self.assertFalse(marker.exists())

    def test_authenticated_archive_requires_one_bounded_regular_manifest(self):
        for change in ('missing', 'duplicate', 'oversized', 'link'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temp:
                package, certificate, marker, archive = self.package(Path(temp))
                with tarfile.open(archive, 'w:gz') as target:
                    count = 0 if change == 'missing' else 2 if change == 'duplicate' else 1
                    for _ in range(count):
                        content = ((package / 'DAILY-CANDIDATE.json').read_bytes()
                            if change != 'oversized' else b' ' * (512 * 1024 + 1))
                        member = tarfile.TarInfo('DAILY-CANDIDATE.json')
                        if change == 'link':
                            member.type = tarfile.SYMTYPE
                            member.linkname = 'synthetic-link'
                        else:
                            member.size = len(content)
                        target.addfile(member, io.BytesIO(content))
                certificate.update(archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                    archive_bytes=archive.stat().st_size)
                with self.assertRaisesRegex(ReleaseRejected, 'authenticated archive'):
                    validate_package(package, certificate)
                self.assertFalse(marker.exists())

    def package(self, root):
        package = root / 'package'
        package.mkdir(mode=0o700)
        marker = root / 'candidate-executed'
        source = ('from pathlib import Path\nfrom types import SimpleNamespace\n'
            f'Path({str(marker)!r}).write_text("synthetic import marker")\n'
            'def memory_module(name):\n'
            '    return SimpleNamespace(versions=lambda package: "0.4.2-rc.1")\n'
            'def validate_supported_hermes(path):\n'
            '    return {"base_commit": "hermes", "patches": []}\n'
            'def validate_prepared_lifeos(path):\n'
            '    return {"upstream_commit": "lifeos", "patches": []}\n')
        files = {'lifeos_hook_bridge/install_source.py': source,
            'optional/lifeos_release_manager/manager.py': '# Synthetic manager\n',
            'python-runtime/pyproject.toml': '# Synthetic closure\n',
            'python-runtime/uv.lock': '# Synthetic lock\n',
            'hermes/hermes-source-manifest.json': '{}',
            'lifeos/lifeos-source-manifest.json': '{}'}
        for name, content in files.items():
            path = package / name
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            path.write_text(content)
        manifest = {'head': 'a' * 40, 'version': '0.4.2-rc.1',
            'plugin_files': {name: hashlib.sha256(content.encode()).hexdigest() for name, content in files.items() if name.startswith('lifeos_hook_bridge/')},
            'manager_files': {'manager.py': hashlib.sha256(files['optional/lifeos_release_manager/manager.py'].encode()).hexdigest()},
            'prepared_manifest_files': {name: hashlib.sha256(content.encode()).hexdigest() for name, content in files.items() if name.endswith('-source-manifest.json')},
            'python_runtime_files': {Path(name).name: hashlib.sha256(content.encode()).hexdigest() for name, content in files.items() if name.startswith('python-runtime/')}}
        (package / 'DAILY-CANDIDATE.json').write_text(json.dumps(manifest))
        download = root / 'download'
        download.mkdir(mode=0o700)
        archive = download / '0.4.2-rc.1-aaaaaaaa.tgz'
        with tarfile.open(archive, 'w:gz') as target:
            for path in sorted(package.iterdir()):
                target.add(path, arcname=path.name)
        certificate = {'format': 1, 'status': 'QUALIFIED', 'program_commit': manifest['head'],
            'version': manifest['version'], 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            'archive_bytes': archive.stat().st_size, 'hermes_base': 'hermes', 'lifeos_base': 'lifeos',
            'hermes_patch_count': 0, 'lifeos_patch_count': 0}
        return package, certificate, marker, archive

    def test_isolated_stock_python_does_not_write_bytecode_into_the_reviewed_bridge(self):
        with tempfile.TemporaryDirectory() as temp:
            bridge = Path(temp) / 'bridge'
            shutil.copytree(Path(__file__).resolve().parents[1] / 'lifeos_hook_bridge', bridge,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            code = ('import sys\nfrom pathlib import Path\n'
                    'sys.path.insert(0,sys.argv[1])\n'
                    'from optional.lifeos_release_manager.release_stage import load_bridge\n'
                    'assert sys.flags.ignore_environment\n'
                    'source=load_bridge(Path(sys.argv[2]))\n'
                    'source.memory_module("release_version")\n')
            result = subprocess.run([sys.executable, '-I', '-c', code,
                str(Path(__file__).resolve().parents[1]), str(bridge)],
                env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, '')
            self.assertEqual(list(bridge.rglob('*.pyc')), [])

    def test_runtime_source_seal_accepts_boot_outputs_and_refuses_program_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            program = root / 'program.py'
            program.write_text('qualified')
            expected = runtime_source_fingerprint(root)
            generated = root / '.hermes'
            generated.mkdir(mode=0o775)
            (generated / 'bin').mkdir(mode=0o775)
            marker = root / '.bytecode-fingerprint'
            marker.write_text('native boot marker')
            marker.chmod(0o664)
            self.assertEqual(runtime_source_fingerprint(root), expected)
            program.write_text('changed')
            self.assertNotEqual(runtime_source_fingerprint(root), expected)
            program.write_text('qualified')
            (root / 'added.py').write_text('unrecorded program')
            self.assertNotEqual(runtime_source_fingerprint(root), expected)

    def test_exact_file_map_refuses_extra_changed_or_escaping_program_files(self):
        for change in ('changed', 'extra', 'escaping', 'link'):
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                (root / 'program.py').write_text('qualified')
                files = {'program.py': hashlib.sha256(b'qualified').hexdigest()}
                if change == 'changed':
                    (root / 'program.py').write_text('changed')
                elif change == 'extra':
                    (root / 'extra.py').write_text('extra')
                elif change == 'link':
                    (root / 'program.py').unlink()
                    (root / 'program.py').symlink_to('/etc/passwd')
                else:
                    files = {'../outside': 'a' * 64}
                with self.assertRaises(ReleaseRejected):
                    validate_files(root, files)

    def test_program_validation_accepts_exact_regular_files_and_ignores_bytecode(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'program.py').write_text('qualified')
            (root / '__pycache__').mkdir()
            (root / '__pycache__/program.pyc').write_bytes(b'generated')
            validate_files(root, {'program.py': hashlib.sha256(b'qualified').hexdigest()})

    def test_qualified_source_validation_refuses_unrecorded_bytecode(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'program.py').write_text('qualified')
            (root / '__pycache__').mkdir()
            (root / '__pycache__/program.pyc').write_bytes(b'unrecorded')
            with self.assertRaises(ReleaseRejected):
                validate_files(root, {'program.py': hashlib.sha256(b'qualified').hexdigest()}, forbid_bytecode=True)

    def test_certificate_mismatch_refuses_before_candidate_module_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'DAILY-CANDIDATE.json').write_text(json.dumps({'head': 'a' * 40, 'version': '0.4.0'}))
            with self.assertRaises(ReleaseRejected):
                validate_package(root, {'program_commit': 'b' * 40, 'version': '0.4.0'})

    def test_missing_frozen_dependency_closure_refuses_before_candidate_module_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'DAILY-CANDIDATE.json').write_text(json.dumps({'head': 'a' * 40, 'version': '0.4.0'}))
            with self.assertRaisesRegex(ReleaseRejected, 'dependency closure'):
                validate_package(root, {'format': 1, 'status': 'QUALIFIED', 'program_commit': 'a' * 40, 'version': '0.4.0'})


class UserRuntimeDirectoryTests(unittest.TestCase):
    def test_runtime_directory_is_the_account_systemd_runtime_directory(self):
        from optional.lifeos_release_manager.release_stage import user_runtime_directory
        self.assertEqual(user_runtime_directory(), '/run/user/' + str(os.getuid()))
