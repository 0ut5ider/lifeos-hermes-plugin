# ABOUTME: Tests actual owner-search validation statements against bounded synthetic response data.
# ABOUTME: Writes only local control results and never constructs guest completion receipts.
import ast,copy,json,sys
from pathlib import Path

root=Path(__file__).resolve().parent
nodes=ast.parse((root/'verify_development_owner_turn.py').read_text()).body
def assignment(node,name):return isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in node.targets)
start=next(i for i,n in enumerate(nodes) if assignment(n,'responses'))
stop=next(i for i,n in enumerate(nodes) if assignment(n,'report'))
code=compile(ast.Module(body=nodes[start:stop],type_ignores=[]),'<actual-owner-search-validation>','exec')
reference={'id':'a'*32,'revision':1}
match={'reference':reference,'content':'Synthetic daily acceptance verification code is STABLE-050-DEV-04EFE633.',
 'category':'project','project':'release-0.5.0-qualification','writer':'terminal:1008','status':'active','source':{'session':'synthetic-save-session'}}
ok={'status':'ok','results':[match]}
refused={'status':'rejected','reason':'Memory tool arguments contain missing or unrecognized fields'}
cases=[('single-success',[ok],True),('argument-refusal-then-success',[refused,ok],True),
 ('repeated-exact-success',[ok,ok],'--characterize' not in sys.argv),
 ('empty-responses',[],False),('unknown-refusal',[{'status':'rejected','reason':'unrecognized fixture refusal'},ok],False),
 ('refusal-after-success',[ok,refused],False)]
for name,key,value in [('reference','reference',{'id':'b'*32,'revision':1}),('content','content','other fixture content'),
 ('writer','writer','terminal:other'),('category','category','assistant'),('project','project','other-project'),
 ('status','status','forgotten'),('session','source',{'session':'other-session'})]:
 wrong=copy.deepcopy(ok);wrong['results'][0][key]=value
 cases.append(('wrong-'+name,[wrong,ok],False))
results=[]
for name,responses,expected in cases:
 accepted=True
 try:exec(code,{'json':json,'results':[{'output':json.dumps(d)} for d in responses],
  'receipt':{'reference':reference},'sessions':['synthetic-save-session','synthetic-search-session']})
 except (AssertionError,IndexError,KeyError,TypeError):accepted=False
 results.append({'case':name,'expected_result_verified':accepted==expected,'accepted':accepted})
report={'status':'PASS' if all(x['expected_result_verified'] for x in results) else 'FAIL','cases':len(results),
 'characterization':'--characterize' in sys.argv,'results':results,'completion_receipt_constructed':False,'remote_commands_run':False}
(root/'owner-search-controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
assert report['status']=='PASS'
