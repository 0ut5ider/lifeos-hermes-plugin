# PR18 release UI review, round 10

Date: 2026-10-13
Agent role: Independent code reviewer
Question: Does preserving the baseline creation time make unchanged-native release plans repeatable while preserving source and drift refusal?
Model: gpt-6.1-sol
Reviewed commit: `914ad24b0eea7f0022e75edc815f5be08566d0f9`
Review scope: The baseline correction, its regression, and the associated unpublished candidate version metadata.

## Result

No actionable defect found in this bounded delta. All 49 selected tests pass in 6.264 seconds with `ResourceWarning` treated as an error. The stdout file is empty. The stderr file contains the unittest case results and its successful summary.

The production correction preserves only `created_at` from the loaded prior baseline when `native_changes` is false. It still calls `create_baseline()` to regenerate the native version, source commit, source root, installed root, and installed file hashes. This retains the timestamp of the unchanged native program baseline while associating the baseline with the new qualified source location.

`load_baseline()` validates the timestamp and installed-root binding before the value is reused. `plan_system_files()` still checks all prior managed files against their baseline hashes and validates reference files against the candidate source. These checks occur before the corrected branch. The native-change branch remains unchanged and obtains its new baseline through the existing mount path.

`_execute()` still recomputes the candidate program plan, checks its target and source bindings, then calls `check_prepared()` before service drain or publication. The correction makes repeated baseline generation produce the same bytes for unchanged native content. It does not weaken transaction fingerprints or bypass a source check.

## Regression fidelity

The added test uses real temporary files, a real Git source repository, the actual native baseline and update planner, real Hermes YAML migration and configuration checking, and the actual `ProgramTransaction`. The `SimpleNamespace` only dispatches the selected native modules. It does not replace their behavior.

The test assigns a valid historical baseline time of 1, so the timestamp assertion cannot accidentally pass because two preparations occur during the same second. It prepares the transaction, regenerates the plan, compares baseline bytes, and runs `check_prepared()`. It verifies the original baseline stays unchanged during preparation. It then edits a tracked installed hook and confirms that the real update planner raises `UpdateConflict`.

The fixture contains a synthetic Bun executable but does not use it to claim a successful native installation. The regression verifies planning and prepared-file consistency. It does not execute the complete worker, service drain, browser action, or release publication.

## Reviewed measured cause

I read the existing safe private-update receipts. `numeric-update-prepublication-conflict.json` records one source mismatch for `generated/baseline.json` while the program transaction remains `prepared`. `numeric-update-baseline-cause.json` records only `created_at` changing, from 1791908692 to 1791908799, with all native file hashes identical. These receipts support the reported regeneration cause. I did not recreate that browser trial or inspect the guest.

The candidate metadata reverts the unpublished version-only candidate to `0.4.2-rc.1` consistently in `VERSION`, both plugin manifests, and both dashboard manifests. The changelog removes the unpublished `rc.2` section and records the measured fixes under unpublished `rc.1`. This source review does not establish any publication state beyond the supplied evidence.

## Independent test command

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=.:tests:/home/outsider/.cache/lifeos-hermes-managed-20261012/upstream \
/home/outsider/.cache/lifeos-hermes-managed-20261012/native-test-environment/bin/python \
  -B -W error::ResourceWarning -m unittest -v \
  test_release_configuration test_release_programs \
  test_version_drift_baseline test_update_plan
```

Result: 49 tests, exit 0. These controls cover repeatable preparation, native edit and collision refusal, reference-source mismatch, symlink refusal, unchanged-file publication, interrupted transaction recovery, retained artifact checks, and baseline behavior. They are component and local file/process controls, not browser or full release acceptance.

## Exact inspected hashes

| File | SHA-256 |
| --- | --- |
| `optional/lifeos_release_manager/release_worker.py` | `24c9dee90698349de295529e76a948416e4d1eec96a3a12b926bbd64d1d3de71` |
| `optional/lifeos_release_manager/release_plan.py` | `3a173b89fb667b81c25693dd3b463e9480d00573dfa8c0148265388c3a14f00a` |
| `optional/lifeos_release_manager/release_programs.py` | `238f912b7c1a0619f570384a33e971218b34a192ae00c4b3480b4187e6e86de4` |
| `lifeos_hook_bridge/version_drift.py` | `853c66889adc9784bcc454157097535cb795fb0fdd153848aaa561e5d03d9865` |
| `lifeos_hook_bridge/update_plan.py` | `66d16d3da44d82d66d665b517a7b57e066cb2b79ebabe17988186adc71033063` |
| `tests/test_release_configuration.py` | `deb29bdce8db3470e3af5f6f192b443816936b7bc77b6ee331c6f04373fe3ec8` |
| `tests/test_release_programs.py` | `637bc4f1416acaaab38e4ee0aa38e8a83dc0da210e6803324cf805c1f2de2f3c` |
| `tests/test_version_drift_baseline.py` | `8e52dc8b947172c7009fa4691f8b609d669cef1ad893b429fd0f55df5df20098` |
| `tests/test_update_plan.py` | `95f3cbf6d637dc23de8780d6cb37eafe8450cecc17bfe288f491b290e9cce7fb` |
| `notes/2026-10-13-unchanged-native-baseline.md` | `76dc53a303b8ad270609e0e9287e02f30262b4af3ef43ebfeebf0c8445a4c718` |
| `VERSION` | `5d3e1681e019cdb752bffc4d443ea66b18b28ec3d517768b2fe0c25fa90f046c` |
| `CHANGELOG.md` | `83df6ed792ee508a8b3217808e84ff0e93e99e7507be88cc21c15e2bd940fdc0` |
| `lifeos_hook_bridge/dashboard/manifest.json` | `32261f0463bb788825a197d023ca1a01eba5323a7797fde0cfb181a2427242b0` |
| `lifeos_hook_bridge/plugin.yaml` | `be0a4286d39bd7d5e0c526448f4b8ffd2d124f4ccf3bf089f3f8269abc727671` |
| `optional/lifeos_release_manager/dashboard/manifest.json` | `bcadb1bd1a9e3225a676a48c33e6565fbc6d6d7c117b821486189801dceefa51` |
| `optional/lifeos_release_manager/plugin.yaml` | `309ad75c42fc2e663cffb5f46bcf9a187bf481ca9377c91e24f352f8101f75c8` |


## Artifacts and scope limits

The report directory contains the committed delta, exact source hashes and line-numbered excerpts, original safe cause receipts, copied engineering note, test command, complete test stdout and stderr, and exit receipt.

I did not change product code, access any guest, mutate sealed sources, run full gates, call memory or journal tools, commit, or push. I wrote only the authorized review artifacts. The corrected seal, full native and integration gates, actual browser numerical update, and recovery acceptance remain with the primary agent.
