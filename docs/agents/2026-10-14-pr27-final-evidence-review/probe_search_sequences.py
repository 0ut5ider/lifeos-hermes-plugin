# ABOUTME: Verifies all repeated successful searches are checked and only exact known argument refusals are tolerated.
# ABOUTME: Executes actual search validation statements with bounded synthetic local responses and writes no guest receipt.
import ast,copy,json
from pathlib import Path

project=Path(__file__).resolve().parents[3]
source=project/'docs/verification/2026-10-14-release-0.5.0'
nodes=ast.parse((source/'verify_development_owner_turn.py').read_text()).body
def assigned(node,name):return isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id==name for target in node.targets)
start=next(i for i,node in enumerate(nodes) if assigned(node,'responses'))
stop=next(i for i,node in enumerate(nodes) if assigned(node,'report'))
code=compile(ast.Module(body=nodes[start:stop],type_ignores=[]),'<actual-search-sequence-validator>','exec')
reference={'id':'a'*32,'revision':1}
match={'reference':reference,'content':'Synthetic daily acceptance verification code is STABLE-050-DEV-04EFE633.',
 'category':'project','project':'release-0.5.0-qualification','writer':'terminal:1008','status':'active','source':{'session':'synthetic-save'}}
ok={'status':'ok','results':[match]}
refused={'status':'rejected','reason':'Memory tool arguments contain missing or unrecognized fields'}
extra_refusal={**refused,'results':[]}
two=copy.deepcopy(ok);two['results'].append(copy.deepcopy(match))
cases=[('interspersed-known-refusals',[refused,ok,refused,ok],True),
 ('three-exact-successes',[ok,ok,ok],True),
 ('two-matches-before-last-success',[two,ok],False),
 ('two-matches-last',[ok,two],False),
 ('no-matches-before-last-success',[{'status':'ok','results':[]},ok],False),
 ('no-matches-last',[ok,{'status':'ok','results':[]}],False),
 ('only-argument-refusals',[refused,refused],False),
 ('nonexact-refusal-shape',[extra_refusal,ok],False)]
results=[]
for name,responses,expected in cases:
 namespace={'json':json,'results':[{'output':json.dumps(response)} for response in responses],
            'receipt':{'reference':reference},'sessions':['synthetic-save','synthetic-search']}
 accepted=True
 try:exec(code,namespace)
 except (AssertionError,KeyError,IndexError,TypeError):accepted=False
 assert accepted==expected,name
 results.append({'case':name,'status':'PASS','accepted':accepted,
                 'successful_searches':namespace.get('successful_searches'),
                 'argument_refusals':namespace.get('argument_refusals')})
report={'status':'PASS','cases':len(results),'results':results,'guest_completion_receipt_written':False,
        'remote_commands_run':False,'raw_conversation_read':False}
Path(__file__).with_name('search-sequence-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
