# Review correctness fixes

Date: 2026-09-29
Scope: Correctness findings from the independent Hermes and LifeOS patch reviews.

Adrian requested the fixes before patch reduction. The implementation keeps the existing patch sequence and adds one Hermes correction patch. The LifeOS fixes update two existing patches. All packaged patch copies must match.

## Required callback failures

The Hermes admission and policy callbacks inherited optional observer failure handling. A callback could raise an exception or time out without stopping the operation. Prompt admission now uses `pre_prompt_admission`. Command approval returns a denial on callback failure. Final-answer checks return an immediate failed-turn decision. Optional `pre_llm_call` context callbacks retain their optional behavior.

Required callbacks use bounded workers in synchronous and asynchronous dispatch. Each policy invocation has an independent identity. The first concurrency test rejected one simultaneous command as already running. Independent call identities fixed that result. Timed-out callbacks remain suppressed during the existing suppression window. A late callback result cannot admit an operation that already failed. Python cannot forcibly terminate an arbitrary callback thread. Such a callback can still modify its own state after timeout.

## Review scope and final-check composition

A session review grant now covers the effective command, backend target, and normalized working directory. Local paths resolve on the host. SSH targets include host, user, and port. Docker targets use the running container identifier. Unknown remote targets cannot reuse a stored review grant. Changing only the task identifier does not invalidate a grant for the same known target and workspace. A subsequent policy denial still wins.

Final checks retain the first valid feedback message. Any valid veto that requests failure at the continuation limit retains that requirement. A callback failure fails immediately and withholds the candidate answer. This behavior is separate from the configured Claude-compatible continuation limit.

## Native LifeOS corrections

TaskGovernance capability discovery executes only the recognized installed native command. Other command and HTTP registrations do not receive a synthetic TaskCreated event. Actual task creation still dispatches the full registered event.

The checkpoint hook previously terminated a valid six-second repository check at five seconds. Verification now has a shared 20-second commit budget. Git metadata calls retain a five-second limit. An overall 25-second internal deadline stays below the registered 30-second hook deadline. Timeout sends TERM to the verifier process group, then KILL after 250 milliseconds. The tests check child cleanup, Git index-lock cleanup, failed-criterion state, and retry. This process-group cleanup is verified on Linux. Windows is not verified.

The terminal audit now measures combined output with UTF-8 byte length. The native fixture `é🚀` records six bytes instead of three UTF-16 code units. Existing separated-stream audit fields retain upstream behavior.

## Installation checks and limits

The dashboard requires the admission event before reporting complete extended hooks. Older extended hosts report partial functionality. A stock host retains the reduced profile. Users must restore an existing host patch transaction before applying the corrected complete bundle to a clean supported Hermes source. This change does not add an incremental host-patch updater.

The earlier review checkout contains partial Git objects. Cloning it failed before patch application. A complete shallow fetch of the exact supported Hermes commit supplies the installation test. The first complete checkout attempt exceeded the temporary filesystem quota. Moving the disposable fixture to the home filesystem resolved that failure. The added test file also required Git new-file metadata before the correction patch applied. No production source or running service is changed by that fixture repair.

## Verification results

- The complete plugin suite runs 389 tests. It passes with 52 environment-dependent skips. The native task, checkpoint, watchdog, audit, failure, desktop-channel, and model-rung checks run against patched LifeOS source.
- The focused Hermes suite passes 192 tests. It covers plugin dispatch, required policy failure, prompt admission, workspace review scope, Stop withholding, turn context, and desktop approval batching. The run reports one upstream SyntaxWarning in `pm/shell.py` for the `\W` escape in a docstring. That unrelated source is unchanged.
- Five source-preparation and bundle-equality tests pass without skips. All 20 Hermes patches and nine LifeOS patches apply in order. Prepared implementation files equal the files used in the behavior tests.
- One installed-plugin integration test passes against the fresh Hermes tree and native LifeOS Safety hook. It verifies neutral review, Docker guard policy without Docker execution, hardline precedence, native deny rules, permanent-allow precedence, and bypass-mode denial.
- The old host fails five of six added workspace and Stop comparison cases. The strict-first control passes. The other cases reproduce grant reuse, strict-policy ordering loss, and delayed callback-failure termination. The before log is retained.

The tests in `docs/verification/2026-09-29-review-fixes/` document the results. This correction set does not establish full 74-hook parity. Live provider, Discord, SSH, Docker, and gateway delivery tests remain separate release requirements. Servers `.211` and `.213` remain outside the deployment scope.
