# ABOUTME: Checks retained archive and certificate identity guards against actual immutable public bytes.
# ABOUTME: Executes only local assertions with public inputs and no installed profile or guest calls.
import ast,hashlib,json
from pathlib import Path
p=Path(__file__).resolve().parents[3];r=Path(__file__).resolve().parent;s=p/'docs/verification/2026-10-14-release-0.5.0/verify_daily_restored_programs.py'
raw=s.read_bytes();tree=ast.parse(raw)
nodes=[n for n in tree.body if isinstance(n,ast.Assert) and "job / 'download/" in ast.unparse(n)]
assert len(nodes)==3
code=compile(ast.Module(body=nodes,type_ignores=[]),'<actual-retained-public-asset-guards>','exec')
archive=Path('/home/outsider/.cache/lifeos-release-0.5.0-20261014/packages/0.5.0-04efe633.tgz').read_bytes()
certificate=(p/'docs/verification/2026-10-14-release-0.5.0/RELEASE-CERTIFICATE.json').read_bytes()
results=[]
for name in ['public-positive','altered-archive','altered-certificate','request-certificate-differs','missing-archive','missing-certificate']:
 class File:
  def __init__(self,key=''):self.key=key
  def __truediv__(self,key):return File(key)
  def read_bytes(self):
   is_archive=self.key.endswith('.tgz')
   if name=='missing-archive' and is_archive or name=='missing-certificate' and not is_archive:raise FileNotFoundError(self.key)
   content=archive if is_archive else certificate
   if name=='altered-archive' and is_archive or name=='altered-certificate' and not is_archive:content+=b' '
   return content
 request={'package_sha256':'a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813','certificate':json.loads(certificate)}
 if name=='request-certificate-differs':request['certificate']={}
 accepted=True
 try:exec(code,{'hashlib':hashlib,'json':json,'job':File(),'request':request})
 except (AssertionError,FileNotFoundError):accepted=False
 assert accepted==(name=='public-positive'),name
 results.append({'case':name,'accepted':accepted,'status':'PASS','remote_calls':False})
result={'status':'PASS','cases':results,'reviewed_verifier_sha256':hashlib.sha256(raw).hexdigest(),'public_archive_sha256':hashlib.sha256(archive).hexdigest(),'public_certificate_sha256':hashlib.sha256(certificate).hexdigest()}
(r/'retained-public-asset-controls.json').write_text(json.dumps(result,indent=2)+'\n');(r/'verify_daily_restored_programs.archive-guard-closure.py').write_bytes(raw);print(json.dumps(result,indent=2))
