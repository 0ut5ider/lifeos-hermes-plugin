Date: 2026-09-28
Agent role: Independent read-only parity reviewer
Question: Which concrete gaps remain in preserving the installed LifeOS Claude Code hook behavior on isolated Hermes .212, with Hermes denial authoritative, one local model mapped by effort, and SSH and Docker opt-in?
Model: GPT-6-Astra, high reasoning effort

Reviewed checkout: `ad9f2dcefaec41730b46bd9cb0a7dd70c7f61bac`. Product code was not changed. This review used the local checkout and disposable temporary fixtures. It made no connection to .211, .212, or .213 and did not use memory or journal tools. The parent agent separately tested native Claude Code behavior for the first finding and reported its result during this review.

## Findings

### 1. Confirmed bridge defect: compound directory changes use the wrong path for file rules

`bash_file_targets()` returns file operands without the directory in effect at each command. `HookBridge.command_approval()` applies its original `cwd` to every operand. With `Bash(*)` allowed and an absolute Read deny on `<workspace>/sub/secret`, `cat sub/secret` returns `{"action":"deny"}`. All three equivalent directory-changing forms return `None`:

```sh
cd sub && cat secret
(cd sub && cat secret)
cd sub; cat secret
```

The parser reports `([('read', 'secret')], True)` for each compound form. The actual shell would read `<workspace>/sub/secret`, but the rule check examines `<workspace>/secret`. No secret or external file was accessed: the fixture created only a synthetic marker and called the bridge's decision method.

Code: `lifeos_hook_bridge/bash_permissions.py:108` creates a flat target list; `lifeos_hook_bridge/bash_permissions.py:387` walks child nodes without directory state; `lifeos_hook_bridge/bridge.py:1394` checks all returned paths against one `cwd`; `lifeos_hook_bridge/bridge.py:1416` permits the Bash allow shortcut.

