# LifeOS 0.4.0 release qualification

The exact complete package is qualified. Publication follows PR15 merge.
The program commit is `a87e7ae94894dabc3651454d1334cb23c4fae27e`.
The archive is `0.4.0-a87e7ae9.tgz`, with 119,131,156 bytes.
Its SHA-256 is `82acd3da141ef5aad322b49f30a8306305c298fa6706d44cc320de54f76442da`.
The release uses Hermes v0.21.7 at `71d34bad1045610252eda02ee79549436896e784`, LifeOS at `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`, and Bun 1.4.3.
Ten Hermes patch groups and twenty-five LifeOS patch groups remain.
All twelve native dependency locks retain their upstream bytes.

| Gate | Actual result | Receipt |
|---|---|---|
| Frozen integration | 625 checks pass | `integration-sealed-a87e7ae9.json` |
| Official Hermes runner | 716 tests across 38 files pass | `native-sealed-a87e7ae9.json` |
| Fresh public plugin commands and actual interrupted installation | Pass; exit 73 at directory-retained; later synthetic data preserved | `fresh-install-a87e7ae9-bunfixed.json` |
| Installed interrupted update | Actual exit 73 at programs-published; exact 0.3.1 recovered | `development-bunfixed-interruption-exit.json`, `development-bunfixed-interruption-recovery.json` |
| Authenticated normal update | Exact package, model mapping, aliases, and services pass | `development-bunfixed-update.json` |
| Actual reboot | Exact package; three services start automatically; zero restarts | `development-bunfixed-boot.json` |
| Off-server whole-guest restoration | Three Atlas recovery cases pass | `whole-guest-recovery.json` |
| Restored programs | All 143 targets and native mount targets verify | `whole-guest-program-coverage.json` |
| Disposable guest cleanup | Guest 110 removed | `whole-guest-controller.json` |
| Authenticated normal rollback | Exact prior 0.3.1; configuration and model mapping preserved; services running | `development-bunfixed-rollback.json` |
| Certificate prerequisite regression | All 29 cases pass; actual historical interruption receipt refuses | `exit-binding-after.stdout`, `primary-exit-review-closure.stdout` |
| Independent focused review | Clear; primary repeats probes and confirms reviewed file bytes | `../../agents/2026-10-12-pr15-exit-proof-review/pr15-exit-proof-review.md` |

The protected development backup is `PBS-01:backup/ct/101/2026-10-13T00:43:38Z`.
The successful restore takes 3,831.084 seconds and verifies coherent live and archived Atlas groups.
Networking is removed and all application services are masked before the disposable guest boots.
The controller removes only its disconnected guest after successful verification.
The first restore is intentionally cancelled before the inadequate one-hour limit. Proxmox removes its partial guest and volume.
The reviewed controller retry reuses the successful backup and permits two hours only for `pct restore`.
`restore-ceiling-adjustment.json` preserves that procedure. The cancellation is not a product failure.

The first rollback request supplies an empty JSON body and refuses HTTP 400 without effects.
The corrected bodyless owner request passes HTTP 200 and the actual worker completes restoration.
`development-normal-rollback-admission.json` records both results.

The Bun 1.3.14 extraction failures and the mixed-timezone fixture failure remain historical evidence.
The corrected Bun 1.4.3 archive passes the cold preparation checks.
The integration runner supplies UTC to direct and governed fixtures. Product assertions and package bytes remain unchanged.
See `EXTRACTION-INVESTIGATION.md` and `TIMEZONE-INVESTIGATION.md`.

`RELEASE-CERTIFICATE.json` binds the exact archive, dashboard, native source, runtime, and completed qualification receipts.
The build manifest remains its immutable build-time checkpoint. The certificate records subsequent qualification.
Fixture certificates remain private and must not become release assets.
Existing 0.3.1 assets remain immutable.

Public GitHub installation and the default stable update path are the next publication checks.
The daily guest `.253` remains on accepted 0.3.1. No personal data is imported or reset.
The main development profile has native memory ownership disabled; its owner dashboard review is not a native memory grant test.
The prior managed-memory acceptance remains in the managed release record.
Voice, media processing, and the Pulse core-file editor remain deferred in `../../../TODO.md`.
