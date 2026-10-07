# ABOUTME: Verifies a named fresh store from the complete pinned native installation payload.
# ABOUTME: Preserves the authenticated source profile and excludes its existing facts and memory files.
from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from lifeos_hook_bridge.memory_access import MemoryUnavailable,NativeMemory
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from test_memory_native import OWNER
import test_memory_import as import_fixture


CANDIDATE=Path(os.environ.get('LIFEOS_FRESH_SOURCE',''))


@unittest.skipUnless(os.environ.get('LIFEOS_FRESH_SOURCE') and shutil.which('bun'),
                     'A complete prepared native candidate and Bun are required')
class FreshStoreTests(unittest.TestCase):
    def setUp(self):
        self.fixture=import_fixture.MemoryImportTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.configuration=self.fixture.configuration
        self.saved=self.fixture.fixture.memory.remember(OWNER,category='principal',
            content='RULE: Synthetic original store marker',title='',project='',request_id='old-store')
        self.assertEqual(self.saved['status'],'committed',self.saved)
        self.original={path:path.read_bytes() for path in (self.configuration.path,
            self.fixture.profile/'config.yaml',self.fixture.sources/'MEMORY.md')}

    def operation(self):
        from lifeos_hook_bridge.fresh_store import FreshStore
        return FreshStore(self.configuration)

    def test_named_store_has_no_adopted_facts_and_preserves_originals(self):
        result=self.operation().prepare(CANDIDATE,principal_name='Adrian',assistant_name='Cerebo',account='dashboard:owner')
        self.assertEqual(result['state'],'review')
        self.assertEqual(result['names'],{'principal':'Adrian','assistant':'Cerebo'})
        self.assertEqual(result['active_facts'],0)
        self.assertFalse(result['ownership_enabled'])
        self.assertFalse(result['sharing_enabled'])
        self.assertFalse(result['services_started'])
        root=Path(result['installed']);user=root.parent/'.config/LIFEOS/USER'
        self.assertEqual((root/'LIFEOS/USER').resolve(),user)
        self.assertEqual((root/'LIFEOS/MEMORY').resolve(),user/'MEMORY')
        memory=NativeMemory(root)
        self.assertEqual(memory.recall(OWNER,'original store marker'),[])
        self.assertEqual(memory.read_hot(OWNER,'principal')['entries'],[])
        self.assertEqual(memory.read_hot(OWNER,'assistant')['entries'],[])
        program=root/'LIFEOS/TOOLS/LifeosConfig.ts'
        code='import {loadLifeosConfig} from '+json.dumps(str(program))+';const c=loadLifeosConfig();console.log(JSON.stringify({principal:c.principal.name,assistant:c.da.name}));'
        env=os.environ|{'HOME':str(root.parent),'LIFEOS_CONFIG_PATH':str(user/'CONFIG/LIFEOS_CONFIG.toml')}
        native=subprocess.run(['bun','--no-install','-e',code],env=env,text=True,capture_output=True,timeout=30)
        self.assertEqual(native.returncode,0,native.stdout+native.stderr)
        self.assertEqual(native.stderr,'')
        self.assertEqual(json.loads(native.stdout),result['names'])
        self.assertIn('Cerebo',(user/'DIGITAL_ASSISTANT/DA_IDENTITY.md').read_text())
        self.assertIn('Adrian',(user/'PRINCIPAL/PRINCIPAL_IDENTITY.md').read_text())
        for path,content in self.original.items():self.assertEqual(path.read_bytes(),content)
        self.assertEqual(self.fixture.fixture.memory.get(OWNER,self.saved['reference'])['content'],
            'RULE: Synthetic original store marker')
        self.assertFalse(self.configuration.load()['ownership_enabled'])
        for path in user.rglob('*'):
            self.assertEqual(path.stat().st_mode & 0o077,0,path)
        evidence=os.environ.get('LIFEOS_FRESH_EVIDENCE')
        if evidence:
            directory=Path(evidence);directory.mkdir(parents=True,exist_ok=True)
            (directory/'named-store-result.json').write_text(json.dumps(result,indent=2)+'\n')
            (directory/'native-name-result.json').write_text(native.stdout)

    def test_unbound_owner_and_invalid_names_refuse_before_native_installation(self):
        for account in (None,'chat:owner','dashboard:other'):
            with self.subTest(account=account):
                with self.assertRaises(PermissionError):
                    self.operation().prepare(CANDIDATE,principal_name='Adrian',assistant_name='Cerebo',account=account)
        for name in ('','A\nB','<private>name</private>','name/'+'x'*130):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.operation().prepare(CANDIDATE,principal_name=name,assistant_name='Cerebo',account='dashboard:owner')
        for path,content in self.original.items():self.assertEqual(path.read_bytes(),content)


if __name__=='__main__':
    unittest.main()
