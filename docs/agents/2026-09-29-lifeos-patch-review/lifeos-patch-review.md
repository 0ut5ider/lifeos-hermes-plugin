Date: 2026-09-29
Agent role: Independent senior code reviewer
Question: Are the nine LifeOS patches correct, and can their LifeOS footprint shrink while preserving native observable behavior?
Model: gpt-6-astra

Adrian, I found two functional issues and one audit accounting issue. I do not recommend removing any whole patch from the pinned source today. Four whole patches are good candidates for upstream LifeOS changes. The largest adapter patch can become smaller if the plugin resolves model tiers and supplies a narrow, trusted carrier record to the native hook.

The review covers plugin commit `1d4929fb983dfbbd0e07dcf862e9592ef77c6c89`. The LifeOS base is `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`. A fresh `git ls-remote https://github.com/danielmiessler/LifeOS.git HEAD` returned that same LifeOS commit. I applied all nine patches, in `install_source.py` order, to a disposable local clone. All applied cleanly. They change 10 unique upstream files, with 178 added and 51 removed lines. These are source diff counts, excluding patch metadata and duplicated distribution copies.

No implementation, installed LifeOS tree, active service, model endpoint, or remote account was changed. Review scripts, raw output, and this report are the only additions in the plugin checkout.

## Findings

### P2: TaskCreated capability discovery runs unrelated creation hooks

Location: `lifeos_hook_bridge/bridge.py:1837-1840`; actual dispatch is `bridge.py:1128-1237`. The optional early return in `lifeos-task-governance.patch:18-21` protects only TaskGovernance itself.

`_supports_native_task_hook()` calls `_run("TaskCreated", payload)` with `hermes_bridge_probe: true` and no task description. `_run()` executes all matching hooks, including project and HTTP hooks. It returns a completed list, so the surrounding `any()` does not short circuit execution. A registered TaskCreated hook can therefore create an audit entry, send a notification, or perform another creation side effect once during discovery and again for the real task. An ordinary schema validator can also reject the malformed synthetic task. That rejection does not prevent the native capability result from becoming true.

Proof: `reproduce.py` registers the real patched TaskGovernance plus a real Python child process that appends its input to a disposable file. The recorder receives two events. The first has `hermes_bridge_probe: true` and no task fields; the second has the actual description and count. The native hook returns the expected capability without touching its legacy counter. See `reproductions.json:capability_probe`.

Minimal fix: probe only the recognized TaskGovernance command, or use a capability recorded from the validated installed patch manifest. Keep ordinary TaskCreated dispatch for actual tasks. Do not send the discovery payload through arbitrary registrations. A manifest approach could also remove the six-line probe branch from the LifeOS patch, but needs an explicit policy for externally installed LifeOS trees whose provenance is unknown.

### P2: Enabling repository verification retains a five-second commit deadline

Location: `lifeos_hook_bridge/patches/lifeos-checkpoint-verification.patch:31`; patched `CheckpointPerISC.hook.ts:35,86-91,209`.

The patch correctly removes `--no-verify`, but `gitRun()` still gives every Git command five seconds. A valid pre-commit suite taking six seconds is terminated. Checkpoint creation consequently fails every time it runs that suite. The new pending-state behavior avoids falsely marking the criterion committed, but does not make the commit usable.

Proof: a disposable clone with a pre-commit hook containing `sleep 6` produces `spawnSync git ETIMEDOUT`, `committed_iscs: []`, and a still-staged `checkpoint-proof.txt`. The outer native hook returns `{continue:true}` with exit zero, as designed. See `reproductions.json:checkpoint_slow_hook`.

Minimal fix: give commit verification a separate, bounded timeout that is compatible with the hook dispatch timeout. Keep fast metadata commands at five seconds. Do not disable verification. Test a successful check longer than five seconds, a real rejecting check, and retry after rejection. Also ensure timeout cleanup does not leave a verifier child running against a temporary or active repository.

### P3: Combined output byte count records UTF-16 code units

Location: `lifeos_hook_bridge/patches/lifeos-terminal-audit.patch:11`, patched `EventLogger.hook.ts:160`.

