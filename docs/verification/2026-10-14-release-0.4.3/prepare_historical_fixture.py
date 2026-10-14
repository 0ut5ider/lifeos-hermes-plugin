# ABOUTME: Prepares an actual historical 0.4.0 operation for current first-install refusal controls.
# ABOUTME: Reports safe identities and model-selection hashes without exporting credentials or personal records.
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib
import json
import os
from pathlib import Path
import sys
from threading import Thread
import time
import types

import shutil
cache = Path('/home/outsider/.cache/lifeos-daily-promotion-20261014')
root = cache / 'historical-fixture-040'
root.mkdir(mode=0o700)
owner = root / 'account'
owner.mkdir(mode=0o700)
profile = owner / '.hermes'
profile.mkdir(mode=0o700)
historical = cache / 'historical-040'
certificate = json.loads((historical / 'RELEASE-CERTIFICATE.json').read_bytes())
archive = historical / (certificate['version'] + '-' + certificate['program_commit'][:8] + '.tgz')
assert hashlib.sha256(archive.read_bytes()).hexdigest() == certificate['archive_sha256']
from optional.lifeos_release_manager.release_catalog import extract_package
source = root / 'published-package'
extract_package(archive, source)
package = {'head': certificate['program_commit'], 'version': certificate['version'], 'archive': str(archive)}
manager = profile / 'plugins/lifeos-release-manager'
manager.parent.mkdir(mode=0o700)
shutil.copytree(source / 'optional/lifeos_release_manager', manager)
(profile / 'config.yaml').write_text('_config_version: 46\nmodel:\n  default: synthetic-local-qualification\n')
for name in (archive.name, 'hermes-dashboard.tgz', 'RELEASE-CERTIFICATE.json'):
    shutil.copy2(historical / name, root / name)
os.environ.update(HOME=str(owner), HERMES_HOME=str(profile), XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus', PYTHONDONTWRITEBYTECODE='1')
os.environ['PATH'] = str(cache / 'fixed-bun-tools') + ':' + os.environ.get('PATH', os.defpath)
namespace = types.ModuleType('lifeos_development_manager')
namespace.__path__ = [str(profile / 'plugins/lifeos-release-manager')]
sys.modules[namespace.__name__] = namespace
cli = importlib.import_module(namespace.__name__ + '.cli')
catalog = importlib.import_module(namespace.__name__ + '.release_catalog')
worker = importlib.import_module(namespace.__name__ + '.release_worker')
from ruamel.yaml import YAML

def model_selection():
    data = YAML(typ='safe').load((profile / 'config.yaml').read_bytes())
    settings = data.get('plugins', {}).get('entries', {}).get('lifeos-hook-bridge', {}).get('settings', {})
    selected = {'model': data.get('model'), 'tiers': {key: value for key, value in settings.items()
        if key.startswith(('haiku', 'sonnet', 'opus', 'fable', 'pinned'))}}
    return hashlib.sha256(json.dumps(selected, sort_keys=True).encode()).hexdigest()

assets = {name: root / name for name in (Path(package['archive']).name, 'hermes-dashboard.tgz', 'RELEASE-CERTIFICATE.json')}
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/repos/0ut5ider/lifeos-hermes-plugin/releases/tags/v' + package['version']:
            value = {'tag_name': 'v' + package['version'], 'draft': False, 'prerelease': True,
                'assets': [{'name': name, 'size': path.stat().st_size,
                    'digest': 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest(),
                    'browser_download_url': origin + '/0ut5ider/lifeos-hermes-plugin/releases/download/v' + package['version'] + '/' + name}
                    for name, path in assets.items()]}
            data = json.dumps(value).encode()
            self.send_response(200); self.send_header('Content-Length', str(len(data))); self.end_headers()
            self.wfile.write(data)
            return
        path = assets.get(self.path.rsplit('/', 1)[-1])
        if path is None:
            self.send_error(404)
            return
        self.send_response(200); self.send_header('Content-Length', str(path.stat().st_size)); self.end_headers()
        import shutil
        with path.open('rb') as stream:
            shutil.copyfileobj(stream, self.wfile)
    def log_message(self, *args):
        pass
server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
origin = 'http://127.0.0.1:' + str(server.server_port)
thread = Thread(target=server.serve_forever)
thread.start()
report = {'profile': str(profile), 'candidate': package['head'], 'test_fixture_only': True,
          'active_programs_selected': False, 'model_selection_sha256': model_selection()}
start = time.monotonic()
try:
    result = cli.prepare(profile, package['version'], name='Synthetic Qualification', assistant='Qualification Hermes', catalog=catalog.ReleaseCatalog(api_origin=origin, asset_origin=origin))
    job, request = cli.operation(profile, result['identifier'])
    plan = importlib.import_module(namespace.__name__ + '.release_operation').validate_plan(job, request)
    assert result['state'] == 'ready'
    report['candidate_plan_prepared_before_ready'] = 'PASS'
    snapshot = cli.read_private(job / 'program-snapshot/programs.json')
    report.update(preparation=result, prepared_program_groups=len(snapshot['entries']), job=str(job))
    assert model_selection() == report['model_selection_sha256'], 'Preparation changes the model or tier mapping'
    report['status'] = 'PASS'
except BaseException as error:
    report.update(status='FAIL', error_type=type(error).__name__, error=str(error))
    raise
finally:
    server.shutdown(); thread.join(); server.server_close()
    report['elapsed_seconds'] = time.monotonic()-start
    path = root / 'fresh-preparation.json'
    path.write_text(json.dumps(report, indent=2)+'\n'); path.chmod(0o600)
    (root / 'fresh-preparation.done').write_text('0\n' if report.get('status') == 'PASS' else '1\n')
