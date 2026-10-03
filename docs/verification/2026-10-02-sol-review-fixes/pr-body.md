## Summary

This pull request adds the accumulated memory implementation, development recorder, and installation acceptance work since the last release.

The implementation adds these functions:

- Governed native fact and proposal operations, corrections, forgetting, stable references, and recoverable publication.
- A Hermes memory provider and optional Model Context Protocol (MCP) access with caller permissions.
- Authentication for the implemented native PULSE, wiki, and Knowledge read paths.
- Current-source checks for the implemented prompt, history, review, and derived-content paths.
- Owner authorization for installation finalization, managed remount, update, and recovery.
- Staged native mounting with a publication journal and restoration of previous files after interruption.
- Browser controls for prepared updates, program version restore, and interrupted-mount recovery.
- A private development recorder with correlated hook, tool, and detached-process events.

Lasting-memory ownership and external sharing remain disabled on the running test installations. The pull request does not claim full hook parity or complete memory acceptance.

## Installation and restore corrections

The detached worker loads the installed Hermes dependency environment. It receives the selected HOME, HERMES_HOME, PATH, and PULSE URL.

Dashboard mutations reject requests from another origin. Fixed installation actions reject query parameters and request bodies before they issue a grant.

Dashboard admission and detached code workers share a private installation lock. A competing action cannot create another job or owner grant. Process termination releases the lock. The transaction journal still determines whether recovery is required.

Program version restore keeps current external LifeOS user data. The snapshot records each external directory link and its physical target identity. Restore refuses replaced links or targets, changed embedded data, and later Hermes profile changes.

Restore retains replaced profile files beside each target. The snapshot records each archive path before the move. Unfinished swaps remain available for authenticated recovery.

Restore and recovery run their synchronous operations in the dashboard thread pool. The independent restore replay reduces the unrelated request delay from 822 milliseconds to 2.2 milliseconds.

Source preparation accepts the preparation branch name in a fresh output clone. It does not reset the input source repository.

The memory page and unavailable-provider message state that ownership activation is unavailable in this release.

## Memory and recorder corrections

The database opener changes the SQLite schema version only during initialization or migration. Opening the current schema preserves the database bytes.

Direct child admission checks the complete request, including generated user content.

The private recorder filters unknown environment values and their echoes. Its startup file names the private recorder configuration. Detached systemd hooks therefore use the selected capture configuration.

Completed mount operations remove temporary credential copies. Interrupted operations retain the copies required for recovery.

These readiness corrections add no Hermes or LifeOS source patch. They change plugin code, tests, and documentation. Earlier recorder corrections change private development code.

## Fresh review corrections (2026-10-02)

The final correction revision is `2c02dc5c1c59c128448fb084d0580f75190abe08`.

Restore writes durable stop intent before it stops the service. Recovery before a program swap starts and verifies the current program. It preserves later user data and profile changes. A later restore still checks the original snapshot constraints.

The dashboard reconciles dead workers with completed durable transactions. A process death after journal completion cannot leave a false interrupted status.

Apply writes its existing stopped intent before the service stop callback. The saved mount snapshot is available before this intent becomes recoverable.

Current source admission checks filenames, metadata, and admitted bodies. Private and normalized forgotten filenames stay excluded from owner responses, including records registered before these corrections.

Rejected-source diagnostics mask excluded filenames and retain safe filenames. Rejected proposals use a fixed eligibility reason instead of an exception containing a target path.

These corrections add no Hermes or LifeOS patch and no dependency. All 19 distributed patch hashes remain unchanged.

The final GPT-6.1-Sol follow-up review uses high reasoning effort. It reports no remaining actionable finding in the bounded correction paths. Its 22 selected tests and four standalone probes pass. The primary independently reruns those selections and probes.

## Final verification

| Check | Result |
| --- | --- |
| Complete Python suite at `2c02dc5` | 1,041 pass and 21 skip out of 1,062 selected cases |
| Resource warnings, failures, and errors | None in the final complete outputs |
| Private development recorder | 32 pass without skips |
| Dashboard interface | 12 pass without skips |
| Final bounded correction review | 22 pass without skips; four standalone probes pass; findings closed |
| Earlier integrated correction gate | 77 pass without skips; six earlier findings closed |
| Current provider warning and real host store flags | Four host cases pass |
| Previous live browser update and program version restore | Both pass through the actual detached worker at the earlier acceptance revision |
| Previous live interrupted native mount recovery | All eight targets regain their prior bytes and permissions |

