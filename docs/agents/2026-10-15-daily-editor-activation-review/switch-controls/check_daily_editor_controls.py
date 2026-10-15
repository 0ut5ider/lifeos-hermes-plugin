# ABOUTME: Checks the daily editor switch preserves all unrelated configuration bytes and values.
# ABOUTME: Uses synthetic TOML and refuses changed, ambiguous, or already enabled configuration.
import hashlib,importlib.util,json,tomllib
from pathlib import Path
path=Path(__file__).with_name('activate_daily_editor.py')
spec=importlib.util.spec_from_file_location('daily_editor_operator',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
before=b'[settings]\nname="Synthetic"\n[modules]\nhermes = false # Keep this comment\ncron=true\n[[job]]\nname="life-morning-brief"\nschedule="0 7 * * *"\ncommand="synthetic only"\nenabled=true\n'
digest=hashlib.sha256(before).hexdigest()
selected=module.enable_editor(before,digest)
assert selected==before.replace(b'hermes = false',b'hermes = true')
cases=[]
for label,content,expected in [
 ('changed-config',before+b'# Concurrent change\n',digest),
 ('wrong-digest',before,'0'*64),
 ('already-enabled',selected,hashlib.sha256(selected).hexdigest()),
 ('missing-flag',before.replace(b'hermes = false # Keep this comment\n',b''),None),
 ('duplicate-module',before+b'\n[modules]\nhermes=false\n',None),
 ('wrong-value',before.replace(b'hermes = false',b'hermes = "false"'),None),
]:
 try:module.enable_editor(content,expected or hashlib.sha256(content).hexdigest())
 except (AssertionError,KeyError,tomllib.TOMLDecodeError):cases.append(label)
 else:raise AssertionError('Unsafe activation accepted: '+label)
print(json.dumps({'status':'PASS','positive_controls':1,'refusal_controls':len(cases),'cases':cases},indent=2))
