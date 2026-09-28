# ABOUTME: Checks the child Claude launcher maps LifeOS model rungs to local reasoning effort.
# ABOUTME: Uses an isolated home and a recording executable, with no model request.

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ADAPTER = Path(__file__).resolve().parents[1] / "lifeos_hook_bridge/bin/claude"


class ClaudeAdapterTests(unittest.TestCase):
    def test_lifeos_model_rungs_map_to_local_effort(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / ".local/bin").mkdir(parents=True)
            (home / ".config/lifeos-hook-bridge").mkdir(parents=True)
            (home / ".config/lifeos-hook-bridge/model.env").write_text(
                "ANTHROPIC_MODEL=local-model\n"
            )
            target = home / ".local/bin/claude"
            target.write_text(
                "#!/usr/bin/env python3\n"
                "import json,sys\n"
                "print(json.dumps(sys.argv[1:]))\n"
            )
            target.chmod(0o700)
            expected = {
                "haiku": "low",
                "sonnet": "medium",
                "opus": "xhigh",
                "claude-fable-5": "xhigh",
            }
            for requested_model, effort in expected.items():
                with self.subTest(model=requested_model):
                    result = subprocess.run(
                        [str(ADAPTER), "--print", "--model", requested_model,
                         "--effort", "high", "hello"],
                        text=True, capture_output=True, check=True,
                        env={**os.environ, "HOME": str(home)},
                    )
                    self.assertEqual(
                        json.loads(result.stdout),
                        ["--print", "--model", "local-model", "--effort", effort, "hello"],
                    )
            equals_form = subprocess.run(
                [str(ADAPTER), "--model=claude-opus-5", "--effort=high", "hello"],
                text=True, capture_output=True, check=True,
                env={**os.environ, "HOME": str(home)},
            )
            self.assertEqual(
                json.loads(equals_form.stdout),
                ["--model=local-model", "--effort=xhigh", "hello"],
            )


if __name__ == "__main__":
    unittest.main()
