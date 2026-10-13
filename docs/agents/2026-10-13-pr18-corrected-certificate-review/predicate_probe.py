# ABOUTME: Evaluates only the certifier's applied-receipt predicate and inventories recovery admission use.
# ABOUTME: Uses safe copied receipts and altered in-memory fixture data without running certificate issuance.
import ast
from copy import deepcopy
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
source = OUT / 'certify_corrected_prerelease.py'
tree = ast.parse(source.read_text())
function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'applied')
fragment = ast.Module(body=[function], type_ignores=[])
build = json.loads((OUT / 'private-stage-candidate-build.json').read_bytes())
receipt = json.loads((OUT / 'private-stage-fresh-recovery.json').read_bytes())
current = receipt
namespace = {'build': build, 'load': lambda name: deepcopy(current)}
exec(compile(fragment, str(source) + ':applied-only', 'exec'), namespace)
namespace['applied']('synthetic-component-fixture')
changed = deepcopy(receipt)
changed['services']['hermes-gateway.service']['LoadState'] = 'not-found'
current = changed
try:
    namespace['applied']('synthetic-component-fixture')
    missing_service_accepted = True
except AssertionError:
    missing_service_accepted = False
loads = [node.args[0].value for node in ast.walk(tree)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'load'
    and node.args and isinstance(node.args[0], ast.Constant)]
admission_checked = 'private-stage-recovery-admission.json' in loads
report = {'actual_fresh_receipt_passes': True, 'missing_gateway_loadstate_accepted': missing_service_accepted,
    'recovery_admission_loaded_for_validation': admission_checked, 'loaded_receipts': loads,
    'source_sha256': __import__('hashlib').sha256(source.read_bytes()).hexdigest(),
    'certificate_issuance_executed': False,
    'limit': 'Only the applied function AST executes against copied JSON and in-memory altered data. The certifier module and destination code never execute.'}
(OUT / 'predicate-probe.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