`r.output.length` is not a byte count. Native output `é🚀` is six UTF-8 bytes but the new `combined_output_bytes` field reports three. The existing stdout field has a similar upstream convention, but this patch introduces a new incorrectly named measurement.

Proof: `extra-probes.py` runs the real EventLogger in a disposable home; `extra-probes.json:unicode_audit` contains the native record and measured UTF-8 size.

Minimal fix: use `Buffer.byteLength(r.output, 'utf8')`. Add one Unicode fixture. Decide separately whether upstream wants to correct existing byte fields in the same generic audit change.

## Patch-by-patch assessment, in installation order

| Patch and diff size | Correctness and carrier dependency | Plugin-only parity and footprint recommendation |
|---|---|---|
| Task governance, +23/-11 | External count fixes the mismatch between a Hermes session and a transient Bun process parent. The native quality rule and 50-task limit still run; the plugin persists counts and reserves concurrent tasks. Safe integers and nonnegative counts are required. Native fallback retains upstream's shared `/tmp` counter limitations. The discovery issue above belongs to the integration. | A plugin can duplicate the current length and count policy, and already has fallback checks, but then future native policy changes and native hook execution diverge. Keep a small optional external session count contract. Prefer a generic `session_task_count` if upstream accepts it. Remove the native probe branch only after replacing discovery safely. No other patch textually depends on this patch. |
| Agent watchdog, +16/-8 | The `agent-starts.json` default and `subagent_type` field match the actual writer, `AgentInvocation.hook.ts:110,167-183`, at the pinned revision. These are generic bug fixes. Path overrides let concurrent Hermes sessions have separate starts and activity files. Timing overrides make the native polling behavior testable. Hermes-specific advice is selected merely by the presence of a path override, which is overly broad for a future generic API. | Keep path overrides while the native watchdog owns alert decisions. A plugin-only replacement must copy silence thresholds, cooldowns, active-agent interpretation, and delivery semantics. Redirecting `LIFEOS_DIR` to a synthetic tree could avoid path overrides, but adds a filesystem compatibility layer and still needs native filename and schema fixes. Upstream the default/schema correction. Make advice a generic optional setting or change it to carrier-neutral wording. Timing settings can remain as useful generic configuration. |
| Terminal audit, +4/-0 | Correctly names Hermes's merged stdout/stderr as combined output. The condition preserves separated streams. No Hermes core patch is intrinsically needed: the adapter must provide the response object it actually receives. Fix the Unicode accounting finding. | Mapping merged output to `stdout` would invent stream provenance. A plugin appending or rewriting audit rows would duplicate the native audit implementation and introduce ordering concerns. Keep this four-line native enhancement until upstream supports combined streams. This whole patch is a good generic upstream candidate. |
| Checkpoint verification, +15/-7 | Runs repository hooks and leaves failed criteria eligible for retry. The long subject fallback preserves the full criterion/slug lookup text in the body. Independent of Hermes. The five-second timeout now conflicts with verification. The inherited `hasChanges()` error-as-false behavior and nontransactional Git index are additional limits, not newly introduced fixes here. | A Git shim could strip `--no-verify`, but cannot cleanly repair native sidecar success bookkeeping or preserve all commit behavior. Keep native state handling. Upstream failed-checkpoint accounting and hook execution; conventional subject style is a policy choice that should be explicit. Do not drop verification to reduce lines. This whole patch can disappear only if upstream implements the required behavior or a genuinely equivalent configurable commit policy. |
| Failure capture, +16/-3 | Correctly pairs standard user-message `tool_result` blocks with assistant `tool_use` IDs instead of treating results as user conversation. Native redaction still runs before tool-call and transcript artifacts are written. Existing legacy top-level result handling is retained. Independent of Hermes core. | Rewriting the shared transcript into legacy result rows would break other native consumers and can mispair parallel tools. A private transcript just for FailureCapture is technically possible, but adds another format and preserves fewer native semantics. Keep the parser correction and upstream it. Add reverse-order results, mixed text/result rows, unknown IDs, and redaction cases. This is a whole generic upstream candidate. |
| Remote desktop gate, +4/-1 across two files | Reuses LifeOS's existing notification-channel contract to prevent Kitty persistence and tab changes during remote/headless turns. Native desktop behavior is preserved by the existing channel resolver. The plugin already sets the remote platform in `LIFEOS_NOTIFICATION_CHANNEL`; Hermes lifecycle context must identify the platform correctly. Applies to other remote carriers too. | Removing Kitty environment variables is insufficient: `tab-setter` reads per-session state and discovers a default socket. Skipping KittyEnvPersist alone misses calls to the shared tab setter from other hooks. Keep both gates; upstream the complete generic channel isolation fix. This whole patch is a good upstream candidate. Test cached terminal state, default sockets, and cmux as well as direct environment values before removal. |
| Remote ISA view, +22/-7 | Adds backend identity and content digest to native stale-write decisions while retaining local checks. Relies on the Hermes remote-file extension and private backend helpers to supply authoritative metadata. The bridge strips model-supplied metadata first. Native tests confirm changed digest blocks, reread clears, and another backend is separate. Unknown/malformed digest deliberately returns no block, so the Hermes core stale-file guard remains important. | Hermes's own stale-write rejection does not reproduce the native ISA state file, message, or decision path. A local mirror risks path/identity confusion and ordering bugs. Keep an explicit backend observation contract. Do not remove the core guard merely because this hook exists. Before generalizing, distinguish missing, unknown, and failed digest states, and bind read observations to the bytes actually read. |
| Model rung effort, +59/-13 | Preserves truthful `message.model`, extends the tail reader to effort, and classifies model/effort pairs using plugin settings. Native Claude model aliases retain priority; unknown routes remain unclassified. Requires Hermes to supply the effort actually used. It is the largest patch, about one third of added lines. Exact matching is attempted before inherited-model fallback. RUNGS is ordered Fable first, so default identical Opus/Fable xhigh routes correctly classify as Fable; I verified and rejected a contrary hypothesis. | Fabricating `claude-fable` in the transcript would corrupt native audit and AgentInvocation's inherited-model observations. Better: resolve provider/model/effort in plugin code and add a small trusted carrier record with actual model, effort, resolved rung, and optional pin to the prompt payload. The native hook then validates the rung and uses its existing policy/logging path. Preserve native transcript fallback for Claude and existing exported `liveModel()` callers. This is an adapter redesign opportunity, not a proven patch deletion. |
| Hermes carrier probe, +19/-1 | IntegrityCheck selects plugin probe checks for the real Hermes carrier and configured main route, retaining native Claude checks otherwise. Child evidence is route-bound and expires after 30 days. Main-rung checks compare provider, model, and effort. Depends on Hermes child routing and the plugin probe, not simply on transcript aliases. The subprocesses have no explicit timeout; failed or stalled provider configuration resolution needs coverage. | A separate plugin health indicator cannot satisfy native IntegrityCheck's blocking findings. Avoid forging Claude CarrierProbe evidence. Keep the two native integration points. For upstream, use a configured carrier-check command interface with argument arrays, explicit timeout, and documented result semantics rather than a Hermes-named variable and hardcoded executable. Current patch is already small; generic naming improves ownership more than line count. |

