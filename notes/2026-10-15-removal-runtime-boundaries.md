# Bind selected commands and the service inventory

Date: 2026-10-15.

The independent removal workflow review finds two adjacent gaps. A changed stock launcher passes the source and manifest checks, then the selected command exits with status 91. An actual inactive runtime-linked user service also passes admission while it names the Bun and native programs selected for removal. The primary reproduces both failures.

The stock review now binds the three commands, Python environment, contained tool store, package-manager bootstrap, enabled features, and runtime metadata. The source binding stays separate. Every dependency link must resolve inside the fixed stock runtime. The executable check excludes bytecode caches and the Python environment's non-executable `.lock` file. The real constructed environment has exactly one shared-write artifact: that lock file, with mode 0666. All executable files still require owner control without shared write access.

The real 2.2 GiB stock runtime passes the seven-component binding check in 4.093 seconds. The synthetic mutation controls cover all three commands, interpreter bytes, dependency bytes, bootstrap bytes, and enabled features. A later interpreter link outside the runtime refuses admission.

Consumer admission now reads the account manager's effective unit paths and loaded fragment, override, and execution metadata. It scans inactive runtime-linked units and preserves their definitions. The primary also finds stale loaded fixture fragments whose temporary directories no longer exist. Admission checks their cached execution metadata and does not treat an unrelated missing file as a selected program. The actual linked-service regression and the existing consumer tests pass.

The broader 144-test run passes after moving an earlier crash hook to its intended boundary: the queue is published, but owner admission has not started. The original failure remains in the evidence. These results do not certify the pending full installed removal or a model turn.
