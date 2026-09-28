Date: 2026-09-28
Agent role: Read-only hook parity inventory reviewer
Question: What observable gaps remain against the pinned LifeOS registrations and the agreed six-point parity plan?
Model: GPT-6-Sol, high reasoning effort (runtime descriptor)

The reviewed plugin revision is `e87c2e8908949b1de988d04c65c3461a354582bf`. The public LifeOS manifest has exactly 74 registrations across 11 events. This audit read local source, existing evidence records, and official hook documentation. It ran eight disposable bridge probes with real child processes. It did not connect to `.212`, modify product code, change a host, or run the whole test suite. The matrix records the state at the start of this implementation task; concurrent fixes require fresh results before closing rows.

The installed LifeOS contract comes first. The manifest copy is `public-hooks.json`; `registrations.csv` gives all 74 entries individual IDs. Each entry currently says `unverified_paired` because no complete paired outcome dataset exists for these registrations. That does not erase the many native effect checks already documented in `docs/hook-parity.md`. Registration counts, source tests, real native hook effects, and a Claude/Hermes comparison are different evidence levels.

## Status definitions and acceptance

- **Confirmed bridge gap** means source inspection or a disposable probe establishes bridge behavior. A native Claude comparison can still be missing.
- **Unverified** means no sufficient paired installed-system result was found. It does not mean the behavior is broken.
- **Accepted difference** is limited to decisions already attributed to Adrian in the master guide and parity record.
- **Dependency** means the behavior relies on a named Hermes or LifeOS patch, service, or host capability.

Close an item only after the same synthetic action runs on pinned Claude Code 2.1.272 and Hermes with equivalent policy and model settings, and its event inputs, decisions, user/model delivery, and filesystem effects match after incidental IDs and timestamps are normalized. Record stronger Hermes denial as the accepted override. An extra approval prompt is a difference unless that override causes it. Do not use newer Claude documentation to silently expand the target beyond the 11 pinned events.

## A. Installed LifeOS registrations and the six workstreams

