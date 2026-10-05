# Governed native InterviewScan

Date: 2026-10-04. This unit governs interview scoring, setup inputs, output modes, and assistant naming. Every source is synthetic. Production remains unchanged.

The corrected [baseline](before-output.txt) reports seven failures and five passes, including three subtest failures. Foreign identity and setup paths, retired identity bytes, and private identity and TELOS sources influence the original scanner. The initial fixture expects the wrong next-target label; its raw output remains under `next-mode-correction-*`.

Two [escaped-name controls](escaped-before-output.txt) show native YAML decoding turning source escapes into private or retired names. Managed scanning uses declared admitted sources and the native identity parser. Admission checks the decoded name and raw source while preserving the exact review digest. Generic identity reads and exact source review use the same projection. Standalone naming retains its original configuration chain.

Setup admission has three exact paths: `.env`, `LIFEOS/PULSE/PULSE.toml`, and `LIFEOS/USER/WORK/config.yaml`. These paths do not expand the generic source reader. Old setup sources need exact review after retirement. Scan reads require current unrestricted owner recall. They do not publish files. When an evidence cache exists, the scanner calculates from current admitted evidence instead of using its stored body.

The first candidate contains a missing Python parenthesis. The [direct probe](probe-candidate-output.txt) records that failure. A later consistency fixture leaves authority revoked between subcases; its raw output remains under `fixture-correction-consistency-*`. Both fixture and candidate errors are corrected before the final gate.

The [final regression gate](final-output.txt) passes 263 tests and 186 subtests without failures, errors, skips, or warnings. It covers scan, identity projection, exact review, source admission, aliases, service dispatch, prompt rendering, freshness, publication, migration, interview completion, evidence, TELOS, source preparation, patch packaging, and footprint. The [command](final-command.json) records the environment and current hashes under `source_sha256`. Its inherited `sources` field contains older baseline hashes and does not describe this candidate.

The [native comparison](original-comparison.json) matches six output modes against the pinned original scanner: JSON, human, next target, file review, phase two, and invalid target. The [recorder](controls-output.txt) captures 16 passing native controls. [Case records](native-outcomes) retain synthetic source bytes and actual process output. Actual post-render source, owner, installation, and evidence-availability changes refuse stale delivery.

All 41 [distributed native files](distributed-comparison.json) match the scratch candidate. Both patch copies are equal. The [Bun build](build-result.json) passes. Bundling does not validate TypeScript types; the runtime and TOOLS packages declare no typecheck, lint, or test scripts.

Other native publishers, derivative orchestration, aggregate recovery, restricted delivery, ownership activation, import, and combined release verification remain open. These controls do not enable external integrations or prove production acceptance.
