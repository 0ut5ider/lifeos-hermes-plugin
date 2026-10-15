# ABOUTME: Runs the actual native tool-closure preparation against the isolated stock runtime.
# ABOUTME: Records pinned tool names and preserves the initial failing runtime evidence.
import json
import os
from pathlib import Path
import sys
import time

repo=Path(__file__).resolve().parents[3]
root=Path('/home/outsider/.cache/lifeos-memory-portability-20261015/stock-runtime-construction')
sys.path[:0]=[str(repo),str(root/'runtime/hermes')]
sys.dont_write_bytecode=True
os.umask(0o077)
os.environ.update(HOME=str(root/'account'),HERMES_HOME=str(root/'runtime/dependency-profile'))
from optional.lifeos_release_manager.release_payload import prepare_stock_tools
started=time.monotonic();receipt={'status':'FAIL','selected_live':False,'qualified_release':False}
try:
 receipt.update(tools=prepare_stock_tools(root/'runtime'),status='PASS')
finally:
 receipt['elapsed_seconds']=time.monotonic()-started
 (root/'tools-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 (root/'tools.done').write_text('0\n' if receipt['status']=='PASS' else '1\n')
