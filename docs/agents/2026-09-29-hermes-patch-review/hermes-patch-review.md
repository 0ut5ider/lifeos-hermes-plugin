Date: 2026-09-29
Agent role: Independent senior code reviewer
Question: Are the 19 Hermes patches correct, and how can their Hermes-core footprint be minimized while preserving LifeOS behavior?
Model: gpt-6-astra

Adrian, the patch set still needs a generic host extension for full behavior. I found three actionable correctness defects, one proven dead hunk, and an existing stock CLI extension that can remove the custom script-launcher hunk after an integration test. I do not recommend deleting any complete patch from the current pinned installation yet. Several patch files can be consolidated without changing the resulting Hermes tree.

## Scope and evidence

Reviewed plugin HEAD `1d4929fb983dfbbd0e07dcf862e9592ef77c6c89` on `feature/initial-scaffold`. The authoritative application order is `lifeos_hook_bridge/install_source.py:23`. All 19 runtime-bundled Hermes patches applied cleanly, in that order, to Hermes `758ad514eb0e800547e015edf05aa18f78b78d82` in `/tmp/hermes-astra-review-20260929`. I read the patched source, bridge consumers, patch tests, README, parity documents, and earlier boundary review. The earlier report's first-allow bug in `HookBridge.command_approval` is fixed in this HEAD and is not a current finding.

I first queried the public remote and fetched its then-observed HEAD, `6a8ef0c061f6f163a5997c03702373c8fd5bf348`. Exact-revision source excerpts are in `source/`. During this review, upstream advanced to `dccb84b92401234db294667ec203d3ac3dc1b87f`. I inspected the exact 28-commit, 23-file delta at approximately 19:13 UTC through GitHub's compare API; it changes Relay configuration/dependencies and related diagnostics, tests and documentation. The only overlap with the 52 patched files is a warning message in `hermes_cli/plugins.py`. It changes none of the reduction conclusions. Details and the raw relevant hunk are in `upstream-delta-inspection.md` and `upstream-delta-inspection.json`. These are source findings at named revisions, not a guarantee about later moving HEAD. Source at these inspected revisions still lacks the four added hook names, per-task delegation model/effort routing, and the cron bootstrap correction. Its auxiliary client still has provider fallback. An issue, proposal, or open pull request is not proof that a patch can be removed. The previously available local checkout, `bac0c45d8593ed9d53a8e3fcacecdc920b71a2c4`, predates both observed remote revisions.

The bundle has 52 distinct touched files: 30 runtime files and 22 test files. Summed across patches, runtime changes are 705 added and 200 removed lines; tests are 1,298 added and 14 removed. These are cumulative patch counts, including later edits of earlier additions. They are not the net final diff. Counting 19 patch files alone exaggerates the number of independent host contracts.

## Findings

### P1: New admission and policy semantics retain observer failure behavior

Locations: `lifeos_hook_bridge/patches/hermes-hook-controls.patch:97` and the new command and Stop hooks in that patch. Resulting source: `agent/turn_context.py:786`, `hermes_cli/plugins_dispatch.py:42`, `hermes_cli/plugins_dispatch.py:209`, `tools/approval.py:1085`, and `agent/turn_stop_gates.py:81` in the disposable patched tree.

The patch lets `pre_llm_call` reject a user prompt, but stock dispatch still treats it as a bounded, fail-open observer. A callback timeout produces no result. Hermes then proceeds without the rejection. This is a concrete concern for this bridge: its prompt callback runs SessionStart and UserPromptSubmit hooks, and individual native commands may have a timeout up to 300 seconds, while the stock callback timeout is 30 seconds. A late callback can continue running after the host has admitted the prompt.

The added `pre_command_approval` and `pre_turn_stop` hooks are absent from both dispatch timeout sets. Their exceptions are logged and discarded, so an exception means no command veto or Stop veto. A hung callback also has no dispatcher deadline. Returning `None` from the command helper's outer exception handler has the same fail-open effect. Ordinary observer error isolation cannot implement a required policy gate.

Reproduction: the saved script imports the real patched `PluginDispatchMixin`; a real raising command or Stop callback produces `[]`. The prompt-timeout branch is exercised by explicitly substituting the dispatcher's timeout sentinel, not by waiting 30 seconds. Source inspection proves that `pre_llm_call` uses this branch and that the new hooks are unbounded. This establishes host error semantics, not the frequency of failures in deployed LifeOS.

Minimal fix: distinguish admission/policy callbacks from optional observers in dispatch. Give each policy event an explicit error result understood by its caller, with bounded execution and fail-closed behavior. Do not simply add command hooks to the existing fail-closed set: its current result is `action: block`, whereas command policy recognizes `deny`. Likewise a Stop dispatcher failure must cause an incomplete turn, not merely a continuation that the default cap can later release. Use a separate prompt-admission event or opt-in gate registration so optional context providers retain their intended semantics.

