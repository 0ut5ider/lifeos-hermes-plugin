# Primary validation of the Opus PR review

Date: 2026-10-02

Reviewer: Claude Opus 5.5, medium effort.

Primary validator: Cerebo, Codex.

Reviewed pull request: https://github.com/0ut5ider/lifeos-hermes-plugin/pull/1

Reviewed head: `4190e9929f90f058622ce6d9cc4d64444fbbb508`.

## Review execution

The delegated run exits with status 0 and replies `DONE`. Its report and structured findings exist. The session log identifies `claude-opus-5-5` and medium effort. The result record contains no permission denials. The error stream contains no unknown-effort warning.

## Independently repeated checks

| Check | Result | Evidence |
| --- | --- | --- |
| Bounded installation and memory selection | 337 pass in 246.816 seconds, no skips or warnings | `gate.txt` |
| Development recorder | 30 pass | `development-tests.txt` |
| Dashboard interface | 11 pass | `dashboard-ui.txt` |
| Child inference and update transactions | Six pass, no skips | `children-update-tests.txt` |
| Fixture patch identity | All 19 fixture patch hashes match the reviewed source | `fixture-hashes.json` |
| Later profile edits during version restore | The guard passes, the later configuration is overwritten, and the new environment file is deleted | `repro-update-data.txt` |
| Forgotten claim in direct child inference | The full-body control refuses the claim, but the child sends it to the synthetic endpoint | `repro-child-direct.txt` |
| Recorder credential-name filtering | Four of seven synthetic credential values remain in the projected output | `repro-recorder-redaction.txt` |

The reproduction scripts run unchanged. They use synthetic data, temporary directories, and a local HTTP endpoint. No validation requires a remote server or a real model.

## Findings accepted

F1 is a confirmed restore defect. The user-data check covers the LifeOS tree but omits the Hermes mount targets. Restore deletes those current targets before it copies the saved targets. Later profile changes are not preserved.

F2 is a confirmed direct-child admission defect. The check receives only the model identifier. The request sent to the model contains system and user content that the check never sees. Ownership remains disabled on the acceptance installations, so this defect blocks later activation.

F3 is a confirmed filtering limit at the recorder function boundary. The probe does not establish that those credential names exist on a running installation. The recorder remains private development tooling.

F4 is verified by code inspection. Each mount creates a snapshot with private copies of environment and configuration files. The transaction has no cleanup for old completed snapshots. This creates a retention concern; it does not establish credential disclosure. Any cleanup policy must preserve snapshots that are still required for recovery.

## Clarification of the concurrent-write probe

The first update-data probe also reproduces a write lost from an unmanaged directory layout. That behavior predates the pull request. Governed memory uses external user-data links, which avoid that failure. It is not a new governed-memory defect.

## Remaining review limits

The review report lists components that received only a partial inspection or no inspection. This review does not establish complete source coverage or release acceptance. The full memory regression, live system services, browser, remote Secure Shell, Docker, and real-model behavior are not rerun.

The remaining concurrency and grant-expiry concerns are hypotheses. No claim of confirmation follows from the current tests.

The shared memory service returns `integrity_error`. The review uses repository evidence and does not bypass that service.

## Recommendation

Keep the pull request in draft. Correct F1 before releasing the restore control. Correct F2 before activating managed memory ownership. Add regressions for both defects and request another review of those corrections.

The review makes no implementation or server changes.
