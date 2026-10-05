# Named fresh-store preparation

Date: 2026-10-05. Adrian selects the names Adrian and Cerebo. The candidate prepares those names in a separate native store. Production on `.212` stays unchanged.

The [complete native test](named-store-output.txt) passes two tests with seven refusal subcases. It runs all six installation tools from LifeOS 7.40.4 at the supported commit with all ten patch groups. The [native configuration result](native-name-result.json) returns Adrian and Cerebo. The [private review metadata](named-store-result.json) records zero active facts, 103 unchanged source templates before name initialization, and the retained original installation. The test preserves the original configuration, Hermes memory bytes, and synthetic native fact.

The preparation checks both empty native hot stores. It moves only the freshly generated MEMORY directory under the new external USER data tree and creates its program link. It saves the three identity originals before setting the selected names. The final user tree has private permissions. Memory ownership, sharing, and services remain disabled.

The [installer gate](installer-output.txt) passes 20 tests. Real child processes verify cancellation after timeout and SIGINT. Changed package manifests, missing package coverage, and later lock edits refuse dependency installation. The tests use Bun 1.3.14 and the complete native candidate. No dependency step is omitted.

The [dependency measurements](dependency-measurements.json) retain two 90-second resolution failures. Disabling the Bun cache does not resolve the failure. The frozen Remotion control completes in 0.042 seconds. This evidence does not establish the internal cause of Bun's resolution delay. The release fixes all 12 package trees to reviewed locks, consistent with [Bun's lockfile guidance](https://bun.sh/docs/pm/lockfile).

The TELOS dashboard ships a stale lockfile. A direct frozen install refuses it because its manifest requires a lock change. The release catalog uses the successful native control's lock. The fresh installer seeds release locks before native deployment, while the target is empty. Native copy-missing behavior retains those locks. The dependency runner refuses to replace a later lock edit. The [lock provenance](dependency-provenance.json) identifies all source manifests and successful control locks.

The original missing-module failures, the 300-second named-store failure, the stale-lock failures, and the before cancellation control remain in this bundle. They do not count as passes. Verbose network headers remain in the private diagnostic directory. This bundle contains synthetic metadata and test output.

Run `python3 docs/verification/2026-10-05-named-fresh-store/verify.py` from the repository root to check artifact and source hashes. The two command records identify the actual test environments. The named-store worker and exit marker retain the detached run.

This unit prepares a private review candidate. It does not implement the dashboard controls, fresh-store selection, interrupted preparation recovery, activation, or the verified return workflow. Normal plugin admission, complete memory caller coverage, model and service acceptance, background jobs, voice, and combined release verification remain open.