Required validation: a slow prompt veto, a raising prompt callback, raising command and Stop callbacks, late worker completion, and a callback already suppressed after timeout. Verify no provider call, command execution, accepted final answer, or durable rejected prompt on the corresponding blocked paths.

### P2: A command review grant is reused across different workspaces

Location: `lifeos_hook_bridge/patches/hermes-command-policy.patch:262`; resulting `tools/approval.py:1256`.

The permission rule key hashes only command text. `cwd`, backend type, and backend identity do not participate. The later context patch passes workspace information into callbacks and into prepared desktop approvals, but it does not scope this stored plugin-review grant.

A user can grant a command for project A, then the same session can run identical text in project B. If B's policy asks for human review, `is_approved(session_key, policy_key)` suppresses it using A's grant. Explicit later denials still win; this defect specifically loses a requested review. Relative commands such as `./deploy` make the distinction material.

Reproduction: the saved source-extracted `check_all_command_guards` receives policy review for `/workspace/project-a` and `/workspace/project-b`, with identical command and session. The callback sees both workspaces, but the human-decision boundary is reached once. The doubles supply grant storage and human approval; the key construction and suppression are the actual patched function.

Minimal fix: bind the review rule key to the effective command, canonical target workspace, and stable backend identity. Define whether an edited policy invalidates existing grants, and include a policy generation if that is the intended behavior. A task ID alone is not backend identity and may change every turn.

Required validation: approve in A then review in B; identical paths on two SSH hosts; Docker image/container identity; same-workspace repeated review; explicit deny after a previous grant; rewritten command approval. Preserve the intended same-workspace session grant.

### P2: First Stop veto loses a later gate's fail-at-limit decision

Location: `lifeos_hook_bridge/patches/hermes-stop-fail-closed.patch:288`; resulting `hermes_cli/plugins.py:2108`.

All callbacks run, but `get_pre_turn_stop_continue_message` returns the first nonempty continuation. If an earlier plugin asks to continue with default cap behavior and a later required gate returns `on_limit: fail`, the later policy is dropped. At the cap, the host can release an answer that the later gate required it to withhold. Registration order changes safety behavior.

Reproduction: the actual extracted merger receives two vetoes, the second carrying `on_limit: fail`, and returns only the first message. The cap logic in `apply_stop_gates` treats that string as `allow` at the limit. Existing tests cover a single fail-at-limit callback, not composition.

Minimal fix: aggregate all valid vetoes before selecting feedback. If any active veto requires failure at the limit, preserve that policy. Choose or combine feedback separately from policy precedence.

Required validation: both callback orders, allow plus veto, two vetoes with mixed limit policies, and a full turn reaching the cap. Assert the result is failed and neither final history nor delivery includes the rejected candidate.

### P3: The batch-order patch adds a dead duplicate `has_hook`

Location: `lifeos_hook_bridge/patches/hermes-policy-batch-order.patch:35`.

The patch adds `hermes_cli.plugins.has_hook`, but the pinned source already defines the same function later. The final patched module has definitions at lines 1843 and 1896; Python replaces the added definition with the stock one. The stock function delegates to `PluginDispatchMixin.has_hook`, which returns the same `bool(self._hooks.get(hook_name))`. Both paths obtain the active delivery manager.

Safe immediate reduction: delete only this added function hunk from both packaged and source patch copies. Keep the desktop batch deferral and tests.

I replayed all 19 patches with that one hunk omitted into `/tmp/hermes-astra-reduced-7tppke2n`. Every patch passed `git apply --check` and applied. Comparing all affected final files found exactly one difference: the unused definition. `reduced-policy-batch-order.json` and `reduced-sequence-result.txt` preserve this review candidate and evidence. I did not edit either implementation patch copy.

## Patch-by-patch classification

“Essential” means needed to preserve the stated behavior on the pinned host, not proof that full Claude Code parity has been achieved. “Conditional” means removable only if the corresponding deployment or feature is explicitly outside scope. The current full target keeps those features.