The listed nine patches modify disjoint files except the desktop patch's own two files. Their installation order is an explicit packaging contract, not a requirement caused by overlapping patch hunks. Semantic dependencies are the carrier metadata and plugin callbacks described above.

## Immediate reduction versus future reduction

On this pinned source, there is no demonstrated whole-patch deletion that preserves all native observable behavior. Moving code into Python and recreating native output is still a maintained fork, even if the upstream diff becomes empty. Do not count duplicate files under `patches/` and `lifeos_hook_bridge/patches/` twice: only the packaged sequence is applied, and tests enforce identical copies.

The first reduction to investigate is replacing TaskCreated event-wide capability discovery. A validated capability record can remove its LifeOS probe branch and fix a real bug at the same time. This needs installation/provenance tests and real project-hook tests before removal. Merely probing the native command alone fixes the side effect without shrinking the patch.

The second candidate is model-rung normalization. The plugin already owns tier routing and provider configuration. Keeping an additional tier-map interpreter in TypeScript increases the chance that inference routing and native warning policy disagree. A narrow carrier payload reduces LifeOS-specific knowledge, but the resulting diff size has not been measured. Do not quote a projected percentage reduction as an achieved result.

For upstream submission, terminal audit, failure capture, desktop isolation, and checkpoint correctness are four whole-patch candidates. Watchdog filename/schema fixes are a fifth generic change embedded in a carrier adapter. If the four whole patches land with equivalent behavior, the bundle can go from nine patches to five after advancing and validating the pinned revision. That is a conditional future reduction, not something available from today's unchanged HEAD. The checkpoint subject convention may need a generic configuration option instead of the exact local policy.

