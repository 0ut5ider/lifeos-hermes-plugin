# ABOUTME: Runs the corrected actual guest preparation with its original caller permissions.
# ABOUTME: Preserves raw output and completion state in a detached local supervisor.
from pathlib import Path
import subprocess
out=Path(__file__).resolve().parent
command=['ssh', '-o', 'UserKnownHostsFile=/home/outsider/.cache/lifeos-ui-install-20261013/public-test-known-hosts', '-o', 'StrictHostKeyChecking=yes', 'lifeos-hermes@192.168.8.249', '/home/lifeos-hermes/.hermes/installs/acfa0c22dc12b46d/environments/59216d02b7b249eab48d5cd6943d225d/venv/bin/python -B /home/lifeos-hermes/release-ui-fixture/prepare_private_stage_fixture.py']
with (out/'private-stage-preparation.stdout').open('w') as stdout,(out/'private-stage-preparation.stderr').open('w') as stderr:
    result=subprocess.run(command,stdout=stdout,stderr=stderr,timeout=900)
(out/'private-stage-preparation.done').write_text(str(result.returncode)+'\n')
