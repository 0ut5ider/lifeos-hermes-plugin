# Native graduation can discard the pending claim

Date: 2026-10-08.

The pinned public hypothesis handler treats a missing existing target frame as a silent skip. It then archives the hypothesis and reports graduation. The characterization fixture names `missing-frame`, sends a real graduate request, receives HTTP 200, and finds the original hypothesis removed. No frame contains the claim.

Matching every native file effect would preserve this loss. The managed planner instead returns HTTP 409 and leaves the hypothesis pending. Ordinary new-frame, existing-frame, rejection, and existing-new-frame skip effects still match the pinned source. The original missing-frame behavior has its own known-bug test, so the deliberate difference cannot disappear inside the broader parity claim.

The same investigation separates interface coverage from caller coverage. Governing the hypothesis HTTP handler does not govern its exported helpers. Seven direct-helper baseline tests record nine failures: unbound, revoked, and read-only callers bypass policy, and retired text still appears. The correction routes those exported helpers through the existing current-owner service and recoverable publication operation.

Evidence: [review gate](../docs/verification/2026-10-08-hypothesis-review/README.md) and [helper gate](../docs/verification/2026-10-08-hypothesis-helpers/README.md).
