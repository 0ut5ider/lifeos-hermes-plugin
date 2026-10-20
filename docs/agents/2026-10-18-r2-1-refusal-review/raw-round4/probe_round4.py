# ABOUTME: Probes check_service_launchers at 7a0cba6a (round 4) with systemctl show text through the real show() parser.
# ABOUTME: Only subprocess.run inside inplace_services is replaced; unit programs and drop-ins are real temporary files.
import subprocess, tempfile
from pathlib import Path
from unittest import mock
from optional.lifeos_release_manager import inplace_services
from optional.lifeos_release_manager.inplace_preparation import check_service_launchers
from optional.lifeos_release_manager.release_catalog import ReleaseRejected

def entry(key, path, argv, ignore='no'):
    return (key + '={ path=' + path + ' ; argv[]=' + argv + ' ; ignore_errors=' + ignore +
            ' ; start_time=[n/a] ; stop_time=[n/a] ; pid=0 ; code=(null) ; status=0/0 }\n')

def run(label, home, outputs, replaced=()):
    def fake(arguments, **kwargs):
        unit = arguments[3]
        text = outputs.get(unit, 'LoadState=not-found\nDropInPaths=\n')
        return subprocess.CompletedProcess(arguments, 0, text, '')
    with mock.patch.object(inplace_services.subprocess, 'run', side_effect=fake):
        try:
            check_service_launchers(home, replaced=replaced)
            print(label, '-> accepted')
        except ReleaseRejected as error:
            print(label, '-> REFUSED:', error)

