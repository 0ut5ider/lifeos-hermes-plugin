# ABOUTME: Checks machine comparisons of native and Hermes outcome artifacts.
# ABOUTME: Refuses missing fields and changed effects in a paired case.

import json
import tempfile
import unittest
from pathlib import Path

from scripts.compare_parity import compare_manifest


class CompareParityTests(unittest.TestCase):
    def test_recorded_permission_outcomes_match(self):
        manifest = Path(__file__).resolve().parents[1] / "docs/parity/paired-permission-rewrites.json"
        self.assertEqual(compare_manifest(manifest), [])

    def test_compares_final_tool_input_and_file_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "native.json").write_text(json.dumps({
                "post_tool_input": {"file_path": "/native/rewritten.txt", "content": "MODIFIED"},
                "original_exists": False,
            }))
            (root / "hermes.json").write_text(json.dumps({
                "effective_args": {"path": "/hermes/rewritten.txt", "content": "MODIFIED"},
                "original_exists": False,
            }))
            manifest = root / "cases.json"
            manifest.write_text(json.dumps({"version": 1, "cases": [{
                "id": "file-rewrite", "native": "native.json", "hermes": "hermes.json",
                "fields": {
                    "target": {"native": "post_tool_input.file_path", "hermes": "effective_args.path",
                               "normalize": "basename", "expected": "rewritten.txt"},
                    "content": {"native": "post_tool_input.content", "hermes": "effective_args.content",
                                "expected": "MODIFIED"},
                    "original_exists": {"native": "original_exists", "hermes": "original_exists",
                                        "expected": False},
                },
            }]}))
            self.assertEqual(compare_manifest(manifest), [])

            (root / "hermes.json").write_text(json.dumps({
                "effective_args": {"path": "/hermes/rewritten.txt", "content": "WRONG"},
                "original_exists": False,
            }))
            self.assertTrue(any("content" in issue for issue in compare_manifest(manifest)))

    def test_missing_field_fails_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "native.json").write_text(json.dumps({"effect": True}))
            (root / "hermes.json").write_text("{}")
            manifest = root / "cases.json"
            manifest.write_text(json.dumps({"version": 1, "cases": [{
                "id": "missing", "native": "native.json", "hermes": "hermes.json",
                "fields": {"effect": {"native": "effect", "hermes": "effect", "expected": True}},
            }]}))
            self.assertTrue(any("missing" in issue for issue in compare_manifest(manifest)))


if __name__ == "__main__":
    unittest.main()
