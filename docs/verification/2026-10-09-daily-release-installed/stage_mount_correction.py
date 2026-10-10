# ABOUTME: Applies the tested Mount correction only to the isolated acceptance installation.
# ABOUTME: Checks the original native bytes and records the changed candidate patch identity.
import hashlib
import json
import os
from pathlib import Path

os.umask(0o077)
stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
package = stage / 'package'
review = json.loads((stage / 'fresh-store-installed.json').read_text())['fresh_store_review']
installed = Path(review['installed'])
manifest = json.loads((package / 'DAILY-CANDIDATE.json').read_text())
patch_name = 'lifeos_hook_bridge/patches/lifeos-mount-yaml-blocks.patch'
patch = (stage / 'lifeos-mount-yaml-blocks.patch').read_bytes()
manifest['plugin_files'][patch_name] = hashlib.sha256(patch).hexdigest()
target = stage / 'profile/plugins/lifeos-hook-bridge/patches/lifeos-mount-yaml-blocks.patch'
if hashlib.sha256(target.read_bytes()).hexdigest() not in {
        json.loads((package / 'DAILY-CANDIDATE.json').read_text())['plugin_files'][patch_name],
        manifest['plugin_files'][patch_name]}:
    raise RuntimeError('The isolated bridge patch changes outside the selected correction')
target.write_bytes(patch)
relative = 'LIFEOS/HERMES/Mount.ts'
original = (package / 'lifeos/LifeOS/install' / relative).read_bytes()
corrected = (stage / 'mount-plugin-source/lifeos/LifeOS/install' / relative).read_bytes()
target = installed / relative
if target.read_bytes() not in (original, corrected):
    raise RuntimeError('The isolated native Mount source changes outside the selected correction')
target.write_bytes(corrected)
manifest['native_mount_correction'] = {'path': relative,
    'before_sha256': hashlib.sha256(original).hexdigest(), 'after_sha256': hashlib.sha256(corrected).hexdigest()}
manifest['native_source_manifest_sha256'] = hashlib.sha256(
    (stage / 'mount-plugin-source/lifeos/lifeos-source-manifest.json').read_bytes()).hexdigest()
(stage / 'APPLICATION-CANDIDATE.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'native_mount_correction': manifest['native_mount_correction'],
    'patch_sha256': manifest['plugin_files'][patch_name], 'live_profile_changed': False}, indent=2))
