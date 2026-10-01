# ABOUTME: Compares managed and unmanaged display of one valid large native proposal.
# ABOUTME: Captures the exact native diagnostic-validation rejection without altering code.
import json,shutil
from dataclasses import replace
from test_memory_diagnostics import MemoryDiagnosticTests
from test_memory_native import OWNER,SOURCE
from lifeos_hook_bridge.memory_sources import _strings
c=MemoryDiagnosticTests();c.setUp()
try:
 m=c.fixture.fixture.memory
 t=c.root/'LIFEOS/TOOLS';t.unlink();shutil.copytree(SOURCE/'LIFEOS/TOOLS',t)
 (c.root/'LIFEOS/USER/PROJECTS.md').write_text('| **SyntheticLab** | synthetic |\n')
 target=c.root/'LIFEOS/USER/CONFIG/OPERATIONAL_RULES.md';target.write_text('# Synthetic\n')
 edit='Synthetic long authorized proposal marker. '+'abcd '*8000
 receipt=m.native_add(replace(OWNER,proposals=('create','review','approve')),{'type':'proposal','target_kind':'operational-rule','target_file':str(target),'edit':edit,'confidence':0.5,'rationale':'Synthetic current owner proposal.'},request_id='long-control',project='',source_session='synthetic')
 assert receipt['ok']
 line=(c.obs/'pending-proposals.jsonl').read_text().strip(); row=json.loads(line)
 text=line+'\n'+'\n'.join(_strings(row))
 check=m._native('validate_batch',items=[{'type':'idea','title':'Native diagnostic sample','content':text}])
 managed=c.call('MemoryInsights.ts').stdout
 (c.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
 unmanaged=c.call('MemoryInsights.ts',context=False).stdout
 assert 'Synthetic long authorized proposal marker' in managed and 'Synthetic long authorized proposal marker' in unmanaged
 assert [s for s in managed.splitlines() if s.strip().startswith('•')] == [s for s in unmanaged.splitlines() if s.strip().startswith('•')]
 print(json.dumps({'receipt':receipt,'edit_chars':len(edit),'diagnostic_validation_chars':len(text),'native_validation':check,'managed':managed,'unmanaged':unmanaged}))
finally:c.doCleanups()
