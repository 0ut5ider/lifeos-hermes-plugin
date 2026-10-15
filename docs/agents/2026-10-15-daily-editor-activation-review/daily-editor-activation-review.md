Date: 2026-10-15
Role: Independent release deployment reviewer
Question: Can the bounded daily Pulse editor activation operator proceed after the qualified daily application and actual owner source admission?
Model: gpt-6.1-sol, high reasoning effort

## Verdict

CLEAR for the current activate_daily_editor.py after the service recovery correction. The measured P2 finding is closed. No additional measured issue remains in this narrow operator scope.

This is a pre-execution source and local control review. It does not claim that daily promotion, owner admission, editor activation, or HTTP acceptance already completed. The operator must obtain those actual prerequisites and export its actual result. The earlier public default-URL deployment CLEAR remains a separate verdict.

## Brief and boundaries

The primary requested review before executing activate_daily_editor.py. The operator must admit the actual daily verification and matching 56-skill admission receipt, verify the exact installed 0.5.0 identity, perform an authenticated owner remount, confirm prior release restoration remains unavailable, and change only modules.hermes in the existing user TOML configuration. It must preserve the morning job, retain the private previous configuration, restart the relevant services, and verify owner metadata, anonymous refusal, and sealed-file refusal.

I did not access a remote guest, memory tools, credentials, personal configuration, private maps, or personal records. I did not run the activation main function. Only review artifacts changed. The source snapshots and hashes are retained in activate_daily_editor.before.py, activate_daily_editor.after.py, and closure-source-hashes.json.

## P2 finding: Partial stop failure skipped service recovery

The initial operator called systemctl stop before entering the try/finally that starts Pulse. A nonzero stop result after a partial stop skipped recovery. The exact local AST control records only stop for that failure path.

The initial finally block also allowed a restart failure to replace an existing configuration publication failure. The local control produced CleanupFailure instead of the original publication error. That loses the measured first cause during recovery.

The preserved fail-first evidence is editor-cleanup-before.json and its stdout and stderr. Two of three desired controls failed. No guest service command ran; the subprocess and publication failure boundaries were local.

The primary moved the stop call inside the cleanup try/finally. The finally block now records the active exception, attempts start, and adds a cleanup note when an original exception already exists. It raises a restart failure when there is no original exception. The primary also flushes the private previous configuration and the destination directory.

I independently reran check_editor_cleanup.py against the current exact AST. All three controls pass:

1. A partial stop failure attempts start and retains the original stop error.
2. A configuration publication failure attempts start and retains the original publication error.
3. A publication failure followed by a start failure retains the publication error and adds a cleanup-failure note.

The current output is editor-cleanup-after.json and its stdout and stderr. The controls do not simulate an end-to-end deployment or write a guest completion receipt.

## Configuration and admission assessment

The pure enable_editor helper requires the exact expected input digest. It parses the existing TOML, requires modules.hermes to be false, changes exactly one matching flag, and compares the full parsed result against a copy with only that flag changed. The tested positive case preserves all unrelated bytes and the flag comment. The complete configuration remains the source for the output, including all job definitions.

I independently reran the primary's seven pure switch controls against the corrected source. The positive case and six refusal cases pass: changed configuration, wrong digest, already enabled, missing flag, duplicate modules table, and wrong flag type. The copied source and raw output are in switch-controls/ and switch-controls-after.stdout. The initial same seven controls also passed before the cleanup correction.

The main operator refuses missing or mismatched daily receipts and requires the matching exact package version, program commit, and archive hash through the installed hermes lifeos-version command. It validates the existing normal 07:00 morning schedule and enabled state before editing. It performs the native owner remount rather than rebinding a release journal. It requires the old operation's restore and recovery flags to remain false. The later owner mount therefore continues to protect against restoration of the earlier release program snapshot.

The operator retains a private previous configuration before publication. It checks the input again before stop and before replacement. It uses a private same-directory temporary file, flushes the new bytes, atomically replaces the target, and flushes the directory. It then starts Pulse and restarts the gateway. Afterward it requires authenticated owner metadata with 24 declared files and no-store, anonymous HTTP 401, and sealed-file HTTP 403. It does not request a personal file body or perform an editor save.

## Execution limits

The existing source review cannot prove the real host HTTP statuses, service availability, current receipt values, or output file identity. The primary must execute the operator only after actual daily acceptance and owner source admission. A PASS receipt must come from that real execution. A service restart failure can still require operator recovery, but the corrected code attempts recovery and retains the first measured exception.

The source also uses the existing hardcoded expected configuration digest. A legitimate intervening configuration edit causes refusal. That behavior protects later user changes. It is not a reason to overwrite or reset personal data.
