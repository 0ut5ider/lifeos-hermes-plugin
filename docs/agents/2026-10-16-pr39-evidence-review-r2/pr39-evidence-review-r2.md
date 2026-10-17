# PR39 evidence review, round 2: follow-up on M1, L1, I1

- Date: 2026-10-16
- Role: independent read-only follow-up evidence reviewer (no subagents, no delegation)
- Question: Does PR39 HEAD fa45a11b resolve the prior findings M1, L1, and I1 without a new defect, and without a change to the immutable deployment asset, initial certificate, or provenance receipt?
- Model: Claude Opus 5.5 (claude-opus-5-5), high
- Head: fa45a11b3d5c5b1c31d87ece88c3c2344d5c57f3 ("docs(release): preserve exact receipt bytes"), parent d593fb1d
- Prior review: [pr39-evidence-review.md](../2026-10-16-pr39-evidence-review/pr39-evidence-review.md)
- Raw data: [data.json](data.json), [link-check.json](link-check.json), [check_links.py](check_links.py)

## Verdict

CLEAR. No actionable findings.

## Per-finding resolution

### M1: RESOLVED

- `deployment/development-public-ui-assets.json` adds one line, `"origin": "http://192.168.8.252:9119"`, after `archive_sha256`. SHA-256 is now `f92c30ef...` (1590 B). This matches the bound hash in `DEPLOYMENT-ACCEPTANCE.json`.
- `deployment/daily-public-ui-assets.json` adds one line, `"origin": "https://lifeos-daily.tail682dd.ts.net"`, at the same position. SHA-256 is now `840c05a2...` (1596 B). This matches the bound hash.
- No other line changes in either file.
- The daily origin name was already tracked before this fix. At d593fb1d it appears in `docs/verification/2026-10-16-release-0.7.2/deployment/daily-public-ui-assets.json:7`. The fix does not add a new disclosure.

### L1: RESOLVED

All six lines now link `verification/2026-10-16-release-0.7.3/README.md`: `docs/hook-parity.md:4`, `docs/installation-workflow.md:5`, `docs/memory-portability.md:3`, `docs/patch-footprint.md:3`, `docs/patch-footprint.md:58`, `docs/update-policy.md:5`. A grep for "current release record" or "current qualified" outside `docs/agents/` finds no other active pointer to an older release. The remaining hits are in `docs/history/` and are dated. `docs/memory-portability.md:68` says "the current release record above", which now refers to 0.7.3. The optional `docs/clean-install.md:5,26` wording about 0.7.2 is unchanged. The prior review marked it optional.

### I1: RESOLVED

- `deployment/daily-http-before.json` is present (646 B) and matches the bound hash `2aca9bf2...`.
- `deployment/daily-http-after.json` is present (645 B) and matches the bound hash `3ea1a1d5...`.
- Both files carry `personal_records_read: false` and `credential_values_exported: false`. They contain no token or secret. Their URLs use the daily Tailscale name that was already tracked.
- The before file shows manifests at 0.7.2, and the after file shows manifests at 0.7.3. Both show 7 connections with 6 enabled. This agrees with `daily-http-metadata.json` and with README:65 ("Authenticated metadata is unchanged").
- README:82-84 relabels the summary link and adds links to both files.

## Checks

| Check | Command | Result |
| --- | --- | --- |
| Bound receipts | python3 -I: sha256 of `git show fa45a11b:<path>` for each `receipt_sha256` entry; also compare the worktree | 21 of 21 MATCH; worktree identical to HEAD for all 21 |
| Immutable files unchanged by the fix | `git diff --stat d593fb1d fa45a11b -- DEPLOYMENT-ACCEPTANCE.json RELEASE-CERTIFICATE.json QUALIFICATION-PROVENANCE.json` | empty |
| Certificate unchanged since publication commit | `git diff --stat d4456973 fa45a11b -- RELEASE-CERTIFICATE.json` | empty |
| Local digests at HEAD | `git show fa45a11b:<file> \| sha256sum; wc -c` | DEPLOYMENT-ACCEPTANCE `d52018c3...` 4866 B; RELEASE-CERTIFICATE `d4b002d3...` 4225 B; QUALIFICATION-PROVENANCE `977dfb09...` 6424 B |
| Published assets unchanged | `gh api repos/0ut5ider/lifeos-hermes-plugin/releases/tags/v0.7.3` | 5 assets; IDs, sizes, digests, and created_at are identical to round 1; the three receipt digests equal the local digests |
| Fix scope | `git diff --name-status d593fb1d fa45a11b` | 14 files: 4 prior-review artifacts added, 5 guide lines, the 0.7.3 README, 2 new HTTP receipts, 2 one-line UI receipt edits. No published asset or immutable receipt touched |
| JSON validity | `python3 -I -m json.tool` on the 4 changed or new JSON files | all parse |
| Local links | `python3 -I check_links.py` on the 6 changed Markdown files | 165 relative links, 0 broken, 0 untracked, 0 bad anchors |
| Em dash | `git grep -c U+2014` in the 0.7.3 record; checker count in the changed Markdown | 0 |
| Worktree state | `git diff --quiet fa45a11b -- <record and guides>` | worktree matches HEAD |

## Scope limits

I did not repeat the qualification audit. I did not inspect product code, servers, private cache inputs, memory, or credentials. I used no SSH. I made no edits outside this directory. I did not download the release assets again in this round. The GitHub API digests match the local bytes, and round 1 compared the downloaded bytes with `cmp`.
