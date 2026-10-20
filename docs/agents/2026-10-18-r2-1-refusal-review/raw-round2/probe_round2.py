# ABOUTME: Probes check_service_launchers with real systemctl show text through the real show() parser.
# ABOUTME: Only subprocess.run inside inplace_services is replaced; files are real temporary files.
import subprocess, sys, tempfile
from pathlib import Path
from unittest import mock
from optional.lifeos_release_manager import inplace_services
from optional.lifeos_release_manager.inplace_preparation import check_service_launchers
from optional.lifeos_release_manager.release_catalog import ReleaseRejected

def entry(path, argv, ignore='no'):
    return ('ExecStart={ path=' + path + ' ; argv[]=' + argv + ' ; ignore_errors=' + ignore +
            ' ; start_time=[n/a] ; stop_time=[n/a] ; pid=0 ; code=(null) ; status=0/0 }')

def run(label, home, outputs):
    def fake(arguments, **kwargs):
        unit = arguments[3]
        text = outputs.get(unit, 'LoadState=not-found\nExecStart=\n')
        return subprocess.CompletedProcess(arguments, 0, text, '')
    with mock.patch.object(inplace_services.subprocess, 'run', side_effect=fake):
        try:
            check_service_launchers(home)
            print(label, '-> accepted')
        except ReleaseRejected as error:
            print(label, '-> REFUSED:', error)

with tempfile.TemporaryDirectory() as directory:
    home = Path(directory)
    managed = str(home) + '/.hermes/.lifeos-releases/' + 'a' * 32 + '/bin/hermes'
    ws = home / 'workspace/hermes-agent/.hermes/bin/hermes'
    ws.parent.mkdir(parents=True); ws.write_text('#!/bin/sh\nexec ' + managed + ' "$@"\n')
    acct = home / '.local/bin/hermes'; acct.parent.mkdir(parents=True); acct.write_text(ws.read_text())
    bun = home / '.local/bin/bun'; bun.write_bytes(b'\0' * (2 * 1024 * 1024))
    pulse = home / '.claude/LIFEOS/PULSE/pulse.ts'; pulse.parent.mkdir(parents=True); pulse.write_text('console.log(1)\n')
    D = 'hermes-dashboard.service'; G = 'hermes-gateway.service'; P = 'com.lifeos.pulse.service'
    daily = {G: 'LoadState=loaded\n' + entry(str(acct), str(acct) + ' gateway run --external-supervisor') + '\n',
             D: 'LoadState=loaded\n' + entry(str(acct), str(acct) + ' dashboard --isolated --no-open') + '\n',
             P: 'LoadState=loaded\n' + entry(str(bun), str(bun) + ' --no-install ' + str(pulse)) + '\n'}
    run('daily-like template units on account launcher and bun', home, daily)
    run('direct forwarder', home, {D: 'LoadState=loaded\n' + entry(str(ws), str(ws) + ' dashboard') + '\n'})
    run('sh -c with forwarder after " ; "', home, {D: 'LoadState=loaded\n' + entry('/bin/sh', '/bin/sh -c true ; exec ' + str(ws) + ' dashboard') + '\n'})
    run('sh -c with forwarder before " ; "', home, {D: 'LoadState=loaded\n' + entry('/bin/sh', '/bin/sh -c exec ' + str(ws) + ' dashboard ; true') + '\n'})
    run('sh -c with quoted forwarder', home, {D: 'LoadState=loaded\n' + entry('/bin/sh', "/bin/sh -c exec '" + str(ws) + "' dashboard") + '\n'})
    run('sh -c with $HOME forwarder', home, {D: 'LoadState=loaded\n' + entry('/bin/sh', '/bin/sh -c exec $HOME/workspace/hermes-agent/.hermes/bin/hermes dashboard') + '\n'})
    run('oneshot, forwarder in first of two ExecStart lines', home, {D: 'LoadState=loaded\n' + entry(str(ws), str(ws) + ' dashboard') + '\n' + entry('/bin/true', '/bin/true') + '\n'})
    run('argument --path=<forwarder> (word boundary match)', home, {D: 'LoadState=loaded\n' + entry(str(acct), str(acct) + ' dashboard --path=' + str(ws)) + '\n'})
    run('account launcher as symlink target elsewhere', home, {})
    big = home / 'notes.txt'; big.write_text('see ' + managed + '\n')
    run('false refusal: small data argument naming the runtime', home, {D: 'LoadState=loaded\n' + entry(str(acct), str(acct) + ' dashboard --log ' + str(big)) + '\n'})
    run('loaded with ExecStart empty', home, {D: 'LoadState=loaded\nExecStart=\n'})
    run('LoadState=bad-setting', home, {D: 'LoadState=bad-setting\nExecStart=\n'})
