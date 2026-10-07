# Paired lifecycle effects

Date: 2026-10-03. Question: Can real native and Hermes lifecycle events provide deterministic file-effect evidence without a model answer?

The boundary probe registers a synthetic UserPromptSubmit hook that blocks the turn. Claude Code 2.1.272 and the staged Hermes CLI both emit SessionStart, UserPromptSubmit, and SessionEnd with a consistent session ID. Both exit successfully. The first native probe completes in 0.567 seconds; Hermes completes in 5.532 seconds. This supplies real lifecycle events for file-effect fixtures without inventing a model response.

Hermes sends two requests to the loopback guard during startup. Initially, their purpose is unknown. The instrumented repeat captures both bodies: `/api/show` requests contain only model metadata fields and no generation payload. The driver records these probes separately and rejects any other request. The blocked turn has zero observed model generation requests. The guard returns HTTP 401 and never supplies model output.

The initial effect run passes executable repair, reviewed freshness, settings merge, direct-edit backport, work cleanup, active-work learning, completed-work learning, and learning with concurrent cleanup. Equal output alone is insufficient: the assertions require the positive file effect, preservation of unrelated state, and successful native hook exits. The UpdateCounts fixture has no OAuth credentials, so its assertion covers only the expected no-op branch.

These controls select individual handlers in disposable synthetic homes. They do not prove the entire installed hook set under concurrent startup, all handler branches, or model and user delivery. The native handler tests supply fixture definitions; the paired runs supply the real client events. Existing production profiles on `.212` remain unchanged.

The final repeat passes all nine cases. It retains exact fixture bytes before and after execution, raw hook input, child output, real event payloads, and CLI output. All 18 CLI runs and 20 selected hook invocations exit with status zero. The evidence gate checks positive effects, event identity, invocation counts, and agreement between the ledger and the retained result. Twelve assertion and ledger regressions pass. The gate accepts the expanded inventory and artifacts, while `--require-complete` still returns status 1.
