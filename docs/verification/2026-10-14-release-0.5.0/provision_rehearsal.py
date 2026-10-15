# ABOUTME: Creates a synthetic daily-layout test guest after checking the Proxmox inventory.
# ABOUTME: Uses temporary file-backed storage and preserves all existing guests.
import json
import os
from pathlib import Path
import subprocess
import time

os.umask(0o077)
out = Path('/root/lifeos-release-0.5.0/provision-111')
out.mkdir(parents=True, exist_ok=True)
rows = []
def run(command, **options):
    start = time.monotonic()
    result = subprocess.run(command, capture_output=True, text=True, timeout=600, **options)
    index = len(rows)
    (out / (str(index) + '.stdout')).write_text(result.stdout)
    (out / (str(index) + '.stderr')).write_text(result.stderr)
    rows.append({'command': command, 'exit_code': result.returncode,
                 'elapsed_seconds': time.monotonic() - start})
    (out / 'operations.json').write_text(json.dumps(rows, indent=2) + '\n')
    assert result.returncode == 0, 'Read the saved operation output'
    return result.stdout

try:
    inventory = json.loads(run(['pvesh', 'get', '/cluster/resources', '--type', 'vm', '--output-format', 'json']))
    assert all(row['vmid'] != 111 for row in inventory)
    occupied = subprocess.run(['ping', '-c', '1', '-W', '1', '192.168.8.246'], capture_output=True, timeout=5)
    assert occupied.returncode != 0, 'The selected disposable address responds before provisioning'
    key = Path('/root/lifeos-release-0.4.2/test-public-key.pub')
    assert key.is_file()
    storage = Path('/var/lib/vz/lifeos-050-tests')
    assert not storage.exists()
    storage.mkdir(mode=0o755)
    run(['pvesm', 'add', 'dir', 'lifeos-050-tests', '--path', str(storage), '--content', 'rootdir,images'])
    run(['pct', 'create', '111', 'local:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst',
         '--hostname', 'lifeos-050-daily-rehearsal', '--rootfs', 'lifeos-050-tests:120',
         '--unprivileged', '1', '--memory', '8192', '--cores', '4', '--features', 'nesting=1',
         '--net0', 'name=eth0,bridge=vmbr0,ip=192.168.8.246/24,gw=192.168.8.1,firewall=1',
         '--onboot', '0', '--tags', 'disposable;lifeos-test', '--ssh-public-keys', str(key), '--start', '1'], umask=0o022)
    (out / 'process.done').write_text('0\n')
except BaseException:
    (out / 'process.done').write_text('1\n')
    raise
