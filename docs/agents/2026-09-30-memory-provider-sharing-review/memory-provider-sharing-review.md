# Memory provider fixes and SSH sharing review

Date: 2026-09-30  
Role: Independent bounded implementation and synthetic integration reviewer  
Question: Do the four provider fixes and optional SSH sharing preserve admission, permissions, key ownership, revocation, and concurrent configuration updates?  
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Outcome

The reviewed baseline passed all requested test gates: 83 memory and sharing tests, 6 provider tests, and 131 host tests. The memory suite includes a real isolated localhost SSH server and generated temporary credentials.

The four previous findings are substantially addressed. Gateway admission now crosses the bounded worker boundary, general discovery loads the bridge, dual loader namespaces share verified caller context, disabled or deleted ownership configuration blocks retained context, and asynchronous required middleware is rejected.

Two additional defects were reproduced against the initial review snapshot:

1. High: the CLI worker handoff still rejects a correctly admitted terminal session.
2. Medium: SSH revocation can delete an unrelated authorized key whose comment matches the client marker.

The primary agent received both findings and began fixes while this review continued. It reported a CLI correction and additional child-routing work. Those later changes are not verified by this report. The initial source snapshots, probe outputs, and observed source drift identify the exact scope of the evidence below.

## Findings

### 1. High: terminal admission cannot cross the worker boundary when gateway platform metadata is empty

Location in the initial snapshot: `lifeos_hook_bridge/memory_runtime.py`, `check_call()` reconstruction of a recorded admission.

`admit()` supports CLI calls without gateway platform metadata by filling `HERMES_SESSION_PLATFORM` from its trusted host `platform` argument. The initial `check_call()` implementation does not perform that same normalization. It requires a nonempty platform field in `current_host_metadata()` before it can reconstruct the recorded admission.

The host CLI publishes its session ID through `agent.agent_init._publish_session_id()`. It does not establish the gateway platform metadata used in the new gateway regression. A CLI model request supplies `platform='cli'` through the actual middleware context, but the initial guard receives it only in ignored extra keyword arguments.

The independent probe used the actual prepared-host plugin manager and bounded prompt-admission dispatcher. It supplied an approved terminal grant, empty gateway platform metadata, the current session ID, and `platform='cli'` at both host boundaries. The admission hook recorded the terminal session successfully. The model guard then raised `MemoryAdmissionError`, with cause `The caller has no trusted host identity metadata`. The downstream recording callback did not run.

Normalize the trusted platform and current session ID symmetrically at both boundaries, while retaining the exact recorded-context comparison. Verify the actual CLI worker handoff, not only a direct same-thread `admit()` call.

Evidence: `raw/probe_terminal.py`, `raw/terminal-probe.jsonl`, and `raw/terminal-probe.stderr`.

Status at report completion: the primary agent reported reproducing this probe, adding a regression, and implementing symmetric normalization. `source-verification.json` records the changed runtime and provider test file. I did not rerun the probe or suite against that later edit in this review.

### 2. Medium: revocation identifies SSH keys by comment alone and can remove unrelated keys

Location in the initial snapshot: `lifeos_hook_bridge/memory_sharing.py:135`.

`revoke()` removes every authorized-key line whose final space-separated field equals `lifeos-memory:<identifier>`. It does not compare the key against the enrolled credential fingerprint or verify that the line is a managed restricted command.

The probe began with an unrelated, unrestricted synthetic Ed25519 key whose comment was `lifeos-memory:researcher`. Enrollment then added a distinct restricted key for the new client `researcher`. Enrollment accepted the file. Revocation removed both lines, leaving the authorized-keys file empty.

A comment is not proof that this enrollment owns a credential. Revocation should match the enrolled key and its managed entry, or enrollment should refuse an existing marker collision before changing configuration. The fingerprint already stored in the grant provides a way to distinguish the enrolled credential. Keep the existing ordering that disables the client grant before changing the key file.

Evidence: `raw/probe_sharing.py` and `raw/sharing-probes.jsonl`, case `revocation_comment_collision`.

Status at report completion: the primary agent said it would fix this after reproducing the probe. This report does not verify that later fix.

## Previous findings verified

| Previous finding | Current verification |
| --- | --- |
| Admission context remains in the worker | The actual gateway worker regression passes. A recorded context is checked against trusted current gateway metadata, then bound on the model caller for provider tools. Finding 1 identifies the remaining initial CLI case. |
| Disabling or deleting ownership configuration releases retained context | Both earlier probes now raise `MemoryAdmissionError`. The regression also clears the live context and verifies rejection using the durable recorded session after configuration deletion. |
| General discovery skips the bridge as exclusive | The manifest is explicitly standalone. The installed-copy probe reports `enabled=true`, a loaded module, and one prompt-admission hook with memory unselected. |
| Separate loader namespaces do not share caller state | The installed-copy provider regression loads both namespaces, dispatches the actual hook and model guard, then successfully calls the provider status tool. Context comparison uses dataclass values rather than class identity. |
| Required asynchronous callbacks are skipped | Canonical host tests reject asynchronous function and callable-instance registration. They also reject awaitable results returned by synchronous functions before provider dispatch, without unawaited-coroutine warnings. |

The prior worker probe intentionally supplies no actual gateway metadata on the caller. It still rejects. That is the correct result for that probe, not evidence that the verified gateway handoff remains broken. The new trusted-gateway regression is the positive test for the fix.

