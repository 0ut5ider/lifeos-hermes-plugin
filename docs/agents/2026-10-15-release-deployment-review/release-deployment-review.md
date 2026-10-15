Date: 2026-10-15
Role: Independent deployment reviewer
Question: Do the public default-URL installation, read-only completion, installation proof, daily checkpoint operator, and proposed public acceptance record make supported claims and fail closed?
Model: gpt-6.1-sol, high reasoning effort

## Verdict

CLEAR for the current reviewed deployment operators and the proposed PUBLIC-LATEST-ACCEPTANCE.json. No unresolved finding remains in this scope. The primary fixed the measured provenance and owner-renewal findings. I independently reran the current controls and checked all six evidence hashes and 20 acceptance conditions against actual safe local receipts.

This verdict does not certify daily promotion, daily editor activation, or a real model turn on the public fixture. Those operations are outside this closure. The initial release certificate remains unchanged. I did not publish an asset, run remote commands, use memory tools, read private records or credentials, edit operators, or change Git state.

## Original brief and reviewed source

The primary requested a focused review of public_ui_replay.py, verify_public_installation.py, and protect_daily.py against the previously reviewed protect_development.py. The requested concerns were unsupported evidence claims, missing admission guards, model and service preservation, and dashboard restart behavior. PR27 was already merged and the public 0.5.0 archive and initial certificate were immutable.

The reviewed product commit remains 04efe633296eb2b1a1d95561ca6d3e9516cd47dc. Its archive SHA-256 remains a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813. The deployment operators are supplementary qualification tools, not a new product build.

The exact reviewed source bytes and hashes are in reviewed-source/ and reviewed-source-sha256.json. Important locations are:

- public_ui_replay.py:25, renew_owner checks the authenticated provider and qualification-owner identity.
- public_ui_replay.py:32, wait_applied handles transport errors, expired authentication, temporary restart responses, and terminal states separately.
- public_ui_replay.py:59, run_browser provides an observer branch that reads the original operation and returns without installation or application actions.
- verify_public_installation.py:7, validate_stock_provenance binds the complete baseline and source proof to the exact fixture and public source archives.
- protect_daily.py:31, the checkpoint try/finally records the recovery obligation before drain and preserves the original error if cleanup also fails.

## Measured findings and fixes

### P2: The initial installation verifier did not bind complete stock provenance

The initial verifier checked limited baseline status and fixture metadata. It did not require the baseline Hermes commit and source archive digest or load the complete actual source proof. The initial local AST controls accepted a changed Hermes commit and a changed source archive digest while the verifier could still claim prior_stock_source_verified.

The primary added validate_stock_provenance and calls it before exporting a successful installation receipt. The helper checks strict types, exact fixture identity, the original stock baseline, the complete source and dashboard proof, all expected counts, and absence of the manager and LifeOS before installation. The exported installation receipt now binds the complete source receipt SHA-256.

Closure: the primary's 17 cases and my independent 10 cases pass against the current helper. My cases include the actual older limited source proof, which the helper now refuses. The independent 10-case suite first ran after the helper existed. It is closure evidence, not a claimed red run. The initial two changed-identity probes are the retained fail-first evidence.

### P2: The initial browser polling logic did not renew an expired owner session

The initial polling helper treated all exceptions as retryable. A local boundary probe showed that an expired 401 response could remain queued until the bounded timeout without a new owner session or useful saved HTTP status.

The primary added explicit HTTP status recording and owner renewal. The helper retries 502, 503, and 504 within a deadline. It refuses other non-200 responses. Three current controls pass: one 401 renewal followed by applied, one temporary 503 followed by applied without renewal, and refusal of a terminal failed operation.

The original live poll's exact HTTP cause remains unproven. The initial browser receipt did not retain that status. The finding concerns the measured local behavior and the missing diagnostic boundary. The report does not convert the suspected live authentication cause into a proven cause.

### P2: The first renewal fix swallowed the wrong-owner refusal

The first renewal fix called renew_owner inside the generic retry exception boundary. The local actual-function probe supplied 401, then an authenticated response for wrong-owner, then an applied response. The helper swallowed the owner assertion and accepted the later operation response.

The primary moved renewal and identity validation outside the transport GET exception handler. The current actual-helper probe refuses the wrong owner before another operation poll. The preserved before and after JSON, stdout, and stderr show the change. The before JSON was restored by the primary from the preserved original stdout after a later probe invocation overwrote that JSON. Its preserved original stdout remains the independent raw record.

