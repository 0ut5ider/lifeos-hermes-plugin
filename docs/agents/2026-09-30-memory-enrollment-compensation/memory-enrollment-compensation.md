# Memory enrollment compensation review

Date: 2026-09-30  
Role: Independent code and regression reviewer delegated by the primary implementation agent  
Question: Does failed-enrollment compensation preserve a concurrent replacement installation or client grant while still disabling the grant created by its own failed operation?  
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Conclusion

The previously reported enrollment compensation defect is fixed in the reviewed snapshot. Both unchanged reproduction scripts now leave replacement configuration and SSH keys unchanged. The current regression confirms that a failed enrollment still disables its own grant when that exact grant remains current.

I found no remaining meaningful defect in this focused compensation change. This conclusion closes the specific error-path finding from `2026-09-30-memory-preferences-closure`; it does not approve activation of the complete memory design.

## Reviewed behavior

`MemorySharing.enroll()` retains the configuration returned by the successful activation update. If SSH key publication fails, it calls `MemoryConfiguration.update()` with a compensation callback. That callback disables the client only when both conditions hold:

1. The current configuration root equals the root of the activated configuration.
2. The current complete client grant equals the grant created by this enrollment.

Both comparisons execute inside the configuration update lock, against the same configuration snapshot that the update publishes. The callback uses `get()` for the client lookup, so an absent client does not cause an unconditional indexed mutation. Changes to the fingerprint, permissions, projects, model route, enabled flag, or additional grant metadata prevent compensation from changing that replacement grant. A different root prevents mutation even when the grant remains identical.

The original key-publication error is still raised in the tested cases. A failed enrollment is not reported as successfully enrolled. The successful enrollment and explicit revocation paths remain covered by the sharing tests.

## Unchanged reproductions

Both prior scripts were executed from their original paths, without modification, using `/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`. Byte-identical copies and hashes are retained in this report directory.

Each probe lets the actual grant update commit, pauses with a scheduling barrier, changes configuration through a real concurrent update, and removes write permission from the temporary SSH directory. Resuming the real enrollment causes its key publication to raise `PermissionError`. Configuration and key publication are not mocked. Temporary permissions are restored in cleanup.

| Probe | Concurrent change | Replacement grant after failure | Configuration changed by compensation | SSH keys changed |
|---|---|---|---|---|
| Original changed-root probe | Root and full client grant replaced | Still enabled and unchanged | No | No |
| Original same-root probe | Client grant replaced, root unchanged | Still enabled and unchanged | No | No |
| Additional root-only control | Root replaced, exact grant preserved | Still enabled and unchanged | No | No |

The root-only control isolates the installation comparison. The original changed-root probe also changes the grant, so it would not independently prove that the root comparison is effective. This additional control confirms both guard conditions separately.

Raw outputs:

- `raw/probe_failed_enrollment.txt`
- `raw/probe_failed_enrollment_same_root.txt`
- `raw/root-only.txt`

The ordinary failure path is covered by `test_failed_publication_disables_its_own_grant`. It triggers the same real filesystem failure without replacing the root or grant. The test verifies that the operation's own client becomes disabled and that no key was published. This passed.

## Tests

All Python commands used the requested environment with declared core, development, and plugin dependencies.

| Suite | Result | Output |
|---|---|---|
| `test_memory_sharing.py` | 8 passed in 0.623 seconds | `raw/sharing-tests.txt` |
| `test_memory_preferences.py` | 6 passed in 1.498 seconds | `raw/preferences-tests.txt` |
| `test_memory_service.py` | 9 passed in 3.176 seconds | `raw/service-tests.txt` |
| Two unchanged failure probes | Expected error, no replacement mutation | Raw files listed above |
| Additional root-only control | Expected error, no mutation | `raw/root-only.txt` |

The sharing tests include same-root and changed-root replacement cases, own-grant cleanup, successful enrollment, client revocation, concurrent enrollment, invalid key handling, symlink refusal, and preservation of unrelated SSH keys. The preferences suite includes the earlier concurrent root check regression. The service suite checks request validation, grant binding, structured unavailability, and configuration updates.

All 23 affected unit and integration tests passed. The probes captured their expected `PermissionError` as structured output. No unexpected test errors or warnings were present in these outputs.

The full memory suite, localhost SSHD transport, generic host middleware suite, child-context probe, and browser UI were not repeated in this focused closure. This change only alters the enrollment failure compensation callback. Earlier reports retain those broader results; this report makes no new claims about them.

## Evidence and source integrity

`raw/source-hashes.json` and `raw/snapshot-*` preserve the reviewed source and test files. `raw/ending-source-hashes.json` matches the starting hashes; `raw/source-drift.json` is empty. `raw/probe-hashes.json` confirms that both saved original probes are byte-identical to the scripts executed. Exact commands are in `raw/commands.txt`.

No implementation code was edited or committed. No live server, production configuration, production memory, or journal was accessed. All test writes affected disposable synthetic fixtures. No actual SSH credentials were changed, and this review did not activate memory ownership.

## What deserves Adrian's review

The operation now distinguishes its own committed grant from a concurrent replacement before compensating for failed key publication. That closes the reported unintended-revocation path. This is a focused correctness result, not a release or activation approval. Native proposals, complete source and session lifecycle coverage, restricted prompts, backup and restore, and full activation remain governed by the existing open gates.
