# ABOUTME: Measures signal shutdown in the actual native Pulse daemon.
# ABOUTME: Requires scheduler cleanup and process exit before the service drain deadline.
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time
import unittest


SOURCE = Path(os.environ['LIFEOS_MEMORY_SOURCE'])


class PulseShutdownTests(unittest.TestCase):
    def test_idle_native_daemon_exits_promptly_and_persists_state(self):
        for observability, assistant in ((False, False), (True, False), (False, True)):
            with self.subTest(observability=observability, assistant=assistant), tempfile.TemporaryDirectory() as directory:
                home = Path(directory)
                root = home / '.claude'
                pulse = root / 'LIFEOS/PULSE'
                pulse.mkdir(parents=True)
                (pulse / 'state').mkdir()
                for item in (SOURCE / 'LIFEOS').iterdir():
                    if item.name not in ('PULSE', 'USER', 'MEMORY'):
                        (root / 'LIFEOS' / item.name).symlink_to(item, target_is_directory=item.is_dir())
                for item in (SOURCE / 'LIFEOS/PULSE').iterdir():
                    if item.name not in ('PULSE.toml', 'PULSE.user.toml', 'state'):
                        (pulse / item.name).symlink_to(item, target_is_directory=item.is_dir())
                modules = subprocess.run(['bun', '--no-install', '-e', 'import {MODULE_DEFAULTS} from '
                    + json.dumps(str(SOURCE / 'LIFEOS/PULSE/lib/modules.ts'))
                    + ';console.log(JSON.stringify(Object.keys(MODULE_DEFAULTS)))'],
                    capture_output=True, text=True, timeout=10)
                self.assertEqual((modules.returncode, modules.stderr), (0, ''), modules.stdout)
                with socket.socket() as listener:
                    listener.bind(('127.0.0.1', 0))
                    port = listener.getsockname()[1]
                (pulse / 'PULSE.toml').write_text('port=' + str(port) + '\n[modules]\n'
                    + ''.join(name + '=' + str(assistant and name == 'da').lower() + '\n'
                        for name in json.loads(modules.stdout))
                    + '[hooks]\nenabled=false\n[observability]\nenabled='
                    + str(observability).lower() + '\n')
                environment = {key: os.environ[key] for key in ('PATH', 'LANG', 'TZ') if key in os.environ}
                environment.update(HOME=str(home), BUN_CONFIG_NO_AUTO_INSTALL='1')
                output = home / 'daemon-output.txt'
                with output.open('w') as stream:
                    process = subprocess.Popen(['bun', '--no-install', str(pulse / 'pulse.ts')],
                        env=environment, stdout=stream, stderr=subprocess.STDOUT)
                    try:
                        deadline = time.monotonic() + 10
                        while 'HTTP server listening' not in output.read_text() and time.monotonic() < deadline:
                            if process.poll() is not None:
                                self.fail(output.read_text())
                            time.sleep(0.02)
                        self.assertIn('HTTP server listening', output.read_text())
                        # The native idle loop reaches its maximum 60-second scheduler sleep.
                        time.sleep(0.2)
                        started = time.monotonic()
                        process.send_signal(signal.SIGTERM)
                        try:
                            process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            self.fail('Pulse does not exit within 3 seconds of SIGTERM: ' + output.read_text())
                        elapsed = time.monotonic() - started
                        self.assertEqual(process.returncode, 0, output.read_text())
                        self.assertIn('LifeOS Pulse stopped', output.read_text())
                        if assistant:
                            self.assertFalse((pulse / 'Assistant/module.ts').exists())
                            self.assertNotIn('Assistant module not available', output.read_text())
                        state = json.loads((pulse / 'state/state.json').read_text())
                        self.assertEqual(state['jobs'], {})
                        self.assertLess(elapsed, 3)
                    finally:
                        if process.poll() is None:
                            process.kill()
                            process.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()
