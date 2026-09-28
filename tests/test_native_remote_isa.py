# ABOUTME: Verifies LifeOS's native ISA guard with backend supplied file digests.
# ABOUTME: Runs the real Bun hook with isolated state and a path absent on the host.

import hashlib
import json
import os
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class NativeRemoteISATests(unittest.TestCase):
    def test_remote_view_blocks_stale_write_and_fresh_read_clears_it(self):
        bun = Path.home() / ".bun/bin/bun"
        hook = Path.home() / ".claude/hooks/ISAStaleWriteGuard.hook.ts"
        if not bun.exists() or not hook.exists():
            self.skipTest("installed LifeOS ISA hook and Bun are required")

        with TemporaryDirectory(prefix="remote-isa-view-") as directory:
            root = Path(directory)
            remote_path = str(root / "absent-on-host/ISA.md")
            self.assertFalse(Path(remote_path).exists())
            driver = root / "check.ts"
            driver.write_text(
                f'import {{check}} from {json.dumps(str(hook))}; '
                'const input=JSON.parse(await Bun.stdin.text()); '
                'console.log(JSON.stringify(check(input)));\n'
            )
            env = {**os.environ, "HOME": str(root)}

            def digest(value):
                return hashlib.sha256(value.encode()).hexdigest()

            def payload(event, value, identity="ssh-one", status="file"):
                return {
                    "hook_event_name": event,
                    "session_id": "remote-isa-test",
                    "tool_name": "Read" if event == "PostToolUse" else "Write",
                    "tool_input": {
                        "file_path": remote_path,
                        "lifeos_remote_file": {
                            "status": status, "sha256": digest(value), "identity": identity,
                        },
                    },
                }

            def run(script, data):
                result = subprocess.run(
                    [str(bun), str(script)], input=json.dumps(data), text=True,
                    capture_output=True, env=env, timeout=20,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)

            run(hook, payload("PostToolUse", "view one"))
            state = root / ".claude/LIFEOS/MEMORY/STATE/isa-session-view/remote-isa-test.json"
            self.assertTrue(state.exists())
            self.assertEqual(
                json.loads(state.read_text())["views"][f"remote:ssh-one:{remote_path}"],
                digest("view one"),
            )
            self.assertTrue(run(driver, payload("PreToolUse", "external edit"))["block"])
            self.assertIsNone(run(driver, payload("PreToolUse", "view one")))
            self.assertIsNone(run(driver, payload("PreToolUse", "external edit", identity="ssh-two")))
            run(hook, payload("PostToolUse", "external edit"))
            self.assertIsNone(run(driver, payload("PreToolUse", "external edit")))

            local = root / "local/ISA.md"
            local.parent.mkdir()
            local.write_text("local view")
            local_read = {"hook_event_name": "PostToolUse", "session_id": "local-isa-test",
                          "tool_name": "Read", "tool_input": {"file_path": str(local)}}
            run(hook, local_read)
            local.write_text("local change")
            local_write = {"hook_event_name": "PreToolUse", "session_id": "local-isa-test",
                           "tool_name": "Write", "tool_input": {"file_path": str(local)}}
            self.assertTrue(run(driver, local_write)["block"])

            hidden = payload("PostToolUse", "unseen", status="missing")
            hidden["session_id"] = "remote-missing-test"
            hidden["tool_input"]["file_path"] = str(local)
            run(hook, hidden)
            self.assertFalse((root / ".claude/LIFEOS/MEMORY/STATE/isa-session-view/remote-missing-test.json").exists())


if __name__ == "__main__":
    unittest.main()
