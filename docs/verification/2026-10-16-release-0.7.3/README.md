# LifeOS 0.7.3 release and deployment

[PR38](https://github.com/0ut5ider/lifeos-hermes-plugin/pull/38) merges as 403c5f48c2e4294cc8fae62b497062a282af001d. The [stable release](https://github.com/0ut5ider/lifeos-hermes-plugin/releases/tag/v0.7.3) contains the qualified cleanup. Both servers pass installed verification.

## Exact identity

| Field | Value |
| --- | --- |
| Version | 0.7.3 |
| Program commit | 70fa8390e86c782bb47e7073c492124970ff68d1 |
| Package | 0.7.3-70fa8390.tgz |
| Package SHA-256 | 2deae5dcedfef8224959312410a5381baa91312532c968afa5534f19fd2149c8 |
| Package bytes | 288173954 |
| Hermes base | 71d34bad1045610252eda02ee79549436896e784 |
| LifeOS base | 5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c |
| Patch groups | Ten Hermes, twenty-five LifeOS |

The [initial certificate](RELEASE-CERTIFICATE.json) remains unchanged after deployment. The [new deployment asset](https://github.com/0ut5ider/lifeos-hermes-plugin/releases/download/v0.7.3/DEPLOYMENT-ACCEPTANCE.json) adds target-server results. Publication preserves all 73 prior assets. The new provenance asset preserves all 76 existing assets. Deployment publication also preserves that provenance asset. No asset replacement occurs.

The program commit is an ancestor of the source merge. Later commits add review records and clarify one test comment. All deployable runtime files are byte-identical. The test syntax tree is identical, but the packaged test file is not byte-identical to the later source. [Source equivalence](qualification/source-review-equivalence.json) records this difference. The archive README retains its prepublication stable pointer; VERSION and the certificate define its 0.7.3 identity.

## Change and independent review

The release shares dashboard requests, hook command parsing, launcher serialization, and dashboard test fixtures. It removes unused imports and preserves public memory interfaces. Contributor instructions, a codebase map, current guides, and historical indexes improve repository navigation.

All three independent Claude Opus 5.5 reviews report CLEAR: [round 1](../../agents/2026-10-16-pr38-review-r1/pr38-review-r1.md), [round 2](../../agents/2026-10-16-pr38-review-r2/pr38-review-r2.md), and [round 3](../../agents/2026-10-16-pr38-review-r3/pr38-review-r3.md). No actionable finding remains. The review receipt is an earlier phase snapshot; its pending-integration flag does not describe the later certificate or deployment.

## Qualification

| Check | Result |
| --- | --- |
| Exact-archive interface tests | 57 pass, no skips |
| Focused archive Python tests | 51 pass |
| Archive memory-module imports | 116 pass |
| Complete archive integration run | 1,129 executed, 1,126 pass in the full workstation run |
| Isolated process-boundary replay | All eight cases pass |
| Short-path backup-module replay | All 35 cases pass |
| Archive integrity | All 21,172 regular files match before and after tests |

The full run has one failure and two errors. Two process-inspection cases refuse on this workstation. All eight associated cases pass under a disposable service account. The third case creates a Unix socket below a long temporary path and reports AF_UNIX path too long. A direct replay reproduces this error. All 35 unchanged backup cases pass with a short private cache directory. This is coverage across environments, not one clean full run.

The [integration receipt](qualification/archive-integration-70fa8390.json) and [full output](qualification/archive-integration-70fa8390.stderr.gz) retain the actual result. [Boundary evidence](qualification/primary-boundary.json), [long-path reproduction](qualification/socket-path-long.txt.gz), and [short-path replay](qualification/socket-path-short.txt.gz) retain the separate checks. No product policy or assertion changes to admit these environment-specific cases.

The [first attempt and test repair](../../agents/2026-10-16-pr38-qualification-repair/pr38-qualification-repair.md) remain recorded. That attempt reports two fixture quota errors and a racy immediate process-state assertion. A real-process probe observes 12 nonterminal grandchildren in 100 runs when the direct-child wait returns. The repaired assertion polls within five seconds. A parent-only kill mutation still fails. Product cancellation code is unchanged. The corrected archive run passes the affected health and process cases.

The [program comparison](qualification/package-verification.json) confirms that Hermes and LifeOS program files, frozen Python inputs, and stock Hermes match [qualified 0.7.2](../2026-10-16-release-0.7.2/README.md). Six native Git metadata files differ. The compiled host dashboard and stylesheets remain unchanged. Their prior native installation and recovery checks remain inherited evidence.

The [supplementary provenance record](qualification/PROVENANCE.md) binds the raw integration log, replay commands and filesystems, and the complete boundary source. It names each error and failure precisely. The initial certificate remains unchanged.

## Deployment

| Installation | Address | Applied operation | Version |
| --- | --- | --- | --- |
| Development | 192.168.8.252 | 430bac1090d04a37ada7bfc88a4f25c8 | 0.7.3 |
| Daily | 192.168.8.253 | 3e74ddd455dd4211bfbd3c18606e98ed | 0.7.3 |

Development updates first. Daily updates after development verification passes. Both prepare the published archive through the public catalog. The supported service-account command-line interface applies the sealed plans. Both plans set fresh and native_mount_required to false. They do not require a native memory mount grant. No authorization check is bypassed.

The first development gateway probe still expects the superseded qualification archive identity. It refuses the installed final archive. The operator corrects that expected identity and repeats all live checks. Daily's first authenticated HTTP metadata attempt fails after the checkpoint restart. An identical retry passes before apply; the first failure's cause is not measured. All final gates pass. These operator retries do not change product source or skip admission checks.

Each guest receives a coherent local checkpoint before apply. The operator drains writers, creates the snapshot, and resumes services. The updates preserve model choices, tier mapping, unrelated configuration, credential bytes, memory configuration, and the existing owner mount journal. No personal-data import or reset occurs.

Both servers pass program integrity, selected Python runtime, active gateway/dashboard/Pulse, fresh heartbeat, connected Discord, current audience, and notification mirror-policy checks. Each server returns the expected marker through its actual private FlashNext model without tools. No Discord message is sent during deployment.

Both dashboards serve the exact archived scripts and stylesheets. Daily retains all 7 HTTP connections, including 6 enabled connections. Authenticated metadata is unchanged. Its registered HTTP Model Context Protocol connection passes status and existing project recall. The primary agent uses registered memory tools, not an owner API or direct memory-file reads, for recall.

Daily retains the enabled 0 7 * * * morning schedule. No new automatic morning observation, whole-guest restore, or installed-browser interaction replay is claimed. Automatic stylesheet loading remains inherited from 0.7.2.

The disposable qualification account and home are removed. No qualification guest is created. Prior release generations and coherent guest checkpoints remain available. The release manager checks the reviewed rollback before it restores program files.

## Known limits and evidence

The standalone development lifecycle patch still differs from the distributed patch. The managed package uses the unchanged qualified distributed patch. An empty-source ownership-activation interface path remains deferred. [TODO](../../../TODO.md) tracks both baseline limits.

- [Current progress](PROGRESS.json)
- [Package identity](package-identity.json)
- [Initial certificate](RELEASE-CERTIFICATE.json)
- [Publication receipt](release-publication.json)
- [Qualification provenance](QUALIFICATION-PROVENANCE.json)
- [Provenance publication](deployment/provenance-publication.json)
- [Deployment acceptance](deployment/DEPLOYMENT-ACCEPTANCE.json)
- [HTTP connection metadata summary](deployment/daily-http-metadata.json)
- [Safe HTTP metadata before apply](deployment/daily-http-before.json)
- [Safe HTTP metadata after apply](deployment/daily-http-after.json)
- [Registered HTTP recall](deployment/daily-registered-mcp-after.json)
