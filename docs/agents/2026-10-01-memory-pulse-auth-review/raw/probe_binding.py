import json,os,secrets
from test_memory_pulse_auth import MemoryPulseAuthTests,BasicAuthProvider,hash_password,register_global_provider,restore_registration
c=MemoryPulseAuthTests();c.setUp()
try:
 def result(r):return {'status':r.status_code,'cache_control':r.headers.get('cache-control'),'contains_fact':'Synthetic authenticated PULSE fact' in r.text}
 token=c.login();out={}
 out['conditional_owner']=result(c.client.get(c.endpoint+'snapshot',headers={'If-None-Match':'*','If-Modified-Since':'Wed, 21 Oct 2030 07:28:00 GMT'}))
 assert out['conditional_owner']['status']==200
 c.client.post('/auth/logout',follow_redirects=False)
 out['cookie_logout']=result(c.client.get(c.endpoint+'snapshot'))
 out['stateless_bearer_after_logout']=result(c.client.get(c.endpoint+'snapshot',headers={'Authorization':'Bearer '+token}))
 assert out['cookie_logout']['status']==401 and out['stateless_bearer_after_logout']['status']==200
 config=c.configuration.load();c.configuration.update(lambda v:v['accounts'].pop('dashboard:basic:synthetic-owner'))
 out['binding_removed_same_bearer']=result(c.client.get(c.endpoint+'snapshot',headers={'Authorization':'Bearer '+token}));assert out['binding_removed_same_bearer']['status']==403
 c.configuration.save(config);c.login()
 path=c.configuration.path;original=path.read_bytes()
 path.chmod(0o644);out['public_config']=result(c.client.get(c.endpoint+'snapshot'));path.chmod(0o600)
 path.write_text('{invalid synthetic configuration');out['malformed_config']=result(c.client.get(c.endpoint+'snapshot'));path.write_bytes(original)
 path.unlink();out['missing_config']=result(c.client.get(c.endpoint+'snapshot'));c.configuration.save(config)
 for name in ('public_config','malformed_config','missing_config'):
  assert out[name]['status']==503 and out[name]['cache_control']=='no-store' and not out[name]['contains_fact']
 other=BasicAuthProvider(username='synthetic-reader',password_hash=hash_password('synthetic-reader-password'),secret=secrets.token_bytes(32));register_global_provider(other)
 try:
  c.client.cookies.clear()
  login=c.client.post('/auth/password-login',json={'provider':'basic','username':'synthetic-reader','password':'synthetic-reader-password'});assert login.status_code==200
  out['other_verified_account']=result(c.client.get(c.endpoint+'snapshot',headers={'X-LifeOS-Owner':'owner','X-Forwarded-User':'synthetic-owner'}))
  assert out['other_verified_account']['status']==403 and not out['other_verified_account']['contains_fact']
 finally:restore_registration('basic',other,c.provider)
 print(json.dumps(out,indent=2))
finally:c.doCleanups()
