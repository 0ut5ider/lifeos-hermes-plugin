# ABOUTME: Replays existing safe qualification receipts against the pinned certifier before development completion.
# ABOUTME: Checks measured refusal locations without creating or accepting missing completion receipts.
import ast
import contextlib
import io
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import traceback

project = Path(__file__).resolve().parents[3]
source = project / 'docs/verification/2026-10-14-release-0.5.0'
out = Path(__file__).resolve().parent
pinned = '94ea72dd52a84425bf39f1e482ba64aaddb0c03b'
relative = 'docs/verification/2026-10-14-release-0.5.0/'
code = subprocess.check_output(['git','show',pinned+':'+relative+'certify_release.py'], cwd=project, text=True)
control_code = subprocess.check_output(['git','show',pinned+':'+relative+'check_certificate_controls.py'], cwd=project, text=True)
tree = ast.parse(control_code)
namespace = {}
for item in tree.body:
    if isinstance(item, ast.FunctionDef) or isinstance(item, ast.Assign) and any(isinstance(target,ast.Name) and target.id == 'cases' for target in item.targets):
        exec(compile(ast.Module(body=[item],type_ignores=[]),'<controls>','exec'),namespace)
cases = [(name, file, mutation) for name,file,mutation in namespace['cases'] if mutation and not file.startswith('development-')]
cases += [
 ('wrong-whole-source-guest','bound-whole-guest-recovery.json',lambda row: row.update(source_guest=253)),
 ('wrong-whole-restore-guest','bound-whole-guest-program-coverage.json',lambda row: row.update(restored_guest=253)),
 ('wrong-runtime-archive','bound-whole-guest-artifact-coverage.json',lambda row: row.update(archive_sha256='0'*64)),
 ('wrong-source-capture-map','source-program-artifact-capture.json',lambda row: row.update(private_map_sha256='0'*64)),
 ('wrong-reboot-source-guest','reboot-verification.json',lambda row: row.update(source_guest=253)),
 ('reboot-claims-production-change','reboot-verification.json',lambda row: row.update(production_guest_changed=True)),
 ('fresh-claims-production-change','stock-first-install.json',lambda row: row.update(production_guest_changed=True)),
]
inputs = set()
for item in ast.walk(ast.parse(code)):
    if isinstance(item, ast.Call) and isinstance(item.func, ast.Name) and item.func.id in {'load','passed','text'} and item.args and isinstance(item.args[0], ast.Constant):
        inputs.add(item.args[0].value)
inputs -= {'development-verification.json','development-owner-turn-verification.json'}
report_source = project / 'docs/agents/2026-10-14-pr27-baseline-review/pr27-baseline-review.md'
results = []
for name,file,mutation in [('baseline-awaits-development',None,None),*cases]:
    root = out / 'guard-inputs' / name / 'docs/verification/2026-10-14-release-0.5.0'
    root.mkdir(parents=True,exist_ok=False)
    (root/'certify_release.py').write_text(code)
    for input_name in inputs:
        shutil.copyfile(source/input_name,root/input_name)
    review = root.parents[1]/'agents/2026-10-14-pr27-baseline-review/pr27-baseline-review.md'
    review.parent.mkdir(parents=True)
    shutil.copyfile(report_source,review)
    if file:
        path=root/file
        value=json.loads(path.read_bytes())
        mutation(value)
        path.write_text(json.dumps(value))
    failure = None
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            runpy.run_path(str(root/'certify_release.py'),run_name='__main__')
        except (AssertionError,FileNotFoundError) as error:
            frames = traceback.extract_tb(error.__traceback__)
            failure={'type':type(error).__name__,'line':frames[-1].lineno,
                     'reason':str(error),'missing_file':getattr(error,'filename',None)}
    assert not (root/'RELEASE-CERTIFICATE.json').exists(), 'No certificate may be written during this review'
    reached_development = failure['type']=='FileNotFoundError' and failure['missing_file'].endswith('/development-verification.json')
    results.append({'case':name,'input':file,'refused_before_development':not reached_development,
                    'reached_pending_development_gate':reached_development,'failure':failure,
                    'certificate_created':False})
(out/'certificate-guard-probes.json').write_text(json.dumps({'pinned_commit':pinned,'results':results,
 'completion_receipts_constructed':False,'remote_commands_run':False},indent=2)+'\n')
print(json.dumps({'cases':len(results),'baseline_refuses_missing_development':results[0]['reached_pending_development_gate'],
 'negative_controls_refused':sum(row['refused_before_development'] for row in results[1:]),
 'mutations_reaching_pending_gate':[row['case'] for row in results[1:] if row['reached_pending_development_gate']],
 'certificate_created':False},indent=2))
