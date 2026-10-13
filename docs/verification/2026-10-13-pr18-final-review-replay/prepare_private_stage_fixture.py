# ABOUTME: Prepares a synthetic installation against real private HTTP assets before publication.
# ABOUTME: Marks fixture qualification explicitly and exports only the safe operation receipt.
from pathlib import Path
import json,hashlib,os,shutil,sys
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
import types
sys.dont_write_bytecode=True
home=Path.home();profile=home/'.hermes';out=home/'release-ui-fixture'
sys.path.insert(0,str(profile/'hermes-agent'))
namespace=types.ModuleType('ui_fixture_manager');namespace.__path__=[str(profile/'plugins/lifeos-release-manager')];sys.modules[namespace.__name__]=namespace
from ui_fixture_manager.cli import prepare
from ui_fixture_manager.release_catalog import ReleaseCatalog
settings={'package_commit': '10459df6c2b27bda8911dfd96a25b92bee769c93', 'version': '0.4.2-rc.3', 'archive': '/home/lifeos-hermes/release-ui-fixture/0.4.2-rc.3-10459df6.tgz', 'archive_bytes': 119155068, 'archive_sha256': 'fe7a9bfbf1c3f68355fc1125f125fac8250a1f9ccecf95ff697b5979dc3d5474', 'dashboard': '/home/lifeos-hermes/release-ui-fixture/hermes-dashboard.tgz', 'hermes_dashboard_sha256': 'e7c93e754de99b6ec66ae17ae313377dc513104da2776a099c391a7aab347bec', 'hermes_base': '71d34bad1045610252eda02ee79549436896e784', 'lifeos_base': '5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c', 'hermes_patch_count': 10, 'lifeos_patch_count': 25}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(settings['archive'])==settings['archive_sha256']
assert sha(settings['dashboard'])==settings['hermes_dashboard_sha256']
certificate={**settings,'format':1,'status':'QUALIFIED','program_commit':settings['package_commit'],'test_fixture_only':True,'production_qualified':False}
assets={Path(settings['archive']).name:Path(settings['archive']),'hermes-dashboard.tgz':Path(settings['dashboard']),'RELEASE-CERTIFICATE.json':json.dumps(certificate).encode()}
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  if self.path=='/repos/0ut5ider/lifeos-hermes-plugin/releases/tags/v'+settings['version']:
   value={'tag_name':'v'+settings['version'],'draft':False,'prerelease':True,'assets':[{'name':name,'size':value.stat().st_size if isinstance(value,Path) else len(value),'digest':'sha256:'+(sha(value) if isinstance(value,Path) else hashlib.sha256(value).hexdigest()),'browser_download_url':origin+'/0ut5ider/lifeos-hermes-plugin/releases/download/v'+settings['version']+'/'+name} for name,value in assets.items()]};value=json.dumps(value).encode()
  else:value=assets.get(self.path.rsplit('/',1)[-1])
  if value is None:self.send_error(404);return
  self.send_response(200);self.send_header('Content-Length',str(value.stat().st_size if isinstance(value,Path) else len(value)));self.end_headers()
  if isinstance(value,Path):
   with value.open('rb') as stream:shutil.copyfileobj(stream,self.wfile)
  else:self.wfile.write(value)
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);origin='http://127.0.0.1:'+str(server.server_port);thread=Thread(target=server.serve_forever);thread.start()
try:
 result=prepare(profile,settings['version'],name='SyntheticAdrian',assistant='SyntheticCerebo',catalog=ReleaseCatalog(api_origin=origin,asset_origin=origin))
 (out/'private-stage-preparation.json').write_text(json.dumps({'test_fixture_only':True,'production_qualified':False,'operation':result},indent=2)+'\n')
finally:
 server.shutdown();thread.join();server.server_close()
