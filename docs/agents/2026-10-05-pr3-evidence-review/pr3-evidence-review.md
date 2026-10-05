# PR #3 evidence and test review

- Date: 2026-10-05
- Role: independent evidence and test reviewer (read-only)
- Model: Claude Opus (claude-opus-5-5)
- Target: PR #3, branch `feature/hook-compatibility-evidence`, head `71987ce`, base `origin/main`
- Question: Do the paired driver, `check_pair`, the per-unit collectors, and the ledger establish that the LifeOS hooks behave the same under real Claude Code 2.1.272 and under Hermes? Where do the checks, normalizations, driver, or tests let a real difference through, or fail to support a README claim?

## Method

1. I read all content through `git archive 71987ce` into `/tmp/pr3full` and `/tmp/pr3clean`. I did not read the working tree, with one exception. The raw captures that `.gitignore` excludes (`*.jsonl`, `*.log`) exist only in the working tree. I copied those 162 files to `/tmp` and confirmed that every one matches the SHA-256 that the ledger at `71987ce` records, so they are the same bytes the ledger refers to.
2. I ran `scripts/check_hook_evidence.py` on a clean checkout, and again with the 162 ignored files added.
3. I ran `paired_lifecycle_effects.py check` on every `paired-results.json`.
4. I ran the three unit test modules (91 tests, all pass).
5. I wrote my own recomputation scripts that do not import the driver. They are in this folder with their output.

Files in this folder:

| File | Content |
| --- | --- |
| `check-hook-evidence-clean-checkout.txt` | Checker output on a clean `71987ce` checkout: 162 missing artifacts, exit 1 |
| `check-hook-evidence-with-ignored-raw.txt` | Same checker with the ignored raw files added: passes |
| `recompute.py`, `recompute-output.txt` | Independent recomputation of 10 cases from raw captures: 76 checks, 0 mismatches |
| `consistency.py`, `consistency-output.txt` | All 106 client records vs `result.json`, state files, raw hashes: 0 issues |
| `raw_diff.py`, `raw-diff-output.txt` | Raw cross-client diff of every changed file, after normalizing session, home path, timestamps |
| `hook_source_pairs.py`, `hook-source-pairs-output.txt` | Selected hook source digest per side per case |
| `source_skew.py`, `source-skew-output.txt` | Native reference programs vs prepared Hermes LifeOS source |

## Findings, most severe first

### F1. Six units do not contain their raw captures in Git, so the ledger check fails on the PR head (confirmed, high)

- Where: `.gitignore` lines `*.log` and `*.jsonl`. Affected units: `paired-atlas-hints`, `paired-file-hints`, `paired-isa-render`, `paired-pre-tool-guard`, `paired-tool-log`, `paired-version-drift`.
- Statement: `hooks.jsonl`, `cli.log`, `fixture-events.jsonl`, and `atlas-events.jsonl` for these six units are listed in `docs/parity/handler-effects.json` `artifacts` with hashes, but `.gitignore` excludes them and no commit force-adds them. The earlier units (feedback, format-contract, time-context, response-cache, context-response, and the 10-03/10-04 units) do have them committed.
- Evidence: `python3 scripts/check_hook_evidence.py` on a clean `git archive 71987ce` prints 162 `missing or external artifact` lines and exits 1 (`check-hook-evidence-clean-checkout.txt`). The same check passes only when the ignored working-tree files are present.
- Wrong pass or fail: On the author's machine the checker passes, so the author sees green. Anyone else (a reviewer, CI, a later agent after a fresh clone) gets a failure, or worse, cannot re-verify the six units at all. Four READMEs make claims that are false for the committed tree: isa-render and version-drift say "Raw synthetic logs and file captures remain in this bundle"; atlas-hints and file-hints say "Each client folder retains its raw `atlas-events.jsonl`".
- Why no test caught it: no test or CI job runs `check_evidence` on the real ledger. `tests/test_hook_evidence.py` uses synthetic ledgers only.

### F2. 13 of the 50 new ledger cases ran a different hook program on each side; READMEs describe them as the same hook (confirmed, high for the parity claim)

- Where: `result.json` `hook_definitions[].source_files` per client; `hook-source-pairs-output.txt`.
- Statement: The native side runs hooks from `/home/lifeos-claude-ref/.claude` (the reference install). The Hermes side runs hooks from the prepared source `/var/tmp/lifeos-paired-context-response-20261005/lifeos`. For these cases the selected hook digest differs between the sides:
  - `format-contract-*` (5 cases): `DriftReminder.hook.ts` 4a7e48a1 vs 3c92fa45. No `lifeos-*.patch` touches this file.
  - `file-hint-*` (3 cases): `ConfigEvalFire.hook.ts` 999dcaa0 vs 74c70121. No patch touches this file.
  - `tool-log-success`, `tool-log-failure`: `EventLogger.hook.ts` bed11b45 vs c2b454d3. Explained by `lifeos-terminal-audit.patch`.
  - `context-response-*` (3 cases): `LoadContext.hook.ts` and two readback libraries. Explained by `lifeos-memory-access.patch`.
  - `isa-render-*` (6 cases): the selected hook matches, but the detached renderer `LIFEOS/TOOLS/ISARender.ts` that writes the page is symlinked from each side's own source, differs between sides, and is not pinned in `source_files`.
