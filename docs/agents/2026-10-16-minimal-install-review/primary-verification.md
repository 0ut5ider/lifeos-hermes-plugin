# 2026-10-16: primary verification of minimal installation

Role: primary agent, Cerebo. Model: GPT-6.1 Sol. Question: which parts of the proposed minimal plugin architecture have direct evidence?

This record contains independent measurements. The Opus architecture report supplies the design review. These checks do not qualify a new installation path.

Owner decision, 2026-10-17: the [accepted plan](../../in-place-installation-plan.md) selects patching the existing Hermes installation as the only path. The review's private-runtime recommendation is superseded. Its raw experiments and this verification remain evidence for the implementation requirements.

- The current source is `f231c30514c547051386306c564c179bf8d44b12`. Product source is unchanged during the investigation.
- The qualified 0.7.3 archive SHA-256 is `2deae5dcedfef8224959312410a5381baa91312532c968afa5534f19fd2149c8`. The primary agent recomputes it and verifies that all ten canonical Hermes patch files equal those in the archive.
- All forty patch commands pass on a disposable stock-source copy: apply check, apply, reverse check, and reverse for ten ordered patch groups.
- Patches affect 94 paths, including 37 test or test-runner paths. They total 347,842 bytes. Original affected file contents total 3,625,055 bytes. Reversal restores all 18,243 original regular files with matching contents and permission modes. This comparison excludes empty-directory cleanup and running-process behavior.
- The existing `tests.test_hermes_install_source` module passes all ten cases. Those cases use local Git fixtures and lifecycle callbacks. They do not prove real service restarts, complete removal, or unknown-version support.
- `git archive HEAD` compressed with gzip level 9 measures 71,323 bytes for the release-manager subtree and 1,945,159 bytes for the bridge subtree. These are source-payload measurements, not actual Git transfer or dependency-download measurements.
- A controlled streaming recompression measures 288,144,751 bytes for all entries, 182,219,879 bytes without Git metadata, and 101,017,647 bytes without Git metadata and `stock-hermes.tgz`. The stripped variants are not installable or qualified. Existing validation requires Git HEAD; removal authenticates the stock archive.

Code observations:

- `lifeos_hook_bridge/install_source.py` has source preparation, staged in-place patch application, restore, and interrupted-operation recovery. This mechanism predates the current complete-release path.
- Its service worker coordinates only `hermes-gateway.service`. Adapting it for public use requires discovery and coordinated handling of all consumers of the same source, including dashboards, scheduled workers, other profiles, and command-line sessions.
- `prepare_lifeos` obtains upstream HEAD and requires it to equal the supported commit. A new activation-time installer needs an explicit pinned-commit fetch, not a dependency on upstream HEAD staying unchanged.
- The qualified Hermes installer uses shallow, blobless, sparse checkout for GitHub subdirectory plugin installs (`hermes_cli/plugins_cmd_git.py`, `_clone_plugin_repo`). The initial small-manager mechanism already exists.
- `release_stage.validate_package` and the two native-source validators explicitly require the current package shape. Compact or component releases require new validated identities and recovery contracts; deleting archive members is insufficient.

Raw measurements, commands, unit output, and compression operators accompany this record. No experimental host patches, personal-data operations, or release-asset replacements occur.

## Review follow-up verification

The Opus run completes with exit code zero, the exact reply `DONE`, and both required artifacts. One direct write outside its working directory is refused; it saves the script through its allowed shell tool and completes the experiments. The main reviewer model is `claude-opus-5-5`. Its result metadata also lists an internal Claude CLI helper model. The primary agent does not request or start a helper review.

The primary agent repeats all 38 tests named by Opus using the existing qualified Python environment. All 38 pass. This resolves the review run's missing-`ruamel` environment failure without modifying source or assertions. Both outputs remain available.

An independent local-edit experiment applies all ten patches over a comment outside the patch contexts. Git accepts every patch, but the result differs from the qualified source. Reversal preserves the local comment. Exact source identity must therefore be checked separately from patch admission. The primary agent also reads the stock updater's stash-conflict reset path directly.

The review counts 58 non-test paths, including `scripts/run_tests.sh`. Excluding that runner leaves 57 runtime paths. Its import-overlay discussion should not be read as evidence of 58 runtime Python modules. Upstream extension points could remove the need for our host patches within a supported version range; they would not guarantee compatibility with every arbitrary Hermes version.

The primary agent completes the review's first proposed derivation gate offline for both programs. Ten Hermes patches applied to stock produce qualified tree digest `9ff7e31b195b247fed4ba24b847ff5ebf9e26f890f5627389d7edf23c9c3f4ce`. Twenty-five LifeOS patches applied to the exact upstream Git archive, followed by the existing capability-record generation, produce qualified tree digest `9291b358a1469021d971e78954d506fce225410ee968545413134f0462276a0a`. Both match the manifests in the qualified 0.7.3 archive. The agent report's statement that LifeOS derivation remains untested describes its earlier checkpoint; the two `primary-*-derivation.json` files record the subsequent checks. No network, hooks, services, dependency installation, or user data is involved.

The original review stderr includes trailing whitespace in a unittest failure rendering. It is retained byte-exactly as `review-existing-tests.stderr.gz` so repository whitespace checks do not rewrite raw evidence. Its decompressed SHA-256 is `3def567897376beeb07a246a1bf904bda6eb63baf3dd77da8896367ed290a6f5`.
