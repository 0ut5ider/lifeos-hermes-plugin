# ABOUTME: Exercises a coordinated LifeOS update and rollback on disposable directories.
# ABOUTME: Verifies user data, Hermes mount files, and the baseline across failures.

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lifeos_hook_bridge.native_capabilities import capability_record, supports_task_count, RECORD_NAME

from lifeos_hook_bridge.update_transaction import (
    UpdateTransactionError, apply_update, recover_update, restore_update, validate_restore,
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class UpdateTransactionTests(unittest.TestCase):
    def test_apply_stop_crash_has_a_recoverable_durable_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(Path(directory))
            code = ('import os, signal, sys\nfrom pathlib import Path\n'
                    'from lifeos_hook_bridge.update_transaction import apply_update\n'
                    'def stopped():\n    os.kill(os.getpid(), signal.SIGKILL)\n'
                    'apply_update(*[Path(arg) for arg in sys.argv[1:]], stop=stopped, start=lambda: None, '
                    'mount=lambda: None, renew=lambda a,b: None, verify=lambda: None)\n')
            process = subprocess.run([sys.executable, '-c', code, *map(str,
                (installed, hermes, prior, selected, reference, baseline, snapshot))],
                capture_output=True, text=True, timeout=30)
            self.assertEqual(process.returncode, -signal.SIGKILL, process.stderr)
            self.assertEqual(process.stderr, '')
            self.assertEqual(json.loads((snapshot / 'manifest.json').read_text())['state'], 'stopped')
            events, stop, start, _, _, _ = self.callbacks(hermes, baseline)
            result = recover_update(snapshot, stop=stop, start=start, verify=lambda: events.append('verify'))
            self.assertEqual(result['state'], 'rolled_back')
            self.assertEqual(events, ['stop', 'start', 'verify'])
            self.assertEqual((installed / 'hooks/owned.ts').read_text(), 'owned-v1')
            self.assertEqual((hermes / 'config.yaml').read_text(), 'prior config')
            self.assertEqual((installed / 'LIFEOS/MEMORY/user.txt').read_text(), 'private memory')

    def test_restore_stop_crash_recovery_preserves_the_selected_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(Path(directory))
            events, stop, start, mount, renew, verify = self.callbacks(hermes, baseline)
            apply_update(installed, hermes, prior, selected, reference, baseline, snapshot,
                         stop=stop, start=start, mount=mount, renew=renew, verify=verify)
            code = ('import os, signal, sys\nfrom pathlib import Path\n'
                    'from lifeos_hook_bridge.update_transaction import restore_update\n'
                    'def stopped():\n    os.kill(os.getpid(), signal.SIGKILL)\n'
                    'restore_update(Path(sys.argv[1]), stop=stopped, start=lambda: None, verify=lambda: None)\n')
            process = subprocess.run([sys.executable, '-c', code, str(snapshot)],
                                     capture_output=True, text=True, timeout=30)
            self.assertEqual(process.returncode, -signal.SIGKILL, process.stderr)
            self.assertEqual(process.stderr, '')
            self.assertEqual(json.loads((snapshot / 'manifest.json').read_text())['state'], 'restore_stopping')
            (hermes / 'config.yaml').write_text('Synthetic edit after interruption')
            (installed / 'LIFEOS/MEMORY/user.txt').write_text('Synthetic later memory')
            events.clear()
            result = recover_update(snapshot, stop=stop, start=start, verify=lambda: events.append('verify'))
            self.assertEqual(result['state'], 'applied')
            self.assertEqual(events, ['start', 'verify'])
            self.assertEqual((installed / 'hooks/owned.ts').read_text(), 'owned-v2')
            self.assertEqual((hermes / 'config.yaml').read_text(), 'Synthetic edit after interruption')
            self.assertEqual((installed / 'LIFEOS/MEMORY/user.txt').read_text(), 'Synthetic later memory')
            self.assertTrue((snapshot / 'live-prior').is_dir())
            self.assertFalse((snapshot / 'restored-selected').exists())

    def test_failed_restart_keeps_restore_stop_intent_recoverable(self):
        with tempfile.TemporaryDirectory() as directory:
            installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(Path(directory))
            events, stop, start, mount, renew, verify = self.callbacks(hermes, baseline)
            apply_update(installed, hermes, prior, selected, reference, baseline, snapshot,
                         stop=stop, start=start, mount=mount, renew=renew, verify=verify)
            def stopped_and_changed():
                stop()
                (hermes / 'config.yaml').write_text('Synthetic stop edit')
            def unavailable():
                raise RuntimeError('Synthetic start failure')
            with self.assertRaisesRegex(RuntimeError, 'Synthetic start failure'):
                restore_update(snapshot, stop=stopped_and_changed, start=unavailable, verify=lambda: None)
            self.assertEqual(json.loads((snapshot / 'manifest.json').read_text())['state'], 'restore_stopping')
            recovered = recover_update(snapshot, stop=stop, start=start, verify=lambda: None)
            self.assertEqual(recovered['state'], 'applied')
            self.assertEqual((hermes / 'config.yaml').read_text(), 'Synthetic stop edit')

    @unittest.skipUnless(os.environ.get("LIFEOS_TASK_HOOK_PATH"), "Prepared native TaskGovernance is required")
    def test_capability_record_applies_and_restores_with_native_hook_files(self):
        with tempfile.TemporaryDirectory() as directory:
            installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(Path(directory))
            name = "hooks/TaskGovernance.hook.ts"
            for root in (installed, prior):
                (root / name).write_text("unpatched native hook")
            for root in (selected, reference):
                (root / name).write_bytes(Path(os.environ["LIFEOS_TASK_HOOK_PATH"]).read_bytes())
                (root / "hooks" / RECORD_NAME).write_text(json.dumps(capability_record()))
            data = json.loads(baseline.read_text())
            data["files"][name] = digest(installed / name)
            baseline.write_text(json.dumps(data))
            self.assertFalse(supports_task_count(installed))
            _, stop, start, mount, renew, verify = self.callbacks(hermes, baseline)
            result = apply_update(installed, hermes, prior, selected, reference, baseline, snapshot,
                                  stop=stop, start=start, mount=mount, renew=renew, verify=verify)
            self.assertEqual(result["state"], "applied")
            self.assertTrue(supports_task_count(installed))
            restored = restore_update(snapshot, stop=stop, start=start, verify=lambda: None)
            self.assertEqual(restored["state"], "rolled_back")
            self.assertFalse(supports_task_count(installed))
            self.assertFalse((installed / "hooks" / RECORD_NAME).exists())
            self.assertEqual((installed / name).read_text(), "unpatched native hook")
            self.assertEqual((installed / "LIFEOS/MEMORY/user.txt").read_text(), "private memory")

    def fixture(self, root):
        installed = root / "home/.claude"
        hermes = root / "home/.hermes"
        prior = root / "prior"
        selected = root / "selected"
        reference = root / "reference/.claude"
        baseline = root / "home/state/baseline.json"
        snapshot = root / "home/state/update"
        for path in (installed, hermes, prior, selected, reference):
            path.mkdir(parents=True)
        for path in (installed, prior, selected, reference):
            (path / "hooks").mkdir()
        (installed / "hooks/owned.ts").write_text("owned-v1")
        (installed / "LIFEOS/MEMORY").mkdir(parents=True)
        (installed / "LIFEOS/MEMORY/user.txt").write_text("private memory")
        (installed / "settings.json").write_text(json.dumps({"model": "private", "hooks": {
            "Stop": [{"matcher": "", "hooks": [
                {"type": "command", "command": "old.sh"},
                {"type": "command", "command": "foreign.sh"},
            ]}],
        }}))
        (installed / "package.json").write_text('{"version":"1"}')
        (installed / "bun.lock").write_text("old-lock")
        (installed / "node_modules").mkdir()
        (installed / "node_modules/library.txt").write_text("old-library")
        (prior / "hooks/owned.ts").write_text("owned-v1")
        (selected / "hooks/owned.ts").write_text("owned-v2")
        (reference / "hooks/owned.ts").write_text("owned-v2")
        (prior / "hooks/hooks.json").write_text(json.dumps({"hooks": {
            "Stop": [{"hooks": [{"type": "command", "command": "old.sh"}]}],
        }}))
        (selected / "hooks/hooks.json").write_text(json.dumps({"hooks": {
            "Stop": [{"hooks": [{"type": "command", "command": "new.sh"}]}],
        }}))
        (reference / "hooks/hooks.json").write_text((selected / "hooks/hooks.json").read_text())
        (prior / "package.json").write_text('{"version":"1"}')
        (selected / "package.json").write_text('{"version":"2"}')
        (reference / "package.json").write_text('{"version":"2"}')
        (reference / "bun.lock").write_text("new-lock")
        (reference / "node_modules").mkdir()
        (reference / "node_modules/library.txt").write_text("new-library")
        (hermes / "config.yaml").write_text("prior config")
        (hermes / "SOUL.md").write_text("prior soul")
        baseline.parent.mkdir(parents=True)
        baseline.write_text(json.dumps({"installed_root": str(installed.resolve()), "files": {
            "hooks/owned.ts": digest(installed / "hooks/owned.ts"),
        }}))
        return installed, hermes, prior, selected, reference, baseline, snapshot

    def callbacks(self, hermes, baseline, *, fail_verify=False):
        events = []

        def stop():
            events.append("stop")

        def start():
            events.append("start")

        def mount():
            (hermes / "config.yaml").write_text("selected config")
            (hermes / "SOUL.md").write_text("selected soul")

        def renew(installed, selected):
            baseline.write_text("selected baseline")

        def verify():
            events.append("verify")
            if fail_verify:
                raise RuntimeError("selected gateway failed")

        return events, stop, start, mount, renew, verify

    def test_applies_update_and_immediate_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(Path(directory))
            events, stop, start, mount, renew, verify = self.callbacks(hermes, baseline)
            result = apply_update(installed, hermes, prior, selected, reference, baseline, snapshot,
                                  stop=stop, start=start, mount=mount, renew=renew, verify=verify)
            self.assertEqual(result["state"], "applied")
            self.assertEqual((installed / "hooks/owned.ts").read_text(), "owned-v2")
            self.assertEqual((installed / "node_modules/library.txt").read_text(), "new-library")
            self.assertEqual((installed / "LIFEOS/MEMORY/user.txt").read_text(), "private memory")
            self.assertEqual(json.loads((installed / "settings.json").read_text())["hooks"]["Stop"][0]
                             ["hooks"][0]["command"], "new.sh")
            self.assertEqual(baseline.read_text(), "selected baseline")
            self.assertEqual(events, ["stop", "start", "verify"])

            restored = restore_update(snapshot, stop=stop, start=start, verify=lambda: None)
            self.assertEqual(restored["state"], "rolled_back")
            self.assertEqual((installed / "hooks/owned.ts").read_text(), "owned-v1")
            self.assertEqual((installed / "LIFEOS/MEMORY/user.txt").read_text(), "private memory")
            self.assertEqual((hermes / "SOUL.md").read_text(), "prior soul")
            self.assertIn("installed_root", baseline.read_text())

    def test_verification_failure_restores_all_prior_state(self):
        with tempfile.TemporaryDirectory() as directory:
            installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(Path(directory))
            before = baseline.read_bytes()
            events, stop, start, mount, renew, verify = self.callbacks(hermes, baseline,
                                                                        fail_verify=True)
            with self.assertRaisesRegex(UpdateTransactionError, "selected gateway failed"):
                apply_update(installed, hermes, prior, selected, reference, baseline, snapshot,
                             stop=stop, start=start, mount=mount, renew=renew, verify=verify)
            self.assertEqual((installed / "hooks/owned.ts").read_text(), "owned-v1")
            self.assertEqual((installed / "node_modules/library.txt").read_text(), "old-library")
            self.assertEqual((installed / "LIFEOS/MEMORY/user.txt").read_text(), "private memory")
            self.assertEqual((hermes / "config.yaml").read_text(), "prior config")
            self.assertEqual(baseline.read_bytes(), before)
            self.assertEqual(json.loads((snapshot / "manifest.json").read_text())["state"], "rolled_back")

    def test_restore_preserves_external_memory_and_audit_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(root)
            external = root / 'owner-data'
            (external / 'MEMORY/OBSERVABILITY').mkdir(parents=True)
            shutil.copy2(installed / 'LIFEOS/MEMORY/user.txt', external / 'MEMORY/user.txt')
            shutil.rmtree(installed / 'LIFEOS/MEMORY')
            (installed / 'LIFEOS/MEMORY').symlink_to(external / 'MEMORY', target_is_directory=True)
            (installed / 'LIFEOS/USER').symlink_to(external, target_is_directory=True)
            audit = external / 'MEMORY/OBSERVABILITY/config-changes.jsonl'
            audit.write_text('{"event":"before-update"}\n')
            _, stop, start, mount, renew, verify = self.callbacks(hermes, baseline)
            apply_update(installed, hermes, prior, selected, reference, baseline, snapshot,
                         stop=stop, start=start, mount=mount, renew=renew, verify=verify)
            audit.write_text(audit.read_text() + '{"event":"after-update"}\n')
            (external / 'MEMORY/user.txt').unlink()
            (external / 'MEMORY/current.txt').write_text('Synthetic current fact')
            before = audit.read_bytes()
            result = restore_update(snapshot, stop=stop, start=start, verify=lambda: None)
            self.assertEqual(result['state'], 'rolled_back')
            self.assertEqual((installed / 'hooks/owned.ts').read_text(), 'owned-v1')
            self.assertEqual(audit.read_bytes(), before)
            self.assertEqual((installed / 'LIFEOS/MEMORY/current.txt').read_text(), 'Synthetic current fact')
            self.assertFalse((installed / 'LIFEOS/MEMORY/user.txt').exists())
            self.assertEqual((installed / 'LIFEOS/MEMORY').resolve(), external / 'MEMORY')

    def test_restore_refuses_embedded_memory_and_audit_changes(self):
        for name in ('user.txt', 'OBSERVABILITY/config-changes.jsonl'):
            with self.subTest(file=name), tempfile.TemporaryDirectory() as directory:
                installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(Path(directory))
                file = installed / 'LIFEOS/MEMORY' / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('Synthetic before update')
                events, stop, start, mount, renew, verify = self.callbacks(hermes, baseline)
                apply_update(installed, hermes, prior, selected, reference, baseline, snapshot,
                             stop=stop, start=start, mount=mount, renew=renew, verify=verify)
                file.write_text('Synthetic after update')
                with self.assertRaisesRegex(UpdateTransactionError, 'User data changed'):
                    restore_update(snapshot, stop=stop, start=start, verify=lambda: None)
                self.assertEqual(file.read_text(), 'Synthetic after update')
                self.assertEqual(events, ['stop', 'start', 'verify'])

    def test_restore_refuses_replaced_external_data_bindings(self):
        for mutation in ('link', 'target', 'prior-link'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(root)
                external = root / 'owner-memory'
                shutil.move(installed / 'LIFEOS/MEMORY', external)
                (installed / 'LIFEOS/MEMORY').symlink_to(external, target_is_directory=True)
                events, stop, start, mount, renew, verify = self.callbacks(hermes, baseline)
                apply_update(installed, hermes, prior, selected, reference, baseline, snapshot,
                             stop=stop, start=start, mount=mount, renew=renew, verify=verify)
                substitute = root / 'substitute'
                shutil.copytree(external, substitute)
                if mutation == 'target':
                    external.rename(root / 'retained-owner-memory')
                    substitute.rename(external)
                else:
                    link = (snapshot / 'live-prior' if mutation == 'prior-link' else installed) / 'LIFEOS/MEMORY'
                    link.unlink()
                    link.symlink_to(substitute, target_is_directory=True)
                with self.assertRaisesRegex(UpdateTransactionError, 'User data binding changed'):
                    restore_update(snapshot, stop=stop, start=start, verify=lambda: None)
                self.assertEqual((installed / 'hooks/owned.ts').read_text(), 'owned-v2')
                self.assertEqual(events, ['stop', 'start', 'verify'])

    def test_restore_preserves_later_profile_edits_and_modes(self):
        mutations = {
            'configuration': lambda home: (home / 'config.yaml').write_text('Synthetic later model choice'),
            'new environment': lambda home: (home / '.env').write_text('SYNTHETIC_KEY=later-value\n'),
            'removed prompt': lambda home: (home / 'SOUL.md').unlink(),
            'file permissions': lambda home: (home / 'config.yaml').chmod(0o600),
            'plugin edit': lambda home: (home / 'plugins/lifeos/guard.py').write_text('Synthetic later guard'),
            'plugin addition': lambda home: (home / 'plugins/lifeos/additional.py').write_text('Synthetic addition'),
            'plugin removal': lambda home: (home / 'plugins/lifeos/guard.py').unlink(),
            'plugin directory': lambda home: (home / 'plugins/lifeos/empty').mkdir(),
            'directory permissions': lambda home: (home / 'plugins/lifeos').chmod(0o700),
        }
        for name, mutate in mutations.items():
            with self.subTest(change=name), tempfile.TemporaryDirectory() as directory:
                installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(Path(directory))
                (hermes / 'plugins/lifeos').mkdir(parents=True)
                (hermes / 'plugins/lifeos/guard.py').write_text('Synthetic installed guard')
                events, stop, start, mount, renew, verify = self.callbacks(hermes, baseline)
                apply_update(installed, hermes, prior, selected, reference, baseline, snapshot,
                             stop=stop, start=start, mount=mount, renew=renew, verify=verify)
                mutate(hermes)
                before = {str(path.relative_to(hermes)): (path.read_bytes(), path.stat().st_mode)
                          for path in hermes.rglob('*') if path.is_file()}
                journal = (snapshot / 'manifest.json').read_bytes()
                with self.assertRaisesRegex(UpdateTransactionError, 'Hermes profile changed'):
                    validate_restore(snapshot, installed=installed)
                with self.assertRaisesRegex(UpdateTransactionError, 'Hermes profile changed'):
                    restore_update(snapshot, stop=stop, start=start, verify=lambda: None)
                self.assertEqual(events, ['stop', 'start', 'verify'])
                self.assertEqual((snapshot / 'manifest.json').read_bytes(), journal)
                self.assertEqual(before, {str(path.relative_to(hermes)): (path.read_bytes(), path.stat().st_mode)
                                         for path in hermes.rglob('*') if path.is_file()})
                self.assertEqual((installed / 'hooks/owned.ts').read_text(), 'owned-v2')

    def test_restore_requires_post_update_profile_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(Path(directory))
            events, stop, start, mount, renew, verify = self.callbacks(hermes, baseline)
            apply_update(installed, hermes, prior, selected, reference, baseline, snapshot,
                         stop=stop, start=start, mount=mount, renew=renew, verify=verify)
            manifest = json.loads((snapshot / 'manifest.json').read_text())
            manifest.pop('mount_state', None)
            (snapshot / 'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(UpdateTransactionError, 'profile restore metadata'):
                restore_update(snapshot, stop=stop, start=start, verify=lambda: None)
            self.assertEqual(events, ['stop', 'start', 'verify'])
            self.assertEqual((hermes / 'config.yaml').read_text(), 'selected config')

    def test_restore_rechecks_profile_after_stopping_the_gateway(self):
        with tempfile.TemporaryDirectory() as directory:
            installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(Path(directory))
            events, stop, start, mount, renew, verify = self.callbacks(hermes, baseline)
            apply_update(installed, hermes, prior, selected, reference, baseline, snapshot,
                         stop=stop, start=start, mount=mount, renew=renew, verify=verify)
            journal = (snapshot / 'manifest.json').read_bytes()
            def stop_and_edit():
                stop()
                (hermes / 'config.yaml').write_text('Synthetic edit while stopping')
            with self.assertRaisesRegex(UpdateTransactionError, 'Hermes profile changed'):
                restore_update(snapshot, stop=stop_and_edit, start=start, verify=lambda: None)
            self.assertEqual((snapshot / 'manifest.json').read_bytes(), journal)
            self.assertEqual((hermes / 'config.yaml').read_text(), 'Synthetic edit while stopping')
            self.assertEqual((installed / 'hooks/owned.ts').read_text(), 'owned-v2')
            self.assertEqual(events, ['stop', 'start', 'verify', 'stop', 'start'])

    def test_restore_archives_a_write_that_races_with_profile_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(Path(directory))
            _, stop, start, mount, renew, verify = self.callbacks(hermes, baseline)
            apply_update(installed, hermes, prior, selected, reference, baseline, snapshot,
                         stop=stop, start=start, mount=mount, renew=renew, verify=verify)
            original_replace = os.replace
            def write_during_move(source, destination):
                if Path(source) == hermes / 'config.yaml' and Path(destination).parent.name.startswith('.lifeos-restore-'):
                    Path(source).write_text('Synthetic edit after the final check')
                return original_replace(source, destination)
            with patch('lifeos_hook_bridge.update_transaction.os.replace', side_effect=write_during_move):
                restored = restore_update(snapshot, stop=stop, start=start, verify=lambda: None)
            self.assertEqual(restored['state'], 'rolled_back')
            archive = Path(restored['profile_archive'])
            self.assertEqual(archive.stat().st_mode & 0o777, 0o700)
            targets = json.loads((archive / 'archive-manifest.json').read_text())['targets']
            self.assertEqual(Path(targets['config.yaml']).read_text(), 'Synthetic edit after the final check')
            self.assertEqual(Path(targets['baseline.json']).read_text(), 'selected baseline')
            self.assertEqual((hermes / 'config.yaml').read_text(), 'prior config')

    def test_restore_retains_a_profile_edit_after_the_program_swap(self):
        with tempfile.TemporaryDirectory() as directory:
            installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(Path(directory))
            events, stop, start, mount, renew, verify = self.callbacks(hermes, baseline)
            apply_update(installed, hermes, prior, selected, reference, baseline, snapshot,
                         stop=stop, start=start, mount=mount, renew=renew, verify=verify)
            events.clear()
            original_replace = os.replace
            def edit_after_swap(source, destination):
                result = original_replace(source, destination)
                if Path(source) == installed and Path(destination) == snapshot / 'restored-selected':
                    (hermes / 'config.yaml').write_text('Synthetic edit after program swap')
                return result
            with patch('lifeos_hook_bridge.update_transaction.os.replace', side_effect=edit_after_swap):
                result = restore_update(snapshot, stop=stop, start=start, verify=lambda: events.append('verify'))
            self.assertEqual(result['state'], 'rolled_back')
            self.assertEqual(events, ['stop', 'start', 'verify'])
            targets = json.loads((Path(result['profile_archive']) / 'archive-manifest.json').read_text())['targets']
            self.assertEqual(Path(targets['config.yaml']).read_text(), 'Synthetic edit after program swap')
            self.assertEqual((hermes / 'config.yaml').read_text(), 'prior config')

    def test_profile_and_baseline_restore_across_filesystems(self):
        # /dev/shm supplies a real second filesystem, so EXDEV is not simulated.
        self.assertTrue(Path('/dev/shm').is_dir(), 'A second filesystem is required for this gate')
        for action in ('restore', 'rollback', 'recover'):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as directory, \
                    tempfile.TemporaryDirectory(dir='/dev/shm') as alternate:
                installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(Path(directory))
                remote = Path(alternate)
                profile = remote / 'hermes'
                shutil.copytree(hermes, profile)
                moved_baseline = remote / 'state/baseline.json'
                moved_baseline.parent.mkdir()
                shutil.copy2(baseline, moved_baseline)
                self.assertNotEqual(profile.stat().st_dev, snapshot.parent.stat().st_dev)
                (profile / '.env').write_text('SYNTHETIC_KEY=private-value\n')
                (profile / '.env').chmod(0o600)
                (profile / 'plugins/lifeos').mkdir(parents=True)
                (profile / 'plugins/lifeos/guard.py').write_text('Synthetic guard')
                before = moved_baseline.read_bytes()
                events, stop, start, mount, renew, verify = self.callbacks(profile, moved_baseline,
                                                                           fail_verify=action == 'rollback')
                options = dict(stop=stop, start=start, mount=mount, renew=renew, verify=verify)
                if action == 'rollback':
                    with self.assertRaisesRegex(UpdateTransactionError, 'selected gateway failed'):
                        apply_update(installed, profile, prior, selected, reference, moved_baseline, snapshot, **options)
                else:
                    apply_update(installed, profile, prior, selected, reference, moved_baseline, snapshot, **options)
                    if action == 'recover':
                        original_replace = os.replace
                        def fail_baseline(source, destination):
                            if Path(source).name == 'baseline.json.restore' and Path(destination) == moved_baseline:
                                raise OSError('Synthetic interrupted baseline publication')
                            return original_replace(source, destination)
                        with patch('lifeos_hook_bridge.update_transaction.os.replace', side_effect=fail_baseline):
                            with self.assertRaisesRegex(OSError, 'interrupted baseline'):
                                restore_update(snapshot, stop=stop, start=start, verify=lambda: None)
                        recover_update(snapshot, stop=stop, start=start, verify=lambda: None)
                    else:
                        restore_update(snapshot, stop=stop, start=start, verify=lambda: None)
                self.assertEqual((installed / 'hooks/owned.ts').read_text(), 'owned-v1')
                self.assertEqual((profile / 'config.yaml').read_text(), 'prior config')
                self.assertEqual((profile / '.env').read_text(), 'SYNTHETIC_KEY=private-value\n')
                self.assertEqual((profile / '.env').stat().st_mode & 0o777, 0o600)
                self.assertEqual(moved_baseline.read_bytes(), before)
                self.assertEqual(json.loads((snapshot / 'manifest.json').read_text())['state'], 'rolled_back')
                indexes = list(snapshot.glob('mount-before-restore/*/archive-manifest.json'))
                self.assertTrue(indexes)
                for index in indexes:
                    for name, path in json.loads(index.read_text())['targets'].items():
                        saved = Path(path)
                        self.assertEqual(saved.parent.stat().st_mode & 0o777, 0o700)
                        self.assertEqual(saved.stat().st_dev, remote.stat().st_dev)
                        if name == '.env':
                            self.assertEqual(saved.read_text(), 'SYNTHETIC_KEY=private-value\n')

    def test_restore_archive_survives_process_death_before_profile_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(Path(directory))
            _, stop, start, mount, renew, verify = self.callbacks(hermes, baseline)
            apply_update(installed, hermes, prior, selected, reference, baseline, snapshot,
                         stop=stop, start=start, mount=mount, renew=renew, verify=verify)
            code = (
                'import os, signal, sys\n'
                'from pathlib import Path\n'
                'from unittest.mock import patch\n'
                'from lifeos_hook_bridge.update_transaction import restore_update\n'
                'snapshot, profile = map(Path, sys.argv[1:])\n'
                'original = os.replace\n'
                'def interrupted(source, destination):\n'
                '    original(source, destination)\n'
                '    if Path(source) == profile / "config.yaml":\n'
                '        os.kill(os.getpid(), signal.SIGKILL)\n'
                'with patch("lifeos_hook_bridge.update_transaction.os.replace", side_effect=interrupted):\n'
                '    restore_update(snapshot, stop=lambda: None, start=lambda: None, verify=lambda: None)\n'
            )
            process = subprocess.run([sys.executable, '-c', code, str(snapshot), str(hermes)],
                                     capture_output=True, text=True, timeout=30)
            self.assertEqual(process.returncode, -signal.SIGKILL, process.stderr)
            self.assertEqual(process.stderr, '')
            self.assertEqual(json.loads((snapshot / 'manifest.json').read_text())['state'], 'restoring')
            index, = snapshot.glob('mount-before-restore/*/archive-manifest.json')
            archived = Path(json.loads(index.read_text())['targets']['config.yaml'])
            self.assertEqual(archived.read_text(), 'selected config')
            self.assertFalse((hermes / 'config.yaml').exists())
            result = recover_update(snapshot, stop=stop, start=start, verify=lambda: None)
            self.assertEqual(result['state'], 'rolled_back')
            self.assertEqual(archived.read_text(), 'selected config')
            self.assertEqual((hermes / 'config.yaml').read_text(), 'prior config')
            self.assertEqual((installed / 'hooks/owned.ts').read_text(), 'owned-v1')

    def test_second_directory_rename_failure_restores_installed_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(Path(directory))
            events, stop, start, mount, renew, verify = self.callbacks(hermes, baseline)
            original_replace = __import__("os").replace

            def fail_selected_swap(source, destination):
                if Path(source) == snapshot / "staged" and Path(destination) == installed:
                    raise OSError("selected swap failed")
                return original_replace(source, destination)

            with patch("lifeos_hook_bridge.update_transaction.os.replace", side_effect=fail_selected_swap):
                with self.assertRaisesRegex(UpdateTransactionError, "selected swap failed"):
                    apply_update(installed, hermes, prior, selected, reference, baseline, snapshot,
                                 stop=stop, start=start, mount=mount, renew=renew, verify=verify)
            self.assertEqual((installed / "hooks/owned.ts").read_text(), "owned-v1")
            self.assertEqual((hermes / "config.yaml").read_text(), "prior config")
            self.assertEqual(json.loads((snapshot / "manifest.json").read_text())["state"], "rolled_back")

    def test_recovers_process_death_between_directory_renames(self):
        with tempfile.TemporaryDirectory() as directory:
            installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(Path(directory))
            snapshot.mkdir()
            (snapshot / "mount").mkdir()
            (snapshot / "mount/config.yaml").write_text("prior config")
            (snapshot / "mount/SOUL.md").write_text("prior soul")
            (snapshot / "baseline.json").write_bytes(baseline.read_bytes())
            (snapshot / "mount-manifest.json").write_text(json.dumps({"present": ["config.yaml", "SOUL.md"]}))
            (snapshot / "manifest.json").write_text(json.dumps({
                "state": "stopped", "installed": str(installed), "hermes_home": str(hermes),
                "baseline": str(baseline),
            }))
            installed.rename(snapshot / "live-prior")
            (hermes / "config.yaml").write_text("interrupted mount")
            baseline.write_text("interrupted baseline")
            events = []
            result = recover_update(snapshot, stop=lambda: events.append("stop"),
                                    start=lambda: events.append("start"),
                                    verify=lambda: events.append("verify"))
            self.assertEqual(result["state"], "rolled_back")
            self.assertEqual((installed / "hooks/owned.ts").read_text(), "owned-v1")
            self.assertEqual((hermes / "config.yaml").read_text(), "prior config")
            self.assertIn("installed_root", baseline.read_text())
            self.assertEqual(events, ["stop", "start", "verify"])
