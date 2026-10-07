# Complete installed hook acceptance controls

Date: 2026-10-07. Target: isolated accounts on `192.168.8.252`. Production `.212` and its Discord gateway stay unchanged.

The final candidate contains eleven Hermes patch groups and twenty-three LifeOS patches. [source-identity.json](source-identity.json) compares 1,952 native files with an independently prepared installer candidate. It finds zero differences. The [installer receipt](installation/installer-receipt.json) records the exact patch hashes and the actual pinned Bun installation. Historical controls keep their original source identities.

| Control | Actual result | Retained evidence |
| --- | --- | --- |
| Native completion and source policies | 89 passing tests, no skips | [native-completion-final.txt](native-completion-final.txt) |
| Patch regeneration and corrected source fixtures | 10 passing tests, no skips | [patch-rebuild-final.txt](patch-rebuild-final.txt) |
| Shell, file, question, child, denial, ISA, and restart workflow | Eight completed turns, two delivered child results, actual shell exit 1, one learning record, completed work, and remembered question answer after process restart | [installed-session-current8](installed-session-current8/) |
| MCP result and discovery delivery | Ordinary data, injection-shaped data, and tool discovery reach the next actual request with native Safety context | [external-delivery-current4/result.json](external-delivery-current4/result.json) |
| Managed startup delivery | One admitted HTTP 200 response; unregistered and revoked sources make zero model calls | [managed-startup-delivery-final](managed-startup-delivery-final/) |
| Native inference on Bun 1.3.14 | Actual FailureCapture, documentation correction, capability audit, and memory review responses | [native-inference-pinned/result.json](native-inference-pinned/result.json) |
| Concurrent review trigger | Eight concurrent admitted Stops and eight immediate repeats produce one actual review; proposals stay pending and the target stays unchanged | [memory-review-trigger-admitted/result.json](memory-review-trigger-admitted/result.json) |
| Unavailable review inference | Actual HTTP 401, reviewer exit 1, no proposal queue, and unchanged target | [memory-review-unavailable-current/result.json](memory-review-unavailable-current/result.json) |
| Actual request interruption and recovery | The control cancels after a conversation request reaches the relay. It preserves the completed-response cache and completes a recovery turn in a fresh process | [installed-interrupt-observed](installed-interrupt-observed/) |
| Complete native update and restore | The final hook replaces the prior hook. Mount, Doctor, source drift, service restart, and restore checks pass. Restore preserves a note written after the update | [installed-update-current8/result.json](installed-update-current8/result.json) |
| Actual service ownership and recovery | 26 tests pass without skips | [services/tests.txt](services/tests.txt) |
| Actual SSH and Docker tools | 19 tests pass without skips | [remote-tools/tests.txt](remote-tools/tests.txt) |
| Actual browser result matching | One test passes after installation of pinned fixture binaries | [browser-final.txt](browser-final.txt) |
| Isolated usage-fetch failure | Three tests pass without external authentication | [usage-final.txt](usage-final.txt) |
| Installed checkpoint, remote view, and tagged drift | Three tests pass without skips | [installed-home-controls-final.txt](installed-home-controls-final.txt) |
| Reminder component contracts | Three tests verify destination refusal, native route labels and date metadata, and interruption before acknowledgement | [reminder-component-controls.txt](reminder-component-controls.txt) |

## Interpretation

The installed settings contain all 74 registrations. Synchronous traces retain actual command exits. Detached native hooks use their real operating-system runner; parent-process command traces do not represent detached completion. The final parent trace records all five startup and all nine prompt registrations, including detached submissions. Individual asynchronous controls and actual state and request effects establish completion behavior.

The preliminary `installed-session-current6` run passes its other assertions but checks shell failure incorrectly. Its shell result requires approval and does not execute. `installed-session-current7` and `installed-session-current8` require a real exit code of 1 without pending approval. The preliminary interruption fixture also watches capability metadata before conversation admission. The final control copies the caller context into the turn thread and waits specifically for `/v1/chat/completions`.

The review recovery test reproduces two reviewer starts after an interrupted cadence write. The final admission patch stamps cadence before spawning inference and passes the same kill-and-retry test. A process killed after admission and before spawn can miss a review until the native cooldown permits another attempt. The patch does not promise exactly-once external inference.

The enabled governed reviewer produces pending proposals and cannot apply them automatically. The native reviewer reports that denied automatic application with exit code 1. The control verifies parsing, pending publication, zero applied proposals, and an unchanged target. It does not classify the whole reviewer as successful.

The update control uses the complete fresh installation and all 13 package roots, including the base root. It starts and restarts an isolated operating-system writer. The native mount and Hermes configuration checks execute the actual code. This control does not send gateway messages or migrate Discord. The selected SDK environment reports missing or outdated optional tool binaries during its configuration check. The check exits 0; the captured warning remains visible in the result.

Reminder component tests use local command acknowledgements to inspect native arguments and marker publication. They create no GitHub issues and do not establish external enabled delivery. These component controls precede the later [enabled private GitHub delivery acceptance](../reminder-delivery/README.md), which passes after Adrian authorizes the test repository. A server-side issue creation followed by a lost acknowledgement has an unknown external outcome.

Safety treats every MCP result as external content under the pinned configuration. Ordinary file reads stay neutral. Safety annotations identify the tested injection shapes; these controls do not prove detection of all prompt injection. The [native ToolSearch limitation](../../2026-10-03-hook-compatibility/README.md) and [native web and batch limitations](../../2026-10-06-hook-completion/README.md) remain explicit.

[credential-scan.json](credential-scan.json) records the export scan. The scan checks raw selected artifacts and decoded base64 payloads for the private authorization bytes. Private model configuration and credential files stay outside the export.

## Final regression and remaining gates

The [complete sweep](regression/complete-results.json) loads 2,235 tests and reports zero failures and zero errors. It skips 25 environment-dependent cases. [skip-classification.json](regression/skip-classification.json) binds every skip to a passing live rerun or the retained title-inference control with an identical source digest. The three additional reminder component cases pass separately; two of them enter the inventory after the sweep loads its suite. The 26 actual service tests run separately because the workstation reaches its inotify limit. This separation preserves service admission checks.

The first complete sweep reports three failures and two errors. Its [retained output](regression/initial-sweep/) shows child metadata expectation, missing ISA fixture dependencies, an inconsistent preparation snapshot, and patch regeneration that omitted untracked fixture files. The corrected fixtures and frozen final source pass. The dedicated browser run first fails because its required binaries are absent; pinned archive digests and [the passing browser run](browser-final.txt) establish the actual browser control. The tagged drift fixture first uses repository paths above the installed native layout. The corrected fixture tracks ten native core paths and passes [all three installed-layout controls](installed-home-controls-final.txt).

The evidence integrity check and [17 evidence contract tests](evidence-final.txt) pass. The final tracked-artifact test initially identifies seven ignored log files; the commit includes those specific retained files and the rerun passes. At the end of this sweep, the strict completion check refuses `UserPromptSubmit.3.1`, `reminders-02`, and `release-adapter-01`. The later [enabled reminder acceptance](../reminder-delivery/README.md) closes the first two gates. The current development completion check passes. The release check refuses only `release-adapter-01`. The current checklist records 151 verified scenarios out of 152. The registration matrix verifies all 74 accepted effects. It does not claim the entire release is complete.

[cleanup.json](cleanup.json) records removal of four fixture containers and the disposable loopback SSH key. The test user service manager stops after verification. Source trees and retained test data stay available for review and the remaining acceptance work. Production and model-tier configuration do not change.
