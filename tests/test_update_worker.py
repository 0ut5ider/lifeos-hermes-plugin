# ABOUTME: Checks the update worker's source-ownership preflight.
# ABOUTME: Ensures a changed prior hook source is refused before the gateway stops.

import hashlib
import tempfile
import unittest
from pathlib import Path

from lifeos_hook_bridge.update_worker import check_prior_source, check_template_compatibility


class UpdateWorkerTests(unittest.TestCase):
    def test_changed_generated_templates_need_a_reviewed_migration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "old"
            new = root / "new"
            for source in (old, new):
                source.mkdir()
                (source / "CLAUDE.template.md").write_text("old instructions")
                (source / "settings.system.json").write_text('{"a":1}')
            check_template_compatibility(old, new)
            (new / "CLAUDE.template.md").write_text("new instructions")
            with self.assertRaisesRegex(ValueError, "CLAUDE template"):
                check_template_compatibility(old, new)
            (new / "CLAUDE.template.md").write_text("old instructions")
            (new / "settings.system.json").write_text('{"a":2}')
            with self.assertRaisesRegex(ValueError, "settings template"):
                check_template_compatibility(old, new)

    def test_prior_source_must_match_installed_hook_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            installed = root / ".claude"
            for path in (source / "hooks", installed / "hooks"):
                path.mkdir(parents=True)
            source_file = source / "hooks/hooks.json"
            installed_file = installed / "hooks/hooks.json"
            source_file.write_text('{"hooks":{}}')
            installed_file.write_bytes(source_file.read_bytes())
            baseline = {"source_root": str(source),
                        "files": {"hooks/hooks.json": hashlib.sha256(source_file.read_bytes()).hexdigest()}}
            check_prior_source(baseline, source, installed)
            source_file.write_text('{"hooks":{"Stop":[]}}')
            with self.assertRaisesRegex(ValueError, "prior hook source changed"):
                check_prior_source(baseline, source, installed)
