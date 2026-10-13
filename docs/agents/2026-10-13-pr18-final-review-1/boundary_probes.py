# ABOUTME: Measures release-preparation admission against actual private files and process identity.
# ABOUTME: Stops before download launch and records a synthetic systemd-boundary profile refusal probe.
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace

from optional.lifeos_release_manager import cli, release_preparation, release_services
from hermes_cli.dashboard_procs import _hermes_home_for_pid


class BoundaryStop(BaseException):
    pass


def preparation_overlap():
    with tempfile.TemporaryDirectory(prefix='pr18-preparation-overlap-') as folder:
        profile = Path(folder)
        result = {}
        lines, start = inspect.getsourcelines(release_preparation.queue)
        boundary = start + next(i for i, line in enumerate(lines) if 'process = subprocess.Popen(' in line)
        def trace(frame, event, arg):
            if frame.f_code is release_preparation.queue.__code__ and event == 'line' and frame.f_lineno == boundary:
                result['queue_reaches_child_launch'] = True
                sys.settrace(None)
                raise BoundaryStop()
            return trace
        class Catalog:
            def download(self, directory, version):
                result['before'] = cli.status(profile)['operations']
                sys.settrace(trace)
                try:
                    release_preparation.queue(profile, {'intent': 'install'})
                except BoundaryStop:
                    pass
                finally:
                    sys.settrace(None)
                result['after'] = cli.status(profile)['operations']
                result['created_jobs'] = len([p for p in (profile / '.lifeos-releases').iterdir() if p.is_dir()])
                raise BoundaryStop()
        try:
            cli.prepare(profile, catalog=Catalog())
        except BoundaryStop:
            pass
        assert result['before'][0]['state'] == 'preparing'
        assert result['queue_reaches_child_launch'] is True
        assert result['created_jobs'] == 2
        result['limit'] = 'Actual functions and private files; trace stops before the second Popen, so no release download or active publication occurs.'
        return result


def foreign_dashboard():
    with tempfile.TemporaryDirectory(prefix='pr18-foreign-dashboard-') as folder:
        home = Path(folder)
        profile, foreign = home / 'requested-profile', home / 'foreign-profile'
        profile.mkdir(mode=0o700)
        foreign.mkdir(mode=0o700)
        launcher = home / '.local/bin/hermes'
        launcher.parent.mkdir(parents=True)
        ready = home / 'ready'
        launcher.write_text('from pathlib import Path\nimport time\nPath(' + repr(str(ready)) + ').touch()\ntime.sleep(30)\n')
        launcher.chmod(0o700)
        process = subprocess.Popen([sys.executable, '-B', str(launcher), 'dashboard'],
            env=dict(os.environ, HOME=str(home), HERMES_HOME=str(foreign)),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        prior_home = os.environ.get('HOME')
        try:
            deadline = time.monotonic() + 5
            while not ready.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert ready.exists()
            observed_home = _hermes_home_for_pid(process.pid)
            assert observed_home == str(foreign)
            os.environ['HOME'] = str(home)
            values = {'ExecStart': '{ path=' + str(launcher) + ' ; argv[]=' + str(launcher) + ' dashboard --isolated --no-open ; }',
                'FragmentPath': str(home / '.config/systemd/user/hermes-dashboard.service'),
                'DropInPaths': '', 'ControlGroup': '', 'MainPID': str(process.pid)}
            class ServiceBoundary:
                def __init__(self, *args, first_installation=False, **kwargs):
                    assert first_installation
                def preview(self):
                    return {'signature': 'synthetic-reviewed-dashboard-signature'}
                def _inspect(self, role):
                    assert role == 'dashboard'
                    return values, 'synthetic-definition'
            module = SimpleNamespace(ProfileServices=ServiceBoundary,
                UNITS={'gateway': 'hermes-gateway.service', 'pulse': 'com.lifeos.pulse.service'},
                _run=lambda *args: 'LoadState=not-found\n')
            current = SimpleNamespace(memory_module=lambda name: module)
            preview = release_services.fresh_preview(current, profile, home / '.claude')
            return {'running_dashboard_pid': process.pid, 'requested_profile': str(profile),
                'actual_dashboard_profile': observed_home, 'accepted_preview': preview,
                'limit': 'Real Hermes-shaped process and native procfs identity; systemd inspection boundary is a synthetic fixed-unit response. No service is stopped or changed.'}
        finally:
            if prior_home is None:
                os.environ.pop('HOME', None)
            else:
                os.environ['HOME'] = prior_home
            process.terminate()
            process.wait(timeout=5)


if __name__ == '__main__':
    output = {'synchronous_preparation_overlap': preparation_overlap(), 'foreign_dashboard': foreign_dashboard()}
    Path(__file__).with_name('boundary-probes.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps(output, indent=2))