with tempfile.TemporaryDirectory() as directory:
    home = Path(directory)
    managed = str(home) + '/.hermes/.lifeos-releases/' + 'a' * 32 + '/hermes/.hermes/bin/hermes'
    ws = home / 'workspace/hermes-agent/.hermes/bin/hermes'
    ws.parent.mkdir(parents=True); ws.write_text('#!/bin/sh\nexec ' + managed + ' "$@"\n')
    acct = home / '.local/bin/hermes'; acct.parent.mkdir(parents=True); acct.write_text(ws.read_text())
    bun = home / '.local/bin/bun'; bun.write_bytes(b'\0' * (2 * 1024 * 1024))
    pulse = home / '.claude/LIFEOS/PULSE/pulse.ts'; pulse.parent.mkdir(parents=True); pulse.write_text('console.log(1)\n')
    D = 'hermes-dashboard.service'; G = 'hermes-gateway.service'; P = 'com.lifeos.pulse.service'
    dropdir = home / '.config/systemd/user'
    for name in (G, D, P):
        (dropdir / (name + '.d')).mkdir(parents=True)
    fedora = home / 'usr-lib-service.d-10-timeout-abort.conf'; fedora.write_text('[Service]\nTimeoutStopFailureMode=abort\n')
    privacy = {name: dropdir / (name + '.d/backup-privacy.conf') for name in (G, D, P)}
    for path in privacy.values():
        path.write_text('[Service]\nUMask=0077\n')
    text = dropdir / (D + '.d/daily-text.conf'); text.write_text('[Service]\nWorkingDirectory=%h/.hermes\nEnvironment=HERMES_HOME=%h/.hermes\n')
    def drops(*paths):
        return 'DropInPaths=' + ' '.join(str(p) for p in paths) + '\n'

    # CT 114 as captured in ct114-systemctl-show.txt, with the home rewritten.
    ct114 = {G: entry('ExecStart', managed, managed + ' gateway run') + 'LoadState=loaded\nDropInPaths=\n',
             D: entry('ExecStart', str(acct), str(acct) + ' dashboard --isolated --no-open') + 'LoadState=loaded\nDropInPaths=\n',
             P: entry('ExecStart', str(bun), str(bun) + ' --no-install ' + str(pulse)) + 'LoadState=loaded\nDropInPaths=\n'}
    run('CT 114 layout, gateway replaced', home, ct114, replaced=('gateway',))
    run('CT 114 layout, gateway not replaced (expect refusal)', home, ct114)
    ct114_fedora = dict(ct114, **{G: ct114[G].replace('DropInPaths=\n', drops(fedora))})
    run('CT 114 layout on Fedora with global 10-timeout-abort.conf, replaced', home, ct114_fedora, replaced=('gateway',))

    daily = {G: 'LoadState=loaded\n' + drops(fedora, privacy[G]) + entry('ExecStart', str(acct), str(acct) + ' gateway run --external-supervisor'),
             D: 'LoadState=loaded\n' + drops(fedora, privacy[D], text) + entry('ExecStart', str(acct), str(acct) + ' dashboard --isolated --no-open'),
             P: 'LoadState=loaded\n' + drops(fedora, privacy[P]) + entry('ExecStart', str(bun), str(bun) + ' --no-install ' + str(pulse))}
    run('daily layout', home, daily)

    # Development host after the owner repoints ExecStart only; the stock-format gateway keeps
    # ExecStop and ExecStopPost on the checkout forwarder, as hermes_cli/gateway.py:3345-3347 writes them.
    dev = dict(daily)
    dev[G] = (daily[G] + entry('ExecStop', str(ws), str(ws) + ' --run-module gateway.systemd_stop_mark', 'yes')
              + entry('ExecStopPost', str(ws), str(ws) + ' --run-module gateway.cgroup_cleanup', 'yes')
              + entry('ExecReload', '/bin/kill', '/bin/kill -USR1 $MAINPID'))
    run('dev layout, ExecStart repointed, ExecStop/ExecStopPost still on checkout forwarder', home, dev)

    run('dashboard ExecStartPre on forwarder', home, {D: 'LoadState=loaded\n' + drops() + entry('ExecStartPre', str(ws), str(ws) + ' version', 'yes') + entry('ExecStart', str(acct), str(acct) + ' dashboard')})
    run('nfs-server style: sh -c with " ; " then forwarder', home, {D: 'LoadState=loaded\n' + drops() + entry('ExecStart', '/bin/sh', '/bin/sh -c true ; exec ' + str(ws) + ' dashboard')})
    run('two ExecStart, forwarder in first', home, {D: 'LoadState=loaded\n' + drops() + entry('ExecStart', str(ws), str(ws) + ' dashboard') + entry('ExecStart', '/bin/true', '/bin/true')})

    def replaced_with(body):
        path = dropdir / (G + '.d/override.conf'); path.write_text(body)
        return {G: ct114[G].replace('DropInPaths=\n', drops(path))}
    run('replaced gateway, drop-in ExecStart forwarder', home, replaced_with('[Service]\nExecStart=\nExecStart=' + str(ws) + ' gateway run\n'), replaced=('gateway',))
    run('replaced gateway, drop-in ExecStop only (account launcher)', home, replaced_with('[Service]\nExecStop=%h/.local/bin/hermes gateway stop\n'), replaced=('gateway',))
    run('replaced gateway, drop-in ExecSearchPath sandbox option', home, replaced_with('[Service]\nExecSearchPath=/usr/bin\n'), replaced=('gateway',))
    run('replaced gateway, drop-in UMask only', home, replaced_with('[Service]\nUMask=0077\n'), replaced=('gateway',))
    run('replaced gateway, drop-in with commented Exec', home, replaced_with('[Service]\n# ExecStart=/x\n;ExecStart=/x\n'), replaced=('gateway',))
    run('replaced gateway, unreadable drop-in path', home, {G: ct114[G].replace('DropInPaths=\n', 'DropInPaths=/nonexistent/x.conf\n')}, replaced=('gateway',))

    # Round 4: development after the owner points every command at the account launcher.
    dev_full = dict(daily)
    dev_full[G] = (daily[G] + entry('ExecStop', str(acct), str(acct) + ' --run-module gateway.systemd_stop_mark', 'yes')
                   + entry('ExecStopPost', str(acct), str(acct) + ' --run-module gateway.cgroup_cleanup', 'yes')
                   + entry('ExecReload', '/bin/kill', '/bin/kill -USR1 $MAINPID'))
    run('dev layout, every command on ~/.local/bin/hermes, ExecReload /bin/kill', home, dev_full)
    for key in ('ExecCondition', 'ExecReload', 'ExecStartPost'):
        bad = dict(daily); bad[G] = daily[G] + entry(key, str(ws), str(ws) + ' x')
        run('daily layout plus ' + key + ' on checkout forwarder (expect refusal)', home, bad)
