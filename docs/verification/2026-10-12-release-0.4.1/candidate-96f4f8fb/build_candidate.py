# ABOUTME: Builds the committed recovery candidate and records process completion.
# ABOUTME: Keeps package preparation detached from the interactive session.
from pathlib import Path
import subprocess,json,os
repo=Path('/home/outsider/.cache/lifeos-hermes-managed-20261012/build-source-96f4f8fb')
out=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/verification/2026-10-12-release-0.4.1/candidate-96f4f8fb')
cache=Path("/home/outsider/.cache/lifeos-hermes-managed-20261012")
command=[str(cache/"native-test-environment/bin/python"),"-B",str(repo/"scripts/build_managed_release.py"),"--output",str(cache/"packages"),"--hermes-source",str(cache/"upstream"),"--lifeos-source","/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/lifeos","--python-closure",str(cache/"dependency-profile/installs/86c8a0d486dc06f6/environments/279bc6c8268c436487b3322f8bd97285/workspace")]
with (out/"build-candidate.stdout").open("w") as stdout,(out/"build-candidate.stderr").open("w") as stderr:
 result=subprocess.run(command,cwd=repo,stdout=stdout,stderr=stderr)
(out/"build-candidate.done").write_text(str(result.returncode)+"\n")
