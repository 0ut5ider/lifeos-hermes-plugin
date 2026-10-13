Date: 2026-10-13
Agent role: Independent follow-up release-stage correctness reviewer
Question: Does the child-umask correction resolve permissive-caller runtime metadata rejection across all run_stage callsites without changing the caller, prior safety boundaries, or qualification claims?
Model: Codex GPT-6, inherited parent model. The exact harness model identifier is not exposed in this review context.

Reviewed commit: `10459df6c2b27bda8911dfd96a25b92bee769c93`.
Follow-up base: `f29e40a6a5e0565abe91994245d494b26a078ebf`, the PR18 merge commit.
Branch: `feature/github-install-replay`.
Follow-up PR: https://github.com/0ut5ider/lifeos-hermes-plugin/pull/19
Product diff SHA-256: `adb9311376ad09563c48291ecf7fe179ca69c19b8ce51772d514bd833faed888`.

## Result

No actionable code-review findings remain in the inspected follow-up product diff. The change sets the private umask in each stage child through the supported subprocess parameter, rather than changing the caller process. The independent suite passes all 36 selected tests, and an additional actual native-metadata experiment reproduces the measured cause and verifies the correction.

The corrected candidate still needs its own complete archive-bound qualification and actual post-merge installation replay. The prior b9 candidate's running full gate does not establish qualification for this new commit. No release publication or guest retry is claimed by this review.

## Measured cause and correction

The primary's private preparation receipt reports caller umask 0002 and actual generated Hermes metadata modes: the hermes_agent-0.0.0.dist-info directory is 0775, and METADATA and entry_points.txt are 0664. The selected runtime fingerprint rejects shared write access. This is a real preparation refusal before active publication, rather than a defect in the fingerprint requirement.

The detached dashboard preparation entry point already sets a private process umask. The synchronous CLI entry point preserves its caller's umask. Both invoke the same stage helper. The native metadata writer creates its directory with the default mkdir mode and writes both files with the default file mode. Its generated permissions therefore followed the permissive caller through the stage child.

`release_stage.py:184` now passes `umask=0o077` to subprocess.run. The current helper still validates process success, bounds execution with its timeout, and captures private stdout and stderr. Its callers, environments, arguments, working directories, and return behavior remain unchanged. The fix does not chmod an existing invalid runtime or bypass source validation; a new staged runtime receives correct creation permissions.

I independently ran the real upstream write_metadata() function from the pinned public Hermes source. An unprotected subprocess under caller mask 0002 produces exactly the reported 0775 directory and 0664 files. The same writer through the corrected run_stage creates the directory at 0700 and both files at 0600. The stage's log files remain 0600. The caller's mask remains 0002 after the stage.

`native-metadata-probe.json` records the complete mode comparison, Python version, and subprocess source path. This experiment creates only a small temporary metadata tree. It performs no package extraction, download, guest action, or complete installation.

## All affected callsites

I traced all five product callsites of run_stage:

1. release_stage.py:203 builds the frozen Python dependency environment. Default-created private build and dependency metadata now inherit 0077.
2. release_stage.py:222 assembles the native bundled runtime and launchers. This stage creates the exact dist-info metadata that caused the refusal.
3. release_stage.py:233 installs the private native reference and its dependencies. The child and descendants inherit the private mask.
4. cli.py:164 invokes the retained qualified candidate's preparation worker. Its generated review artifacts use the same private stage boundary, including synchronous CLI invocation.
5. release_worker.py:206 migrates and validates staged configuration. It operates on the generated configuration under the same private child mask.

The helper's explicit 0600 log permissions remain independent of the caller mask. Existing explicit executable permissions and copied source modes are not rewritten by a umask. The source integrity requirement continues to reject shared write access. The correction changes artifact creation at the common boundary and does not weaken validation or alter later publication targets.

## Safety and qualified-runtime portability

The actual qualified test interpreter is Python 3.14.7. Its subprocess.Popen signature includes umask, and the local standard-library POSIX implementation passes that value to the low-level child spawn routine. The parameter applies in the child before execution and leaves the parent mask unchanged. It avoids a process-wide os.umask change in a dashboard thread or a custom Python preexec_fn.

