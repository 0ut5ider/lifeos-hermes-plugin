# PR 1 review correction gate

Date: 2026-10-02

## Scope and revision

This record resolves the fresh GPT-6.1-Sol review of PR 1. The review starts at `85c09023235fb358af18516b67bd5d012b2578ab`. The final runtime revision is `2c02dc5c1c59c128448fb084d0580f75190abe08`.

The correction changes plugin code, tests, and documentation. All 19 distributed Hermes and LifeOS patches retain their previous hashes. The prepared source identities and hashes are in [the source manifest](final/source-identity.json).

## Corrections and behavior

1. Restore writes and synchronizes its `restore_stopping` journal before it stops the service. Recovery from this state starts and verifies the current program. It preserves later user data and profile changes because no program swap has occurred. A later restore still requires the original data and profile checks.
2. Dead restore and recovery workers reconcile with a completed durable transaction. A worker that dies after the journal reaches `applied` or `rolled_back` cannot leave the dashboard reporting an unfinished action.
3. Apply records its existing `stopped` intent after it saves the mount snapshot and before it stops the service. Process death during the stop callback remains recoverable. This adjacent defect existed before the correction branch.
4. Adoption, canonical readers, and owner search validate current source paths, metadata, and admitted bodies. Private source names and normalized forgotten filename labels remain excluded, including registrations created before the correction.
5. Rejected-source diagnostics mask excluded filenames. Safe rejected filenames remain visible. Rejected proposal diagnostics use a fixed eligibility message instead of an exception that can contain a foreign target path.

The source-label result covers enabled owner preview and retrieval responses while memory ownership and sharing are disabled. It does not demonstrate model delivery or external-client behavior. A forgotten dynamic frontmatter title retains the existing canonical refusal. Operational Knowledge directory names retain their structural meaning.

## Test development and independent verification

The primary reproduced the original restore interruption and source-label findings before changes. [The primary verification record](../../agents/2026-10-02-sol-pr-fresh-review/primary-verification.md) lists the original probes and neighboring tests.

The primary adds regressions before each correction. Failed outputs remain in this directory:

- [Original restore and source-label regressions](regressions-before.txt).
- [Completed worker status regression](completion-before.txt).
- [Apply stop interruption regression](apply-before.txt).
- [Early rejected filename regression](early-rejection-before.txt).
- [Rejected proposal reason regression](proposal-reason-before.txt).

The expanded focused selection passes 90 cases without skips in [closure-final.txt](closure-final.txt). The final source-label and adoption selection passes 22 cases without skips in [proposal-reason-after.txt](proposal-reason-after.txt). These selections overlap with the complete suite. Their counts must not be added to the complete result.

The parent independently reruns the reviewer's standalone closure probes. [Restore and source-label results](primary-closures.txt) and [apply and authenticated admission results](primary-apply-closure.txt) preserve the earlier reruns.

At the final runtime revision, the parent reruns all four standalone probes again. The previously failing foreign-target assertion passes. The diagnostic matrix retains safe filenames and excludes private and forgotten filenames. The original restore, apply, and retrieval closures still pass. [The final primary manifest](final-primary-probes.json) records all four commands, exits, and the tested revision. This independently confirms the final review's probe results. The parent's final 22-case selection also matches the reviewer's test selection.

## Independent review sequence

- [Fresh review](../../agents/2026-10-02-sol-pr-fresh-review/sol-pr-fresh-review.md): two original findings.
- [First correction review](../../agents/2026-10-02-sol-review-fix-followup/sol-review-fix-followup.md): both original findings close; an adjacent apply interruption gap remains.
- [Apply closure review](../../agents/2026-10-02-sol-apply-closure/sol-apply-closure.md): the apply gap closes.
- [Diagnostic review](../../agents/2026-10-02-sol-diagnostic-closure/sol-diagnostic-closure.md): rejected filenames remain excluded; a raw proposal exception still exposes a forgotten target label.
- [Final proposal diagnostic review](../../agents/2026-10-02-sol-proposal-reason-closure/sol-proposal-reason-closure.md): the final bounded correction review.

Each report names its reviewed revision. A finding in an earlier report describes that earlier revision. The complete gate and final review determine the final result.

## Complete gate

The complete gate runs against prepared public native sources and a separate synthetic home. Resource warnings count as errors. [The command manifest](final/commands.json) records the exact commands and environment. [The detached runner](run-final.py) records each exit and a completion marker. Fixture preparation occurs synchronously before the detached test run.

The complete gate passes at the final runtime revision. [The result manifest](final-result.json) records the totals and all 21 skipped cases.

| Selection | Result | Evidence |
| --- | --- | --- |
| Complete Python suite | 1,041 pass and 21 skip out of 1,062 selected cases | [Complete output](final/regression.txt) |
| Private development recorder | 32 pass without skips | [Recorder output](final/recorder.txt) |
| Dashboard interface | 12 pass without skips | [Dashboard output](final/dashboard.txt) |
| Final bounded independent review | 22 selected tests and four standalone probes pass; no actionable finding remains | [Final review](../../agents/2026-10-02-sol-proposal-reason-closure/sol-proposal-reason-closure.md) |
| Primary independent probe verification | All four standalone probes pass at the final runtime revision | [Command manifest](final-primary-probes.json) |

All three complete commands exit 0. Their final outputs contain no failures, errors, or resource warnings. The complete Python run takes 938.814 seconds.

The 21 skipped cases require eight Docker fixtures, eleven remote workspace fixtures, one browser-tool fixture, and one private child-model configuration. The real localhost memory SSH enrollment test runs and passes. It does not establish remote workspace hook parity.

Earlier complete runs were deliberately interrupted when the next concrete correction was identified. Their partial outputs remain under `complete/`, `final-eed9bdb-superseded/`, and `final-22745d4-superseded/`. Their marker records explain the interruption. None is claimed as a completed passing gate.

## Limits and rollback

This correction does not activate lasting-memory ownership or external sharing. It does not establish full hook parity, remote workspace parity, live recovery, current browser acceptance, or compatibility with newer upstream revisions.

No server, installed plugin, service, firewall rule, credential, or GitHub permission changes during this correction. The previous isolated `.212` acceptance results remain historical. These corrections are not deployed to `.212`, `.211`, or `.213`.

The reviewer and primary use real native validation, files, and killed disposable child processes. Service callbacks, systemd liveness, and detached worker launch are isolated test boundaries. The authenticated admission probe uses an actual Hermes password session and a native owner grant, but it does not start a real service worker.

Rollback consists of reverting correction commits `30906ed`, `eed9bdb`, `22745d4`, and `2c02dc5`, then running the same gate. No external system needs rollback. Synthetic fixture homes and generated authentication files remain outside the public evidence package.
