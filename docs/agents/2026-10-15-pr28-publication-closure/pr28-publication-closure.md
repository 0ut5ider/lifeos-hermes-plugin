Date: 2026-10-15
Role: Independent PR28 publication and metadata closure reviewer
Question: Do the final local publication records, documentation, and compressed review artifact match the approved immutable deployment evidence?
Model: GPT-6 Codex reviewer. The harness does not expose a more specific backend identifier.

# Verdict

CLEAR at HEAD `f2dd001d1a40fef469aa7d7ac98ff7aa6e1af8e8`. No actionable finding remains in this narrow publication closure. The earlier PR28 deployment review remains CLEAR at `f648f7a6`.

The new publication metadata identifies exactly the reviewed supplementary asset. All 55 prior asset records remain equal in the supplied actual before and after inventories. The final inventory contains 56 records. The only added record is `DEPLOYMENT-ACCEPTANCE.json` for `v0.5.0`.

# Brief and scope

The primary requests a final metadata closure after the successful publication. Review includes final documentation claims, candidate and source preservation, the new publication receipt, fresh native cleanup metadata, local operator resource cleanup, and lossless compression of the earlier review diff. No complete old test suite is repeated.

I use local safe records and read-only Git commands. I make no network or guest requests, memory or journal calls, personal or private-map reads, source changes, commits, pushes, publication actions, or merge actions. The only writes are these reviewer artifacts.

# Checks and results

`check_publication_metadata.py` passes with resource warnings treated as errors. Its output is preserved in `publication-metadata-checks.json` and `.stdout`; `.stderr` is empty.

1. The new asset has ID `642573776`, size 3,957 bytes, and update time `2026-10-15T03:46:58Z`.
2. Its recorded digest equals the SHA-256 of the approved local candidate: `0d6a52ae5a88f0e3874db09ccd13050fa9b0180c626112c136eb58f93f3d1478`.
3. The publication receipt names the same asset record as the sole difference between the exact supplied before and after inventories.
4. All 55 prior asset records retain every recorded field. Comparison uses each tag and asset ID as identity and compares the complete record, including name, size, digest, timestamp, and URL.
5. Every source and input digest from the previous review snapshot remains unchanged. This includes the certifier, its controls, all actual certificate inputs, the candidate, the initial release certificate, and the public installation acceptance receipt.
6. The fresh native cleanup receipt retains the protected daily archive `PBS-01:backup/ct/102/2026-10-15T03:19:34Z`, reports CT110 through CT113 absent, and reports the owned storage registration and directory absent.
7. The fresh preserved guest map equals the earlier reviewed cleanup map for CT100, CT101, CT102, CT106, and VM801, including type, name, and status.
8. The operator resource cleanup receipt reports the three owned login bridges stopped and both owned dashboard tunnels closed or already closed. It reports no user browser profile changes.
9. PROGRESS records `DEPLOYMENT_COMPLETE`, the exact published deployment digest, 55 preserved prior assets, and no new 07:00 wall-clock observation.
10. README, TODO, the full-experience release plan, and the release README now describe the completed deployment and publication. They preserve the historical automatic-observation boundary and the deferred voice, media, import, and reverse migration work.
11. `git diff origin/main --check` passes with empty output. The outputs are retained.

The first reviewer checker run assumed the inventories were top-level lists. Both actual files contain an `assets` list. The checker was corrected to read that field, then passed. This was a reviewer harness assumption and required no source or receipt change.

# Compressed artifact preservation

`initial-documentation.diff.gz` decompresses successfully. The decompressed SHA-256 is `0b07ea94f005ed5a8393db5fb93f4c19467fa48a852869f7bdbeb9a2334524fc`, which equals `initial-documentation.diff.sha256`.

The decompressed bytes also equal the complete pre-compression file retained in Git commit `23c6830b75bb0b73e97b446fd703f754088a9150`. The checker pins that commit so later commits do not change the evidence object. This confirms exact original-byte preservation, rather than only agreement with a newly written checksum. The earlier review report now references the compressed artifact. `publication-documentation.diff.gz` retains the final documentation delta reviewed in this closure.

# Limits and next action

The before and after inventories are the primary's safe records from its actual live publication check. I independently compare their contents and the approved bytes locally. I do not perform another live GitHub query or redownload the remote asset. The publication receipt, exact added inventory record, byte digest, and unchanged prior records agree.

The product remains commit `04efe633296eb2b1a1d95561ca6d3e9516cd47dc`, archive SHA-256 `a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813`. The initial certificate remains unchanged. No new product or policy work is needed for this closure.

The primary can commit these review artifacts, merge PR28 under the existing authorization, and verify the resulting merge. This report does not claim the merge already occurred.
