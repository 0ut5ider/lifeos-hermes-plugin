# ABOUTME: Enables the selected private model route only on the synthetic disposable guest.
# ABOUTME: Accepts one provider environment line privately and preserves the original guest configuration.
import io
import importlib
import os
from pathlib import Path
import sys
import types

from ruamel.yaml import YAML

os.umask(0o077)
home=Path('/home/lifeos-hermes');profile=home/'.hermes'
if os.getuid()!=1000 or home!=Path.home():raise RuntimeError('Use the disposable guest account')
line=sys.stdin.buffer.read(16385)
if not line.startswith(b'CUSTOM_API_KEY=') or len(line)>16384 or len(line.splitlines())!=1:
    raise RuntimeError('Provide the exact selected provider environment line privately')
backup=home/'install-input/model-acceptance'
backup.mkdir(mode=0o700)
for name in ('config.yaml','.env'):
    path=backup/name;path.write_bytes((profile/name).read_bytes());path.chmod(0o600)
yaml=YAML();yaml.preserve_quotes=True
config=yaml.load((profile/'config.yaml').read_text())
if config['model']['default']!='flashnext-w4a16-fp8ple' or config['model']['provider']!='custom':
    raise RuntimeError('The disposable model selection changes')
config['model']['base_url']='http://192.168.8.90:42071/v1'
config['model']['key_env']='CUSTOM_API_KEY'
stream=io.StringIO();yaml.dump(config,stream)
lines=(profile/'.env').read_bytes().splitlines(keepends=True)
if sum(item.startswith(b'CUSTOM_API_KEY=') for item in lines)!=1:
    raise RuntimeError('The disposable provider key selection is ambiguous')
environment=b''.join(line.rstrip(b'\r\n')+b'\n' if item.startswith(b'CUSTOM_API_KEY=') else item for item in lines)
namespace=types.ModuleType('portability_config_publisher')
namespace.__path__=[str(profile/'plugins/lifeos-hook-bridge')]
sys.modules[namespace.__name__]=namespace
publish=importlib.import_module(namespace.__name__+'.memory_transaction').publish
publish(profile/'.env',environment);publish(profile/'config.yaml',stream.getvalue().encode())
print('Disposable private model route configured. Model and tier selections are preserved.')
