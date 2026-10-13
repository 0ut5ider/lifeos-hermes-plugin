# Native child test log cleanup

2026-10-13, isolated managed release qualification.

The native child route assertions pass, but temporary directory cleanup sometimes fails with `Directory not empty` for its `logs` directory.

The actual Hermes QueueListener processes queued agent-close log records after AIAgent.close returns. An audit hook and a controlled writer pause reproduce the original failure through the official native test runner. The main thread removes agent.log and reaches logs directory removal. The listener thread then reopens agent.log before that removal completes.

The test drains the existing Hermes log queue after it closes both agents and before TemporaryDirectory removes the home. This change affects the test fixture only. It does not change delegation behavior or disable asynchronous logging.

The initial uncontrolled trace passes with no pending records at cleanup. The controlled trace fails the same cleanup path with one failed and seven passed tests. After the explicit drain, the controlled trace passes all eight tests. Both controls use actual agent constructors, the actual queued file handler, and the official native runner. The instrumentation changes only thread scheduling and records filesystem events. Raw traces and output are in docs/verification/2026-10-13-release-ui-install/native-logging-race.* and native-logging-race-fixed.*.
