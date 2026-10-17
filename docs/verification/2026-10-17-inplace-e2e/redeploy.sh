#!/bin/bash
# ABOUTME: Rebuilds the integration release from HEAD and stages it with the manager on the test container.
# ABOUTME: The container is the disposable Proxmox guest 110 at 192.168.8.233 with the account owner.
# Rebuild the integration release from HEAD and stage it, with the release manager plugin, on the test container.
set -euo pipefail
R=~/Projects/Hermes_agent/LifeOS_plugin; E=${E2E_DIR:-$HOME/agent-scratch/e2e}; T=${TARGET:-root@192.168.8.233}
H=~/.cache/lifeos-release-0.7.3-20261016/archive-integration-wgrx453d/package/hermes
PY=/home/outsider/.cache/lifeos-daily-promotion-20261014/frozen-test-environment/bin/python
if [ -z "${NOBUILD:-}" ]; then
rm -rf $E/build $E/release; mkdir -p $E/release
(cd $R && PYTHONPATH=$R:$H $PY -B scripts/build_integration_release.py --output $E/build > $E/build.json)
E2E_DIR=$E python3 - <<'PY'
import json,shutil
from pathlib import Path
import os; d=Path(os.environ.get('E2E_DIR', str(Path.home()/'agent-scratch/e2e'))); b=json.loads((d/'build.json').read_text())
cert={'format':2,'status':'QUALIFIED','version':b['version'],'program_commit':b['head'],'archive_sha256':b['archive_sha256'],'archive_bytes':b['archive_bytes'],'host_compatibility_sha256':b['host_compatibility_sha256'],'lifeos':b['lifeos'],'qualification':'loopback test certificate, not a published release'}
(d/'release/RELEASE-CERTIFICATE.json').write_text(json.dumps(cert,indent=2))
shutil.copy(d/'build'/b['archive_name'], d/'release'/b['archive_name'])
print(b['archive_name'])
PY
tar -C $E/build/$(python3 -c "import json;print(json.load(open('$E/build.json'))['archive_name'][:-4])")/optional -czf $E/manager.tgz --exclude=__pycache__ lifeos_release_manager
fi
ssh $T 'rm -rf /srv/lifeos-e2e/release && mkdir -p /srv/lifeos-e2e/release'
scp -q $E/release/* $T:/srv/lifeos-e2e/release/
scp -q $E/manager.tgz $R/scripts/local_release_server.py $R/docs/verification/2026-10-17-inplace-e2e/driver.py $T:/srv/lifeos-e2e/
ssh $T 'chmod -R a+rX /srv/lifeos-e2e; runuser -u owner -- bash -lc "[ -f /tmp/release-server.pid ] && kill \$(cat /tmp/release-server.pid) 2>/dev/null; sleep 0.5; setsid nohup python3 /srv/lifeos-e2e/local_release_server.py --directory /srv/lifeos-e2e/release --tag v\$(tar -xzOf /srv/lifeos-e2e/manager.tgz lifeos_release_manager/plugin.yaml | sed -n \"s/^version: //p\") > /tmp/release-server.log 2>&1 < /dev/null & echo \$! > /tmp/release-server.pid; rm -rf ~/.hermes/plugins/lifeos-release-manager; d=\$(mktemp -d); tar -xzf /srv/lifeos-e2e/manager.tgz -C \$d; mv \$d/lifeos_release_manager ~/.hermes/plugins/lifeos-release-manager; rmdir \$d; XDG_RUNTIME_DIR=/run/user/1000 ~/.local/bin/hermes plugins enable lifeos-release-manager >/dev/null 2>&1 || true"'
echo staged