This is a confirmed mismatch between the bridge's checked path and the command's real target. The parent agent subsequently ran a paired native Claude Code probe on .212: `cd sub && cat secret` had zero denials in the control and one denial with the Read deny, with the exact Bash tool input retained. The [parent's native probe record](native-cd-probe.json) confirms a parity gap for that form. I did not independently run the native probe; the other two compound forms remain unmeasured in native Claude Code. The parent is preparing a fix.

Lowest-risk next step: add a regression and conservatively request review when a command changes directories before a relative file operation. Reconstructing shell execution state across conditionals, subshells, and `pushd` would touch more parser behavior and needs more verification. Preserve Hermes's independent denials.

### 2. Confirmed bridge inconsistency: malformed managed policy is ignored for direct local file tools

An invalid `managed-settings.json` produces an unknown file-policy result. The Bash path requests human review. Direct local Read discards the result, and direct Write proceeds when a real PermissionRequest child hook grants it. The probe results were:

| Operation | Bridge result |
| --- | --- |
| Direct local `read_file` | `None` |
| Direct local `write_file`, native hook allow | `None` |
| Bash `cat allowed.txt`, native hook allow | `{"action":"review"}` |

`_managed_permission_sources()` represents the unreadable source as `None` at `lifeos_hook_bridge/bridge.py:180`. `file_target_decision()` returns `unknown` for that source at `lifeos_hook_bridge/file_permissions.py:146`. The direct-tool caller records unknown results only when `not host_paths`, at `lifeos_hook_bridge/bridge.py:1602`.

This is confirmed bridge behavior with real hook child execution. No native Claude Code invalid-managed-policy probe was run. It is an inconsistency in conservative review policy, not yet a measured difference from Claude Code.

Lowest-risk next step: distinguish unknown caused by malformed policy from unknown caused by an ordinary path outside `cwd`. The current single `unknown` value covers both. Requiring review for every local unknown would widen ordinary file approvals and should not be slipped in as a one-line fix. A focused diagnostic state plus a regression can preserve existing outside-workspace behavior while retaining review for unreadable policy.

### 3. Confirmed extension gap: PreToolUse `permissionDecision: ask` is discarded

A real command hook returns a correctly event-tagged `PreToolUse` response with `permissionDecision: ask` and a reason. `pre_tool_call('read_file', ...)` returns `None`. The bridge handles only deny/block at `lifeos_hook_bridge/bridge.py:1547`; it then processes updated input and context without carrying the ask decision.

This can silently skip a project or user hook's requested approval. A native Claude Code comparison was not run. The current local public LifeOS source snapshot's PreToolUse hooks do not show an ask producer in the reviewed command hooks. Therefore this is not established as a blocker for the currently installed LifeOS behavior, although it limits the advertised native-hook contract and trusted project support.

Lowest-risk next step after current installed-hook gaps: add a real child-process test and return Hermes approval with a stable rule key. Deny must take precedence if any other handler denies. Hermes hardline behavior must remain authoritative.

### 4. Confirmed extension gap: SessionStart matchers never receive the start source

A `SessionStart` group with `matcher: startup` never executes on `is_first_turn=True`. The same group without a matcher would execute. The payload includes `source: startup`, but `_run()` matches its third argument, which defaults to an empty string. `pre_llm_call()` does not pass the source as that argument.

Code: `lifeos_hook_bridge/bridge.py:1083` matches `tool_name`; `lifeos_hook_bridge/bridge.py:1797` computes source; `lifeos_hook_bridge/bridge.py:1799` dispatches without the source matcher value. The fixture's marker file remained absent.

The public source snapshot's current five SessionStart handlers have no matcher, so this does not break those installed registrations. No native Claude Code comparison was run. Treat it as a small compatibility gap for user/project registrations. SessionEnd also passes no matcher value and hardcodes `reason: other` at `lifeos_hook_bridge/bridge.py:1908`; that analogous case was inspected but not separately reproduced.

## Documentation assessment

`docs/hook-parity.md:21` already qualifies Bash parsing as tested forms and describes full parity as incomplete. It should additionally name changed-directory operands, because the current statement that literal operands are checked omits the wrong-directory condition reproduced here.

`docs/hook-parity.md:16` limits unreadable managed-policy review to commands, which accurately describes the tested Bash behavior. Do not broaden that statement to all tools. The direct-file paragraph at line 21 should record the malformed-policy limitation until it is addressed.

`docs/hook-parity.md:9` accurately describes deny and input changes, but omits that PreToolUse ask is unsupported. `docs/hook-parity.md:13` accurately describes the current matcher-free installed hooks, but should not imply source-specific registrations are supported.

The review did not find evidence that one local model with low, medium, and xhigh effort violates the accepted .212 target. `docs/hook-parity.md:133` explicitly records Adrian's chosen equivalence. Distinct model tiers are not a remaining requirement. Internal server reasoning depth remains unobservable and is already stated as such.

The documented `execute_code` source-text limit, terminal combined-output limit, remote-backend opt-in, and unconfigured external services should retain their stated boundaries. They are not new defects discovered here. Expanding SSH or Docker access would not complete the local parity target.

## Verification and artifacts

The dependency imports fail under the host's default `python` because `tree_sitter` is absent. The existing `/tmp/lifeos-shell-ast/bin/python` environment has the repository dependencies and ran these checks:

| Check | Result |
| --- | --- |
| `python -m unittest discover -s tests -p test_bridge.py` | 161 tests passed in 6.477 seconds |
| `python -m unittest discover -s tests -p test_file_permissions.py` | 9 tests passed |
| `python -m unittest discover -s tests -p test_model_tiers.py` | 7 tests passed |
| Disposable candidate probe | All four behaviors reproduced |

The bridge suite emitted three uncaptured `Remote project settings are unavailable: No module named 'tools'` warnings. Its test runner reports OK, but the output is not clean under the repository's test rules. The warnings reflect the local environment without Hermes tool modules; this review did not run the installed .212 suite or change tests to suppress them.

Reproduce the candidate probe from the repository root:

```sh
PYTHONPATH=. /tmp/lifeos-shell-ast/bin/python docs/agents/2026-09-28-parity-fresh-review/probe_candidates.py
```

The script uses `TemporaryDirectory`, synthetic data, a real hook subprocess, and an in-process temporary managed-policy directory override. It does not execute the candidate Bash reads or perform candidate tool writes. Raw results are in `probe-output.json` and expected malformed-policy warnings are in `probe-stderr.txt`. Each test suite has a separate raw output file. The source excerpts and the current public registration summary are in `source-evidence.txt`.

The source excerpt file had trailing spaces removed before commit. Its line content and source line numbers were retained.

Review priority: land and verify the compound-directory fix against the now-confirmed native behavior. Then decide the policy-error behavior before editing its shared result type. The PreToolUse ask and SessionStart matcher gaps are bounded changes, but their current installed-hook impact is lower. This review made no deployment, configuration, Git commit, or remote-system changes.
