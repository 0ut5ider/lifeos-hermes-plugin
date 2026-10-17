#!/bin/bash
# Rebuilds the integration release from the removal worktree HEAD and stages it with the manager on CT 111.
set -euo pipefail
R=/home/outsider/Projects/Hermes_agent/LifeOS_plugin-removal; E=/home/outsider/agent-scratch/e2e-removal; T=root@192.168.8.236
H=/home/outsider/.cache/lifeos-release-0.7.3-20261016/archive-integration-wgrx453d/package/hermes
PY=/home/outsider/.cache/lifeos-daily-promotion-20261014/frozen-test-environment/bin/python
rm -rf $E/build $E/release; mkdir -p $E/release
(cd $R && PYTHONPATH=$R:$H $PY -B scripts/build_integration_release.py --output $E/build > $E/build.json)
python3 - <<'PY'
import json,shutil
from pathlib import Path
d=Path('/home/outsider/agent-scratch/e2e-removal'); b=json.loads((d/'build.json').read_text())
cert={'format':2,'status':'QUALIFIED','version':b['version'],'program_commit':b['head'],'archive_sha256':b['archive_sha256'],'archive_bytes':b['archive_bytes'],'host_compatibility_sha256':b['host_compatibility_sha256'],'lifeos':b['lifeos'],'qualification':'loopback test certificate, not a published release'}
(d/'release/RELEASE-CERTIFICATE.json').write_text(json.dumps(cert,indent=2))
shutil.copy(d/'build'/b['archive_name'], d/'release'/b['archive_name'])
print(b['archive_name'])
PY
tar -C $R/optional -czf $E/manager.tgz --exclude=__pycache__ lifeos_release_manager
ssh $T 'rm -rf /srv/lifeos-e2e/release && mkdir -p /srv/lifeos-e2e/release'
scp -q $E/release/* $T:/srv/lifeos-e2e/release/
scp -q $E/manager.tgz $R/scripts/local_release_server.py /tmp/inplace-removal/driver.py $T:/srv/lifeos-e2e/
ssh $T 'chmod -R a+rX /srv/lifeos-e2e; runuser -u owner -- bash -lc "[ -f /tmp/release-server.pid ] && kill \$(cat /tmp/release-server.pid) 2>/dev/null; sleep 0.5; setsid nohup python3 /srv/lifeos-e2e/local_release_server.py --directory /srv/lifeos-e2e/release --tag v\$(tar -xzOf /srv/lifeos-e2e/manager.tgz lifeos_release_manager/plugin.yaml | sed -n \"s/^version: //p\") > /tmp/release-server.log 2>&1 < /dev/null & echo \$! > /tmp/release-server.pid; rm -rf ~/.hermes/plugins/lifeos-release-manager; d=\$(mktemp -d); tar -xzf /srv/lifeos-e2e/manager.tgz -C \$d; mv \$d/lifeos_release_manager ~/.hermes/plugins/lifeos-release-manager; rmdir \$d"'
echo staged
