# ABOUTME: Checks isolated selected-profile model resolution and private route review output.
# ABOUTME: Uses synthetic endpoints and credentials without sending any model request.
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from lifeos_hook_bridge.memory_owner_access import _route,reviewed
from lifeos_hook_bridge.memory_context import host_context,route_identity
from lifeos_hook_bridge.memory_policy import MemoryPolicy,CATEGORIES
from lifeos_hook_bridge.memory_access import MemoryUnavailable


class RouteControls(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(prefix='review-owner-route-');self.addCleanup(self.directory.cleanup)
        self.base=Path(self.directory.name);self.profile=self.base/'selected';self.profile.mkdir(mode=0o700)
        self.secret='SYNTHETIC-ROUTE-SECRET-DO-NOT-EXPORT'
        self.config={'model':{'default':'review-model','provider':'custom','base_url':'http://127.0.0.1:9/v1','api_key':self.secret}}

    def write(self,config=None):
        data=json.dumps(config or self.config).encode();(self.profile/'config.yaml').write_bytes(data);return data

    def environment(self,**values):
        before={key:os.environ.get(key) for key in values}
        def restore():
            for key,value in before.items():
                if value is None:os.environ.pop(key,None)
                else:os.environ[key]=value
        self.addCleanup(restore);os.environ.update(values)

    def policy(self):
        return {'version':1,'root':str(self.base/'installed'),'principal':'owner','ownership_enabled':False,
            'sharing_enabled':False,'accounts':{'dashboard:owner':'owner'},'destinations':{},'clients':{}}

    def test_exact_resolved_route_admits_owner_and_denies_other_account_profile_and_route(self):
        data=self.write();selected,disclosure=reviewed(self.policy(),self.profile,data)
        route=disclosure['model_route'];self.assertEqual(route,route_identity('custom','review-model','http://127.0.0.1:9/v1','chat_completions'))
        context=host_context(selected,{'HERMES_SESSION_PLATFORM':'cli'},model_route=route,hermes_home=str(self.profile))
        from dataclasses import replace
        policy=MemoryPolicy(selected);self.assertEqual(policy.resolve(context).reason,'')
        self.assertTrue(policy.resolve(replace(context,author='unapproved')).reason)
        self.assertTrue(policy.resolve(replace(context,destination=str(self.base/'other'))).reason)
        self.assertTrue(policy.resolve(replace(context,model_route='unapproved-route')).reason)
        self.assertEqual(set(policy.resolve(context).read),CATEGORIES)
        self.assertNotIn(self.secret,json.dumps(disclosure));self.assertNotIn(self.secret,json.dumps(selected))

    def test_parent_profile_and_python_path_cannot_select_another_config(self):
        other=self.base/'other';other.mkdir();(other/'config.yaml').write_text(json.dumps({'model':{'default':'wrong-model','provider':'custom','base_url':'http://127.0.0.1:10/v1','api_key':'other-synthetic-secret'}}))
        self.environment(HERMES_HOME=str(other),PYTHONPATH=str(other),PYTHONSTARTUP=str(other/'startup.py'))
        data=self.write();route=_route(self.profile,data)
        self.assertEqual(route['model'],'review-model');self.assertEqual(route['base_url'],'http://127.0.0.1:9/v1')
        self.assertEqual(os.environ['HERMES_HOME'],str(other))

    def test_selected_profile_dotenv_stays_in_child_and_secret_is_not_returned(self):
        variable='REVIEW_OWNER_ROUTE_EP_20261015';token='REVIEW_OWNER_ROUTE_SECRET_20261015'
        self.assertNotIn(variable,os.environ);self.assertNotIn(token,os.environ)
        (self.profile/'.env').write_text(variable+'=http://127.0.0.1:9/v1\n'+token+'='+self.secret+'\n')
        self.config['model']['base_url']='${'+variable+'}';self.config['model']['api_key']='${'+token+'}'
        data=self.write();route=_route(self.profile,data)
        self.assertEqual(route['base_url'],'http://127.0.0.1:9/v1');self.assertNotIn(self.secret,json.dumps(route))
        self.assertNotIn(variable,os.environ);self.assertNotIn(token,os.environ)
        self.assertEqual((self.profile/'config.yaml').read_bytes(),data)

    def test_named_provider_resolves_its_actual_endpoint_without_returning_key(self):
        self.config={'model':{'default':'review-model','provider':'review-private'},'providers':{
            'review-private':{'base_url':'http://127.0.0.1:9/v1','api_key':self.secret}}}
        route=_route(self.profile,self.write())
        self.assertEqual(route['provider'],'custom');self.assertEqual(route['base_url'],'http://127.0.0.1:9/v1')
        self.assertEqual(route['model_route'],route_identity('custom','review-model','http://127.0.0.1:9/v1','chat_completions'))
        self.assertNotIn(self.secret,json.dumps(route))

    def test_changed_config_before_child_start_refuses_without_reverting_edit(self):
        data=self.write();later=json.dumps({'model':{'default':'later-model','provider':'custom','base_url':'http://127.0.0.1:10/v1','api_key':self.secret}}).encode();edited=False
        def trace(frame,event,arg):
            nonlocal edited
            caller=frame.f_back
            if (not edited and event=='call' and frame.f_code.co_name=='run' and caller is not None
                    and caller.f_code.co_filename.endswith('/memory_owner_access.py')):
                (self.profile/'config.yaml').write_bytes(later);edited=True
            return trace
        sys.settrace(trace)
        try:
            with self.assertRaises(MemoryUnavailable):_route(self.profile,data)
        finally:sys.settrace(None)
        self.assertTrue(edited);self.assertEqual((self.profile/'config.yaml').read_bytes(),later)

    def test_invalid_route_error_has_no_secret_or_endpoint_details(self):
        self.config['model']['base_url']='https://synthetic:'+self.secret+'@example.invalid/v1'
        with self.assertRaises(MemoryUnavailable) as raised:_route(self.profile,self.write())
        self.assertNotIn(self.secret,str(raised.exception));self.assertNotIn('example.invalid',str(raised.exception))

    def test_isolated_child_ignores_parent_python_startup_code(self):
        poison=self.base/'parent-python';poison.mkdir();marker=self.base/'unwanted-startup'
        source='from pathlib import Path\nPath('+repr(str(marker))+').write_text("unexpected")\n'
        (poison/'sitecustomize.py').write_text(source);(poison/'startup.py').write_text(source)
        self.environment(PYTHONPATH=str(poison),PYTHONSTARTUP=str(poison/'startup.py'))
        route=_route(self.profile,self.write())
        self.assertEqual(route['model'],'review-model');self.assertFalse(marker.exists())
