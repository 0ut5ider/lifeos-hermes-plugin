# ABOUTME: Exercises the actual native LocalIntelligence fetch boundary with disposable owner context.
# ABOUTME: Observes real fetch calls without replacing responses and requires refusal before unbound requests.
from dataclasses import asdict
import json
import os
import subprocess
import unittest
import test_memory_local_refresh as fixture


class MemoryLocalRefreshNativeTests(unittest.TestCase):
    setUp = fixture.MemoryLocalRefreshTests.setUp

    def fetch(self, *, context, city='SyntheticCity'):
        module = self.root / 'skills/LocalIntelligence/Tools/Refresh.ts'
        home = {'city': city, 'state': 'TX', 'county': 'Synthetic', 'zip': '78701',
            'citySlug': city.lower(), 'stateSlug': 'tx'}
        program = ('import {refresh} from ' + json.dumps(str(module)) + ';'
            'let requests=0;const original=globalThis.fetch;globalThis.fetch=(...args)=>{requests++;return original(...args)};'
            'try{await refresh(' + json.dumps(home) + ');console.log(JSON.stringify({refused:false,requests}))}'
            'catch{console.log(JSON.stringify({refused:true,requests}))}')
        environment = dict(os.environ, HOME=str(self.owner.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1')
        for name in ('LIFEOS_MEMORY_CONTEXT', 'LIFEOS_MEMORY_INTERNAL', 'LIFEOS_PRINCIPAL_IDENTITY'):
            environment.pop(name, None)
        if context: environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.owner.context))
        result = subprocess.run(['bun', '--no-install', '-e', program], capture_output=True, text=True,
            env=environment, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def test_unbound_exported_refresh_refuses_before_any_actual_fetch(self):
        result = self.fetch(context=False)
        self.assertEqual(result, {'refused': True, 'requests': 0})

    def test_changed_hometown_cannot_enter_native_fetches(self):
        result = self.fetch(context=True, city='OtherSyntheticCity')
        self.assertEqual(result, {'refused': True, 'requests': 0})
