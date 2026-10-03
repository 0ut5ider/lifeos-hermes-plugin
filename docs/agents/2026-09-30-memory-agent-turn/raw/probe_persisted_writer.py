from pathlib import Path
import json,sys
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tests')]
from test_memory_agent import MemoryAgentTests
from test_memory_native import OWNER
case=MemoryAgentTests('test_actual_agent_turn_commits_native_fact_and_reports_its_receipt')
case.setUp()
try:
 case.test_actual_agent_turn_commits_native_fact_and_reports_its_receipt()
 receipt=json.loads(case.outcome['conversation']['final_response'])
 native=case.fixture.fixture.fixture.fixture.memory.get(OWNER,receipt['reference'])
 assert native['writer']=='chat-a:100',native
 assert native['category']=='project' and native['project']=='lab',native
 print(json.dumps({'final_receipt':receipt,'persisted_native_record':native,'http_requests':case.fixture.fixture.received},indent=2))
finally:
 case.doCleanups()
