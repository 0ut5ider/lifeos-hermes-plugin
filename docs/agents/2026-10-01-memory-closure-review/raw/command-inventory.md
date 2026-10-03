# Command inventory

All project commands use /home/outsider/Projects/Hermes_agent/LifeOS_plugin unless a preserved shell script specifies a disposable checkout extracted from the archived baseline. The completed baseline checkout is moved to /tmp/lifeos-memory-closure-baseline-d1a919e so repository test discovery cannot collect its duplicate tests.

Read-only inspection uses cat, sed, rg, nl, git show, git log, git rev-parse, git status, git ls-files, sha256sum, and the recorded source archive. The archive is produced by git archive HEAD for lifeos_hook_bridge, tests, patches, the approved design, and the implementation plan. No Git mutation is performed.

The common probe environment is:

```sh
export PYTHONPATH=.:tests
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/hermes
```

The interpreter is /home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python.

The interpreter executes these preserved programs, with stdout and stderr redirected to the corresponding log:

1. probe_hot_neighbors.py to hot-neighbors.log.
2. probe_schema_provenance.py to schema-provenance.log.
3. probe_delta_and_grants.py to delta-grants.log.
4. probe_recovery_delta.py to recovery-delta.log.

The exact detached hypothesis command and done-marker handling are in run-journal-hypothesis.sh. The exact detached baseline gate command and done-marker handling are in run-baseline-targeted.sh. Each detached job uses setsid with stdin from /dev/null. Child processes are owned synthetic native test processes.

baseline-sha256.txt contains initial tracked implementation/test/patch hashes. prefix-drift-check.txt verifies those bytes after independent baseline probes, before primary source changes. public-source-hashes.json records the public distributed source files read for native and host boundary review. head-after-baseline-probes.txt records the intervening documentation-only HEAD.

The reusable baseline script now extracts the same preserved archive into a fresh /tmp/lifeos-closure-baseline directory before it executes the original test command. The measured run uses the same archive and test command; only the temporary working-directory location changes after completion.

## Follow-up closure commands

The same interpreter and public source environment execute probe_recovery_journal_hypothesis.py, probe_recovery_contracts.py, probe_distinct_delta_latency.py, probe_explicit_context_provenance.py, and probe_agent_source_session.py. Each program preserves observations or explicit contract assertions in JSON. A successful process marker alone does not prove an observational contract passes. The report checks the saved values.

run-final-closure.sh sequences the five final probes and run-final-targeted.sh at 0913b30. The latter runs nine modules and saves final-targeted.log and final-targeted.done. Its preserved 0913b30 result has 113 passing tests. The isolated eight-second case is test_memory_delta.MemoryDeltaTests.test_distinct_hot_capacity_finishes_within_registered_hook_timeout.

probe_corpus_instrumentation.py changes only a disposable connector to execute instrument_native_rpc.py. That program records call action, operation, native duration, and Python caller stack, then invokes the actual native method with unchanged arguments. It uses LIFEOS_REVIEW_PROJECT for the reviewed project import and LIFEOS_REVIEW_CALL_LOG for a synthetic-home output path. The original 0913b30 log and JSON remain preserved with the revision suffix.

run-closure-0400794.sh sequences the unchanged recovery, capacity, explicit context, complete Hermes turn, and instrumented call-count probes. It then runs the actual isolated eight-second capacity case and 11 affected modules. Each phase has a separate log and done marker. This script starts only after the primary expanded gate completes.

closure-source-0400794.tar.gz preserves the 186 reviewed tracked paths listed in closure-sha256-0400794.txt. Its capture uses Python tarfile and hashes each file. No extracted repository copy remains under the report directory.

The final integrity command parses closure-sha256-0400794.txt and compares all 186 files with SHA-256, compares all 26 public-source hashes, verifies the final unittest count and OK result, checks for failure/error/skip output, and requires all nine final markers to equal 0. It saves closure-final-integrity.json. The observation-check command parses each current probe JSON, asserts the reported recovery/count/session contracts, and saves closure-observation-checks.json. review-logs.tar.gz stores every raw .log file with its original basename.

The report evidence check resolves every backtick raw path, checks Python probe syntax with ast.parse, checks shell syntax with sh -n, and checks authored text for the em dash character. report-evidence-checks.json records the final report hash. approved-design-integrity.json compares the approved design in the initial source archive with its final bytes. primary-corroboration-corpus-results.json copies the primary's independently rerun native call observation. All reports and raw artifacts are complete before the reviewer returns.
