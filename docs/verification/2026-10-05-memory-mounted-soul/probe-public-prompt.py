# ABOUTME: Measures canonical public LifeOS prompt loading in the actual Hermes loader.
# ABOUTME: Uses synthetic identity and captures explicit model-window limits.
import json,sys,os
from pathlib import Path
sys.path.insert(0,'tests')
import test_memory_prompt as fixture_module
from agent.prompt_builder import load_soul_md
f=fixture_module.MemoryPromptTests();f.setUp()
try:
 f.write('LIFEOS/LIFEOS_SYSTEM_PROMPT.md',(fixture_module.SOURCE/'LIFEOS/LIFEOS_SYSTEM_PROMPT.md').read_text())
 result=f.native()
 assert result['ok'],result
 soul=result['soul']
 profile=f.fixture.configuration.path.parent
 (profile/'SOUL.md').write_text(soul)
 os.environ['HERMES_HOME']=str(profile)
 results=[]
 for context_length in (None,32768,131072,262144):
  loaded=load_soul_md(context_length=context_length,home_override=profile)
  results.append({'context_length':context_length,'source_chars':len(soul.strip()),'loaded_chars':len(loaded or ''),'complete':loaded==soul.strip()})
 print(json.dumps({'canonical_soul_chars':len(soul),'loads':results},indent=2))
finally:
 f.doCleanups()
