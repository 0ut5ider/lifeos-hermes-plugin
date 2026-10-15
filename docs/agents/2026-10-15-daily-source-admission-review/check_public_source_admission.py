# ABOUTME: Checks source admission uses the exact public archive and refuses altered source previews.
# ABOUTME: Runs actual extraction, digest, owner, and preview guards locally without personal inputs or HTTP calls.
import ast,copy,hashlib,json,re,tarfile,time
from pathlib import Path
from types import SimpleNamespace
p=Path(__file__).resolve().parents[3];r=Path(__file__).resolve().parent;s=p/'docs/verification/2026-10-14-release-0.5.0/admit_daily_program_sources.py'
raw=s.read_bytes();tree=ast.parse(raw)
archive=Path('/home/outsider/.cache/lifeos-release-0.5.0-20261014/packages/0.5.0-04efe633.tgz')
actual=hashlib.sha256(archive.read_bytes()).hexdigest();assert actual=='a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813'
extract=next(n for n in tree.body if isinstance(n,ast.With) and 'tarfile.open' in ast.unparse(n.items[0].context_expr))
ns={'tarfile':tarfile,'archive':archive,'contents':{},'prefix':'lifeos/LifeOS/install/','re':re}
exec(compile(ast.Module(body=[extract],type_ignores=[]),'<actual-public-archive-extraction>','exec'),ns)
contents=ns['contents'];assert len(contents)==57 and sum(x.startswith('skills/') for x in contents)==56
configuration={'root':'/synthetic/public-admission','principal':'synthetic-review-owner'}
expected_node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='expected' for t in n.targets))
ns.update(configuration=configuration,hashlib=hashlib,json=json)
exec(compile(ast.Module(body=[expected_node],type_ignores=[]),'<actual-expected-digest-map>','exec'),ns);expected=ns['expected']
actual_digest_source=ast.parse((p/'lifeos_hook_bridge/memory_source_review.py').read_text())
functions=[n for n in actual_digest_source.body if isinstance(n,ast.FunctionDef) and n.name in {'_digest','_source_digest'}]
d={'hashlib':hashlib,'json':json};exec(compile(ast.Module(body=functions,type_ignores=[]),'<actual-source-review-digest>','exec'),d)
assert all(expected[k]==d['_source_digest'](SimpleNamespace(root=Path(configuration['root'])),SimpleNamespace(principal=configuration['principal']),k,v) for k,v in contents.items())
http=next(n for n in tree.body if isinstance(n,ast.With) and 'httpx.Client' in ast.unparse(n.items[0].context_expr));body=http.body
start=next(i for i,n in enumerate(body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='preview' for t in n.targets))
preview_nodes=body[start:start+3]
base={'sources':[{'path':k,'accepted':True,'digest':expected[k],'content':v} for k,v in contents.items()],'signature':'a'*64}
mutations=[('public-positive',lambda q:None,True),('source-refused',lambda q:q['sources'][0].update(accepted=False),False),('wrong-digest',lambda q:q['sources'][0].update(digest='0'*64),False),('wrong-content',lambda q:q['sources'][0].update(content='Synthetic changed content'),False),('foreign-path',lambda q:q['sources'][0].update(path='LIFEOS/USER/PRINCIPAL/IDENTITY.md'),False),('missing-path',lambda q:q['sources'].pop(),False),('extra-path',lambda q:q['sources'].append({'path':'LIFEOS/USER/HEALTH.md','accepted':True,'digest':'0'*64,'content':'Synthetic private marker'}),False),('duplicate-path',lambda q:q['sources'].__setitem__(0,copy.deepcopy(q['sources'][1])),False)]
results=[]
for name,mutate,should_accept in mutations:
 q=copy.deepcopy(base);mutate(q);accepted=True
 env={'response':SimpleNamespace(json=lambda:q),'contents':contents,'expected':expected}
 try:exec(compile(ast.Module(body=preview_nodes,type_ignores=[]),'<actual-source-preview-guards>','exec'),env)
 except (AssertionError,KeyError):accepted=False
 assert accepted==should_accept,name
 results.append({'case':name,'accepted':accepted,'status':'PASS'})
owner_guard=next(n for n in body if isinstance(n,ast.Assert) and "me['provider']" in ast.unparse(n))
for name,me,should_accept in [('owner-positive',{'provider':'basic','user_id':'adrian','expires_at':time.time()+60},True),('wrong-owner',{'provider':'basic','user_id':'other','expires_at':time.time()+60},False),('wrong-provider',{'provider':'oauth','user_id':'adrian','expires_at':time.time()+60},False),('expired-owner',{'provider':'basic','user_id':'adrian','expires_at':time.time()-60},False)]:
 accepted=True
 try:exec(compile(ast.Module(body=[owner_guard],type_ignores=[]),'<actual-owner-guard>','exec'),{'me':me,'time':time})
 except AssertionError:accepted=False
 assert accepted==should_accept,name
 results.append({'case':name,'accepted':accepted,'status':'PASS'})
report={'status':'PASS','public_archive_sha256':actual,'public_sources':len(contents),'public_skills':56,'public_constitution':1,'actual_native_digest_matches':len(expected),'cases':results,'remote_calls':False,'personal_inputs_used':False,'approvals_sent':False,'completion_receipt_created':False,'reviewed_operator_sha256':hashlib.sha256(raw).hexdigest()}
(r/'public-source-admission-controls.json').write_text(json.dumps(report,indent=2)+'\n');(r/'admit_daily_program_sources.reviewed.py').write_bytes(raw)
print(json.dumps(report,indent=2))
