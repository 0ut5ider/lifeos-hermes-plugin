# PR39 evidence review: 0.7.3 deployment receipts and final release claims

- Date: 2026-10-16
- Role: independent read-only evidence reviewer (no subagents, no delegation)
- Question: Do the PR39 final claims match the receipts? Do version, commit, and package identity agree? Do the deployment receipt hashes bind repository evidence correctly? Does publication preserve initial assets? Do the new local links work?
- Model: Claude Opus 5.5 (claude-opus-5-5), high
- Target: PR39 HEAD d593fb1d81ab36dedd21a427a9168694d1eb8b66 against origin/main 403c5f48c2e4294cc8fae62b497062a282af001d
- Raw data: [data.json](data.json), [github-release-v0.7.3.json](github-release-v0.7.3.json), [github-release-assets-all.json](github-release-assets-all.json)

## Verdict

NOT CLEAR. One medium defect and one low defect. Identity, publication, sequencing, links, and the stated known limits all check out.

## Actionable findings

### M1 (medium): two retained UI-asset receipts do not match the hashes in the published deployment receipt

- Binding: `docs/verification/2026-10-16-release-0.7.3/deployment/DEPLOYMENT-ACCEPTANCE.json:72` (development, `f92c30ef...`) and `:80` (daily, `840c05a2...`).
- Repository files: `deployment/development-public-ui-assets.json` hashes differently, and so does `deployment/daily-public-ui-assets.json`.
- Cause, development: I measured it. The repository copy drops the key `"origin": "http://192.168.8.252:9119"` after `archive_sha256`. Putting that key back and serializing with `json.dumps(indent=2)` plus a trailing newline gives exactly `f92c30ef...`. Every value that remains is unchanged.
- Cause, daily: not recovered. I tried an `origin` key with http or https, on 192.168.8.253, 127.0.0.1, or localhost, with every port from 1 to 65535 and with no port. None matched. The likely cause is the same removed key with a different value, such as a hostname, but that is a guess.
- Precedent: the 0.7.2 record keeps `origin` in both UI receipts, and both of its hashes match (`docs/verification/2026-10-16-release-0.7.2/deployment/development-public-ui-assets.json:7`).
- Impact: the README claim at `docs/verification/2026-10-16-release-0.7.3/README.md:65` ("Both dashboards serve the exact archived scripts and stylesheets") rests on two repository files that the immutable deployment asset does not bind. Nothing discloses the edit. These are 2 of the 21 bound hashes, and they are the only edited ones.
- Fix, two options:
  1. Restore the exact original bytes. The development value is an address the README already prints at line 54.
  2. If the daily origin must stay private, keep the redacted copies. Add a disclosed redaction note that names the removed field and records the original hash from the deployment asset.

  Do not touch the published asset.

### L1 (low): active guides still call 0.7.2 the current release record

PR39 moves the root README, `docs/README.md`, `docs/codebase.md`, `TODO.md`, and the verification index to 0.7.3. Six lines in active guides still link the 0.7.2 record as the "current release record":

- `docs/hook-parity.md:4`
- `docs/installation-workflow.md:5`
- `docs/memory-portability.md:3`
- `docs/patch-footprint.md:3`
- `docs/patch-footprint.md:58`
- `docs/update-policy.md:5`

These lines contradict `docs/README.md:31`, which names 0.7.3 as the current qualified release. A reader who starts at the installation guide lands on the superseded package identity. Fix: point these six lines at `verification/2026-10-16-release-0.7.3/README.md`. Two more lines are dated statements that stay true: `docs/clean-install.md:5` ("The published 0.7.2 package uses the distributed copy") and `:26`. They could say "0.7.2 and 0.7.3", but that is optional.

## Informational (not a defect)

### I1: some repository receipts are unbound, and two bound files are absent

