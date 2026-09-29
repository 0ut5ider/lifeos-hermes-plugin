# ABOUTME: Checks that paired trace coverage reports missing and mismatched registrations.
# ABOUTME: Keeps private hook output out of the public parity evidence.

import json
import tempfile
import unittest
from pathlib import Path

from scripts.paired_coverage import build_coverage


class PairedCoverageTests(unittest.TestCase):
    def test_reports_matches_mismatches_and_unobserved_hooks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "registrations.csv"
            manifest.write_text("id,event,handler\nStop.1.1,Stop,a\nRead.1.1,Read,b\nEdit.1.1,Edit,c\n")
            native = root / "native.jsonl"
            hermes = root / "hermes.jsonl"
            native.write_text("\n".join(json.dumps(row) for row in (
                {"session_id": "n", "id": "Stop.1.1", "exit_code": 0,
                 "stdout_size": 0, "stderr_size": 0},
                {"session_id": "n", "id": "Read.1.1", "exit_code": 2,
                 "stdout_size": 0, "stderr_size": 5},
            )))
            hermes.write_text("\n".join(json.dumps(row) for row in (
                {"session_id": "h", "id": "Stop.1.1", "exit_code": 0,
                 "stdout_size": 0, "stderr_size": 0},
                {"session_id": "h", "id": "Read.1.1", "exit_code": 0,
                 "stdout_size": 0, "stderr_size": 5},
            )))
            report = build_coverage(manifest, [("probe", native, "n", hermes, "h")])
            self.assertEqual(report["counts"], {
                "matched_dispatch_and_output_shape": 1, "mismatch": 1,
                "observed_with_different_input": 0, "not_observed": 1,
            })
            self.assertNotIn("secret", json.dumps(report))
            self.assertEqual(report["registrations"][1]["cases"][0]["native"][0]["exit_code"], 2)

    def test_does_not_compare_stop_output_for_different_final_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "registrations.csv"
            manifest.write_text("id,event,handler\nStop.1.1,Stop,voice\n")
            native = root / "native.jsonl"
            hermes = root / "hermes.jsonl"
            for path, session, message, stderr_size in (
                (native, "n", "reply A", 0), (hermes, "h", "reply B", 7),
            ):
                path.write_text(json.dumps({"session_id": session, "id": "Stop.1.1",
                                            "last_assistant_message": message,
                                            "exit_code": 0, "stdout_size": 0,
                                            "stderr_size": stderr_size}))
            report = build_coverage(manifest, [("read", native, "n", hermes, "h")])
            self.assertEqual(report["counts"]["observed_with_different_input"], 1)
            self.assertIsNone(report["registrations"][0]["cases"][0]["transport_match"])

    def test_event_filter_excludes_incidental_permission_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "registrations.csv"
            manifest.write_text("id,event,handler\nPostToolUse.1.1,PostToolUse,a\nPermissionRequest.1.1,PermissionRequest,b\n")
            native = root / "native.jsonl"
            hermes = root / "hermes.jsonl"
            native.write_text(json.dumps({"session_id": "n", "id": "PostToolUse.1.1",
                                          "exit_code": 0, "stdout_size": 0, "stderr_size": 0}))
            hermes.write_text("\n".join(json.dumps(row) for row in (
                {"session_id": "h", "id": "PostToolUse.1.1", "exit_code": 0,
                 "stdout_size": 0, "stderr_size": 0},
                {"session_id": "h", "id": "PermissionRequest.1.1", "exit_code": 0,
                 "stdout_size": 0, "stderr_size": 0},
            )))
            report = build_coverage(manifest, [("write", native, "n", hermes, "h", "PostToolUse")])
            self.assertEqual(report["counts"]["matched_dispatch_and_output_shape"], 1)
            self.assertEqual(report["counts"]["not_observed"], 1)


if __name__ == "__main__":
    unittest.main()
