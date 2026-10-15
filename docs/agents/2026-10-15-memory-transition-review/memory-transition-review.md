# Memory transition review

Date: 2026-10-15

Role: Independent read-only code reviewer.

Question: Do the provider activation and return orchestration primitives preserve recovery, source admission, and service state?

Model: gpt-6.1-sol, high reasoning effort.

Disposition: Four measured issues require correction. The supplied corrected test suite passes 21 tests. Additional boundary probes fail as described below.

This review does not certify removal, authenticated dispatch, a browser workflow, or a real model session. Those features are outside this review scope. I did not read personal data, access remote hosts, change product code, or call memory or journal tools. All actual service changes use synthetic units under the existing service-manager fixture lock.

## Findings

### 1. P2: An exit before the service journal prevents both return recovery choices

Location: `lifeos_hook_bridge/memory_transition.py:137`, and the recovery branches at lines 139 and 161 in the captured source.

The transition publishes `draining` before `services.drain` publishes its own journal. A process exit in this interval leaves a transition journal without a service journal. A retry selects `services.quiesce`, which requires the missing journal. Rollback also selects `services.quiesce`. Both operations refuse with `The selected profile services have no recovery state`.

The probe uses a real child process and `os._exit(73)` immediately after `_state(..., 'draining')` returns. All three service writers remain active. Both recovery choices fail. The profile files remain unchanged, but the supported API cannot complete or cancel the operation.

Evidence: `crash-before-service-journal.json`, `review-transition-probes-corrected.stderr`, and `review_probes.py:26`.

Required correction: Make the service admission intent durable before recovery depends on it. Alternatively, admit the exact reviewed services again when the transition has no service journal. Test a real process exit at this boundary and preserve any changed service state.

### 2. P2: Runtime-linked enabled Pulse units disappear during disablement

Location: `lifeos_hook_bridge/memory_transition.py:81`, especially the disable command at lines 87 through 90 in the captured source.

The implementation accepts `enabled-runtime`. When the unit fragment is an external file linked into the runtime user unit directory, `systemctl --user disable --runtime` removes the fragment link and the enablement link. This is normal service-manager behavior for this layout.

The probe creates a real runtime-linked Pulse fixture with an Install section and enables it at runtime. Return publishes the built-in memory configuration. Disablement then removes the runtime fragment link. Safe service metadata reports `LoadState=not-found`, `UnitFileState=` and an empty FragmentPath. The source unit file remains present. The transition stops at `configured`. Rollback also fails because the bound service has unsupported program properties.

Evidence: `enabled-runtime-pulse.json`, `review-transition-enabled-pulse-recovery.stderr`, and `review_probes.py:50`.

Required correction: Preserve the exact reviewed fragment link during disablement, or refuse this layout during preparation before any publication. The supplied fixture tests use `linked-runtime` units without enablement, so they do not exercise the disable command.

### 3. P2: A cancelled activation permanently prevents another activation review

Location: `lifeos_hook_bridge/memory_activation.py:68` through line 70 in the captured source.

Preparation refuses any existing `binding.json`. Recovery can return `cancelled`, but it does not remove or archive that binding. The underlying OwnershipSetup permits another operation after cancellation. MemoryActivation prevents the caller from reaching it.

The probe publishes a real import, prepares a real profile backup, cancels the activation through `recover`, and selects a new backup destination. The next prepare refuses with `Complete or recover the existing import activation first`. Repeating recovery cannot remove the terminal binding.

Evidence: `cancelled-activation-retry.json`, `review-transition-probes-corrected.stderr`, and `review_probes.py:93`.

Required correction: Archive or replace the binding only after the existing setup reaches an allowed terminal state. Retain current owner, source, and reference checks for the replacement review.

### 4. P2: Required imported references can change after the final activation check

Location: `lifeos_hook_bridge/ownership_setup.py:169` through line 174, as called by `memory_activation.py:57` in the captured source.

The final readiness callback checks the import references after draining. It releases the native memory transaction before `ownership.apply` changes the provider. An independent native memory writer does not need the profile installation lock or one of the three drained services.

The probe performs an actual `NativeMemory.correct` when execution enters `memory_ownership.apply`, immediately after the final readiness callback. The corrected item is one of the required published import receipts. Activation still returns `configured`, enables ownership, and restarts services. The required reference no longer represents the reviewed imported content at cutover.

Evidence: `activation-changed-reference-boundary.json`, `review-activation-reference-boundary.stderr`, and `review_probes.py:106`.

Required correction: Bind required reference validity through publication. A later readiness check must refuse completion and service restart on conflict. A native writer barrier or a transaction held across the cutover gives stronger admission guarantees. Recovery must preserve the correction and any later edits.

## Tests and limits

The first supplied baseline run executes three transition tests successfully. Both activation tests fail in fixture construction because USER.md uses the unsupported category `preference`. The supported category is `principal`. The primary agent corrects this fixture during review. The corrected activation, transition, and ProfileServices suite then passes all 21 tests in 42.070 seconds.

The initial review probe run inherits that fixture error. The retained corrected probe has a narrow test-only fallback that selects `principal` when the original fixture fails. The primary category correction makes the fallback inactive. No product code is changed by the reviewer.

Probe execution uses the repository's `run_tests.py` runner, the qualified native LifeOS tools, and real user-systemd service writers. The crash probe exits an actual process. Reference mutation uses the actual native memory implementation. These probes do not use a fake service manager or a model response.

The copied runner receipts record each command, source paths, return code, and duration. The original runner output also remains in `docs/verification/2026-10-15-memory-portability/`. The intentional regression failures are evidence of findings, not release qualification passes.

The primary agent is implementing fixes after receiving each measured finding. This report describes the captured source. It does not claim that later edits are reviewed or clear.

## Captured source identities

The `source/` directory contains the exact reviewed source captured before the primary fixture correction.

| File | SHA-256 |
| --- | --- |
| memory_activation.py | c5f2dcfcff42f55849bc2dd7c8b1e852d0ac33f5a2f8156be60533ebdca11fb5 |
| memory_transition.py | 1e598035a9b9bb6cac0ff013668d8841a7530b28a8447a18e4e129840ed25be1 |
| ownership_setup.py | 3d816b098fbafbe793e264c01c38f071226efd6f6033331a0ea912f75b8c483f |
| profile_services.py | 04df4e5527eab85d841ee052e3dc15478dce089eb670bacc681e05c2d1aa5460 |
| test_memory_activation.py | 7f98b4c870b15d39d014cad2003ecf73bf1d07e3270df3a0186c0b3e71f67642 |
| test_memory_transition.py | 0d8d3ff9aa3d94996e0bfd9abaa4d14dff37cdf284ead902678b54c7296ee763 |
