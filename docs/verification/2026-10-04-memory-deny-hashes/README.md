# Governed native private-token hashes

Date: 2026-10-04. This unit governs `DeriveDenyHashes.ts`. Every identity, setting, source, and destination is synthetic. Production remains unchanged.

The [baseline](before-output.txt) reports five failures and two passes. The original command exposes tokens without owner context, includes private sources, follows redirected corpus files, publishes for a read-only owner, and creates public files. The managed command requires unrestricted current owner recall. Both hash and salt publication require unrestricted owner write access.

The bridge admits the six fixed native corpus paths, the latest network Markdown snapshot, and the operator allowlist. JSON admission checks decoded content. Exact review can restore an older unrelated source after retirement. These paths do not expand the generic source reader. Native token extraction, dictionary filtering, operator allowlist rules, hash generation, and payload fields remain in the native program.

Managed publication uses the installed environment and `LIFEOS/USER/SECURITY/DENY_HASHES.json`. The existing memory journal protects both artifacts. The service response contains counts and publication results. It contains token text only when the owner explicitly requests `--show-tokens`. It never returns salt or environment bytes. Public installs retain the native skip when the private consumer is absent; the operation does not create that marker.

The first candidate passes six controls and fails cold publication. Five [direct attempts](probe-publication-output.txt) all refuse before an operation receipt exists. The [fixed-target probe](probe-cold-target-output.txt) shows the shared system path checker comparing an existing environment file with a missing registry. The checker now compares aliases when the registry exists. The [cold correction gate](cold-correction-output.txt) passes 32 tests and 40 subtests, including registry aliases and system publication.

The [actual conflict gate](consistency-output.txt) passes three tests and six subtests. Source, private-source, authority, environment, oversized-environment, and consumer-marker changes refuse stale output. Later source and environment edits survive. An actual exit after the environment write restores previous environment and hash bytes, or removes the new hash destination, on the next governed operation.

The [native comparison](original-comparison.json) matches token review, hash payload bytes, and unchanged environment bytes with the pinned original tool. It does not retain generated salt values. Managed publication console messages omit absolute paths.

The [broad gate](final-output.txt) passes 128 tests and 94 subtests without failures, errors, skips, or warnings. A subsequent [CRLF control](environment-before-output.txt) finds newline conversion while adding a salt. The [boundary probe](probe-environment-output.txt) measures two CRLF sequences in the file and zero in the admitted text. The environment collector now preserves line endings. Other source readers retain their existing newline behavior. The [final correction gate](environment-correction-output.txt) passes 47 tests and 31 subtests. The broad gate predates this correction and is not rerun. Its current hashes are in [the correction command](environment-correction-command.json).

The [recorder](controls-output.txt) captures 14 passing native controls. [Case records](native-outcomes) preserve synthetic corpus bytes, process output, permissions, and environment line-ending counts and digests. They omit generated salt values. All 43 [distributed native files](distributed-comparison.json) match the scratch candidate. Both patch copies are equal. The [Bun build](build-result.json) passes. Bundling does not validate TypeScript types; the runtime and TOOLS packages declare no typecheck, lint, or test scripts.

DerivedSync, adapters, other publishers, complete service recovery, restricted delivery, ownership activation, import, and the combined release remain open. The cooperative file boundary does not protect against hostile same-UID replacement between final checks and publication.
