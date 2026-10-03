# ABOUTME: Runs a complete scripted Hermes turn and inspects its saved fact source session.
# ABOUTME: Preserves native registry readback without using a live model or installation.
import json
from pathlib import Path
import test_memory_agent as agent
from test_memory_native import OWNER
out=Path(__file__).parent
f=agent.MemoryAgentTests();f.setUp()
try:
    f.test_actual_agent_turn_commits_native_fact_and_reports_its_receipt()
    memory=f.fixture.fixture.fixture.fixture.memory
    receipt=json.loads(f.outcome['conversation']['final_response'])
    record=memory.get(OWNER,receipt['reference'])
    result={'outcome':f.outcome,'record':record}
    (out/'agent-source-session-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'record':record,'turn_session':f.outcome['conversation'].get('session_id')},indent=2))
finally:f.doCleanups()
