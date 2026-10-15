# ABOUTME: Checks whether the stock source validator refuses an extra executable Python startup module.
# ABOUTME: Uses exact local archived source and executes only validation statements without writing a completion receipt.
import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
import shutil
import tarfile
import tempfile

project=Path(__file__).resolve().parents[3]
source=project/'docs/verification/2026-10-14-release-0.5.0'
archive=Path('/home/outsider/.cache/lifeos-release-0.5.0-20261014/stock-source.tar')
metadata=json.loads((source/'stock-source.json').read_bytes())
assert hashlib.sha256(archive.read_bytes()).hexdigest()==metadata['archive_sha256']
body=ast.parse((source/'verify_public_stock_source.py').read_text()).body
stop=next(index for index,item in enumerate(body) if isinstance(item,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='report' for target in item.targets))
body=body[:stop]
with tempfile.TemporaryDirectory(prefix='stock-source-extra-program-') as temporary:
    home=Path(temporary)
    stage=home/'releases/qualification-0.5.0'
    stage.mkdir(parents=True)
    shutil.copyfile(source/'stock-source.json',stage/'stock-source.json')
    (home/'releases/stock-source.tar').symlink_to(archive)
    runtime=home/'runtime/stock-hermes'
    runtime.mkdir(parents=True)
    with tarfile.open(archive) as reader:reader.extractall(runtime,filter='data')
    extra=runtime/'sitecustomize.py'
    assert not extra.exists()
    extra.write_text("import os; os.environ['LIFEOS_EXTRA_STARTUP_PROBE'] = 'executed'\n")
    for item in body:
        if isinstance(item,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='home' for target in item.targets):
            item.value=ast.Call(func=ast.Name(id='Path',ctx=ast.Load()),args=[ast.Constant(str(home))],keywords=[])
    module=ast.fix_missing_locations(ast.Module(body=body,type_ignores=[]))
    namespace={}
    rejected=False
    try:exec(compile(module,'<actual-stock-validation-prefix>','exec'),namespace)
    except AssertionError:rejected=True
    startup=subprocess.run([sys.executable,'-B','-c',"import os; print(os.environ.get('LIFEOS_EXTRA_STARTUP_PROBE'))"],env=dict(os.environ,PYTHONPATH=str(runtime),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,check=True)
    assert startup.stdout.strip()=='executed'
    result={'extra_startup_module_executed':True,'case':'extra-sitecustomize-program','extra_relative_path':'sitecustomize.py',
        'extra_source_rejected':rejected,'source_files_verified':namespace.get('files'),
        'exact_archived_source_files_unchanged':True,'completion_receipt_written':False,
        'remote_commands_run':False,'stock_source_archive_sha256':metadata['archive_sha256']}
Path(__file__).with_name('stock-extra-source-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