- Scale: of 269 native reference programs that also exist in the prepared source, 82 differ. Patches explain 51. 31 differ with no patch, including `DriftReminder`, `ConfigEvalFire`, `ISARender.ts`, `Safety`, `PromptProcessing`, `FormatGate` (`source-skew-output.txt`). My best guess is that the reference install and the prepared base (`5e2f2e8c`) are different LifeOS versions. I did not confirm the cause.
- README wording: format-contract says "Five cases run the actual `DriftReminder.hook.ts` through Claude Code 2.1.272 and Hermes"; file-hints says "exercise the native AtlasEventCapture and ConfigEvalFire hooks"; tool-log says "the native EventLogger". Only `runtime-check.json` in file-hints and tool-log records the two digests (`selected_hook_sha256`), with no comment. format-contract and context-response record no per-side selected digest at all.
- Wrong pass or fail: A pass here means "unpatched-or-other-version hook under Claude Code" and "patched-or-other-version hook under Hermes" produce equal summaries for the selected inputs. That does not show that the plugin runs the native hook faithfully, and a client difference can be masked by a compensating source difference (F3 shows EventLogger is exactly this case). Conversely, a version skew could cause a failure that is blamed on the client. Neither `check_pair` nor `check_hook_evidence` compares the per-side source digests.

### F3. The summary hides real data differences in the tool-log unit; the ledger marks the effect as verified (confirmed, medium-high)

- Where: `paired_lifecycle_effects.py` lines 627-635 (`summarize`, `ground_truth_command_matches`, `error_names_exit_code`); `raw-diff-output.txt` tool-log section.
- Statement: The raw files differ in content that the effect description covers, but the summary keeps only booleans:
  - `tool-log-success` `tool-activity.jsonl` `ground_truth`: native writes `stdout_preview`, `stdout_bytes`, `stderr_preview`. Hermes writes `combined_output_preview`, `combined_output_bytes`, `exit_code`. Any consumer that reads `stdout_preview` gets nothing under Hermes. `check_pair` compares only `ground_truth.command`.
  - `tool-log-failure` `tool-failures.jsonl` `error`: native `"Exit code 2\nls: cannot access 'pair-missing-tool-log': No such file or directory"`; Hermes `"exit 2"`. The stderr diagnostic is lost under Hermes. The check is `'2' in str(row.get('error'))` (line 635), so it passes. The ledger row `PostToolUseFailure.1.1` says "Write the native tool-failure audit row with the actual tool and error", and its status is `paired_case_verified`.
- Wrong pass: both cases above pass now. Also, the `'2' in` check passes for any error text with the digit 2 in it (for example `exit 127 at 2026-...`).
- The tool-log README does not mention either difference.

### F4. The comparison is a whitelist, so extra writes and unchecked effects are invisible (confirmed, medium)

- Where: `check_pair` line 321 compares only the dicts that `state_snapshot` builds; no raw file-set comparison exists.
- Statement: Any file that a client writes outside the whitelisted fields does not affect the result.
- Concrete evidence from `raw-diff-output.txt`:
  - Every Hermes run writes `LIFEOS/MEMORY/STATE/hermes-transcripts/<session>.jsonl`. Native runs do not. Probably intended plugin behavior, but no check would notice if a client wrote something harmful there.
  - In feedback cases the hook also updates `work.json` and `work-events.jsonl` (the `__pulse_strip` rating). The driver checks neither file. They happen to match (only epoch-ms timestamps differ).
  - `summarize` (line 627) builds a set of tuples, so duplicate rows collapse. `tool-failures.jsonl` has no row-count check in the driver. A client that writes the failure row twice passes `check_pair`. The tool-log `collect.py` (line 128, `row,=`) would catch it, but only on the fixture host.
- The READMEs say "equal selected state", which is accurate but easy to read as "equal state".

### F5. A README claim that the fixture cannot observe: "not to PostToolUse" (confirmed, medium-low)

- Where: `make_fixture` lines 973-977; tool-log README "Both clients route it to PostToolUseFailure and not to PostToolUse."
- Statement: The failure fixture registers hooks only for `PostToolUseFailure` (plus the observer events). The committed `settings.json` for both sides has no `PostToolUse` key. If a client fired PostToolUse in addition to PostToolUseFailure for the failed call, nothing records it.
- Wrong pass: a client that fires both events passes `tool-log-failure`.