- `DEPLOYMENT-ACCEPTANCE.json:83-84` binds `daily-http-after.json` and `daily-http-before.json`. Neither file is in the repository.
- The README links `deployment/daily-http-metadata.json` (line 82), and no hash binds it.
- `daily-cli-prepare.json` and `development-cli-prepare.json` are also unbound, and so are the two publication receipts. The publication receipts can't be bound, because each one postdates or records its own asset.
- The 0.7.2 record has the same pattern: the same before/after files are missing and its metadata summary is unbound. So this follows precedent and is not a regression.
- Optional: one sentence in the README saying that the raw before/after metadata stays private and that `daily-http-metadata.json` is a summary of it.

## Checks that pass

| Check | Result |
| --- | --- |
| JSON validity | All 33 JSON files under the 0.7.3 record parse |
| Receipt hash binding | 17 of 21 match; 2 DIFF (M1); 2 absent by precedent (I1) |
| Local vs GitHub digests | DEPLOYMENT-ACCEPTANCE `d52018c3...` (4866 B), QUALIFICATION-PROVENANCE `977dfb09...` (6424 B), RELEASE-CERTIFICATE `d4b002d3...` (4225 B); the downloaded bytes match the repository copies exactly (`cmp`) |
| Initial assets | Archive (id 648990111, 288173954 B, `2deae5dc...`), dashboard (`e7c93e75...`), and certificate keep their IDs and digests; no duplicate names; no clobber |
| Preservation counts | 78 assets across 15 releases, 73 of them outside v0.7.3. Assets created before each upload: 73, 76, 77, matching release-publication, provenance-publication, and deployment-publication |
| Identity agreement | VERSION 0.7.3, commit 70fa8390, archive `2deae5dc...` and 288173954 B agree across the README, package-identity, certificate, provenance, deployment acceptance, all CLI/postapply/gateway/UI receipts, the HTTP manifests, and the tag object |
| Source lineage | PR38 MERGED as 403c5f48; 70fa8390 is its ancestor; the only test change is a comment in `tests/test_memory_owner_job_processes.py` |
| Sequencing | Development checkpoint 00:24:11Z, development model reply about 00:28Z, daily checkpoint 00:54:43Z, daily model reply about 00:58Z, observed 00:59:12Z, asset 00:59:13Z. Development comes before daily |
| CLI transport | All four CLI receipts: supported-service-account-cli, fresh false, native_mount_required false, owner_grant_required false |
| Certificate immutability | The certificate is unchanged since d4456973. It keeps development/daily_promotion_verified false; the deployment receipt records PASS |
| Links | 221 relative links in the 10 changed Markdown files: 0 broken, 0 untracked, 0 bad anchors. External: PR38, the tag page, and the deployment asset URL resolve |
| Em dash | None in the changed Markdown |

## Known limits: each one is preserved in the text

- 1,126 of 1,129 cases, not one clean run: README:35, :40; PROGRESS `single_clean_full_run` false; root README:76.
- No installed-browser, automatic morning, or whole-guest restore claim: README:67; PROGRESS; DEPLOYMENT-ACCEPTANCE:55, :63-64.
- Runtime bytes match but not all packaged bytes: README:20; certificate `source_review_equivalence`.
- Daily HTTP 7/6 (0.7.2 was 5/4): README:65; daily-http-metadata.json.
- Stale development archive identity and its correction: README:59.
- Daily HTTP-before failure after the checkpoint restart, then a passing retry, cause not measured: README:59.
- CLI with native_mount_required false and no grant: README:57.

## Optional ideas (not defects)

- `README.md:18` could give the deployment-publication count (77) alongside 73 and 76.
- `docs/agents/README.md` does not index the PR38 reviews or the 0.7.3 evidence reviews. The 0.7.3 README links them directly, so nothing is lost.
- Daily `foreground_session_mirror_allowed` is false, and development's is true. 0.7.2 daily recorded the same value, so I treated it as expected.

## Scope limits

I did not inspect product code. I did not rerun the qualification audit. I did not read private cache inputs. I did not open SSH. I made no edits outside this directory. GitHub `created_at` counts show that no asset was replaced or removed. They do not prove byte stability for older releases' assets; I compared digests only for v0.7.3.
