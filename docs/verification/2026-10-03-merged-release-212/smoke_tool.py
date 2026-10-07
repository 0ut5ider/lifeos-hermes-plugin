# ABOUTME: Executes a synthetic tool turn through each installed Hermes agent.
# ABOUTME: Keeps raw model streams private and reports only verified release outcomes.
from pathlib import Path
import os,sys,json,subprocess,time
os.umask(0o077)
r=Path(__file__).parent
target=sys.argv[1]
sys.argv=[str(r/'deploy_release.py'),target,'smoke']
namespace={}
source=(r/'deploy_release.py').read_text().split("if ACTION == 'prepare':")[0]
exec(compile(source,str(r/'deploy_release.py'),'exec'),namespace)
marker='MERGED-212-'+target.upper()+'-TOOL-READY'
prompt=r/'tool-prompt.txt'
prompt.write_text('Use the terminal tool to execute pwd. After the successful tool result, reply exactly '+marker+'.')
try:
 with (r/'tool-stream.jsonl').open('w') as out,(r/'tool-stderr.txt').open('w') as err:
  result=subprocess.run([str(namespace['COMMAND']),'chat','--oneshot','-Q','--format','stream-json','-t','terminal','--query-file',str(prompt)],cwd=namespace['OPERATING_HOME'],env=namespace['ENV'],stdout=out,stderr=err,timeout=300)
 rows=[]
 for line in (r/'tool-stream.jsonl').read_text().splitlines():
  try: rows.append(json.loads(line))
  except ValueError: continue
 uses=[x for x in rows if x.get('type')=='tool_use' and x.get('name')=='terminal']
 results=[x for x in rows if x.get('type')=='tool_result' and x.get('name')=='terminal' and not x.get('is_error')]
 final=[x for x in rows if x.get('type')=='result']
 assert result.returncode==0 and uses and results and final and final[-1].get('exit_code')==0 and marker in final[-1].get('text',''), 'Real agent tool verification fails; inspect private stream'
 assert any(x.get('input',{}).get('command','').strip()=='pwd' for x in uses), 'Expected read-only pwd tool call'
 record={'target':target,'exit_code':0,'tool':'terminal','command':'pwd','tool_succeeded':True,'final_reply_marker':marker,'session_id':final[-1]['session_id']}
 (r/'tool-result.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
 (r/'tool.exit').write_text('0\n')
except BaseException:
 (r/'tool.exit').write_text('1\n')
 raise
finally:
 (r/'tool.done').touch()
