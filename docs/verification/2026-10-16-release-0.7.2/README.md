# LifeOS 0.7.2 release qualification

The qualified program commit is `b257d29f81fa2b88d202da72914b778d4eda3bb5`. The archive is `0.7.2-b257d29f.tgz`, with SHA-256 `293cfa2c6593b597c327fb8ad11f458d3e374352552dfbe7f4dbba5cd7e67265`. Its size is 288,201,691 bytes.

The [independent PR36 review](../../agents/2026-10-16-pr36-review-r1/pr36-review-r1.md) reports CLEAR after one P3 evidence correction. The correction removes trailing whitespace from a saved failing test log. The reviewer verifies the correction and repeats all 42 interface tests. No product file changes after review. The [review equivalence receipt](review-equivalence.json) binds the reviewed program inputs to the exact archive.

Both plugins declare their own scoped stylesheet. The interface separates address setup, permissions, sign-in requests, and connected agents. The release page separates preparation, operation review, and advanced ownership controls. The [interface record](../2026-10-16-plugin-setup-ui/README.md) gives the screenshots and compiled-host inspection limits.

## Exact-package checks

All 42 interface component and Software Development Kit contract tests pass from the exact package. The 1,124-case archive integration run passes 1,122 cases on the workstation. One error and one failure refuse executable inspection of the unrelated non-dumpable `sshd-session` process. These are the same named cases recorded during 0.7.1 qualification.

All eight exact-archive process-boundary cases pass again under the isolated stock guest service account. The [boundary receipt](process-boundary.json) binds their test and program source hashes. No assertion or product policy changes. This is coverage across two environments, not one clean full run.

The integration gate verifies the archive file map before and after execution. All 21,170 archived regular files retain their bytes and required modes. Generated test bytecode and the existing bytecode guard metadata remain separate from archived files. No unhandled diagnostic occurs.

The [package comparison](package-verification.json) verifies that every backend program, both native program trees, the frozen Python closure, and stock Hermes match qualified 0.7.1. The changed program files are the two interface bundles, their stylesheets, their dashboard manifests, and plugin version declarations. Earlier installed update, rollback, HTTP, notification, and recovery gates remain inherited 0.7.1 evidence. No new automatic morning run or whole-guest restore is claimed.

The [initial qualification certificate](RELEASE-CERTIFICATE.json) records this scope and the exact archive identity. Publication must preserve that certificate and all prior release assets.

## Qualification guest

The owned guest starts from the retained synthetic stock baseline. Its messaging and Pulse services are masked before first boot. It receives the exact archived boundary-test sources and Bun 1.4.3. The tests use synthetic profiles and services. They do not use a production profile.

The [cleanup receipt](guest-cleanup.json) verifies graceful shutdown, removal, and unchanged power states for all original guests, including VM801. The initial cleanup check does not immediately observe stopped status in the aggregate inventory. The resumed operator verifies stopped status directly before removal and waits for inventory convergence. No host restart occurs.

## Promotion state

At this qualification checkpoint, neither installed server changes. Development `.252` must complete its owner-reviewed update and verification before daily `.253`. Both retain their qualified 0.7.1 packages until their respective updates complete. The existing daily HTTP grants, model choices, memory configuration, and normal morning schedule form part of the promotion baseline.
