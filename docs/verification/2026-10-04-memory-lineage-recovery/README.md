# Recovery after an interrupted compression handoff

Date: 2026-10-04. The combined gate passes 165 tests and 98 subtests without skips, failures, or uncaptured warnings. The [command](regression-command.json), [result](regression-result.json), and [output](regression.txt) retain the environment. The initial focused gate passes 12 tests before the additional fork and missing-record controls.

The complete Hermes probe exits with code 73 on entry to the LifeOS rotation callback. Hermes has already committed its child. The test checks that the parent's memory admission exists and the child's admission does not. A separate process opens the actual session database, reads the child history, and attempts its next owner turn. The [initial result](before.txt) blocks that turn. The corrected [outcome](outcome.json) completes it. The [requests](requests.json) retain actual local SDK HTTP traffic across both processes.

Recovery reads the selected profile's regular private owner database in read-only mode. It checks the parent compression end stamp, the live child, the native author and destination, and the unique continuation. It uses the pinned Hermes continuation predicate. Branches, reset forks, delegated children, and tool sessions cannot become compression continuations. A delegated sibling does not make a valid continuation ambiguous.

The runtime then checks the saved parent admission against the current host context, permissions, model route, prompt, and applied proposal state. It publishes the child and its parent reference in one private admission write. It leaves the parent unchanged. A fact-only retirement preserves the stale generation until foreground history repair. An auxiliary call cannot bypass that repair.

The gate refuses multiple live continuations, unknown parents, missing admission, public or redirected databases, invalid databases, changed native authors and destinations, changed permissions, changed prompts, and missing proposal metadata. The ordinary rotation, in-place compression, resume, child-routing, backup, and source preparation controls also pass.

The [source identities](source-identities.json) bind the candidate files and pinned source revisions. The local model is a scripted protocol endpoint. This evidence establishes recovery and admission behavior. It does not measure model reasoning quality. Raw native output retains its original punctuation. This unit changes no server configuration and does not enable memory ownership.
