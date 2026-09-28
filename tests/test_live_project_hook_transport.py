# ABOUTME: Verifies project hook input and output over a disposable SSH backend.
# ABOUTME: Keeps stdout, stderr, environment, and a large hook payload distinct.

import hashlib
import json
import os
import shlex
import unittest

from lifeos_hook_bridge.remote_hooks import run_project_hook


class LiveProjectHookTransportTests(unittest.TestCase):
    def test_remote_hook_receives_large_payload_and_separate_streams(self):
        host = os.environ.get("LIFEOS_SSH_PROBE_HOST")
        user = os.environ.get("LIFEOS_SSH_PROBE_USER")
        key = os.environ.get("LIFEOS_SSH_PROBE_KEY")
        project = os.environ.get("LIFEOS_SSH_PROBE_PROJECT")
        if not all((host, user, key, project)):
            self.skipTest("disposable SSH project is required")

        from tools.environments.ssh import SSHEnvironment

        env = SSHEnvironment(host=host, user=user, cwd=project, key_path=key, probe_only=True)
        try:
            prompt = "X" * 200000
            payload = {"session_id": "project-hook-probe", "prompt": prompt}
            code = (
                "import hashlib,json,os,sys; "
                "data=json.load(sys.stdin); "
                "print(json.dumps({'length':len(data['prompt']),"
                "'digest':hashlib.sha256(data['prompt'].encode()).hexdigest(),"
                "'env':os.environ.get('LIFEOS_PROJECT_PROBE')})); "
                "print('remote refusal',file=sys.stderr); sys.exit(2)"
            )
            result = run_project_hook(
                env, "python3 -c " + shlex.quote(code), payload, project, 20,
                {"LIFEOS_PROJECT_PROBE": "remote-value"},
            )
            self.assertIsNotNone(result)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout), {
                "length": len(prompt),
                "digest": hashlib.sha256(prompt.encode()).hexdigest(),
                "env": "remote-value",
            })
            self.assertEqual(result.stderr.strip(), "remote refusal")
        finally:
            env.cleanup()


if __name__ == "__main__":
    unittest.main()