| Order and patch | Classification and smallest defensible treatment |
| --- | --- |
| 1. `hermes-hook-controls.patch` | Essential composite host change. Split conceptually into prompt admission, universal final gate, command policy, post-transform context, turn result, approve-with-modified-input, and nested dispatch identity. Stock pre-tool block/modify and observer hooks already cover some adjacent behavior, but they do not supply these timing and authority guarantees. Fold later corrective hunks into these contracts. |
| 2. `hermes-command-denial.patch` | Essential command-policy correction. Merge into the command contract in patch 1. Stock pre-tool block alone cannot provide native permission grants inside the existing safety floor ordering. |
| 3. `hermes-remote-file-staleness.patch` | Conditional on remote whole-file write safety. Generic host file-safety correction, suitable for independent upstreaming. A plugin middleware guard is potentially possible, but must reproduce backend identity, full-read coverage, redaction/truncation, page version matching, own-write baselines, and direct tool entry coverage. Moving this bookkeeping to private host imports is not a demonstrated maintenance reduction. |
| 4. `hermes-stop-effort.patch` | Essential metadata for model/effort-sensitive Stop hooks. Fold into the final-gate payload. Keep policy about LifeOS tiers in the plugin. |
| 5. `hermes-delegate-tier-routing.patch` | Conditional on per-child tier routing, required by current target. Generic per-child model/effort constructor fields. Stock global delegation config cannot represent different routes in a concurrent batch. Keep the small host plumbing; tier selection stays plugin-owned. |
| 6. `hermes-cron-worker-bootstrap.patch` | Conditional on scheduled workers in the managed source-install layout. Generic launch bug. Keep independently until an exact upstream or alternative install passes real scheduled-worker delivery. Both inspected upstream revisions still launch `sys.executable -m cron.scheduler`. |
| 7. `hermes-delegate-provider-routing.patch` | Conditional on per-child provider selection, required by current target. Merge with patch 5. The existing configured-provider credential resolver is already reused, which avoids copying provider handling into LifeOS. |
| 8. `hermes-direct-provider-inference.patch` | Mixed. Strict no-provider-fallback is a conditional host LLM capability. Its `--run-file` addition is potentially replaceable entirely by stock plugin CLI registration. A registered `hermes lifeos-infer`/`lifeos-probe` handler can invoke plugin code inside the initialized runtime. The pinned host already has `register_cli_command`, `--run-module`, and `--print-runtime-command`; direct arbitrary file execution is not required as a new host primitive. Prove installed execution before removing it. |
| 9. `hermes-stop-fail-closed.patch` | Essential final-gate correction. Merge with patches 1 and 4. Withholding must cover persistence, returned history, streaming, and budget fallback together. Disabling streaming for every gate is a current behavior tradeoff, not proof of provider-wide validation. |
| 10. `hermes-command-policy.patch` | Essential command-policy coverage for ordinary commands and review decisions. Fold into one contract and fix workspace grant scoping. Current stock observer transports cannot express this policy authority. |
| 11. `hermes-command-context.patch` | Essential target context for remote and project policy. Fold into the command contract. The current patch correctly adds context to prepared approval identity, but stored review grants still need the same scope. |
| 12. `hermes-command-rewrite.patch` | Essential at the permission-decision stage. Stock pre-tool modify handles earlier rewrites, so LifeOS should use it for PreToolUse outputs. PermissionRequest replacements still need effective-command feedback and guard reruns at this stage. Keep one generic replacement contract and bounded cycle detection. |
| 13. `hermes-session-reasons.patch` | Essential session lifecycle completion for `/resume`. Combine with patches 14 through 16. A plugin cannot reconstruct a silent host boundary reliably. |
| 14. `hermes-prompt-exit-reason.patch` | Essential for exact prompt-exit reason and empty-session identity. Combine into the lifecycle patch. Translate generic reasons to native LifeOS values in the plugin where possible. |
| 15. `hermes-empty-session-clear.patch` | Essential for finalization when no agent has yet been constructed. Fold into lifecycle changes. Stock on-session hooks do not compensate for an event that is never emitted. |
| 16. `hermes-empty-session-resume.patch` | Essential correction to patch 13's agent-presence condition. Fold directly into its final hunk; no independent feature or extension is needed. |
| 17. `hermes-permanent-policy-precedence.patch` | Essential ordering correction to the command contract. A permanent user allow must not skip explicit plugin denial. Fold into the final guard implementation. |
| 18. `hermes-policy-batch-order.patch` | Essential execution-time policy ordering when desktop batching is enabled. Keep deferral; remove the already-stock, dead `has_hook` addition immediately. |
| 19. `hermes-bypass-policy.patch` | Essential explicit-deny precedence in yolo/off modes. Fold into command policy. Also characterize internal `terminal_tool(force=True)`, which still skips `_run_approval_guards` entirely. I found that source-level bypass but did not establish an active untrusted caller, so it is a validation gap rather than a separate confirmed exploit. |

No whole patch is demonstrated to be superseded by either inspected public upstream revision. For lifecycle and remote staleness patches I did not conduct a complete current-HEAD behavioral audit, so their upstream removal status remains unverified. For hooks, delegation, cron, and auxiliary fallback, named-revision source establishes the relevant gaps directly.