The complete runner uses the prepared native source and treats resource warnings as errors. The final outputs contain no failures, errors, or resource warnings.

The 21 skipped cases require separate browser-tool, remote SSH, Docker, or private child-model fixtures. The skip inventory records each case and reason. These skips do not establish remote or container parity.

Earlier failed outputs remain as evidence. Their causes include temporary filesystem quota, incomplete regeneration metadata, synthetic-home isolation, missing fixture directories, an incorrect tagged installation layout, and an outdated warning assertion. The corrected cases pass before the final complete run.

The earlier integrated review closes its six findings at its recorded revision. The fresh review and its follow-ups close the additional recovery and source-label findings. The final bounded review does not claim complete hook parity or live service acceptance.

## Previous live acceptance

The separate `.212` acceptance installation runs the earlier tested runtime at `36727e5`. All 75 packaged files match that acceptance runtime.

The latest review corrections are not deployed. This correction work changes no `.212`, `.211`, or `.213` service or installation.

The real password session rejects 18 unsupported installation requests. The visible browser update control runs the actual detached worker and restarts the gateway.

The browser restore test adds a synthetic audit row after the update. Restore preserves all 321,597 audit bytes and the original file identity.

A real SIGKILL interrupts native mounting after the first published target. The visible browser recovery control restores the previous bytes and permissions for all eight targets.

The dashboard, gateway, native routes, and loopback PULSE services remain active. The existing `.212` account and both `.211` and `.213` remain unchanged.

These checks use the pinned revisions. They do not establish compatibility with a newer upstream release.

## Remaining acceptance limits

- Remaining native readers and derivatives, restricted prompt and delivery cases, and retained-session reconstruction.
- Recoverable memory ownership activation, source-review page controls, and schema rollback compatibility.
- Established-profile trials, reviewed memory import, removal, and return-to-Hermes workflows.
- Complete paired side effects for all 74 native hook registrations.
- Browser acceptance of the Hermes-extension install and restore buttons.

These items remain unavailable or unclaimed. They do not prevent review of the implemented, inactive memory components and installation corrections.

## Review guide

Start with `lifeos_hook_bridge/`, the distributed patches, and the associated tests. Most other changed files archive review and verification evidence.

Review owner authorization, action-bound grants, shared transaction ownership, publication recovery, retirement checks, and restore refusal behavior first.

The development recorder stays outside the public plugin installation package. Private runtime captures and credentials are not release artifacts. Public evidence uses synthetic acceptance data.

The current publication check finds no acceptance password or recognizable credential pattern in the new evidence. This check does not certify detection of arbitrary secrets.

The branch preserves the existing main README introduction. The readiness record describes the updated behavior and limits.

## Documentation

- [Fresh review corrections and final verification](https://github.com/0ut5ider/lifeos-hermes-plugin/blob/feature/lifeos-memory/docs/verification/2026-10-02-sol-review-fixes/README.md)
- [Final independent correction review](https://github.com/0ut5ider/lifeos-hermes-plugin/blob/feature/lifeos-memory/docs/agents/2026-10-02-sol-proposal-reason-closure/sol-proposal-reason-closure.md)
- [PR readiness and final verification](https://github.com/0ut5ider/lifeos-hermes-plugin/blob/feature/lifeos-memory/docs/verification/2026-10-02-pr-readiness/README.md)
- [Independent integrated review](https://github.com/0ut5ider/lifeos-hermes-plugin/blob/feature/lifeos-memory/docs/agents/2026-10-02-pr-ready-integrated-review/pr-ready-integrated-review.md)
- [Browser acceptance guide](https://github.com/0ut5ider/lifeos-hermes-plugin/blob/feature/lifeos-memory/docs/browser-acceptance-212.md)
- [Memory implementation and activation gates](https://github.com/0ut5ider/lifeos-hermes-plugin/blob/feature/lifeos-memory/docs/memory-implementation-plan.md)
