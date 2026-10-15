# ABOUTME: Prepares the exact staged complete release for development owner review.
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

profile = Path('/home/lifeos-hermes/.hermes')
root = Path('/home/lifeos-hermes/releases/qualification-0.5.0')
package = json.loads((root / 'stable-build.json').read_bytes())
os.environ.update(HERMES_HOME=str(profile), XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus', PYTHONDONTWRITEBYTECODE='1')
os.environ['PATH'] = '/home/lifeos-hermes/.local/bin:' + os.environ.get('PATH', os.defpath)
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
report = {'profile': str(profile), 'candidate': package['head'], 'staged_development_candidate': True,
          'active_programs_selected': False, 'model_selection_sha256': model_selection(), 'caller_home': str(Path.home())}
start = time.monotonic()
try:
    result = cli.prepare(profile, package['version'], intent='update', catalog=catalog.ReleaseCatalog(api_origin=origin, asset_origin=origin))
    job, request = cli.operation(profile, result['identifier'])
    plan = importlib.import_module(namespace.__name__ + '.release_operation').validate_plan(job, request)
    assert result['state'] == 'ready'
    assert request['account_home'] == '/home/lifeos-hermes'
    assert request['installed'] != '/home/lifeos-hermes/.claude'
    assert not plan['fresh']
    report['candidate_plan_prepared_before_ready'] = 'PASS'
    snapshot = cli.read_private(job / 'program-snapshot/programs.json')
    report.update(preparation=result, prepared_program_groups=len(snapshot['entries']), account_home=request['account_home'], installed=request['installed'], services=plan['services'], native_mount_required=plan['native_mount_required'])
    assert model_selection() == report['model_selection_sha256'], 'Preparation changes the model or tier mapping'
    report['status'] = 'PASS'
except BaseException as error:
    report.update(status='FAIL', error_type=type(error).__name__, error=str(error))
    raise
finally:
    server.shutdown(); thread.join(); server.server_close()
    report['elapsed_seconds'] = time.monotonic()-start
    path = root / 'development-preparation.json'
    path.write_text(json.dumps(report, indent=2)+'\n'); path.chmod(0o600)
    (root / 'development-preparation.done').write_text('0\n' if report.get('status') == 'PASS' else '1\n')
