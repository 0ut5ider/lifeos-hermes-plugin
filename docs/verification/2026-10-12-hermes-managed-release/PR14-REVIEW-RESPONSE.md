# PR14 review response

Date: 2026-10-12. Program commit: c801feef00744ed8eb5d23b5e21da49706518351.

Three independent review rounds establish eight actionable findings. All eight findings are resolved. The third reviewer reports no unresolved finding. The captured final fix diff exactly matches the committed fix. Read pr14-review-clear.json for the binding hashes.

| Finding | Result | Verification |
|---|---|---|
| A coordinator exits before launch recording, or a stale worker removes a successor grant | Recovery requires free launch and execution locks. Admission validates before grant cleanup. | Actual fork exit, process locks, private grants, and a stale action |
| An older manager omits required command targets | The qualified candidate builds the plan. Execution compares the complete candidate target map before service work. | Historical 0deb335e manager archive and real plan refusal |
| A later native mount expires an earlier rollback | Status hides expired rollback. Admission checks the bound retained native snapshot before service work. | Two actual governed Bun mounts |
| Restore admission uses an undefined profile | Admission uses the recorded selected profile. | Actual public admission and re-admission after early refusal |
| Native prior copies are missing or changed | Status and preflight validate bounded private prior copies and recorded digests. | Actual governed mount, missing copy, and corrupted copy |
| A delayed failure report overwrites a successor admission | Failure publication and grant cleanup remain inside the execution lock. | Actual fork paused at failure publication |
| Early recovery refusal prevents repair and retry | Queued recovery retains recovery_required. Early rollback refusal retains applied. | Actual governed refusal, exact repair, and public re-admission |
| Recovery detects program damage after native mutation | Recovery checks native targets and required prior program copies before mutation or service interruption. | Actual governed worker, missing program copy, and later native edit |

The primary agent repeats 67 focused tests and 31 operation/program tests. Both runs pass without skips. The primary agent also repeats the real governed recovery probes. Missing native copies, missing program copies, and later native edits refuse before configuration or journal mutation. Exact repair permits public re-admission. The reviewer repeats 14 real catalog, staging, and authenticated HTTP boundary checks.

The older coordinator result establishes safe refusal. It does not establish a successful update through an older incompatible planner. Install the qualified manager before preparing the next complete release.

Final frozen package acceptance is recorded separately. The package certificate remains private and test_fixture_only. No public production qualification, immutable 0.3.1 asset replacement, or daily server deployment occurs in this PR workflow.

Raw diff and terminal installation artifacts are stored as lossless gzip archives. Decompress each .gz file to its recorded raw path for replay. raw-review-artifact-archives.json records both hashes. The original raw files remain available in the local workspace.
