# ABOUTME: Binds the actual acceptance runtime to every packaged plugin and native program byte.
# ABOUTME: Verifies daily scheduling, selected efforts, and service health without inspecting personal records.
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
from ruamel.yaml import YAML

stage=Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
package=Path(__file__).resolve().parents[1]/'package'
prepared=json.loads((stage/'applications-prepared.json').read_text())
profile,root=Path(prepared['profile']),Path(prepared['installed'])
os.environ.update(HOME=str(root.parent),HERMES_HOME=str(profile),XDG_RUNTIME_DIR='/run/user/1008',
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1008/bus')
sys.path[:0]=[str(profile/'plugins'),str(stage/'package/hermes')]
module=lambda name:importlib.import_module('lifeos-hook-bridge.'+name)
source=module('install_source')
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
manifest=json.loads((package/'DAILY-CANDIDATE.json').read_text())
installed=json.loads((stage/'APPLICATION-CANDIDATE.json').read_text())
assert installed['head']==manifest['head']
for relative,digest in manifest['plugin_files'].items():
    assert sha(profile/'plugins/lifeos-hook-bridge'/Path(relative).relative_to('lifeos_hook_bridge'))==digest,relative
hermes=source.validate_supported_hermes(package/'hermes')
runtime=stage/'package/hermes'
hermes_files={}
for path in (package/'hermes').rglob('*'):
    relative=path.relative_to(package/'hermes')
    if '.git' in relative.parts or not path.is_file():continue
    assert sha(runtime/relative)==sha(path),str(relative)
    hermes_files[str(relative)]=sha(path)
additions={}
for path in runtime.rglob('*'):
    relative=path.relative_to(runtime)
    if {'.git','node_modules','__pycache__'} & set(relative.parts) or not path.is_file():continue
    if str(relative) in hermes_files:continue
    assert str(relative)=='.bytecode-fingerprint' or relative.is_relative_to('hermes_cli/web_dist'),str(relative)
    additions[str(relative)]=sha(path)
canonical=stage/'pulse-daemon-types-source/lifeos'
lifeos=source.validate_prepared_lifeos(canonical)
assert lifeos==source.validate_prepared_lifeos(package/'lifeos')
programs={};generated={}
for path in (canonical/'LifeOS/install/LIFEOS').rglob('*'):
    relative=path.relative_to(canonical/'LifeOS/install')
    if {'USER','MEMORY','node_modules','__pycache__'} & set(relative.parts) or not path.is_file():continue
    if str(relative)=='LIFEOS/DOCUMENTATION/ARCHITECTURE_SUMMARY.md':
        generated[str(relative)]={'canonical_sha256':sha(path),'installed_sha256':sha(root/relative),
                                  'reason':'Native installation generates this architecture document'}
        continue
    assert sha(root/relative)==sha(path),str(relative)
    programs[str(relative)]=sha(path)
schedule=root/'LIFEOS/USER/CONFIG/PULSE.user.toml'
assert sha(schedule)==sha(package/'docs/deployment/daily-text/PULSE.user.toml')
configuration=(profile/'config.yaml').read_bytes()
assert hashlib.sha256(configuration).hexdigest()=='db397e27d76475e121fbe333dde75a6b2a21539c9aa2757676c2c1f113049a20'
value=YAML(typ='safe').load(configuration)
settings=value['plugins']['entries']['lifeos-hook-bridge']['settings']
assert value['model']['default']=='flashnext-w4a16-fp8ple' and settings['pinned_tier']=='fable'
assert {name:settings[name+'_effort'] for name in ('haiku','sonnet','opus','fable')}=={
    'haiku':'low','sonnet':'medium','opus':'xhigh','fable':'xhigh'}
units=json.loads((stage/'application-units.json').read_text())['units']
services=module('profile_services').ProfileServices(profile,root,units=units)
assert services.status()['state']=='active'
report={'status':'PASS','head':manifest['head'],'plugin_files':manifest['plugin_files'],
    'native_program_files':programs,'hermes_manifest':hermes,'lifeos_manifest':lifeos,
    'hermes_source_files':hermes_files,'hermes_runtime_additions':additions,
    'generated_native_documents':generated,
    'daily_schedule_sha256':sha(schedule),'model_configuration_sha256':hashlib.sha256(configuration).hexdigest(),
    'services':services.status(),'live_profile_changed':False}
(stage/'release-runtime.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':'PASS','head':manifest['head'],'plugin_files':len(manifest['plugin_files']),
                  'native_program_files':len(programs)},indent=2))