The Linux qualified runtime supports this parameter directly. I do not extend this conclusion to an unqualified Windows installation path. Release management already depends on POSIX ownership, flock, procfs, and owner user services.

The change does not newly force a different spawn strategy in these calls: the existing helper always supplies a working directory, and the qualified interpreter's posix_spawn fast path requires cwd=None. No new performance claim or benchmark is needed for this correctness change.

The new regression uses an isolated outer subprocess to set caller umask 0002. It does not change the test harness's global mask. It runs the real stage helper and a real child that creates files, then checks directory 0700, file 0600, unchanged caller 0002, and clean captured stage output. It does not mock subprocess behavior.

## Preserved prior review boundaries

The complete follow-up product diff contains only three files: the stage helper's child umask argument, its actual subprocess regression, and the rc.3 changelog note. No native patch, active configuration logic, user-data path, archive authentication rule, service barrier, process/profile adapter, owner grant, or preparation lease changes in this diff.

The previous foreign-profile admission, lifecycle revalidation, shared preparation lease, effective-environment parsing, and exact bundled-launcher corrections remain unchanged from the merged product. I checked the relevant caller and service sources as context. I did not rerun complete UI, service, native, or archive suites merely to restate their earlier results.

PR18's merge prerequisite is now resolved. The actual default-GitHub bootstrap and complete first-install replay still need their post-merge acceptance result. The private preflight failure and this child-permission correction must remain visible in that evidence. The b9 rc.3 candidate was not published, so the primary can rebuild the candidate at the corrected commit. Published rc.1 and rc.2 archives and certificates remain immutable historical inputs.

The observed failure occurs before active changes. This report does not claim that the corrected full guest installation or archive qualification has completed. Production and development guests remain outside this review; daily production qualification and automatic memory activation are not added to its scope.

## Independent tests and exact commands

All commands run from /home/outsider/Projects/Hermes_agent/LifeOS_plugin.

Selected stage, CLI, and preparation controls:

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=.:tests:/home/outsider/.cache/lifeos-hermes-managed-20261012/upstream \
/home/outsider/.cache/lifeos-hermes-managed-20261012/native-test-environment/bin/python \
  -B -W error::ResourceWarning -m unittest -v \
  test_release_stage test_release_manager_cli test_release_preparation
```

Result: exit 0; all 36 pass with no skips in 0.720 seconds. The complete report is in focused-tests.stderr; stdout is empty. No ResourceWarning or unexpected diagnostic occurs.

Independent actual native metadata experiment:

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=.:tests:/home/outsider/.cache/lifeos-hermes-managed-20261012/upstream \
/home/outsider/.cache/lifeos-hermes-managed-20261012/native-test-environment/bin/python \
  -B -W error::ResourceWarning \
  docs/agents/2026-10-13-pr18-stage-permissions-review/native_metadata_probe.py
```

Result: exit 0; the unprotected native writer reproduces 0775/0664; the protected writer produces 0700/0600; both stage logs are 0600; the caller stays at 0002. Stderr is empty. The script restores its isolated process's prior mask before it exits.

I inspected the actual qualified subprocess source, all five callsites, the native metadata and launcher generators, and the primary's safe permission receipt. A preliminary filesystem search included two absent guessed standard-library paths. The actual source path was then obtained from subprocess.__file__ and inspected directly. That discovery error is not a product test failure or a missing runtime capability.

## Raw artifacts and scope of actions

This directory contains product-diff.patch, reviewed-state.json, inspected-file-hashes.json, commands.json, the independent metadata probe source and JSON, complete raw test output, and a copy of the primary's private-preparation-permissions.json receipt. The hash map identifies 12 inspected product, context, native reference, evidence, and runtime source files.

The repository has a pre-existing primary edit to the preceding review report. This reviewer does not alter that report or its artifacts. All writes here are new authorized review artifacts. I do not edit product code, initialize or commit a repository, push, merge, mutate a guest, change published assets, inspect private credentials or personal memory records, change agent settings, or call memory/journal tools. I do not rely on the removed retained extraction or create a new large copy.

The remaining work is exact qualification of the corrected candidate and actual user-action acceptance. It is separate from this completed source and stage-boundary review.
