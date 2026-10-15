# ABOUTME: Checks the public install verifier against altered stock identity and complete source evidence.
# ABOUTME: Runs the real provenance helper without importing remote installation code or reading personal records.
import ast,copy,json
from pathlib import Path

root=Path(__file__).resolve().parent
tree=ast.parse((root/'verify_public_installation.py').read_text())
node=next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='validate_stock_provenance'),None)
assert node is not None,'The verifier does not bind complete stock provenance'
namespace={}
exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual-provenance-helper>','exec'),namespace)
check=namespace['validate_stock_provenance']
baseline=json.loads((root/'public-stock-baseline.json').read_bytes())
provenance=json.loads((root/'public-stock-source-verification.json').read_bytes())
check(baseline,provenance)
cases=[]
for label,document,field,value in [
 ('baseline-commit','baseline','hermes_commit','0'*40),
 ('baseline-archive','baseline','stock_source_sha256','0'*64),
 ('baseline-guest','baseline','guest',112),
 ('baseline-manager','baseline','release_manager_installed',True),
 ('baseline-lifeos','baseline','lifeos_installed',True),
 ('source-status','provenance','status','FAIL'),
 ('source-commit','provenance','hermes_commit','0'*40),
 ('source-archive','provenance','stock_source_sha256','0'*64),
 ('source-dashboard','provenance','dashboard_sha256','0'*64),
 ('source-incomplete','provenance','complete_runtime_file_set_verified',False),
 ('source-count','provenance','runtime_files_verified',18308),
 ('source-links','provenance','source_links_verified',1),
 ('source-guest','provenance','guest',112),
 ('source-patches','provenance','hermes_patches',1),
 ('source-manager','provenance','release_manager_installed',True),
 ('source-lifeos','provenance','lifeos_installed',True),
]:
 b=copy.deepcopy(baseline);p=copy.deepcopy(provenance)
 (b if document=='baseline' else p)[field]=value
 try:check(b,p)
 except (AssertionError,KeyError,TypeError):cases.append(label)
 else:raise AssertionError('Altered provenance accepted: '+label)
print(json.dumps({'status':'PASS','positive_controls':1,'refusal_controls':len(cases),'cases':cases},indent=2))
