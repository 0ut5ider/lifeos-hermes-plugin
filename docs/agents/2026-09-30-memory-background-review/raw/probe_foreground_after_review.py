# ABOUTME: Runs a real foreground turn after a real background skill review in one agent process.
# ABOUTME: Checks that the review-origin ContextVar does not remove the subsequent human quote exception.
from pathlib import Path
import json,os,subprocess,sys
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tests')]
from test_memory_review import MemoryReviewTests,OWNERSHIP,SKILL
from test_memory_native import OWNER
import test_memory_model_calls
raw=Path.cwd()/'docs/agents/2026-09-30-memory-background-review/raw'
source=Path('tests/memory_host_calls.py').read_text().replace('str(Path(__file__).parents[1])','str(Path.cwd())')
needle='        denied_writes = []'
assert needle in source
source=source.replace(needle,'''        from tools.skill_provenance import get_current_write_origin
        foreground_origin = get_current_write_origin()
        with redirect_stdout(diagnostics):
            followup = agent.run_conversation(settings['followup_message'],conversation_history=conversation['messages'])
        denied_writes = []''')
source=source.replace("'review_done':review_done,'review_summaries':review_summaries}","'review_done':review_done,'review_summaries':review_summaries,'foreground_origin':foreground_origin,'followup':followup}")
program=raw/'foreground_after_review_child.py';program.write_text(source)
case=MemoryReviewTests();case.setUp()
try:
 host=case.fixture;fixture=host.fixture
 native=host.fixture.fixture.fixture
 marker='Synthetic forgotten followup foreground quote'
 saved=native.remember(marker,'followup-original');native.memory.forget(OWNER,saved['reference'],'followup-forget')
 def respond(request):
  reviewing=any(row.get('role')=='user' and isinstance(row.get('content'),str) and row['content'].startswith('Review the conversation above') for row in request['messages'])
  if not reviewing:return {'role':'assistant','content':'SYNTHETIC-FOREGROUND-OK'}
  results=[row for row in request['messages'] if row.get('role')=='tool']
  if results:return {'role':'assistant','content':results[-1]['content']}
  return {'role':'assistant','content':None,'tool_calls':[{'id':'review-skill','type':'function','function':{'name':'skill_manage','arguments':json.dumps({'operations':[{'action':'create','name':'synthetic-review','content':SKILL}]})}}]}
 fixture.response_message=respond
 configuration=dict(fixture.host_config,memory=OWNERSHIP,plugins={'enabled':['lifeos-hook-bridge']},skills={'write_approval':False})
 configuration['model']=dict(configuration['model'],streaming=False,context_length=131072)
 (host.home/'config.yaml').write_text(json.dumps(configuration))
 env={key:os.environ[key] for key in ('PATH','LANG','TZ') if key in os.environ}
 env.update(HOME=str(native.home),HERMES_HOME=str(host.home),LIFEOS_HERMES_SOURCE=str(test_memory_model_calls.HOST),LIFEOS_HOOK_SETTINGS=str(native.root/'settings.json'),BUN_CONFIG_NO_AUTO_INSTALL='1')
 settings={'route':fixture.route,'operation':'conversation','message':'Verify a synthetic task.','author':'100','background_review':True,'review_focus':None,'review_explicit':False,'followup_message':marker}
 result=subprocess.run([sys.executable,str(program)],input=json.dumps(settings),env=env,capture_output=True,text=True,timeout=60)
 outcome=json.loads(result.stdout) if result.returncode==0 else None
 print(json.dumps({'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'requests':fixture.received},indent=2))
 assert result.returncode==0 and result.stderr=='',result
 assert outcome['review_done'] and outcome['review_summaries'],outcome
 assert outcome['foreground_origin']!='background_review',outcome
 assert not outcome['followup']['failed'] and outcome['followup']['final_response']=='SYNTHETIC-FOREGROUND-OK',outcome
 calls=[r for r in fixture.received if r['path']=='/v1/chat/completions']
 assert len(calls)==4,calls
 assert marker in json.dumps(calls[-1]),calls[-1]
 assert (host.home/'skills/synthetic-review/SKILL.md').read_text()==SKILL
 for name,data in host.original.items():assert (host.home/'memories'/name).read_bytes()==data
finally:case.doCleanups()
