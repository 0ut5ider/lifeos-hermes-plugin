# ABOUTME: Replays route resolution under a real local managed-store Python without bundled dependencies.
# ABOUTME: Compares the retained direct-child code with the corrected Hermes bootstrap on synthetic profiles.
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

RUNTIME=Path('/home/outsider/.cache/lifeos-memory-portability-20261015/stock-full-9b204dad/runtime')
BARE=RUNTIME/'dependency-profile/tools/python-3.14.7+20260901-linux-x64/bin/python3'
HOST=RUNTIME/'hermes'
REPO=Path(__file__).resolve().parents[3]
OLD=REPO/'docs/agents/2026-10-15-owner-route-closure/source/lifeos_hook_bridge/memory_owner_access.py'


class ManagedControls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='review-managed-route-');self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)/'account';self.home.mkdir(mode=0o700)
        self.profile=self.home/'.hermes';self.profile.mkdir(mode=0o700)
        self.expected=json.dumps({'model':{'default':'review-managed-model','provider':'custom',
            'base_url':'http://127.0.0.1:9/v1','api_key':'SYNTHETIC-MANAGED-KEY'}}).encode()
        (self.profile/'config.yaml').write_bytes(self.expected)
        self.environment=dict(os.environ,HOME=str(self.home),HERMES_HOME=str(self.profile),
            PYTHONDONTWRITEBYTECODE='1',HERMES_DISABLE_LAZY_INSTALLS='1')

    def run_child(self,code):
        from hermes_cli import _launchers
        command=_launchers.runtime_command(HOST,[str(REPO),str(self.profile),str(OLD)],code=code,python=BARE,home=self.profile)
        command.insert(1,'-B')
        child=subprocess.run(command,cwd=self.home,env=self.environment,text=True,capture_output=True,timeout=60)
        self.assertEqual(child.returncode,0,child.stdout+child.stderr);self.assertEqual(child.stderr,'')
        observation=json.loads(child.stdout)
        output=Path(__file__).parent/'observations';output.mkdir(exist_ok=True)
        (output/(self._testMethodName+'.json')).write_text(json.dumps(observation,indent=2)+'\n')
        return observation

    def test_bare_store_python_has_no_route_dependencies(self):
        code='''import importlib.util,json
print(json.dumps({name:importlib.util.find_spec(name) is None for name in ('dotenv','ruamel')}))
'''
        child=subprocess.run([str(BARE),'-B','-I','-c',code],env=self.environment,text=True,capture_output=True,timeout=10)
        self.assertEqual(child.returncode,0,child.stderr);self.assertEqual(child.stderr,'')
        observation=json.loads(child.stdout)
        self.assertEqual(observation,{'dotenv':True,'ruamel':True})
        output=Path(__file__).parent/'observations';output.mkdir(exist_ok=True)
        (output/(self._testMethodName+'.json')).write_text(json.dumps(observation,indent=2)+'\n')

    def test_old_direct_child_refuses_but_corrected_managed_route_admits_exact_owner(self):
        code='''import importlib.util,json,os,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]);profile=Path(sys.argv[2]);before=(profile/'config.yaml').read_bytes()
from lifeos_hook_bridge.memory_access import MemoryUnavailable
spec=importlib.util.spec_from_file_location('lifeos_hook_bridge.review_old_access',sys.argv[3]);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
try:old._route(profile,before)
except MemoryUnavailable:old_refuses=True
else:old_refuses=False
from lifeos_hook_bridge.memory_owner_access import reviewed
from lifeos_hook_bridge.memory_context import host_context
from lifeos_hook_bridge.memory_policy import MemoryPolicy
from dataclasses import replace
configuration={'version':1,'root':str(profile.parent/'installed'),'principal':'owner','ownership_enabled':False,'sharing_enabled':False,'accounts':{'dashboard:owner':'owner'},'destinations':{},'clients':{}}
selected,disclosure=reviewed(configuration,profile,before)
context=host_context(selected,{'HERMES_SESSION_PLATFORM':'cli'},model_route=disclosure['model_route'],hermes_home=str(profile))
policy=MemoryPolicy(selected)
print(json.dumps({'old_direct_child_refuses':old_refuses,'exact_owner_admitted':policy.resolve(context).reason=='',
'unknown_account_denied':bool(policy.resolve(replace(context,author='unapproved')).reason),
'unknown_profile_denied':bool(policy.resolve(replace(context,destination=str(profile.parent/'other'))).reason),
'unknown_route_denied':bool(policy.resolve(replace(context,model_route='unapproved')).reason),
'config_unchanged':(profile/'config.yaml').read_bytes()==before,'secret_absent':'SYNTHETIC-MANAGED-KEY' not in json.dumps(disclosure),
'interpreter':sys.executable}))
'''
        result=self.run_child(code)
        self.assertTrue(all(value is True for key,value in result.items() if key!='interpreter'),result)
        self.assertEqual(Path(result['interpreter']).resolve(),BARE.resolve())
        self.assertEqual((self.profile/'config.yaml').read_bytes(),self.expected)

    def test_bootstrap_selects_runtime_dependencies_and_ignores_parent_python_payload(self):
        poison=self.home/'unrelated-parent-python';poison.mkdir();marker=self.home/'unexpected-startup'
        (poison/'sitecustomize.py').write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("unexpected")\n')
        self.environment.update(PYTHONPATH=str(poison),VIRTUAL_ENV=str(poison),HERMES_HOME=str(self.home/'wrong-profile'))
        # The same exact selected-profile environment is passed by the production route helper.
        self.environment['HERMES_HOME']=str(self.profile)
        code='''import dotenv,json,sys,ruamel.yaml
from pathlib import Path
print(json.dumps({'dotenv':str(Path(dotenv.__file__).resolve()),'ruamel':str(Path(ruamel.yaml.__file__).resolve()),'home':__import__('os').environ['HERMES_HOME']}))
'''
        result=self.run_child(code)
        dependencies=RUNTIME/'python-environment/lib/python3.14/site-packages'
        self.assertTrue(Path(result['dotenv']).is_relative_to(dependencies))
        self.assertTrue(Path(result['ruamel']).is_relative_to(dependencies))
        self.assertEqual(result['home'],str(self.profile));self.assertFalse(marker.exists())
