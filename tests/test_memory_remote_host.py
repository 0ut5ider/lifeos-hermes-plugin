# ABOUTME: Loads the installed HTTP memory plugin in the exact native Hermes dashboard host.
# ABOUTME: Verifies startup mounting, cookie separation, protocol discovery, and live plugin disablement.

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

from lifeos_hook_bridge.memory_remote import MemoryRemote
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_memory_native as native_fixture


class MemoryRemoteHostTests(unittest.TestCase):
    def test_native_dashboard_loads_builtin_http_without_a_host_patch(self):
        fixture = native_fixture.NativeMemoryTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        profile = fixture.home / '.hermes'
        plugin = profile / 'plugins/lifeos-hook-bridge'
        shutil.copytree(Path(__file__).parents[1] / 'lifeos_hook_bridge', plugin,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        (profile / 'config.yaml').write_text('plugins:\n  enabled: [lifeos-hook-bridge]\n')
        configuration = MemoryConfiguration(profile / 'lifeos-memory.json')
        configuration.save({'version': 1, 'root': str(fixture.root), 'principal': 'owner',
            'ownership_enabled': True, 'sharing_enabled': False, 'destinations': {}, 'clients': {},
            'accounts': {'dashboard:basic:synthetic-owner': 'owner'}})
        remote = MemoryRemote(configuration.path)
        remote.configure({'enabled': True, 'public_url': 'http://127.0.0.1:9100'}, account='dashboard:basic:synthetic-owner')
        saved = remote.enroll({'client': 'native-host', 'read': ['project'], 'write_project': False,
            'projects': ['lab'], 'model_route': 'unknown'}, account='dashboard:basic:synthetic-owner')
        code = '''
import json, os
from pathlib import Path
from fastapi.testclient import TestClient
from hermes_cli import web_server
from lifeos_hook_bridge.memory_remote import MCP_PATH, RESOURCE_METADATA_PATH
assert getattr(web_server.app.state, 'lifeos_memory_http', False), 'Native plugin import must install HTTP MCP'
web_server.app.state.auth_required = True
with TestClient(web_server.app, base_url='http://127.0.0.1:9100') as client:
    assert client.get('/api/plugins/lifeos-hook-bridge/memory/http/settings').status_code == 401
    assert client.get(RESOURCE_METADATA_PATH).status_code == 200
    assert client.post(MCP_PATH).status_code == 401
    token=json.loads(Path(os.environ['HTTP_PROBE_INPUT']).read_text())['token']
    headers={'Authorization':'Bearer '+token, 'Accept':'application/json, text/event-stream', 'MCP-Protocol-Version':'2025-03-26'}
    response=client.post(MCP_PATH,headers=headers,json={'jsonrpc':'2.0','id':1,'method':'tools/list','params':{}})
    assert response.status_code==200,response.text
    assert len(response.json()['result']['tools'])==9
    assert client.get('/api/plugins/lifeos-hook-bridge/memory/http/settings',headers=headers).status_code==401
    (Path(os.environ['HERMES_HOME'])/'config.yaml').write_text('plugins:\\n  enabled: []\\n  disabled: [lifeos-hook-bridge]\\n')
    assert client.post(MCP_PATH,headers=headers,json={}).status_code==404
Path(os.environ['HTTP_PROBE_INPUT']).with_name('http-host-receipt.json').write_text(json.dumps({'native_plugin_mount':True,'cookie_separation':True,'discovery':True,'disabled_plugin_refused':True}))
'''
        credentials = fixture.home / 'http-probe-input.json'
        credentials.write_text(json.dumps(saved)); credentials.chmod(0o600)
        result = subprocess.run([sys.executable, '-B', '-c', code],
            env={**os.environ, 'HOME': str(fixture.home), 'HERMES_HOME': str(profile), 'HTTP_PROBE_INPUT': str(credentials)},
            text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        receipt = credentials.with_name('http-host-receipt.json')
        self.assertTrue(receipt.is_file(), result.stderr + result.stdout)
        self.assertTrue(json.loads(receipt.read_text())['native_plugin_mount'])


if __name__ == '__main__':
    unittest.main()
