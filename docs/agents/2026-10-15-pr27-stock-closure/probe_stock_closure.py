# ABOUTME: Checks extra executable, directory-link, and special-file refusal against exact stock and frontend archives.
# ABOUTME: Runs validation statements only and preserves original startup repro without writing acceptance receipts.
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import traceback

project=Path(__file__).resolve().parents[3]
source=project/'docs/verification/2026-10-14-release-0.5.0'
stock=Path('/home/outsider/.cache/lifeos-release-0.5.0-20261014/stock-source.tar')
frontend=Path('/home/outsider/.cache/lifeos-daily-promotion-20261014/hermes-dashboard.tgz')
code=(source/'verify_public_stock_source.py').read_text()
metadata=json.loads((source/'stock-source.json').read_bytes())
assert hashlib.sha256(stock.read_bytes()).hexdigest()==metadata['archive_sha256']
assert hashlib.sha256(frontend.read_bytes()).hexdigest()=='e7c93e754de99b6ec66ae17ae313377dc513104da2776a099c391a7aab347bec'
results=[]
for case in ('original-startup-module','extra-directory-symlink','extra-fifo'):
    body=ast.parse(code).body
    stop=next(index for index,item in enumerate(body) if isinstance(item,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='report' for target in item.targets))
    body=body[:stop]
    with tempfile.TemporaryDirectory(prefix='stock-source-independent-closure-') as temporary:
        home=Path(temporary);stage=home/'releases/qualification-0.5.0';stage.mkdir(parents=True)
        shutil.copyfile(source/'stock-source.json',stage/'stock-source.json')
        (home/'releases/stock-source.tar').symlink_to(stock)
        (home/'releases/hermes-dashboard.tgz').symlink_to(frontend)
        runtime=home/'runtime/stock-hermes';runtime.mkdir(parents=True)
        for archive in (stock,frontend):
            with tarfile.open(archive) as reader:reader.extractall(runtime,filter='data')
        startup=False
        if case=='original-startup-module':
            (runtime/'sitecustomize.py').write_text("import os; os.environ['LIFEOS_EXTRA_STARTUP_PROBE'] = 'executed'\n")
        elif case=='extra-directory-symlink':
            outside=home/'outside';outside.mkdir()
            (runtime/'extra-package').symlink_to(outside,target_is_directory=True)
        elif case=='extra-fifo':
            os.mkfifo(runtime/'extra-fifo')
        for item in body:
            if isinstance(item,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='home' for target in item.targets):
                item.value=ast.Call(func=ast.Name(id='Path',ctx=ast.Load()),args=[ast.Constant(str(home))],keywords=[])
        module=ast.fix_missing_locations(ast.Module(body=body,type_ignores=[]))
        namespace={};failure=None
        try:exec(compile(module,'<actual-stock-validation-prefix>','exec'),namespace)
        except AssertionError as error:
            line=traceback.extract_tb(error.__traceback__)[-1].lineno
            failure={'line':line,'statement':code.splitlines()[line-1].strip()}
        assert failure is not None
        assert failure['statement'] in {'assert actual==expected','assert stat.S_ISREG(mode) or stat.S_ISLNK(mode)'}
        if case=='original-startup-module':
            check=subprocess.run([sys.executable,'-B','-c',"import os; print(os.environ.get('LIFEOS_EXTRA_STARTUP_PROBE'))"],env=dict(os.environ,PYTHONPATH=str(runtime),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,check=True)
            startup=check.stdout.strip()=='executed';assert startup
        results.append({'case':case,'status':'PASS','extra_source_rejected':True,'refusal':failure,
                        'original_startup_effect_reproduced':startup,'source_files_verified':namespace['counts'][0][0],
                        'frontend_files_verified':namespace['counts'][1][0],
                        'completion_receipt_written':False,'remote_commands_run':False})
report={'status':'PASS','cases':len(results),'results':results,'actual_archives_used':True}
Path(__file__).with_name('independent-stock-closure.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
