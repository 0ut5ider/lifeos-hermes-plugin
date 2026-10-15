# ABOUTME: Verifies every stock runtime source and compiled dashboard file against admitted inputs.
# ABOUTME: Separately generates native distribution metadata and emits only safe file counts and hashes.
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

os.umask(0o077)
repo=Path(__file__).resolve().parents[3]
root=Path('/home/outsider/.cache/lifeos-memory-portability-20261015/stock-full-9b204dad/runtime')
sys.path[:0]=[str(repo),str(root/'stock-source')]
sys.dont_write_bytecode=True
from optional.lifeos_release_manager.stock_hermes import verify_source,validate_archive
from optional.lifeos_release_manager.release_stage import runtime_source_fingerprint
from scripts.build.agent import write_metadata

runtime=json.loads((root/'runtime.json').read_bytes())
record=runtime['stock_source'];verify_source(root/'stock-source',record)
package=Path('/home/outsider/.cache/lifeos-memory-portability-20261015/stock-closure-packages/0.5.0-9b204dad')
validate_archive(package/'stock-hermes.tgz',record['archive'])


def files(directory, *, excluded=()):
 result={}
 for path in directory.rglob('*'):
  name=path.relative_to(directory)
  if name.parts[0] in excluded or '__pycache__' in name.parts or path.suffix=='.pyc':continue
  if path.is_symlink():raise ValueError('The actual stock source introduces an unreviewed link')
  if path.is_file():result[name.as_posix()]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'mode':path.stat().st_mode & 0o777}
 return result


expected=files(root/'stock-source')
web=files(root/'compiled-dashboard/hermes_cli/web_dist')
for name,metadata in web.items():expected['hermes_cli/web_dist/'+name]=metadata
with tempfile.TemporaryDirectory() as temp:
 generated=Path(temp);write_metadata(root/'stock-source/pyproject.toml',generated)
 metadata=files(generated);expected.update(metadata)
actual=files(root/'hermes',excluded={'.hermes','.bytecode-fingerprint'})
if actual!=expected:
 missing=sorted(set(expected)-set(actual));extra=sorted(set(actual)-set(expected))
 changed=sorted(name for name in set(actual)&set(expected) if actual[name]!=expected[name])
 raise ValueError(json.dumps({'missing':missing,'extra':extra,'changed':changed}))
receipt={'status':'PASS','qualified_release':False,'selected_live':False,'stock_commit':record['commit'],
 'patches':0,'source_files':len(files(root/'stock-source')),'dashboard_files':len(web),
 'generated_metadata_files':len(metadata),'runtime_files':len(actual),
 'complete_runtime_source_file_set_verified':True,'source':runtime_source_fingerprint(root/'hermes'),
 'native_generated_root_metadata_excluded':['.hermes','.bytecode-fingerprint']}
output=Path(__file__).parent/'stock-runtime-source-verification.json'
output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
