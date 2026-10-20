# ABOUTME: Probes check_service_launchers with unit layouts that real systemd accepts.
# ABOUTME: Prints, for each case, whether preparation refuses and what systemd would execute.
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from optional.lifeos_release_manager.inplace_preparation import check_service_launchers
from optional.lifeos_release_manager.release_catalog import ReleaseRejected


def run(label, unit, dropins=(), extra=None):
    with tempfile.TemporaryDirectory() as directory:
        home = Path(directory)
        units = home / '.config/systemd/user'
        units.mkdir(parents=True)
        managed = str(home) + '/.hermes/.lifeos-releases/' + 'a' * 32 + '/bin/hermes'
        workspace = home / 'workspace/hermes-agent/.hermes/bin/hermes'
        workspace.parent.mkdir(parents=True)
        workspace.write_text('#!/bin/sh\nexec ' + managed + ' "$@"\n')
        other = home / '.local/bin/hermes-dev'
        other.parent.mkdir(parents=True)
        other.write_text(workspace.read_text())
        link = home / 'opt/hermes'
        link.parent.mkdir(parents=True)
        link.symlink_to(home / '.local/bin/hermes')
        account = home / '.local/bin/hermes'
        account.write_text(workspace.read_text())
        values = {'W': str(workspace), 'H': str(home), 'O': str(other), 'L': str(link)}
        (units / 'hermes-dashboard.service').write_text(unit.format(**values))
        for name, text in dropins:
            path = units / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text.format(**values))
        try:
            check_service_launchers(home)
            outcome = 'accepted'
        except ReleaseRejected as error:
            outcome = 'REFUSED: ' + str(error).replace(str(home), '~')
        except Exception as error:
            outcome = 'CRASH: ' + type(error).__name__ + ': ' + str(error)
        print(f'{label:55s} {outcome}')


run('baseline: workspace forwarder', '[Service]\nExecStart={W} dashboard\n')
run('quoted like stock Hermes', '[Service]\nExecStart="{W}" "dashboard"\n')
run('line continuation', '[Service]\nExecStart={W} \\\n  dashboard --isolated\n')
run('spaces around =', '[Service]\nExecStart = {W} dashboard\n')
run('%h specifier', '[Service]\nExecStart=%h/workspace/hermes-agent/.hermes/bin/hermes dashboard\n')
run('other forwarder in ~/.local/bin', '[Service]\nExecStart={O} dashboard\n')
run('symlink elsewhere to account launcher', '[Service]\nExecStart={L} dashboard\n')
run('prefix drop-in hermes-.service.d', '[Service]\nExecStart={H}/.local/bin/hermes dashboard\n',
    dropins=[('hermes-.service.d/x.conf', '[Service]\nExecStart=\nExecStart={W} dashboard\n')])
run('type drop-in service.d', '[Service]\nExecStart={H}/.local/bin/hermes dashboard\n',
    dropins=[('service.d/x.conf', '[Service]\nExecStart=\nExecStart={W} dashboard\n')])
run('drop-in reset only (unit cannot load)', '[Service]\nExecStart={W} dashboard\n',
    dropins=[('hermes-dashboard.service.d/x.conf', '[Service]\nExecStart=\n')])
run('/bin/sh -c wrapper', '[Service]\nExecStart=/bin/sh -c "exec {W} dashboard"\n')
run('unterminated quote', '[Service]\nExecStart="{W} dashboard\n')
