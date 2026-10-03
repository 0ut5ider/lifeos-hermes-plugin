# Memory preferences closure review

Date: 2026-09-30  
Role: Independent implementation reviewer delegated by the primary agent  
Question: Do the installation root and minimal-client UI fixes close their reproductions, while preserving retained-context revocation?  
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Conclusion

Both previously reported preferences findings are fixed in the reviewed snapshot. The unchanged root-race probe now refuses enrollment and revocation without changing configuration or SSH keys. The unchanged minimal-client UI probe now passes. The retained-context negative probe remains correct across all 18 cases.

One adjacent error-path defect remains: **enrollment compensation can disable an unrelated replacement grant after SSH key publication fails.** This is a medium configuration consistency and availability issue. It does not demonstrate disclosure or successful unauthorized enrollment. The evidence was sent promptly to the primary agent.

This is a bounded closure review of preferences, enrollment compensation, and the previously reproduced child-context revocation path. It is not an activation review for the complete memory design.

## Closed finding: installation root race

`MemoryPreferences` now constructs `MemorySharing` with its expected installation root. The `activate` and `disable` callbacks check that root inside `MemoryConfiguration.update()`, under the same lock that publishes the configuration.

The original `probe_preferences_race.py` was run unchanged. It pauses after the initial preferences root check, uses a real concurrent configuration update to change the root, then resumes the requested operation.

| Operation | Result | Configuration changed by operation | SSH keys changed |
|---|---|---|---|
| Enroll | `MemoryUnavailable`, different-installation error | No | No |
| Revoke | `MemoryUnavailable`, different-installation error | No | No |
| Sharing toggle control | Same rejection | No | No |

See `raw/unchanged-root-probe.txt`. The current regression test also covers both enrollment and revocation using a real update and synchronization barriers.

## Closed finding: minimal-client UI failure

The renderer supplies defaults for optional connection fields: `read` defaults to project access, `write` and `projects` to empty arrays, and `model_route` to `unknown`. These match `MemoryService.client_scope()` defaults. A valid grant that omits these fields now renders without throwing.

The original `probe_ui_minimal_grant.cjs` was run unchanged. All three assertions passed, including the previously failing render assertion. The current memory and existing dashboard UI suites passed all seven tests. These are SDK unit tests, not a browser rendering certification.

See `raw/unchanged-ui-probe.txt` and `raw/ui-tests.txt`.

## Remaining finding: enrollment compensation ignores current grant identity

Location in the reviewed snapshot: `lifeos_hook_bridge/memory_sharing.py:145`.

Enrollment commits the new client grant before publishing the SSH key. When that publication raises, the exception handler updates the current configuration with:

```python
config['clients'][identifier].update(enabled=False)
```

This callback checks neither the installation root nor whether the current grant is the grant created by this operation. The new checks in `activate` and `disable` do not cover this compensation callback.

### Real failure reproduction

`raw/probe_failed_enrollment.py` performs these steps using disposable files:

1. Invoke the real preferences enrollment and let its grant update commit.
2. Pause immediately after that real configuration update with a scheduling barrier.
3. Use a second real configuration update to change the root and replace the same client identifier with an unrelated enabled grant and fingerprint.
4. Change the temporary SSH directory permissions to `0500`.
5. Resume enrollment. Its actual SSH publication fails with `PermissionError`.
6. Inspect the configuration after the real compensation callback completes.

Observed result:

```text
Publication: PermissionError
Replacement grant before: enabled=True, unrelated fingerprint
Replacement grant after:  enabled=False, same unrelated fingerprint
Configuration changed:   True
SSH keys changed:        False
```

The probe uses an instrumented `MemoryConfiguration` subclass only to pause after `super().update()` returns. It does not replace configuration locking or publication, mock SSH publication, or synthesize the raised filesystem exception. The temporary permissions are restored during cleanup.

`raw/probe_failed_enrollment_same_root.py` repeats the experiment without changing the root. It replaces only the grant under the same identifier. The unrelated replacement grant is still disabled. Therefore an installation-root check alone will not close the compensation defect.

Raw evidence is in `raw/failed-enrollment.jsonl` and `raw/failed-enrollment-same-root.jsonl`.

### Required correction

Bind compensation to the committed operation. Under the configuration update lock, verify both the expected installation and the exact grant that this enrollment created before disabling it. If the current installation or grant differs, leave it unchanged and report the original enrollment failure. Verify the two saved probes, plus the normal failure case where the original grant remains current and must be disabled.

The reproduction assumes a concurrent configuration replacement plus a real SSH publication failure. It is not a normal successful-enrollment failure or an unauthenticated request. The consequence demonstrated is revocation of an unrelated replacement credential.

## Retained-context closure remains verified

The previously adapted negative probe was rerun unchanged against the current runtime. Results in `raw/context-summary.json`:

- Approved raw child and approved actual Hermes provider child each sent one localhost request.
- Missing enabled caller context and mismatched configuration profile sent zero requests.
- Disabled and deleted configurations refused re-admission and environment rebinding.
- Disabled and deleted configurations refused raw children carrying either full inherited context or only the sealed session ID.
- A deleted configuration with a persisted session still refused after the process binding was cleared.
- A genuinely fresh inactive conversation sent its separate public synthetic request.
- Unapproved provider route, missing provider child context, and post-forget provider calls sent zero requests.
- The native Claude fallback refused inherited governed context.

The complete actual child process output is in `raw/unchanged-context-probe.txt`. There was no further private-marker transmission in any denied case. As in the preceding review, the fresh-conversation control clears the old process binding and uses a separate public marker; it does not discard retained lineage to continue an old conversation.

## Tests and scope

All Python tests and probes used `/home/outsider/.cache/lifeos-plugin-memory/memory-test-env/bin/python`.

| Gate | Result |
|---|---|
| Complete `test_memory_*.py` suite | 93 passed |
| Existing and memory dashboard UI unit tests | 7 passed |
| Unchanged minimal-client reproduction | 3 passed |
| Unchanged installation-race reproduction | All 3 operations reject without mutation |
| Unchanged context negative reproduction | All 18 cases retain their expected outcome |

The full memory suite includes the real localhost SSHD test, native preferences/API fixtures, runtime tests, actual child HTTP recorder, and installed-copy MCP test. Raw outputs and exact commands are retained in `raw/`.

The 131 generic host tests were not repeated because their code did not change in this closure scope. The prior review independently exercised the actual prepared host dashboard mount and authentication middleware. The primary agent was given the unchanged script path: `docs/agents/2026-09-30-memory-context-revocation-review/raw/probe_dashboard_auth.py`. This closure does not claim a new authentication result from that script.

## Snapshots and boundaries

Starting sources are preserved as `raw/snapshot-*` with SHA-256 hashes in `raw/source-hashes.json`. Ending hashes and any concurrent changes are recorded in `raw/ending-source-hashes.json` and `raw/source-drift.json`. The three prior probes were copied byte-for-byte into this report directory and their original hashes recorded in `raw/unchanged-probe-hashes.json`.

No implementation files were edited or committed. No fleet host, live Hermes runtime, production memory, or journal was accessed. All active mutation tests used synthetic temporary configuration, native records, HTTP services, or SSH fixtures. No existing host SSH keys were changed.

## What deserves Adrian's review

The two original defects are independently closed. The remaining compensation callback needs operation identity checks, with the original grant and concurrent replacement cases both verified. Activation, native proposals, complete source and session lifecycle coverage, restricted prompts, backup/restore, and browser runtime verification remain outside this closure. The successful tests do not imply approval of those open gates.