## Minimal host contract

1. **Admission and final outcome:** an explicit prompt-admission result before persistence/provider calls; a final-candidate gate before user delivery and durable acceptance; a reliable terminal outcome event. Include session/turn identity, platform, effective provider/model/effort, attempt and budget state. Define callback errors, veto composition, cap behavior, streaming withholding, and cancellation. LifeOS hook names, native cap environment variables, subprocess policy and tier names belong in the plugin.
2. **Command policy:** one event after non-overridable host floors, with command and stable target identity. Results are neutral, grant, deny, review, or replacement. Define precedence once for interactive, unattended, permanent/session grants, desktop preparation and bypass modes. Replacements reenter guards and expose effective arguments to result hooks. The host owns approval persistence and execution; the plugin owns LifeOS rules.
3. **Tool and lifecycle facts:** preserve session/turn/task identity through nested local and remote dispatch; carry approved modified inputs; append context after transformations; emit finalization for real session boundaries even without an agent object. Reuse existing hook and middleware infrastructure when it provides the required timing.
4. **Child and auxiliary routes:** explicit provider/model/effort on each child, no global config mutation, host credential resolution, selected fallback policy, and effective-route evidence. Keep LifeOS inference envelopes and carrier probes in plugin CLI handlers.

Remote file safety and cron launch correctness are generic host fixes outside the plugin API. Keeping them upstream as independent fixes is preferable to maintaining copies of their internals in the plugin.

## Migration and verification sequence

1. Resolve the three policy findings with negative tests before reducing or reorganizing behavior. Preserve current explicit-deny precedence and the documented distinction between cap exhaustion and iteration-budget exhaustion.
2. Remove the proven dead `has_hook` hunk. Rerun bundle equality, clean ordered application, desktop batch tests, and the current-policy-after-earlier-command case. The saved reduced sequence already proves application compatibility.
3. Replace `--run-file` with registered plugin CLI handlers. Verify an installed plugin under the managed dependency generation, with a spaced install path, correct profile/home and interpreter, stdin and argument forwarding, text and image inference, probe checks, provider errors, and no fallback. Update both the bridge launcher and LifeOS carrier patch callers before dropping the launcher hunk. Do not remove `allow_provider_fallback=False` until an equivalent strict API exists.
4. Regenerate coherent patches from the final tree: command policy; admission/final gate/outcome; tool identity/result contracts; session lifecycle; child routing; strict auxiliary routing; remote file safety; cron bootstrap. This is an organization proposal, not an automatic authorization to restructure source. Prove byte-for-byte equality of resulting host files before calling consolidation behavior-preserving. Retain tests even where they dominate patch line count.
5. For each accepted upstream fix, select a specific Hermes revision and remove that local change only in a disposable installation. Remote safety needs read/change/write, paged and redacted reads, missing and unverifiable targets, own writes, SSH/Docker identity and concurrency cases. Cron needs a real scheduled child and delivery under the managed runtime. Child routing needs concurrent heterogeneous children and route failures. Lifecycle needs fresh/empty/nonempty sessions, resume, new/reset, prompt exit and active shutdown on CLI and gateway. Final gating needs providers, streaming consumers, durable resume and budget exhaustion.
6. Run the native effect parity ledger and package the resulting set as one tested release. Current dispatch observations for 63 of 74 registrations do not establish side-effect parity. Do not trade away remote, cron or route behavior merely to reduce the patch count.

## Tests, limits and review emphasis

The two `tests.test_patch_bundle` unit tests passed. All 19 patches apply cleanly. The reduced sequence also applies cleanly and differs only by dead code. `reproduce_review_findings.py` passed its assertions and saved `reproduction-results.json`. These probes intentionally use minimal boundary doubles and are not end-to-end tests.

I did not run the full patched Hermes suite: the available local Python environments lack pytest and the Hermes dependency set. I did not run provider, SSH, Docker, Discord, native LifeOS or gateway deployment tests. The first attempt to run the plugin bundle test from the Hermes directory failed because that test module is in the plugin repository; rerunning from the correct repository passed. Existing reported live results are documentary evidence, not newly reproduced results.

No implementation, deployment, credentials, service state, Git branch or commit was changed. I fetched public upstream objects into the disposable local upstream checkout and wrote review artifacts plus temporary source trees. Adrian's review should focus on failure semantics for required hooks, workspace scope of consent, composition of multiple final gates, and whether the proposed generic contracts preserve the exact native effects. The plugin CLI substitution is supported by source-level API evidence but still needs the installed-runtime test before removal.
