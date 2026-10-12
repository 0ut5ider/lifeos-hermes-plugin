# ABOUTME: Verifies complete package identities before staging dependencies or native programs.
# ABOUTME: Uses regular synthetic package files to exercise refusal before candidate code runs.
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from optional.lifeos_release_manager.release_stage import validate_files, validate_package, runtime_source_fingerprint
from optional.lifeos_release_manager.release_catalog import ReleaseRejected


class ReleaseStageTests(unittest.TestCase):
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