| ID | Workstream | Remaining observable question | Status and existing evidence | Resolution and gate |
| --- | --- | --- | --- | --- |
| A01 | 1. Checklist | Do all 74 registrations have an expected effect and paired evidence? | Unverified. Full manifest inventory exists now; existing evidence is narrative and selective. | Attach paired scenario and result paths to each CSV row. Include nested handlers invoked by PreToolGuard, PostToolObserver, and StopGates. |
| A02 | 2. Reference | Are reference settings and child effort mappings equivalent? | Unverified. `claude-reference.md` says child adapter still uses medium; Hermes uses low/medium/xhigh. | Read installed adapters and selected tier settings without credentials. Record emitted request model/effort and align the reference before inference-dependent comparisons. |
| A03 | 2. Reference | Can identical actions produce machine-comparable traces? | Missing aggregate comparison runner. Several individual native probes already exist. | Reuse synthetic workspaces; capture both traces and outcome side effects; normalize only incidental differences. Fail on missing events and extra approvals. |
| A04 | 3. Bounded fixes | Does malformed managed policy force direct-file review through the gateway? | Source fixed and regression exists. `notes/2026-09-28-invalid-managed-policy.md` explicitly lacks installed gateway probe. | Isolated installed Read and Write, with allow hook and malformed managed JSON; verify prompt and zero unapproved write. Compare native behavior separately. |
| A05 | 4. Permissions | Does Bash PermissionRequest fire at the same point? | Unverified beyond tested commands. Only narrow simple pwd/echo forms skip it. | Paired plain commands, wrappers, compound forms, session/permanent grants, policy edits, and unattended modes. Measure hook sequence and approval count. |
| A06 | 4. Permissions | Do Bash/file rules cover shell targets equivalently? | Partial. Literal readers, redirects, tee, sort output, recognized wrappers, and cd targets tested. Dynamic targets, other file openers, uncommon forms incomplete. | Table of explicit tested forms plus uncertain forms, native decision per form, and regression for each mismatch. Do not label conservative review equal to allow. |
| A07 | 4. Permissions | Are MCP rules and server trust equivalent? | Unverified; MCP PermissionRequest works but Hermes trusted-server policy differs. | Disposable MCP server and specific tool rules; compare allow/ask/deny, server wildcard, trusted/untrusted state, and later policy change. |
| A08 | 4. Permissions | Do direct Read/Write/Edit rule scopes and grants match? | Partial. Literal deny/ask, multi-target patch, remote path checks tested. Hermes guard and approval scope differ. | Paired relative/absolute, source anchors, symlink, outside workspace, new file, multi-file, and changed-policy cases. Preserve Hermes denial. |
| A09 | 4. Permissions | Does ContextReduction's native allow plus rewritten Bash input have the expected result? | Installed producer found at ContextReduction.hook.sh:111-119. Bridge rewrites arguments but does not retain PreToolUse allow. Installed effect not paired here. | Exercise an actual RTK rewrite with synthetic git/gh data; verify rewritten command is rechecked under correct policy, event timing, and approval count. |
| A10 | 4. Permissions | Are source precedence and managed-only locks equivalent? | File-based managed policy tested; other managed sources absent. Other tool rule types incomplete. | User/project/local/managed deny-ask-allow matrix; distinguish applicable Linux policy from unsupported OS/server sources. |
| A11 | 5. Lifecycle | Do ConfigChange detection, rejection, and application agree? | One-second polling, active-session lifetime, project routing, same-size rewrite, remote digest checks exist. Hermes does not apply general Claude managed settings. | Paired valid/rejected edits, multiple active projects, settings replacement, skill change, and shutdown. Record timing tolerance explicitly instead of assuming exact equality. |
| A12 | 5. Files | Are patch paths, deletion, movement, failure, and transcript readers equivalent? | Multiple real local and Docker effects verified. Successful patch expands per path; failed patch keeps original Hermes shape. Full content and unchanged context unavailable from patch input. | Paired native consumer assertions for update/add/delete/move and failed multi-file patch, including side effects and error path. |
| A13 | 5. Sessions | Are resumed history, rejected drafts, attachments, and nested events sufficient for every native reader? | Text Stop and prompt timing paired; native readers selectively checked; other transcript fields and attachment shapes unverified. | Paired reader results across resume, rejection/retry, tool failure, image-only, attachment text, and nested tool history. |
| A14 | 5. Browser | Do remaining page-content carriers reach Safety? | Navigation/snapshot/console/image metadata live tested. Vision, CDP, Browser Use scripts, dialogs unverified installed. | Real disposable loopback page triggers each available carrier, retain raw result and native Safety output. Mark unavailable carriers unverified. |
| A15 | 5. Remote | Do SSH/Docker hooks, permissions, files, and nested calls cover the target? | Opt-in trust, project command/HTTP/async, ISA, cache, and inner Read have live evidence. Distinct remote hosts, other nested tools, and several file forms unverified. | Complete target backend matrix with synthetic workspace effects; inspect trust binding and clean up resources. Other backends remain outside verified set. |
| A16 | 5. Native effects | Do every registered handler's effects work beyond selected probes? | Many native effects verified; 45 or more optional fixtures skipped in earlier suite depending environment. No complete per-registration outcome matrix. | Use registration CSV and linked notes to identify missing effects, then run real dependencies. Count fixture skips explicitly. |
| A17 | 5. Async | Are timeout, delivery, and session-finalization outcomes equivalent? | systemd and detached async survival tested; 64 KiB output cap and next-prompt delivery. Other service managers unverified. Local async path does not pass configured timeout into spool. | Paired timeout and output boundary probes; parent exit, same-session exactly-once delivery, closed-session cleanup, and async configuration update. |
| A18 | 6. Install | Does a clean distinct-root account pass real model and child calls? | Clean install mounted/loaded/prompt-hook tested; account had no model credentials. | Run pinned complete package with same model mapping, real main/child calls, native effects, and registration/installed-file hash checks. |
| A19 | 6. Updates | Can installation/update/rollback preserve synthetic user data? | `update-policy.md` says staged update and rollback automation does not yet exist. prepare_sources only prepares pinned sources. | Stage compatible triple and manifest, snapshot code/config/data separately, install as one release, induce verification failure, rollback, compare user-data hashes. |
| A20 | 6. UI | Do setup/update controls enforce the tested workflow? | Future workflow described, no demonstrated implementation in this audit. | Expose only concrete staged compatibility result and recoverable apply operation; verify API/UI failure and rollback states. |
| A21 | 6. Review | Has the completed package received independent review? | Prior Astra review found gaps; no final full-package review exists. | Review final checklist, raw paired evidence, patches, install and rollback results. Convert confirmed findings into regressions before release. |

## B. User/project extension contract within the same 11 events

These rows matter because the master guide explicitly includes user and trusted project hooks. They must not be described as failures of current installed LifeOS registrations without an actual producer or effect trace.

