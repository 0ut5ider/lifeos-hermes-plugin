# Governed native Wisdom frame updates

Date: 2026-10-05. Role: primary implementation and verification.

The managed native Wisdom writer checks current owner authority before reading or publishing a frame. The native renderer preserves the five observation transformations. The existing memory operation journal protects one fixed frame destination. Publication uses mode 0600.

The interface admits one lowercase domain name, one supported update type, and an observation within 64 KiB. The frame stays within 256 KiB. The existing remote procedure call transport limit also applies. The interface refuses private or retired observations, excluded current frames, read-only or revoked callers, changed authority, redirected destinations, and invalid physical source paths. It rechecks the frame after native rendering. A later valid or private edit survives refusal and subsequent recovery.

## Evidence

The initial probe reproduces seven policy failures. Its positive case also has five assertion failures because the test searches escaped JSON as plain text. The corrected positive characterization passes one test and five subtests before product changes. The first candidate passes eight tests and five subtests. A separate retry regression then reproduces a previously successful receipt bypassing current retirement admission after frame removal. Admission now runs before the operation can return a cached receipt.

The combined gate passes 76 tests and 38 subtests in 95.31 seconds. It covers the native writer, service, source admission, native operations, and backup. Ten original-native controls compare exact JSON results and frame bytes for creation and update across all five observation types. Actual process death after file publication recovers both an existing frame and an initially absent frame through a subsequent transaction. The boundary probe changes actual source files or authority after the actual native worker returns.

The recorder saves 12 passing controls with individual native process results and synthetic frame bytes. Failed pre-fix outputs remain available. The source comparison confirms all 50 native memory files match the prepared distributed tree. Root and runtime native patches contain the same bytes. No dependency or patch group is added.

## Limits

These tests set the native LifeOS root explicitly and use an unrestricted synthetic owner. They do not verify the live Hermes terminal environment or default path binding, a model's choice of observation, restricted conversation prompts, other Wisdom readers or publishers, scheduled learning synthesis, or ownership activation.

A Wisdom frame is a native source document. This operation does not claim that its entire generated body becomes a new explicit fact reference. If the registry already refers to an unchanged body in that frame, publication preserves its exact body and adjusts its position. An update that cannot preserve one unambiguous registered body refuses publication. Other native adoption and recall contracts remain separate.

Ownership and sharing remain disabled. No running server, configuration, or production release changes in this unit.