## Smallest maintainable LifeOS-facing contract

Keep the native hooks responsible for policy, observable logs, and persistent native state. The plugin should supply facts that only the carrier knows:

1. A trusted, session-owned task count, with capability discovery outside ordinary creation events.
2. Watchdog starts/activity locations, using the native active-agent schema and a carrier-neutral alert contract.
3. Accurate tool-result channels, including a combined stream when separation is unavailable, and standard transcript call/result IDs.
4. The existing notification-channel value for desktop isolation.
5. A backend file observation: stable backend identity, canonical path, explicit status, digest, and the operation whose observed content the digest represents.
6. A validated carrier observation: actual provider/model/effort, resolved semantic rung, and optional configured pin. Native policy should retain real model names in logs and use Claude fallback when no carrier record exists.
7. Configured integrity probe commands that execute in the carrier runtime and fail within a bounded deadline. Evidence must describe actual execution and invalidate on route changes.

This should be a handful of optional fields and narrow integration points, not a new framework. The task, remote-file, model, and integrity inputs should be carrier-neutral if upstream accepts them. Do not put plugin routing configuration, credential handling, Hermes process registries, or provider discovery into native LifeOS hooks.

## Verification and remaining risks

I reran 28 focused repository tests successfully against the freshly patched source: task governance, watchdog, terminal audit, failure capture, Kitty channel, model rung, carrier probe unit tests, and patch bundle equality. All 28 ran without skips. Exact command and full result are in `native-tests.txt`. FailureCapture's fixture uses a synthetic Claude executable, and carrier probe tests include stubs. These tests validate parsing and integration boundaries; they do not establish real child model execution or full carrier parity.

Additional real-process probes reproduced the two functional issues and Unicode accounting defect, verified native remote ISA blocks and refresh behavior, and confirmed default highest-tier classification. `reproduce.py`, `reproductions.json`, `extra-probes.py`, and `extra-probes.json` contain the commands and raw results. No live provider or remote backend was invoked.

Before removing or shrinking patches, require these behavior comparisons in dependency order:

1. Clean patch application, packaged-copy equality, and native Claude fallback tests against the exact candidate upstream SHA.
2. Discovery without extra TaskCreated events, valid/invalid descriptions, count 49/50, restart persistence, concurrent reservations, failed task rollback, and unrelated project-hook denials.
3. Native transcript and audit artifacts for ASCII/Unicode merged output, separated streams, multiple tool calls with reverse-order results, failures, and redaction.
4. Checkpoint success with real checks longer than five seconds, rejected checks, retry, long slugs, multiple repos, no eligible paths, and timeout cleanup. Verify both Git history and native sidecar state.
5. Remote desktop calls with direct and cached Kitty state, default socket discovery, cmux, and a real desktop positive control.
6. Real SSH/container ISA tests including local-path collisions, different backend identities, failed digest retrieval, read/edit/write, and a controlled edit between the tool read and post-tool dispatch. The current bridge calls `file_digest()` again in `post_tool_call`, so the native stored digest can describe content the read did not return. That timing concern is identified from source, not demonstrated as a current core-guard bypass; retain the core protection and test it explicitly.
7. Model and integrity comparisons across native Claude aliases, plugin pins, identical Opus/Fable routes, distinct providers sharing a model name, unknown effort, child sidechains, route changes, expired evidence, missing runtime, and stalled probes. A real child execution is required for the final probe claim.

The main review decisions are whether to adopt the narrow carrier contract, whether checkpoint commit formatting is an upstream policy or local setting, and whether native remote-file observations must fail closed when unavailable. Those decisions affect behavior and deserve review before implementation. No commits or deployments were made.
