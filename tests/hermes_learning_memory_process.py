# ABOUTME: Runs actual Hermes learning graph and mutation operations in an isolated profile.
# ABOUTME: Records original files and current disabled-store behavior without mock APIs.
import json
import sys
from pathlib import Path

from agent.learning_graph import _memory_cards, memory_fingerprint
from agent.learning_mutations import node_detail, edit_node, delete_node
from hermes_constants import get_hermes_home

request=json.loads(sys.stdin.read())
profile=get_hermes_home()
source=request['source']
filename='MEMORY.md' if source=='memory' else 'USER.md'
path=profile/'memories'/filename
before=path.read_bytes()
entry=before.decode().strip()
identifier=f'memory:{source}:{0 if source=="memory" else 1}:'+memory_fingerprint(entry)
if request['operation']=='cards':
 result=_memory_cards()
elif request['operation']=='detail':
 result=node_detail(identifier)
elif request['operation']=='edit':
 result=edit_node(identifier,'Synthetic replacement journey fact.')
elif request['operation']=='delete':
 result=delete_node(identifier)
else:
 raise ValueError('Choose a test operation')
print(json.dumps({'result':result,'unchanged':path.read_bytes()==before,'bytes':path.read_text()}))
