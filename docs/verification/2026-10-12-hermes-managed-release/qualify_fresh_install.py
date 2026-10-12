# ABOUTME: Exercises the complete manager on a fresh synthetic profile through actual HTTP assets and Hermes commands.
# ABOUTME: Uses a private fixture certificate and reports no production qualification or live selection.
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Thread
import time

repo = Path(__file__).resolve().parents[3]
out = Path(__file__).resolve().parent
cache = Path('/home/outsider/.cache/lifeos-hermes-managed-20261012')
build = json.loads(Path(os.environ.get('LIFEOS_QUALIFICATION_BUILD', str(cache / 'packages/0.4.0-dev.1-5ad7570f-build.json'))).read_bytes())
package = Path(build['package'])
frontend = json.loads((out / 'frontend-build.json').read_bytes())
base = cache / ('fresh-qualification-' + build['head'][:8] + '-' + os.environ.get('LIFEOS_QUALIFICATION_TAG', 'repeat'))
base.mkdir(mode=0o700)
profile = base / '.hermes'
profile.mkdir(mode=0o700)
(base / '.local/bin').mkdir(parents=True, mode=0o700)
(profile / 'config.yaml').write_text('model:\n  default: synthetic-model\n')
(profile / 'config.yaml').chmod(0o600)
os.environ.update(HOME=str(base), HERMES_HOME=str(profile), PYTHONDONTWRITEBYTECODE='1')
sys.path.insert(0, str(package))
sys.path.insert(0, str(cache / 'upstream'))
from optional.lifeos_release_manager.release_catalog import ReleaseCatalog
from optional.lifeos_release_manager.cli import prepare, operation, launch, read_private
from optional.lifeos_release_manager.release_stage import sha
from optional.lifeos_release_manager.release_worker import review_operation

certificate = {**build, 'format': 1, 'status': 'QUALIFIED', 'program_commit': build['head'],
    'hermes_dashboard_sha256': frontend['sha256'], 'test_fixture_only': True}
assets = {Path(build['archive']).name: Path(build['archive']), 'hermes-dashboard.tgz': Path(frontend['archive']),
    'RELEASE-CERTIFICATE.json': json.dumps(certificate).encode()}
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/repos/0ut5ider/lifeos-hermes-plugin/releases/tags/v' + build['version']:
            value = {'tag_name': 'v' + build['version'], 'draft': False, 'prerelease': True,
                'assets': [{'name': name, 'size': data.stat().st_size if isinstance(data, Path) else len(data),
                'digest': 'sha256:' + (sha(data) if isinstance(data, Path) else hashlib.sha256(data).hexdigest()),
                'browser_download_url': origin + '/0ut5ider/lifeos-hermes-plugin/releases/download/v' + build['version'] + '/' + name}
                for name, data in assets.items()]}
            data = json.dumps(value).encode()
        else:
            name = self.path.rsplit('/', 1)[-1]
            data = assets.get(name)
        if data is None:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Length', str(data.stat().st_size if isinstance(data, Path) else len(data)))
        self.end_headers()
        if isinstance(data, Path):
            import shutil
            with data.open('rb') as stream:
                shutil.copyfileobj(stream, self.wfile)
        else:
            self.wfile.write(data)
    def log_message(self, *args):
        pass
server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
origin = 'http://127.0.0.1:' + str(server.server_port)
thread = Thread(target=server.serve_forever)
thread.start()
start = time.monotonic()
report = {'test_fixture_only': True, 'production_qualified': False, 'live_selection_changed': False,
          'package_commit': build['head'], 'profile': str(profile)}
