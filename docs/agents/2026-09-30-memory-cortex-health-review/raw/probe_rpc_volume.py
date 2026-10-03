# ABOUTME: Confirms the actual RPC request truncation behind the saved large health report.
# ABOUTME: Reuses synthetic captured native output and never opens a memory configuration.
from pathlib import Path
import json,subprocess,sys,os
r=Path(__file__).resolve().parent
rows=[json.loads(line) for line in (r/'health-edges.txt').read_text().splitlines()]
report=json.loads(next(row for row in rows if row['case']=='invalid-hot-volume')['unmanaged']['stdout'])
content=json.dumps(report,separators=(',',':'),ensure_ascii=False)
request=json.dumps({'operation':'filter_diagnostic','arguments':{'content':content,'timestamp':report['ts']}},separators=(',',':'),ensure_ascii=False)
# The parser fails before accessing this deliberately nonexistent configuration path.
result=subprocess.run([sys.executable,'lifeos_hook_bridge/memory_rpc.py','--configuration',str(r/'nonexistent-synthetic-configuration.json')],input=request,text=True,capture_output=True,env=dict(os.environ),timeout=5)
print(json.dumps({'request_bytes':len(request.encode()),'input_read_limit':131073,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}))
