# Prepare pinned sources for development

This guide prepares source trees for isolated development and tests. For a supported installation, use the [complete-package workflow](installation-workflow.md).

**Patch copies:** `scripts/prepare_sources.py` reads `patches/`, while the release builders read `lifeos_hook_bridge/patches/`. The two copies are byte-identical, and `tests/test_patch_bundle.py` checks that. The development copy of `hermes-session-lifecycle.patch` once lacked the distributed Discord mirror-policy and webhook-threading additions; the [documentation audit follow-up](../TODO.md#documentation-audit-follow-ups) records the synchronization. The published 0.7.2 package uses the distributed copy.

Run the preparation command from the plugin repository. Supply local Git repositories that contain the pinned upstream base commits:

```bash
python scripts/prepare_sources.py \
  --hermes-repo /path/to/hermes-agent \
  --lifeos-repo /path/to/LifeOS \
  --output /path/to/new-prepared-tree
```

The output must not exist, including as a symlink. The command leaves both input repositories unchanged. It checks each patch against the preceding result, applies the ordered patches, checks whitespace, and publishes both trees only after preparation succeeds.

## Output and source authority

| Output | Purpose |
| --- | --- |
| `hermes/` | Pinned Hermes source with the supported patch groups |
| `lifeos/` | Pinned LifeOS source with the native patches |
| `source-manifest.json` | Base revisions and ordered patch hashes |

The patch declarations live in [`scripts/prepare_sources.py`](../scripts/prepare_sources.py). The managed installer declares the same base revisions and patch names in [`lifeos_hook_bridge/install_source.py`](../lifeos_hook_bridge/install_source.py). The qualified 0.7.2 combination uses ten Hermes and twenty-five LifeOS patches. Keep the development patch files in `patches/` and runtime copies in `lifeos_hook_bridge/patches/` synchronized.

Do not rename `source-manifest.json` to `manifest.json`. Hermes can treat the latter as packaged-runtime metadata and refuse ordinary source setup. The prepared Git working trees contain the applied changes for review; source preparation does not install a runtime or select live programs.

## Use prepared sources in tests

Tests declare their own fixture requirements. Two common memory/backend fixtures are:

```bash
export LIFEOS_HERMES_SOURCE=/path/to/new-prepared-tree/hermes
export LIFEOS_MEMORY_SOURCE=/path/to/new-prepared-tree/lifeos/LifeOS/install
export PYTHONPATH="$LIFEOS_HERMES_SOURCE:$PWD${PYTHONPATH:+:$PYTHONPATH}"
```

Use a Python interpreter with the required Hermes and plugin dependencies. Native tests also need the appropriate Bun runtime. Other suites can require additional explicit fixtures; check their environment reads and skip conditions before selecting a run. The [contributor guide](../CONTRIBUTING.md#focused-checks) gives starting commands.

## Source installation limits

Preparation proves that the patches apply to their declared bases. It does not prove native effects, memory ownership, service integration, messaging delivery, or release qualification. Build a complete candidate and exercise the relevant isolated gates before deployment.

The [September 28 manual setup snapshot](history/2026-10-16-clean-install.md) preserves the earlier separate-account installation probe. Its patch counts, model values, command paths, and host-specific results describe that historical fixture. Do not use it as the current installation procedure.
