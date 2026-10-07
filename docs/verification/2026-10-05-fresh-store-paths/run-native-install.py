# ABOUTME: Installs the pinned native payload into a separate home and retains original data controls.
# ABOUTME: Records installed paths and source identity without enabling ownership or starting services.
from pathlib import Path
import hashlib,json,os,traceback
from lifeos_hook_bridge.install_source import prepare_latest_lifeos,install_prepared_lifeos
root=Path(__file__).resolve().parent
home=root/'full-selected-home'
current=root/'full-current-home'
data=current/'.config/LIFEOS/USER';data.mkdir(parents=True)
marker=data/'synthetic-retained.txt';marker.write_text('Synthetic original outside the selected store.\n')
before={str(p.relative_to(data)):hashlib.sha256(p.read_bytes()).hexdigest() for p in data.rglob('*') if p.is_file()}
status=1
try:
 candidate=root/'native-candidate'
 manifest=prepare_latest_lifeos(candidate)
 os.environ.update(HOME=str(current),LIFEOS_CONFIG_DIR=str(current/'.config/LIFEOS'),LIFEOS_DIR=str(current/'.claude/LIFEOS'),CLAUDE_CONFIG_DIR=str(current/'.claude'))
 installed=home/'.claude'
 result=install_prepared_lifeos(candidate,installed,root/'native-failed')
 actual=(installed/'LIFEOS/USER').resolve()
 assert actual==home/'.config/LIFEOS/USER'
 assert not (actual/'synthetic-retained.txt').exists()
 after={str(p.relative_to(data)):hashlib.sha256(p.read_bytes()).hexdigest() for p in data.rglob('*') if p.is_file()}
 assert after==before
 settings=json.loads((installed/'settings.json').read_text())
 assert settings['env']['LIFEOS_CONFIG_DIR']==str(home/'.config/LIFEOS')
 assert settings['env']['LIFEOS_DIR']==str(installed/'LIFEOS')
 report={'installation':result,'source':manifest,'selected_program':str(installed),'selected_data':str(actual),'retained_original':str(data),'retained_original_hashes':after,'old_marker_in_selected_store':False,'memory_ownership_enabled':False,'services_started':False,'environment_paths':{k:settings['env'][k] for k in ('LIFEOS_DIR','LIFEOS_CONFIG_DIR')}}
 (root/'native-install-results.json').write_text(json.dumps(report,indent=2)+'\n')
 status=0
except Exception:
 traceback.print_exc()
finally:
 (root/'native-install.done').write_text(str(status)+'\n')
