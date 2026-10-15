from pathlib import Path
import subprocess,json,shutil
root=Path(__file__).resolve().parents[3];out=Path(__file__).resolve().parent
label='review-return-capture-closure'
command=['/home/outsider/.cache/lifeos-daily-promotion-20261014/frozen-test-environment/bin/python','docs/verification/2026-10-15-memory-portability/run_tests.py',label,'test_memory_return','test_memory_transition','docs.agents.2026-10-15-portability-package-review.package_probes.ReturnCaptureControls','docs.agents.2026-10-15-portability-package-review.package_probes.PreCaptureSourceControls.test_builtin_source_edit_before_input_capture_is_preserved','test_memory_import','test_memory_export','test_memory_removal_workflow']
(out/'command.json').write_text(json.dumps(command,indent=2)+'\n')
with (out/'supervisor.stdout').open('w') as stdout,(out/'supervisor.stderr').open('w') as stderr:
 result=subprocess.run(command,cwd=root,stdout=stdout,stderr=stderr)
for suffix in ('stdout','stderr','json','done'):
 source=root/'docs/verification/2026-10-15-memory-portability'/f'{label}.{suffix}'
 if source.exists():shutil.copyfile(source,out/source.name)
(out/'.done').write_text(str(result.returncode)+'\n')
