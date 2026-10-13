Date: 2026-10-13
Role: Independent focused service parser reviewer
Question: Does the WorkingDirectory syntax correction preserve safe fixed-service installation and recovery?
Model: gpt-6.1-sol, high reasoning effort

Reviewed committed correction: c9ada3bf705ef60e53b5ebee15fa863b5d1df52a
Comparison base: db48eb5beb92b8cec91a37e4e10e3ee186e24e77
Also reviewed: subsequent working-tree service-path validation, its test, and README scope statement.
Exact source hashes: reviewed-file-identities.json

## Result

The parser correction and the explicit supported-path boundary are clear in this focused review. No additional concrete defect remains in those changes. The real private guest retry, fresh installation, update acceptance, and complete release qualification remain separate gates.

The previous release candidates remain unpublished. I performed no guest mutation, publication, product source edit, commit, push, or memory operation.

## Actual parser verification

The corrected renderer uses an unquoted WorkingDirectory scalar. It escapes literal percent signs as %% so systemd does not expand them as specifiers. It retains separate quoted ExecStart and Environment arguments.

I ran the actual new systemd-analyze --user verify test and neighboring configuration/preparation controls. The initial committed correction passes 15 tests. After the path boundary correction, all 16 selected tests pass in 2.788 seconds. There are no skips or failures. ResourceWarning is an error. The actual parser test requires both exit zero and empty stdout/stderr.

A separate actual parser probe accepts the generated gateway, dashboard, and Pulse units for ordinary paths and a home containing a literal %h. All parser diagnostics are empty. The probe creates executable fixtures but starts no service.

## Supported path boundary

Additional bounded parser probes on the committed correction found existing renderer limitations. A home containing a literal dollar sign produces a doubled-dollar executable path that the verifier cannot find. A home containing a backslash fails the verifier's executable path rules. The initial raw probe preserves those failures in scalar-path-parser-probes.json.

Those failures came from the existing executable argument renderer, not the unquoted WorkingDirectory correction. Before boundary validation, systemd also accepts a WorkingDirectory containing spaces. The rest of the fixed-launcher inspection contract cannot safely inspect all such names. Its executable extraction excludes spaces, semicolons, and closing braces.

The primary adds a preflight boundary instead of publishing unsupported definitions. Fresh preview and service_files now require absolute physical home, profile, and native installation paths. They refuse whitespace, characters below ASCII 32, dollar signs, single/double quotes, backslashes, semicolons, and closing braces. Literal percent signs remain supported through specifier escaping.

The final probe confirms that ordinary and percent paths pass the actual parser. Space, dollar, backslash, semicolon, and closing-brace cases refuse before any generated service file exists. The regression checks every home/profile/installed field and eight unsupported character cases. The README states the restricted supported scope.

This narrower scope is deliberate. It matches the existing Linux fixed-launcher contract. It does not claim support for arbitrary filesystem names or foreground dashboard lifecycle.

## Planned activation and recovery

The follow-up does not change activation or recovery behavior. Newly created gateway/Pulse unit definitions remain inactive and disabled. Existing accepted local unit bytes remain retained in the reviewed program transaction. The managed first-install dashboard still drains through its separate journal while the worker runs in its own systemd unit.

Post-publication verification reloads the user manager and inspects the three-role binding. The actual guest trial reported by the primary demonstrates why this live gate matters: string comparisons alone did not detect the invalid quoted WorkingDirectory. I did not independently run that guest trial in this review.

The caught-error dashboard-return helper still finishes only the already admitted program phase or verifies untouched prepared programs before it resumes a verified dashboard runtime. It preserves later edits by refusal. Abrupt exits, invalid configuration, or tampering can still require external recovery. This parser correction does not make a missing installed manager directory recoverable through the ordinary public plugin command.

The README now states the important distinction: the retained public command can recover only when the installed manager can load. If the manager directory is absent, the operator must use the retained qualified worker and reviewed journal. Replacing the missing directory or erasing the operation is not an accepted recovery method.

## Correction to the round 2 report

The round 2 report incorrectly described an exploratory pre-quiesce reload helper as present in its final reviewed head. That helper was removed after the actual identical-republication probe disproved its hypothesized necessity. The round 2 source hashes and committed diff were accurate; that prose was stale.

I corrected both affected paragraphs and added a dated explanation to the round 2 report. Its original text remains in pr18-release-ui-review-2-before-prose-correction.md. The current worker performs daemon-reload in post-publication verification. It does not contain the exploratory helper.

## Raw data

- followup.diff: committed db48-to-c9 correction, test, README, and note.
- path-boundary.diff: reviewed subsequent service-path boundary and regression.
- reviewed-file-identities.json: exact inspected source hashes.
- python.stdout/python.stderr: initial 15-test run.
- final-python.stdout/final-python.stderr: corrected 16-test run.
- scalar-path-parser-probes.json: actual ordinary/special-path parser results before the boundary.
- scalar_path_parser_probes.py: repeatable renderer/parser probe.
- final_scalar_path_probe.py and final-scalar-path-probe.json: actual parser acceptance and refusal after the boundary.
- final-scalar-path-probe.stderr: empty final probe diagnostics.

The controls establish component syntax and bounded input behavior. They do not establish browser, conversational, fresh guest, update, or release certificate acceptance.