### F6. Tautological or vacuous sub-checks (confirmed, low)

- `time-context-*` before-state (lines 552-554): `state_snapshot` returns `clock_timezone(case)` and `case == 'time-context-async-utc'` without reading the fixture. The `before` comparison in `check_pair` (lines 399, 404) can never fail. The same applies to `drift_before`'s `asynchronous` field (line 694).
- `tool-log-failure` `tool_output_in_model: False`: the command `ls pair-missing-tool-log` cannot print `PAIR_TOOL_LOG`, so this expectation cannot fail.
- `guard-bash-*` `project_files: []`: no command writes into the project, and `plutil` is not on a Linux host, so this is always empty. The real "did not run" evidence is the missing `PAIR_GUARD_OUTPUT` marker, which is a good, discriminating check.
- `file-hint-write-plain` `hints_current`: `all()` over zero rows is always true.
- ConfigEvalFire (`PostToolUse.8.4`, `9.4`) is `paired_case_verified` with only the no-op branch exercised. The effect "ran, exited 0, printed nothing, wrote no state" is also what a hook that ignores its input would produce. The ledger `remaining` field discloses the missing branches, so this is a status-semantics issue, not hidden.
- `tier-route-wire`: `run.py` line 43 maps every tier to the same model `lifecycle-fixture`, and the relay overwrites `model` anyway, so the unit cannot detect a wrong tier-to-model route. Its `sonnet` row cannot tell "map applied" from "caller effort passed through", because both are `medium`. `verify.py` checks against a hard-coded copy of the same `MAPPING` that `run.py` injects through `LIFEOS_MODEL_TIER_MAP`. The README is honest about scope ("explicit tier map"), and haiku, opus, and fable do discriminate.
- `paired_response_server.py` line 62 records `actual_model=model`, the relay's configured value, not a value from the upstream response. The name suggests an upstream observation.

### F7. Driver failure modes that crash the run instead of recording a failure (confirmed by reading, low)

- `state_snapshot` time-context branch, line 559: if the invalid-zone hook emitted a clock on one client (a real behavioral difference), `ZoneInfo('PAIR_INVALID_ZONE')` raises `ZoneInfoNotFoundError`. The run aborts and no paired record exists for that case or later cases.
- Lines 680, 704, 717: `json.loads(stdout)` on hook stdout with no empty-stdout guard for isa-render and format-contract. An empty or non-JSON stdout on one side crashes the run.
- None of these produce a wrong pass. The runner writes a non-zero `run.done`. But the evidence of the difference is a traceback, not a recorded failed case.

### F8. Detached ISA renderer: "no page" is sampled with no settle time (plausible, low)

- Where: `run_side` lines 1263-1266 wait up to 30 s only when the expected page is `rendered`.
- Statement: The hook returns in about 20 ms and a detached process writes the page (README: "the detached native renderer"). For the three `absent` cases the driver samples immediately after client exit.
- Wrong pass: a client or hook version that wrongly spawns the renderer for first-authoring would write the page after the snapshot and still pass. The `skipped` log row partly guards this, if the hook (not the renderer) writes that row. I could not check which process writes the row, because the hook source is not in this repository.

### F9. Model-delivery claims cannot be re-verified from the repository (confirmed, disclosed, low)

- `model_context_contains`, `model_received_block`, `model_received_loop_alert`, `tool_output_in_model`, `clock_context_in_model`, `model_nag_present`, and `model_contract_present` come from full request bodies in `requests-private.json`, which stay outside Git. `collect.py` scripts read `/var/tmp` sources, host home roots, and the private bodies, so they run only on the fixture host. The proof JSON files hold hashes and booleans. A reviewer must trust them. The READMEs disclose that bodies are private, but "independently reads the raw captures" describes a one-time host step, not something a reader can repeat.

## Answers to the five questions

### 1. Do the assertions establish the README claims?

Mostly yes, for the selected effects as summarized. My recomputation of 10 cases from raw captures (`feedback-low-rating`, `format-contract-violations`, `time-context-sync-toronto`, `response-cache-limit`, `version-drift-aged`, `tool-log-repeat`, `atlas-bash-multiple`, `guard-bash-plutil-block`, `isa-render-first-authoring`, `file-hint-edit-gear`) gives 76 checks and 0 mismatches. That includes the exact contract string, the 72-hour tag age, the Toronto clock (`Mon 2026-10-05 10:48 EDT (morning)`, inside the client interval), the 2000-character cache prefix of 13,099 and 14,031 character Stop messages, and the third-call loop alert.