## SSH sharing and configuration review

The enrollment command binds a fixed server-selected client, configuration file, interpreter, and installed MCP program. The remote command must equal `lifeos-memory`; it cannot select another client or append arguments. The generated authorized-key entry uses `restrict` and a forced command. The forced command launches an isolated Python interpreter with `-I` through `/usr/bin/env -i`, a bounded PATH, an explicit HOME, and only the quoted original SSH command needed for validation.

The real localhost test proves that a generated client key can access the MCP protocol, that an `id` shell request is refused, that project reads exclude synthetic principal memory, and that the default grant cannot write. After revocation, another request on the same open MCP connection is rejected. A new SSH connection with the revoked key is also rejected. The synthetic fact remains available to the owner.

Configuration is loaded for each tool request. The sharing code disables the client grant before removing its key, so a running MCP process does not rely on disconnecting the SSH session for revocation. Enrollment records a default project-only read grant and validates optional project writes through the shared configuration validator.

`MemoryConfiguration.update()` acquires a private file lock before loading, mutating, validating, and atomically publishing the configuration. The existing thread test preserves concurrent edits and a revocation. An additional independent probe started four separate Python processes with eight updates each. All 32 edits survived, the revoked client remained disabled, and every process exited 0 with empty stderr. Invalid updates also preserve the previous configuration in the supplied regression.

The code checks key-file ownership and private permissions, rejects key-file symlinks, validates the Ed25519 wire structure, and prevents enrolling a key already present in the file. These checks passed the supplied tests. Finding 2 concerns the ownership test used during removal, which is weaker than enrollment's credential binding.

The same operating system user remains trusted. This SSH transport provides a restricted remote credential and fixed server grant. It does not claim isolation from arbitrary local code already running as the server account.

## Test results

| Gate | Result |
| --- | --- |
| SDK interpreter, `test_memory_*.py` | 83 tests passed in 53.931 seconds, exit 0. Includes native tools, MCP, configuration, sharing, and real localhost SSH. |
| Host test interpreter, `test_hermes_memory_provider.py` | 6 tests passed in 2.844 seconds, exit 0. Includes gateway worker dispatch and dual loader integration. |
| Canonical host runner, four requested files | 131 tests passed across 4 files in 16.8 seconds, 0 failed, exit 0. |
| Earlier provider probe, prepared-host path updated only | Disable/delete guards now reject; general discovery now loads; missing trusted caller metadata remains rejected. |
| CLI worker handoff probe | Confirmed finding 1 in the initial snapshot. |
| Separate-process configuration updates | 32 updates survived with revocation preserved. |
| SSH key comment collision | Confirmed finding 2 in the initial snapshot. |
| Top-level and bundled required patch | Byte-identical. |

The host runner used `/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-native/hermes`, the owned prepared source named in the task. It ran through `scripts/run_tests.sh`, not direct pytest. The native source fixture was `/home/outsider/.cache/lifeos-plugin-memory/managed-source/LifeOS/install`.

The earlier provider probe was copied with only its prepared-host directory changed from the previous `source-gate-20260930-provider` tree to the requested current `source-gate-20260930-native` tree. The copied script and complete results are preserved. Its stderr includes the expected missing-metadata rejection and a dependency diagnostic from the separate host test environment about `mcp==2.0.0`. MCP and SSH protocol tests ran successfully under the specified SDK environment. This is not a verification of a deployed unified package environment.

## Evidence and source identity

- `raw/reviewed-*` and `raw/reviewed-hashes.json`: initial plugin, patch, and test snapshots with SHA-256 hashes.
- `raw/host-*` and `raw/host-hashes.json`: relevant prepared host sources.
- `raw/source-verification.json`: runtime and provider-test source drift observed after the primary agent began the CLI fix; bundled patch comparison.
- `raw/memory-tests.txt`, `raw/provider-tests.txt`, and `raw/host-tests.txt`: complete baseline test output.
- `raw/probe_previous.py`, `raw/previous-probes.jsonl`, and `.stderr`: earlier reproductions with the prepared-source path updated.
- `raw/probe_terminal.py`, `raw/terminal-probe.jsonl`, and `.stderr`: actual terminal admission reproduction.
- `raw/probe_sharing.py` and `raw/sharing-probes.jsonl`: process concurrency and key-ownership probes.
- `raw/commands.txt`: exact verification commands.

The full baseline gates ran before the primary agent reported the new terminal and child-route edits. Later source changes are not silently included in the baseline conclusion.

## Scope and open gates

This review covered the four prior fixes, the new runtime reconstruction and shared binding, optional SSH enrollment and MCP command restriction, and configuration update serialization. It did not repeat the unrelated memory foundation or logging audit.

Activation and UI remain unfinished. Restricted/shared prompts remain deliberately refused until filtered prompts are verified. Raw child routing and the complete native source inventory remain open; the primary agent's later child-route implementation needs its own follow-up verification. Native proposals, preferences, and installation and backup work are not claimed complete here.

No implementation code was edited or committed. No memory or journal tools were called. No live Hermes installation or fleet host was accessed. The only SSH server was the authorized disposable localhost fixture, with generated temporary keys and cleanup of its own daemon. Persistent review output is confined to the requested report directory, plus normal test-runner output in the owned prepared tree.

The next review should rerun the unchanged terminal and key-collision probes after the fixes, then verify the settled child-route work separately within its requested scope.
