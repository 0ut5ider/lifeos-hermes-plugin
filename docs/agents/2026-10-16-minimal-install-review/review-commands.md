# Review commands, 2026-10-16

Commands this review ran, in order. Paths under `S` are disposable. No command wrote to the archive, the extracted qualification fixture, product files, servers, or the parent's `primary-*` files.

```bash
S=/home/outsider/.cache/minimal-install-review-20261016
R=/home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/agents/2026-10-16-minimal-install-review

# Identity and extraction
sha256sum /home/outsider/.cache/lifeos-release-0.7.3-20261016/packages/0.7.3-70fa8390.tgz
# -> 2deae5dcedfef8224959312410a5381baa91312532c968afa5534f19fd2149c8 (matches RELEASE-CERTIFICATE.json)
mkdir -p $S/extract $S/work $S/results
(cd $S/extract && tar -xzf /home/outsider/.cache/lifeos-release-0.7.3-20261016/packages/0.7.3-70fa8390.tgz)
du -sb $S/extract/*
mkdir -p $S/stock && (cd $S/stock && tar -xzf $S/extract/stock-hermes.tgz)

# Patch copies
for f in lifeos_hook_bridge/patches/*.patch; do cmp -s $f $S/extract/lifeos_hook_bridge/patches/$(basename $f) || echo DIFF; done   # no output
for f in patches/*.patch; do cmp -s $f lifeos_hook_bridge/patches/$(basename $f) || echo "DIFF $(basename $f)"; done                 # DIFF hermes-session-lifecycle.patch
(cd $S/stock && git apply --numstat $S/extract/lifeos_hook_bridge/patches/<name>.patch)                                                # per-patch stats

# Packaged Git state
git -C $S/extract/hermes rev-parse HEAD; git -C $S/extract/hermes status --porcelain    # 68 M, 27 ?? including the manifest
git -C $S/extract/hermes rev-list --count HEAD                                         # 1 (shallow)
git -C $S/extract/hermes count-objects -vH                                             # 19262 objects, 83.40 MiB pack
git -C $S/extract/lifeos rev-list --count HEAD                                         # 717

# Measurements and patch experiments E1 to E7 plus per-component gzip sizes
(cd $S/work && python3 -I $R/scripts/measure.py $S/extract $S/stock $S/work $S/results)

# Clean disposable Hermes clone at the base for Git experiments and the existing test
git clone -q --no-checkout $S/extract/hermes $S/work/hermes-clean
git -C $S/work/hermes-clean checkout -q --detach 71d34bad1045610252eda02ee79549436896e784

# Git experiments E8 and E9a to E9d
(cd $S/work && python3 -I $R/scripts/git_experiments.py $S/work/hermes-clean $S/extract/lifeos_hook_bridge/patches $S/work $S/results)

# Existing unit tests (bytecode writes disabled)
LIFEOS_LATEST_HERMES_SOURCE=$S/work/hermes-clean LIFEOS_TEST_PYTHON=python3 PYTHONDONTWRITEBYTECODE=1 \
  python3 -B -m unittest tests.test_hermes_install_source tests.test_release_programs tests.test_stock_hermes tests.test_latest_hermes -v
# -> Ran 38, 37 ok, 1 FAIL (ruamel not installed for the import check in test_latest_hermes)

# Python closure comparison
python3 -I - $S/stock/uv.lock $S/extract/python-runtime/uv.lock   # tomllib name/version set difference

# Searches (read-only)
git grep -n -E "stage_supported_hermes_patch|apply_hermes_patch|restore_hermes_patch|..." -- ':!docs'
git grep -n -E "rmtree|prune|retention|cleanup" -- optional/lifeos_release_manager/*.py optional/lifeos_release_manager/dashboard/plugin_api.py
git grep -n -i -E "hermes update|self-update|update_mechanism" -- '*.py'
git ls-files | grep -i release_validation     # no result
```

The first run of `git_experiments.py` staged intent-to-add entries before `git stash push`, which made Git refuse the stash (rc 128). That was an artifact of the experiment, not of Hermes; the stock updater handles intent-to-add entries separately (`update_cmd_stash.py`, `_intent_to_add_paths`). The script was corrected and rerun. The first E9b variant expected a conflict but auto-merged; it is reported as E9b (adjacent edit), and E9d adds a true overlapping edit. The final raw output is `review-git-experiments-raw.json`.
