# Managed release continuation

The authorized task remains incomplete. Finish roadmap and observer work, complete installation and updates from Hermes, and qualify latest stable Hermes on .252. Do not change .253.

Current branch: feature/hermes-managed-release. Last root commit: f289f41f. Roadmap and observer commits already exist. Candidate version declarations are now 0.4.0-dev.1, uncommitted.

The current ported native tree is /home/outsider/.cache/lifeos-hermes-managed-20261012/ported at commit 12d8f4237. It targets v0.21.7 at 71d34bad1045610252eda02ee79549436896e784. All twelve upstream checks pass in native-lint-qualified.*. The official expanded native runner passes 716 tests across 38 files in native-official-final.*. Root canonical and packaged ten-group patches have been regenerated from regeneration-qualified. GROUPS contains 92 files. Twenty-five LifeOS groups stay unchanged. The unused protected-instruction patch remains inactive.

New manager package: optional/lifeos_release_manager. Its catalog, archive extraction, program transaction, validation, CLI, staged dependency preparation, worker prototype, and dashboard prototype are on disk. The last focused run passes 29 tests and 11 subtests, including release_version, catalog, stage validation, program recovery, and CLI. Full worker admission and installed execution are NOT verified.

The first combined diagnostic runs 574 cases with five legacy clarify fixture errors and two assertion failures. Those fixture/assertion changes are now in tests/test_native_clarify.py, test_profile_backup_recovery.py, and test_footprint_contracts.py. The updated clarify fixture passes six cases on the current native batch callback and queue. Full combined repeat still required.

MountTransaction now has restore_completed() and execute(retain_for_rollback=True). Two completed restoration tests plus the existing credential-snapshot-pruning test pass. Ordinary mounting still prunes completed credential snapshots. This addition is uncommitted and requires the full mount suite.

Critical unfinished worker issues to address before qualification:
- request/plan binding and action-state admission need real authority and crash tests. Bind plan fingerprints into the request before issuing owner grants.
- recovery while the bridge directory is absent needs a verified retained bridge fallback.
- generated native files are projected by the existing system-file planner. USER and MEMORY roots never move during existing-store updates. Internal dependency links are allowed only inside a package directory.
- native mount uses current installed helpers. After bridge publication the worker reloads mount_transaction to obtain the retention option; test this across actual 0.3.1 to new candidate namespaces.
- mount-intent.json gates completed or interrupted mount rollback. Test interruption before mount execution and after mount commit.
- fresh native installation copies only a newly prepared native reference, empties template personal sections, sets names, and retargets USER. Test every generated path and preservation of a new store on failure.
- runtime fingerprint can change after normal native boot creates .bytecode-fingerprint or other known caches; use a bounded source-file identity rather than accepting arbitrary new files.
- fresh account launchers/dependency parent paths require preparation.
- verify resumed services, exact loaded program identity, model/effort preservation, and complete native baseline.
- owner API recovery while installed bridge is absent needs a safe fallback.
- rollback eligibility for a fresh first installation needs a clear safe UI state.

No reusable current package builder exists yet. Build committed source with prepare_supported_hermes(stock v0.21.7) and prepare_lifeos(pinned clean cache). Include python-runtime pyproject.toml, uv.lock, and plugin-deps manifests copied from the native PM workspace. Record python_runtime_files and manager_files in DAILY-CANDIDATE.json. Build the current Hermes dashboard through native source_build APIs and distribute as a separate bound asset. Do not reuse the old frontend. All existing v0.3.1 assets remain immutable.

Dependency runtime: /home/outsider/.cache/lifeos-hermes-managed-20261012/dependency-profile/installs/86c8a0d486dc06f6/environments/279bc6c8268c436487b3322f8bd97285/venv/bin/python. Its adjacent workspace has the combined frozen lock. Test environment: /home/outsider/.cache/lifeos-hermes-managed-20261012/native-test-environment/bin/python, built through public PM with Discord, Anthropic, and dev group. The release runtime does not include the optional Anthropic test addition.

Actual .252 Linux account is lifeos-hermes, UID 1008. Gateway/dashboard ExecStart is /home/lifeos-hermes/workspace/hermes-agent/.hermes/bin/hermes. The stable launcher runs accepted 0.3.1 runtime. Pulse uses /home/lifeos-hermes/.local/bin/bun at 1.3.14. Selected native home is the existing private fresh-store home below /home/lifeos-hermes/.local/state/lifeos-hook-bridge/fresh-stores. Use lifeos_installation.selection; do not assume account-home/.claude. .252 has about 80 GB free. Neither .252 nor .253 has been changed or deployed in this task. Installed qualification has NOT begun.

No push or PR has occurred for this branch. Current explicit task authorizes implementation and development evaluation. Respect approval requirements for pushing. Do not spawn agents without applicable explicit authorization. Memory MCP is unavailable with integrity_error; do not bypass through files.