### Observer completion and receipt preservation

The primary preserved public-ui-actions.json with status RUNNING and operation_state queued-apply. It contains four actual UI action responses. A separate observer authenticates a fresh qualification-owner session and reads the same operation until applied. It does not send another install or apply request.

The primary encountered an observer-attempt-4 SystemExit handler error and fixed the successful observer branch to return from run_browser. Attempt 5 has an actual UI_APPLIED receipt and process.done value 0. The public acceptance record binds attempt 5 through public-ui-readonly-completion.json. My attempted older exit probe failed during AST setup because the refactor landed before extraction. observer-exit.stderr preserves that setup failure. I do not claim that probe independently reproduced the primary's SystemExit finding.

## Current independent checks

All commands below ran locally against actual functions or safe receipt metadata. The HTTP and failure boundaries are focused unit controls. They are not simulated end-to-end acceptance and do not replace the real guest receipts.

1. The copied primary provenance suite passes one real positive and 16 refusal controls.
2. The independent provenance suite passes 10 cases, including refusal of the older limited proof.
3. The actual polling helper passes three renewal, restart, and terminal-state controls.
4. The actual renewal and polling helpers refuse the wrong authenticated owner.
5. The exact daily checkpoint try/finally passes seven failure and cleanup controls. They cover a failure before drain and partial drain, backup, and resume failures, including cleanup failure. Each applicable path attempts recovery and writes the failure marker. Cleanup retains the original exception.
6. The acceptance bundle check passes 20 conditions, including all six recorded file hashes.

The command exit codes and raw stdout and stderr are retained in current-control-results.json and the corresponding final output files. All current commands exit 0. The obsolete initial probe_deployment_gaps.py is historical characterization. Its original AST selection does not cover the new provenance helper and is not used as closure evidence.

## Proposed public acceptance record

PUBLIC-LATEST-ACCEPTANCE.json is supported by the actual safe receipts. The local check copied those input bytes to safe-inputs/ and recorded acceptance-bundle-checks.json.

The bundle establishes:

- Stock CT113 at 192.168.8.244 began with the exact unpatched Hermes source archive and dashboard archive. The complete source proof covers 18,309 regular files.
- The native web interface installed the manager from the default public GitHub URL. The request used no ref override and no force flag. The manager verification covers 21 exact files.
- The UI used a blank version field, selected latest stable 0.5.0, reviewed the exact program commit and package digest, and sent one actual apply for operation 568cd8927be849e7a92f0d048999d070.
- The four original action responses remain unchanged. The later owner-authenticated read-only observer received HTTP 200 and state applied for that exact operation. The receipt explicitly says the original observer did not complete and no duplicate apply occurred.
- The actual read-only installation verifier reports the exact active package, verifies 11 sealed program targets and the native mount, and binds the complete stock source receipt digest.
- The selected model and tiers remain preserved. The dashboard is active. The gateway and Pulse are inactive on this public fixture, consistent with the stated exclusion of owner memory activation and a real model turn.
- The initial RELEASE-CERTIFICATE.json digest remains c8a0ac35fa6f084d417951fd7538bee8f9d330ff101a9f71e3855b5da8a2dd20. It matches publication.json and the installed public certificate proof.

The field owner_session_renewed_for_readonly_completion describes the fresh authenticated observer session. It does not prove that the original poll received a 401. The acceptance record does not claim original 07:00 wall-clock execution, daily promotion, public-fixture memory activation, or a public-fixture real model turn.

## Daily checkpoint assessment

The daily checkpoint operator targets CT102 and admits the existing 0.4.3 identity before using its profile service controller. It waits for the completed whole-guest recovery prerequisite, drains writers, creates a protected snapshot backup, records the CT102 archive, and resumes services. The finally block checks actual recovery_required status, preserves an original exception when recovery fails, and writes process.done.

The diff against protect_development.py is retained in daily-vs-development-checkpoint.patch. The seven current controls find no cleanup regression. This local review does not prove a new daily backup ran or that daily 0.5.0 application completed.

## Limits and next scope

No current finding blocks publication of the proposed supplementary public acceptance asset. Publication itself is the primary's action and was not performed by this reviewer. The original certificate must remain immutable.

The next proposed daily editor activation operator is not covered by this verdict. Its review must finish before the primary executes that operator. The daily candidate operation and promotion remain separate from this completed public installation evidence.