try:
    environment = dict(os.environ, PYTHONPATH=str(cache / 'upstream'))
    installed = subprocess.run([sys.executable, '-B', '-m', 'hermes_cli.main', 'plugins', 'install',
        'file://' + str(repo) + '#optional/lifeos_release_manager', '--ref', build['head']], env=environment, input='y\n',
        text=True, capture_output=True, timeout=300)
    (out / ('fresh-stock-plugin-install-' + os.environ.get('LIFEOS_QUALIFICATION_TAG', 'repeat') + '.stdout')).write_text(installed.stdout)
    (out / ('fresh-stock-plugin-install-' + os.environ.get('LIFEOS_QUALIFICATION_TAG', 'repeat') + '.stderr')).write_text(installed.stderr)
    assert installed.returncode == 0, 'The native plugin installer refuses the manager. Read the fixture log.'
    report['stock_plugin_install'] = 'PASS'
    enabled = subprocess.run([sys.executable, '-B', '-m', 'hermes_cli.main', 'plugins', 'enable', 'lifeos-release-manager'], env=environment, text=True, capture_output=True, timeout=90)
    assert enabled.returncode == 0, 'The native manager does not enable'
    status = subprocess.run([sys.executable, '-B', '-m', 'hermes_cli.main', 'lifeos-release', 'status'], env=environment, text=True, capture_output=True, timeout=90)
    (out / ('fresh-stock-manager-status-' + os.environ.get('LIFEOS_QUALIFICATION_TAG', 'repeat') + '.stdout')).write_text(status.stdout)
    (out / ('fresh-stock-manager-status-' + os.environ.get('LIFEOS_QUALIFICATION_TAG', 'repeat') + '.stderr')).write_text(status.stderr)
    assert status.returncode == 0, 'Stock Hermes does not discover the installed management command'
    report['stock_command_discovery'] = 'PASS'
    result = prepare(profile, build['version'], name='SyntheticAdrian', assistant='SyntheticCerebo',
        catalog=ReleaseCatalog(api_origin=origin, asset_origin=origin))
    report['preparation'] = result
    job, request = operation(profile, result['identifier'])
    report['job'] = str(job)
    assert not (base / '.claude').exists(), 'Preparation publishes native files'
    review_operation(job, request)
    phase = os.environ.get('LIFEOS_QUALIFICATION_INTERRUPTION')
    report['interruption_phase'] = phase
    retained = None
    if phase:
        from optional.lifeos_release_manager.release_worker import admit_operation
        admit_operation(job, request, 'apply')
        actor = base / 'interrupted-worker.py'
        actor.write_text(
            '# ABOUTME: Executes the frozen worker and terminates at one actual publication boundary.\n'
            '# ABOUTME: Uses the admitted synthetic operation without replacing native functions.\n'
            'import importlib,os,sys,types\nfrom pathlib import Path\n'
            'job=Path(sys.argv[1]);phase=sys.argv[2]\n'
            'namespace=types.ModuleType("qualification_worker");namespace.__path__=[str(job/"worker")]\n'
            'sys.modules[namespace.__name__]=namespace\n'
            'worker=importlib.import_module(namespace.__name__+".release_worker")\n'
            'worker.execute(job,"apply",checkpoint=lambda point:os._exit(73) if point==phase else None)\n')
        interrupted = subprocess.run([request['runtime']['python'], '-B', str(actor), str(job), phase],
            env=dict(os.environ, PYTHONPATH=''), text=True, capture_output=True, timeout=300)
        (out / ('fresh-interruption-' + phase + '.stderr')).write_text(interrupted.stderr)
        assert interrupted.returncode == 73, 'The frozen worker does not reach the requested interruption boundary'
        report['actual_process_exit'] = interrupted.returncode
        if phase != 'seed-prepared':
            retained = Path(request['installed']).parent / '.config/LIFEOS/USER/later-synthetic-data.txt'
            retained.write_text('Synthetic data added after worker interruption\n')
        recovery = launch(profile, result['identifier'], 'recover')
        report['recovery_admission'] = recovery
    else:
        launch(profile, result['identifier'], 'apply')
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        state = read_private(job / 'status.json')['state']
        if state in {'applied', 'rolled_back', 'recovery_required', 'rejected'}:
            break
        time.sleep(0.2)
    report['worker_state'] = read_private(job / 'status.json')
    assert state == 'applied', 'The worker does not apply the fresh integration'
    if retained is not None:
        assert retained.read_text() == 'Synthetic data added after worker interruption\n'
        report['later_user_data_preserved'] = 'PASS'
    result = subprocess.run([str(base / '.local/bin/hermes'), 'lifeos-version'],
        env=dict(os.environ, PYTHONPATH=''), capture_output=True, text=True, timeout=90)
    (out / ('fresh-installed-version-' + os.environ.get('LIFEOS_QUALIFICATION_TAG', 'repeat') + '.stdout')).write_text(result.stdout)
    (out / ('fresh-installed-version-' + os.environ.get('LIFEOS_QUALIFICATION_TAG', 'repeat') + '.stderr')).write_text(result.stderr)
    assert result.returncode == 0, 'The installed Hermes command does not load'
    assert build['head'] in result.stdout and 'verified' in result.stdout
    report['installed_identity'] = 'PASS'
    report['status'] = 'PASS'
except BaseException as error:
    report.update(status='FAIL', failure_type=type(error).__name__, failure=str(error))
    raise
finally:
    server.shutdown()
    thread.join()
    server.server_close()
    report['elapsed_seconds'] = time.monotonic() - start
    suffix = '-' + os.environ['LIFEOS_QUALIFICATION_TAG'] if 'LIFEOS_QUALIFICATION_TAG' in os.environ else ''
    (out / ('fresh-install-' + build['head'][:8] + suffix + '.json')).write_text(json.dumps(report, indent=2) + '\n')
    (out / ('fresh-install-' + build['head'][:8] + suffix + '.done')).write_text('0\n' if report.get('status') == 'PASS' else '1\n')
