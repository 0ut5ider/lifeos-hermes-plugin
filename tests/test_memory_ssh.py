# ABOUTME: Exercises enrolled memory credentials through an isolated localhost SSH server.
# ABOUTME: Verifies protocol access, shell refusal, private fact filtering, and open-session revocation.
import asyncio
import json
import os
from pathlib import Path
import pwd
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest

from mcp import Client
from mcp.client.stdio import StdioServerParameters, stdio_client
from sharing_component import sharing as load_component
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_memory_native as native_fixture


class MemorySSHTests(unittest.TestCase):
    def test_enrolled_key_restricts_real_ssh_session_and_revocation(self):
        self.assertTrue(shutil.which('sshd'), 'OpenSSH server is required for this release gate')
        subprocess.run(['sudo', '-n', 'true'], check=True, capture_output=True)
        fixture = native_fixture.NativeMemoryTests()
        fixture.temporary_parent = Path.home() / '.cache'
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        home = fixture.home
        config = home / 'hermes/memory.json'
        MemoryConfiguration(config).save({'version':1, 'root':str(fixture.root), 'principal':'owner',
                                         'accounts':{}, 'destinations':{}, 'sharing_enabled':False, 'clients':{}})
        keys = home / '.ssh/authorized_keys'; keys.parent.mkdir(mode=0o700)
        host_key = home / 'host-key'; client_key = home / 'client-key'
        for key in (host_key, client_key):
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)], check=True, capture_output=True)
        installed = home / 'plugins/lifeos-hook-bridge'
        shutil.copytree(Path(__file__).parents[1] / 'lifeos_hook_bridge', installed,
                        ignore=shutil.ignore_patterns('__pycache__'))
        sharing = load_component().MemorySharing(config, Path(sys.executable), installed / 'memory_mcp.py', keys_file=keys)
        sharing.enroll('sshreader', client_key.with_suffix('.pub').read_text(), projects=['lab'], model_route='unknown')
        saved = fixture.remember()
        fixture.remember('RULE: forbidden SSH private marker', 'private-ssh', 'principal')
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
        user = pwd.getpwuid(os.getuid()).pw_name
        pidfile = home / 'sshd.pid'; configuration = home / 'sshd.conf'; log = home / 'sshd.log'
        configuration.write_text(f'''Port {port}
ListenAddress 127.0.0.1
HostKey {host_key}
PidFile {pidfile}
AuthorizedKeysFile {keys}
PasswordAuthentication no
KbdInteractiveAuthentication no
UsePAM no
PermitRootLogin no
AllowUsers {user}
StrictModes yes
AllowTcpForwarding no
AllowAgentForwarding no
X11Forwarding no
PermitTTY no
LogLevel VERBOSE
''')
        subprocess.run(['sudo', '-n', '/usr/bin/sshd', '-t', '-f', str(configuration)], check=True, capture_output=True)
        subprocess.run(['sudo', '-n', '/usr/bin/sshd', '-f', str(configuration), '-E', str(log)], check=True, capture_output=True)
        def stop():
            if pidfile.exists():
                subprocess.run(['sudo', '-n', 'kill', pidfile.read_text().strip()], check=True, capture_output=True)
        self.addCleanup(stop)
        deadline = time.monotonic() + 5
        while not pidfile.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertTrue(pidfile.exists(), 'The isolated SSH server did not start')
        known = home / 'known_hosts'
        known.write_text(f'[127.0.0.1]:{port} ' + host_key.with_suffix('.pub').read_text())
        args = ['-T', '-i', str(client_key), '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
                '-o', 'StrictHostKeyChecking=yes', '-o', f'UserKnownHostsFile={known}', '-p', str(port), f'{user}@127.0.0.1']
        denied = subprocess.run(['ssh', *args, 'id'], input='', capture_output=True, text=True, timeout=10)
        self.assertNotEqual(denied.returncode, 0)
        diagnostic = subprocess.run(['sudo', '-n', 'cat', str(log)], check=True, capture_output=True, text=True).stdout
        self.assertIn('Only the lifeos-memory command is permitted', denied.stderr, diagnostic)
        self.assertNotIn('uid=', denied.stdout)
        parameters = StdioServerParameters(command='ssh', args=[*args, 'lifeos-memory'])
        async def exercise():
            with tempfile.TemporaryFile(mode='w+') as errors:
                async with Client(stdio_client(parameters, errlog=errors), cache=None) as client:
                    response = await client.call_tool('lifeos_memory_search', {'query':'synthetic lab'})
                    result = response.structured_content
                    self.assertEqual(result['status'], 'ok', result)
                    self.assertEqual(result['results'][0]['reference'], saved['reference'])
                    self.assertNotIn('forbidden', json.dumps(result))
                    response = await client.call_tool('lifeos_memory_remember', {
                        'category':'project', 'content':'Prohibited SSH write', 'title':'Denied',
                        'project':'lab', 'request_id':'ssh-denied'})
                    self.assertEqual(response.structured_content['status'], 'rejected')
                    sharing.revoke('sshreader')
                    response = await client.call_tool('lifeos_memory_get', {'reference':saved['reference']})
                    self.assertEqual(response.structured_content['status'], 'rejected')
                errors.seek(0)
                self.assertEqual(errors.read(), '')
        asyncio.run(exercise())
        self.assertEqual(fixture.memory.get(native_fixture.OWNER, saved['reference'])['status'], 'ok')
        denied = subprocess.run(['ssh', *args, 'lifeos-memory'], input='', capture_output=True, text=True, timeout=10)
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn('Permission denied', denied.stderr)


if __name__ == '__main__':
    unittest.main()
