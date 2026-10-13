# ABOUTME: Revalidates retained qualified source and evidence without extracting another complete archive.
# ABOUTME: Exercises the current fresh-service controller with the candidate installation lease in a tiny isolated profile.
import hashlib
import json
from pathlib import Path
import tempfile

from optional.lifeos_release_manager.release_stage import load_bridge, validate_package
from optional.lifeos_release_manager.release_services import fresh_services

ROOT = Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
OUT = Path(__file__).resolve().parent
EVIDENCE = ROOT / 'docs/verification/2026-10-13-release-ui-install'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


build_path = ROOT / 'docs/agents/2026-10-13-pr18-final-review-1/sealed-review-bg1aw0o2/build.json'
build = json.loads(build_path.read_bytes())
package = Path(build['package'])
certificate_path = EVIDENCE / 'test-release-0.4.2-rc.1/RELEASE-CERTIFICATE.json'
certificate = json.loads(certificate_path.read_bytes())
manifest = validate_package(package, certificate)
candidate = load_bridge(package / 'lifeos_hook_bridge')
with tempfile.TemporaryDirectory(prefix='pr18-retained-lease-') as folder:
    home = Path(folder)
    profile = home / '.hermes'
    profile.mkdir(mode=0o700)
    with candidate.memory_module('installation_lock').installation_lock(profile) as lease:
        controller = fresh_services(candidate, profile, home / '.claude', installation_lease=lease)
        status = controller.status()
        assert status['state'] == 'none'
acceptance = json.loads((EVIDENCE / 'PUBLIC-USER-ACTION-ACCEPTANCE.json').read_bytes())
matches = {name: sha(EVIDENCE / name) == expected for name, expected in acceptance['evidence_sha256'].items()}
assert all(matches.values())
certificates = {}
for version in ('0.4.2-rc.1', '0.4.2-rc.2'):
    path = EVIDENCE / ('test-release-' + version) / 'RELEASE-CERTIFICATE.json'
    value = json.loads(path.read_bytes())
    receipts = {name: sha(EVIDENCE / name) == expected for name, expected in value['qualification_receipt_sha256'].items()}
    assert all(receipts.values())
    assert value['production_qualified'] is False
    certificates[version] = {'certificate_sha256': sha(path), 'receipt_hash_matches': receipts}
report = {'retained_package': str(package), 'retained_archive_sha256': sha(build['archive']),
    'retained_manifest_version': manifest['version'], 'same_candidate_lease_status': status,
    'new_full_package_extracted': False, 'acceptance_hash_matches': matches,
    'certificates': certificates, 'default_branch_bootstrap': acceptance['default_branch_web_bootstrap']}
(OUT / 'retained-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
