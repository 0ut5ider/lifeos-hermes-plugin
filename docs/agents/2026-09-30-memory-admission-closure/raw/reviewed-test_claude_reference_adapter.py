# ABOUTME: Checks the reference Claude child launcher against the accepted tier effort mapping.
# ABOUTME: Uses a fake local Claude executable and synthetic gateway environment.

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ADAPTER = Path(__file__).resolve().parents[1] / "scripts/claude_reference_adapter.sh"


class ReferenceAdapterTests(unittest.TestCase):
    def test_model_tiers_select_effort_without_exposing_gateway_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / ".config/lifeos-reference"
            config.mkdir(parents=True)
            (config / "model.env").write_text("ANTHROPIC_MODEL=synthetic-local-model\n")
            bin_dir = home / ".local/bin"
            bin_dir.mkdir(parents=True)
            (bin_dir / "claude").write_text(
                "#!/usr/bin/env python3\n"
                "import json,os,sys\n"
                "print(json.dumps({'args':sys.argv[1:], 'model':os.environ['ANTHROPIC_MODEL']}))\n"
            )
            (bin_dir / "claude").chmod(0o755)
            for tier, effort in (("haiku", "low"), ("sonnet", "medium"),
                                 ("opus", "xhigh"), ("fable", "xhigh")):
                with self.subTest(tier=tier):
                    result = subprocess.run(
                        ["bash", str(ADAPTER), "--model", tier, "--effort", "high", "-p", "synthetic"],
                        env={**os.environ, "HOME": str(home)}, capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    output = json.loads(result.stdout)
                    self.assertEqual(output["model"], "synthetic-local-model")
                    self.assertEqual(output["args"],
                                     ["--model", "synthetic-local-model", "--effort", effort, "-p", "synthetic"])

    def test_effort_is_added_when_lifeos_does_not_supply_one(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / ".config/lifeos-reference"
            config.mkdir(parents=True)
            (config / "model.env").write_text("ANTHROPIC_MODEL=synthetic-local-model\n")
            bin_dir = home / ".local/bin"
            bin_dir.mkdir(parents=True)
            (bin_dir / "claude").write_text("#!/bin/sh\nprintf '%s\\n' \"$*\"\n")
            (bin_dir / "claude").chmod(0o755)
            result = subprocess.run(
                ["bash", str(ADAPTER), "--model=haiku", "-p", "synthetic"],
                env={**os.environ, "HOME": str(home)}, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--effort low", result.stdout)


if __name__ == "__main__":
    unittest.main()