| ID | Behavior | Evidence and current result | Next gate |
| --- | --- | --- | --- |
| B01 | PreToolUse ask and reason | Prior independent real-child review confirms ask discarded; source still handles deny only at audit start. No ask producer found in installed public hook search. | Native paired ask, conflicting deny/allow, argument rewrite, prior approval, and installed gateway prompt. |
| B02 | SessionStart source matcher | Prior review confirms startup matcher skipped; source dispatch supplies payload source but no matcher argument. Five installed handlers have no source matcher. | Native startup/resume fixtures plus unmatched groups; preserve first prompt timing. |
| B03 | SessionEnd reason/matcher | New probe: matcher `other` does not execute. Source hardcodes `reason: other` and passes no matcher argument. Six installed handlers have no matcher. | Native paired shutdown reasons; inspect actual host reason availability before mapping. |
| B04 | Match-all and regex semantics | New probes: `*` raises `PatternError: nothing to repeat at position 0`; `Read, Write` skips Read; `^Re` skips Read; exact Read control executes and denies. Pinned manifest uses none of these forms. | Establish pinned native behavior for all examples, invalid patterns, aliases, and events without matcher support. |
| B05 | PreToolUse allow | Source processes rewrite/context but ignores allow. ContextReduction is an installed allow producer, see A09. | Define allow under accepted Hermes denial floor; compare remaining native permission evaluation. |
| B06 | PermissionRequest updated input/permissions | New real-child allow+updatedInput returns None without modification. No updatedPermissions consumer found. | Native paired argument update, persistence scope, deny reason/interruption. No installed producer established. |
| B07 | PostToolUse block reason | New probe runs hook returning block and reason; post_tool_call returns None. | Compare native model feedback; preserve already-executed tool effect. No installed producer established. |
| B08 | PostToolUse MCP output replacement | No updatedMCPToolOutput consumer found. | Real MCP result replacement pair, with generic context composition. No installed producer established. |
| B09 | Common output controls | New PreToolUse continue:false/stopReason child runs and returns None. No suppressOutput consumer found. | Native control semantics per applicable event, including user delivery and stop behavior. Installed search found continue:true, not continue:false. |
| B10 | Hook handler types | _run executes command and HTTP only; other types log and skip. Installed 74 contain those two types only. | Pin supported prompt/agent handler schema before implementation or explicit scope decision. Do not invent support from registration acceptance. |
| B11 | HTTP configuration | Local and remote URLs restricted to loopback HTTP; local request uses only Content-Type header; custom headers/env allowlists absent. | Paired supported URL/header/timeout/error forms. Installed Pulse routes fit current restricted shape. Broader trusted hooks are not verified. |
| B12 | Hook environment/input/config fields | No CLAUDE_ENV_FILE or permission_mode handling found; _payload includes event/session/transcript/cwd and limited child IDs. Managed hook registrations are not equivalent to managed permission rules. | Inventory fields actually required by pinned contract; native env persistence/input captures and managed hook inheritance. |
| B13 | Handler lifecycle fields | Timeout clamps, duplicates, once, disabled hooks, async delivery, stderr on failure need explicit paired coverage. New local async timeout observation in A17. | Verify supported pinned fields first; avoid treating newer documented features as automatic scope. |

