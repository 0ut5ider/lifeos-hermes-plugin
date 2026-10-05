# ABOUTME: Changes real selected-profile flags after a learning mutation loads its store.
# ABOUTME: Checks whether the actual native mutation refuses the queued write under its file lock.
import json
import sys

from agent.learning_graph import memory_fingerprint
from agent.learning_mutations import edit_node, delete_node
from hermes_constants import get_hermes_home
import tools.memory_tool as memory_tool

request=json.loads(sys.stdin.read())
profile=get_hermes_home()
source=request['source']
path=profile/'memories'/('MEMORY.md' if source=='memory' else 'USER.md')
before=path.read_bytes()
identifier=f'memory:{source}:0:'+memory_fingerprint(before.decode().strip())
original_load=memory_tool.load_on_disk_store
loads=[]


def load():
    store=original_load()
    loads.append(store.target_enabled('memory' if source=='memory' else 'user'))
    (profile/'config.yaml').write_text('memory:\n  memory_enabled: false\n  user_profile_enabled: false\n')
    return store


memory_tool.load_on_disk_store=load
result=edit_node(identifier,'Synthetic queued replacement.') if request['operation']=='edit' else delete_node(identifier)
print(json.dumps({'result':result,'unchanged':path.read_bytes()==before,'loaded_enabled':loads}))