Unsupported or misleading claims: F1 (raw captures "remain in this bundle"), F2 ("the actual DriftReminder.hook.ts" and "native" hooks, when the Hermes side runs a different program), F3 (failure row "with the actual error"), F5 ("not to PostToolUse"). Vacuous sub-checks are in F6. Real differences that pass are in F3 and F4.

Strong points worth keeping: the `PAIR_%s` marker trick (the command text cannot contain the output marker), the exact-string expectations for DriftReminder and VersionDrift, timestamps checked against the actual client interval instead of being ignored, and the hard-coded expected values, which are independent of the hook code.

### 2. Do the normalizations hide real differences?

| Normalization | Justified? | Disclosed? | Hides a real difference here? |
| --- | --- | --- | --- |
| Absolute paths to relative or boolean | Yes, the homes differ per uid | Yes (isa-render) | No |
| Session ID to `session_matches` | Yes | No | Hermes IDs (`20261005_181859_2d040a`) are not UUIDs. LifeOS files are keyed by session ID (`loop-detector/<id>.json`, `isa-render-debounce/<id>.json`). A consumer that expects UUID format is untested. Plausible, not observed. |
| Timestamps to "inside client interval" | Yes, and stronger than ignoring them | Yes | No |
| "At least N" calls (repeat and file cases) | Yes, the model picks the call count | Yes (tool-log, file-hints) | Partly. Some sub-checks use only the first N calls (`commands_match`, loop `tools`, `failed`, `one_signature`), so extra calls are not validated. This run had exactly N calls on both sides. |
| Final answer only "nonempty" for feedback, format, time, drift, file-hint | Yes, LLM prose differs | Yes in most READMEs. format-contract does not say it. | No |
| Field whitelist summary | Partly | Only as "selected state" | Yes: F3 and F4 |

### 3. Driver and collector bugs

F1 (artifact retention), F5 (unobservable event), F7 (crash paths), F8 (settle race), and the duplicate-collapsing `summarize` in F4. I checked these and found no problem:
- Trace appends use `O_APPEND` and `flock`, so there is no interleaving.
- The `observed_ids` repeat logic rejects uneven per-hook counts.
- The paired-results, result.json, before-state, and after-state records are all consistent with each other and with the raw hashes (106 of 106).
- The ledger outcomes equal `result.json` for all recomputed cases.
- One minor point: the driver and collectors classify generation requests differently (`path != '/api/show'` vs `path.startswith('/v1/')`). I found no case where this matters.

### 4. Is the ledger consistent with the raw results?

Yes, for every case I checked, once the ignored raw files are present (see the recompute output and the consistency output). The ledger `native` and `hermes` blocks are copies of the paired record. `check_lifecycle_case` re-runs the current `check_pair`, which validates expectations but not raw-to-summary derivation. My recomputation covers that derivation for 10 cases across 10 units. On a clean checkout the ledger is not verifiable for 6 units (F1).

### 5. What do the unit tests cover?

`tests/test_paired_lifecycle_effects.py` is mostly hand-built after-state dicts fed to `check_pair`, usually with the native and Hermes sides deep-copied from each other. Those tests show that `check_pair` rejects a wrong summary. They cannot catch a measurement bug in the driver.

Beyond that, the tests cover some `make_fixture` layout (settings, matchers, async flags, before-state) and three after-state measurements: `feedback-rating`, `version-drift-recent`, and `isa-render-existing-page`.

Untested:
- All of `run_side`: generation filtering, user-response extraction from both CLI formats, every `model_*` and `tool_output_in_model` computation from wire bodies, the `observed_ids` repeat logic, the render wait loop, and the exit-code expectations.
- `state_snapshot(after=True)` for tool-log, file-hint, atlas, guard, time-context (clock regex, day periods, interval truncation), format-contract, response-cache, and context.
- `check_evidence` on the real ledger (this would have caught F1).
- The `collect.py` scripts and `tier-route-wire/verify.py`.
- Any assertion that the two sides ran the same hook source (this would have surfaced F2).

## What I did not get to

- I did not read the hook sources. They are not in this repository, so I could not diff the two DriftReminder and ConfigEvalFire versions or confirm who writes the ISA render log row.
- I did not read every `collect.py` in full. I read tool-log fully and skimmed the others through their READMEs and proofs.
- I did not review `fresh-store-status` or `capability-validation` beyond their claims. Both are unit-test transcripts with no command lines or test IDs. Their numeric claims (59 tests OK; 16 critical of 62 findings; 13/2/1 locations) match the retained outputs.
- I did not review the 2026-10-03 and 2026-10-04 units that the ledger also cites. They pass the current `check_pair`. Their raw files are committed.
- I did not run any client. All conclusions come from retained artifacts.
