# ABOUTME: Counts native graph projection fields with the actual history walker.
# ABOUTME: Identifies admission thresholds using retained synthetic native results.
from pathlib import Path
import json
from lifeos_hook_bridge.memory_history import project_value
from lifeos_hook_bridge.memory_operational_views import projection
out=Path(__file__).resolve().parent
rows=[]
for path in sorted((out/'native-raw').glob('*.json')):
    document=json.loads(path.read_text());value=document['graph'] if path.name.endswith('.graph.json') else document;strings=[]
    project_value(value,lambda s:strings.append(s) and False)
    content=json.dumps(value,ensure_ascii=False)
    proj=projection(content)
    rows.append({'label':path.name,'fields':len(strings),'graph_python_bytes':len(content.encode()),'projection_bytes':len(proj.encode()) if proj is not None else None,'accepted_projection':proj is not None})
(out/'projection-measurements.json').write_text(json.dumps(rows,indent=2)+'\n')
for row in rows:print(row)