The official documentation currently describes wildcard, comma alternatives, and regex search for matching, plus input/output control fields. Its content is not a frozen 2.1.272 specification. These observations support the need for pinned native probes; they do not replace them. Source: [Claude Code hooks reference](https://code.claude.com/docs/en/hooks), accessed 2026-09-28. No native reference process was run in this audit.

## Native reference evidence received during the audit

The parent ran pinned Claude Code reference probes and supplied `../2026-09-28-native-contract-probe/results.jsonl` and `pretool-effects.jsonl`. I read those artifacts but did not rerun the native processes. The records establish that SessionStart `startup` and `*` each ran once on startup, while the `resume` matcher did not run on startup. SessionEnd `other` and `*` each ran once with reason `other`. Thus B02, B03, and the wildcard portion of B04 now have native reference evidence. Comma and regex examples remain native-unmeasured.

The first native ask probe records one Bash permission denial, while its allow control records none. Both initial runs exited 1, so they are incomplete execution checks. A second effects probe exited 0: the allow case wrote its marker; the ask case also wrote its marker with `printf ... > effect.txt` and then denied a later `cat`. The actual file content was the requested marker even though model prose claimed otherwise. This makes observed filesystem state essential. It also means B01 cannot be reduced to an assumption that native ask always denies every action in this execution context. The parent is investigating approval timing and interactions with other hooks. These records narrow uncertainty without constituting a complete paired parity result.

## C. Accepted differences and limits that require precise wording

| Item | Classification | Required treatment |
| --- | --- | --- |
| Hermes hardline/user denial and guard floors | Accepted difference | Preserve them. Record the denial causing any otherwise different approval outcome. |
| One local model mapped by configured effort | Accepted difference | Match actual requested routes and retain real model identity. Distinct model supply and private server reasoning depth are not parity gates. |
| SSH/Docker project hooks require opt-in trust | Accepted difference | Complete live checks on those two backends; do not expand access automatically. |
| Python/Bash source hooks cannot predict computed later effects | Shared contract limit, not a bypass fix specification | Compare like actions. Current source text guard catches literal patterns; arbitrary subprocess interception would be a separate host design. |
| Terminal stdout/stderr merged by host | Current installed adaptation | EventLogger patch preserves combined output. Future hooks requiring separate streams need host support and must stay unresolved if in scope. |
| MultiEdit has no exact Hermes tool | Mapping limit | Verify native effects from per-file Edit expansion. Do not count a MultiEdit registration as literally executed in Hermes. |
| Other OS policy providers, remote backends, service managers | Unverified or unsupported platform boundary | Do not turn absent platform evidence into a universal parity claim. |
| Voice, Cloudflare, GitHub login and other external services absent from fixture | Unconfigured dependency | Keep affected effects unverified unless configured by existing authorization. |
| UpdateCounts with no Claude OAuth credentials | Verified native no-op for fixture | Do not manufacture a usage cache as a parity requirement. |

## D. Patch and installation dependencies

`patch-dependencies.json` records exact ordered patch names and SHA-256 hashes from `scripts/prepare_sources.py`. Pinned Hermes base is `758ad514eb0e800547e015edf05aa18f78b78d82`; pinned LifeOS base is `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`.

| Component | Patches | Behavior depending on them |
| --- | --- | --- |
| Hermes | hook-controls, stop-effort, stop-fail-closed | Prompt rejection, final-answer continuation/withholding, result augmentation, nested session identity, effective effort. |
| Hermes | command-denial, command-policy, command-context | Native permission verdicts, review/deny precedence, every guarded Bash command, correct workspace/backend. |
| Hermes | remote-file-staleness | Backend digest and complete-read checks before remote overwrite. |
| Hermes | delegate-tier-routing, delegate-provider-routing, direct-provider-inference | Selected child provider/model/effort and no silent route fallback. |
| Hermes | cron-worker-bootstrap | Scheduled worker dependency/runtime bootstrap used by notifications. |
| LifeOS | task-governance | Native task event and session counts. |
| LifeOS | agent-watchdog | Hermes notification route and watchdog effects. |
| LifeOS | terminal-audit, checkpoint-verification, failure-capture | Combined terminal audit, checkpoint verification, Hermes transcript failure evidence. |
| LifeOS | remote-desktop-gate, remote-isa-view | Avoid remote desktop effects; read backend digest for ISA protection. |
| LifeOS | model-rung-effort, hermes-carrier-probe | Local route classification and child carrier evidence. |

A passing patch application only proves textual applicability. Removing any patch requires installing the chosen upstream revision without it and rerunning the relevant host, native hook, and live transport checks. Pulse and Bun are real runtime dependencies. The existing `.212` symlink layout is a fixture workaround; the separate-root clean installation is the distributable layout under test. Preserve USER and MEMORY during system replacement. Current test fixture notes also identify the Research skill collision and installer placeholder substitution behavior as installer considerations.

## Artifacts and reproduction

- `commands-results.txt`: raw local source/document search commands, results, and reviewed Git identity.
- `public-hooks.json`: copied public manifest, SHA-256 `27a8578d5aec7e17a1e1584a3e1d371483913ef1bf37f618ba4de6459946180f`.
- `registrations.csv`: 74 unique registration rows, 11 events, no blanket passing status.
- `patch-dependencies.json`: pinned revisions, ordered patch files, hashes.
- `public-hook-output-search.txt`: raw producer search in the public LifeOS hook tree. This includes unregistered nested hooks, so a hit alone is not an installed event mapping.
- `probe_contract.py`, `probe-results.json`, `probe-stderr.txt`: eight disposable contract probes. Stderr is empty. Reproduce from repository root with `PYTHONPATH=. /tmp/lifeos-shell-ast/bin/python docs/agents/2026-09-28-parity-inventory/probe_contract.py`.

The probe script creates temporary roots and invokes hook processes but does not execute file tool writes. It reports observations, not expected assertions. No full suite pass, native paired match, or installed-system equivalence is claimed by this audit.
