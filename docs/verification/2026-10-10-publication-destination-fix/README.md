# Publication destination correction verification

Date: 2026-10-10. Corrected code revision: `5511bbb9815e60eac1c22c0e10be12b13ef97165`.

The [targeted review](../../agents/2026-10-10-pr5-publication-targeted-review/pr5-publication-targeted-review.md) reproduces premature receipt finalization in Algorithm summaries, LocalIntelligence digests, and Conduit insights. The correction closes that finding by verifying every expected output inside the publication callback, before its committed receipt.

A destination mismatch raises a recoverable failure. The unknown SQLite receipt and recovery journal remain. Expected-digest recovery refuses to overwrite the later edit before it restores any group member.

## Failure and correction evidence

The [baseline output](before.json) contains 12 expected failures across three test methods. Its [record](before.json) retains exit status 1. Each failure concerns success or a removed journal before destination verification. The baseline contains no test setup error.

The same tests pass after the correction. They change all six output destinations at two boundaries: after the actual publisher returns, and after the actual post-write snapshot returns. They keep actual native planning, file publication, authorization, and SQLite receipts.

Each case checks refusal, an unknown receipt, and the journal. It then requires a fresh transaction to preserve the later destination and all other group members. After the synthetic test restores the operation's expected bytes, recovery returns the complete group to its original state and clears the reservation.

## Final checks

The [summary](verification-summary.json) records **166 distinct passing tests**. The three new test methods exercise **12 destination-change subcases**. These counts describe different units and must not be added.

| Gate | Result | Evidence |
| --- | --- | --- |
| after | 3 pass | [Output](after.stderr.txt), [command and hashes](after.json) |
| algorithm | 23 pass | [Output](algorithm.stderr.txt), [command and hashes](algorithm.json) |
| local | 23 pass | [Output](local.stderr.txt), [command and hashes](local.json) |
| conduit | 36 pass | [Output](conduit.stderr.txt), [command and hashes](conduit.json) |
| controls | 81 pass | [Output](controls.stderr.txt), [command and hashes](controls.json) |

All final gates have exit status 0 and no failures, errors, skips, or warnings. The summary verifies every recorded runtime and new-test hash against the corrected committed code. The exact environments use the real prepared Hermes and LifeOS source trees from the preceding publication verification.

The gates cover normal publication, source and destination conflicts, owner revocation, nested native rechecks, process death, expected-digest recovery, connector loss, standalone native operation, authenticated job requests, and job shutdown. They do not establish complete repository testing or daily deployment acceptance.

## Release boundaries

This work changes three publication callbacks and adds their destination regressions. It changes no source pin, functional patch, model tier, server, Discord configuration, ownership setting, or deployment state. The earlier two publication findings and this targeted destination finding have correction evidence.

The staged archive predates these fixes and must be rebuilt before deployment. Atlas initialization, private-channel acceptance, final package and recovery checks, and daily guest deployment remain open release gates. File recovery does not rewrite a completed native Git commit.
