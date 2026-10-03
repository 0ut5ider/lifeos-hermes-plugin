# Merged release on .212

The two active test installations on `192.168.8.212` run plugin version `0.1.0` from merged commit `d5dafbcac41434eb9aac2c4c7880a9b9be8135a4`. Both pull requests are merged. The deployed runtime includes the final PR #1 corrections and the PR #2 version metadata.

The release preserves the existing profiles, credentials, identity, user data, hook settings, and memory ownership. Memory ownership and optional sharing remain disabled. The Discord installation keeps Hermes built-in memory. The browser installation keeps its prepared memory configuration.

## Installed compatibility set

| Component | Discord installation | Browser acceptance installation |
| --- | --- | --- |
| Account | `lifeos-hermes` | `lifeos-plugin-install-probe` |
| Operating home | `/home/lifeos-hermes` | `/home/lifeos-plugin-install-probe/acceptance-20261002` |
| Plugin revision | `d5dafbcac41434eb9aac2c4c7880a9b9be8135a4` | Same revision |
| Plugin runtime files | 75, all match | 75, all match |
| Hermes source | Base `758ad514`, nine compatibility patches | Same prepared source, with existing acceptance helpers |
| Hermes local commit | `6056259cc67cb6daeaf8d6ceffabbc524598e418` | Existing patched acceptance checkout |
| LifeOS source | Base `5e2f2e8`, ten compatibility patches | Same prepared source |
| Native hook registrations | 74, settings preserved | 74, settings preserved |
| Native baseline files | 1,798, zero changes at verification | 1,798, zero changes at verification |
| Dashboard | Port 9119 | Port 8921 |

[source-manifest.json](source-manifest.json) records the full upstream revisions and the 19 patch hashes. [release-results.json](release-results.json) records installed source checks, services, model replies, dependencies, and recorder outcomes.

The Discord release changes six Hermes files, 51 plugin files, 28 native files, and three external recorder files. The browser release changes eight plugin files and one external recorder file. File counts include additions. The release copies only changed files and preserves local helpers and ignored files.

The managed environments contain `tree-sitter==0.26.0`, `tree-sitter-bash==0.25.1`, `pathspec==1.1.1`, and `mcp==2.0.0`. The release preserves the Hermes core dependency files.

## Verification

| Check | Result | Evidence |
| --- | --- | --- |
| Release, native, memory, and lifecycle regression gate | 103 pass | [regression.txt](regression.txt) |
| External recorder gate | 32 pass | [recorder.txt](recorder.txt) |
| Dashboard gate | 12 pass | [dashboard.txt](dashboard.txt) |
| Sharing, owner preferences, and SSH gate | 22 pass | [sharing-tests.txt](sharing-tests.txt) |
| Hermes middleware, policy, stop, and child routing gate | 38 pass | [host-tests.txt](host-tests.txt) |
| Real kernel session gate with fixture pipe cleanup | Four pass | [kernel-session.txt](kernel-session.txt) |
| Actual file apply and rollback rehearsal | 88 Discord files and nine browser files pass | [release-results.json](release-results.json) |
| Actual Hermes plugin manager | Required execution and admission middleware load on both hosts | [release-results.json](release-results.json) |
| Native mount check | Prompt and configuration current on both hosts | [release-results.json](release-results.json) |
| Private model inference | Both expected markers return | [release-results.json](release-results.json) |
| Real agent tool turn | `terminal` executes `pwd`; both replies contain the expected marker | [release-results.json](release-results.json) |
| Owner dashboard API | Login, memory, settings, and drift routes return HTTP 200 | [owner-http-result.json](owner-http-result.json) |

The previous full PR #1 gate passes 1,041 tests with 21 skips. This deployment reruns the focused gates above. It does not rerun the full gate.

All three Discord services and all four browser services are active. The Discord gateway reconnects as `Shiny Hermes Bot#3996`. The `/chat` and `/lifeos-bridge` pages return HTTP 200. Unauthenticated requests to `/api/plugins` return HTTP 401. That authentication check does not establish that `/api/plugins` is a valid authenticated catalog endpoint.

The external recorders retain their existing run IDs. Their source fingerprints match. Each final tool verification window has 34 hook starts and 34 completions, with zero failed hooks and zero capture gaps. Some identifiers are redacted, so the capture report uses the tool verification time window. The report does not establish hook side-effect parity or historical capture completeness.

## Validation limits

The Hermes catalog validator exits 1 on both hosts. Its `RecordingContext.register_middleware` stub rejects the required middleware keyword. Its scanner also reports 16 `ssh_backdoor` matches in the optional, owner-controlled SSH enrollment implementation. The release records these findings and verifies the actual Hermes manager separately. The scanner remains enabled. The release installs no SSH enrollment key and does not enable sharing.

The original kernel test fixture leaves process pipes open and reports resource warnings. The focused real session check closes those pipes after the original fixture teardown. This verifies nested execution behavior; it does not fix production kernel pipe cleanup.

The private release scripts needed corrections for installed-module selection, native owner authority, and Bun PATH preservation. A recorder startup file disappeared between preflight and the post-dependency snapshot. The release restores that file. A later revision metadata write temporarily gave the Discord recorder config root ownership. The operator corrects the owner and repeats capture verification. [The deployment note](../../../notes/2026-10-03-release-preservation.md) records these observations.

A real tool turn updates only the generated `last_updated` field in `ARCHITECTURE_SUMMARY.md`. The operator verifies that the remaining document bytes match the pre-release copy, records the review, and renews the native baseline. Later generated document updates can create new drift.

The release does not activate lasting-memory ownership, migrate existing memory, establish full hook parity, or update `.211` and `.213`.

## Private snapshots and rollback

Each operating home contains `workspace/releases/20261003-merged-d5dafbc`. That private directory holds the prepared sources, the original code files, the profile snapshot, native data snapshots, the baseline, the dependency selection snapshot, and detailed command failures. Raw profiles and model streams remain outside Git.

The reviewed [deployment operator](deploy_release.py) uses an installation lock, checks source hashes, and saves the prior code before it replaces files. [check_runtime.py](check_runtime.py) verifies the actual manager. [rehearse_files.py](rehearse_files.py) verifies real copy and restore operations in disposable directories. [smoke_tool.py](smoke_tool.py) runs the real agent check.

Rollback restores the prior code, baseline, dependency selection, plugin install metadata, and recorder config. It preserves current user data. It refuses a changed protected profile. The file rehearsal verifies this behavior; the live release does not perform a rollback.

For an approved Discord rollback:

```sh
sudo -u lifeos-hermes -H python3 /home/lifeos-hermes/workspace/releases/20261003-merged-d5dafbc/deploy_release.py discord restore
```

For an approved browser rollback:

```sh
sudo -u lifeos-plugin-install-probe -H python3 /home/lifeos-plugin-install-probe/acceptance-20261002/workspace/releases/20261003-merged-d5dafbc/deploy_release.py acceptance restore
```

The Discord rollback restores working-tree files but retains the release commit in Git history. The responsible agent must record the restored tree in a new commit after rollback. The acceptance checkout retains its existing patched layout and helper files.

The shared memory service returns `integrity_error`, so the operator cannot save this deployment to shared memory. This repository record provides the deployment evidence.
