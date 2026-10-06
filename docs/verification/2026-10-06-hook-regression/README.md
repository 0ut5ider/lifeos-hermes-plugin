# Hook release regression checks

Date: 2026-10-06. Product code and evidence remain on the feature branch.

The [selected hook report](../2026-10-06-hook-completion/README.md) records passing
live cases for the original 15 registration gaps. This directory retains broader
regression results and the failures found during validation.

## Patch regeneration

The prepared source test initially fails because the regeneration utility does
not assign the three new web-result classifier files to a patch group. The
utility now assigns those files to `hermes-web-result-status.patch`.

Two real Git tests pass. They generate the complete ten-patch bundle, apply it to
a clean base checkout, and compare every changed source file byte for byte with
the prepared source. The first reconstruction attempt uses `/tmp` and exceeds its
quota. The recorded passing run uses temporary files on the project filesystem.

## Installer and fresh store

The initial fresh-store run receives a patched source checkout without the
required installer candidate manifest. It reports one error and three failures.
The corrected run uses `prepare_lifeos` and `validate_prepared_lifeos` with the
actual twelve-patch bundle. All 37 checks pass. The verified candidate manifest
is retained in [installer-source-manifest.json](installer-source-manifest.json).

The 59 neighboring installer and configuration tests pass with one skip. The
initial run times out in the interrupt cancellation check. The rerun explicitly
sets the detached launcher's interrupt signal default and passes. This rerun does
not establish the cause of the initial timeout. The skipped installed-command
case requires a separate dependency generation.

The complete regression sweep and its errors are recorded below. These focused
results do not establish full hook parity or authorize production deployment.

## Complete dependency preparation

Two broader sweeps stop after incomplete fixture dependencies invalidate their
results. A direct PULSE import reports missing `smol-toml`. A separate real graph
test reports missing `graphology` from the native tools package.

The corrected fixture uses the actual native dependency wrapper to install all
twelve catalog package trees with frozen locks. It verifies the Bun version,
source package hashes, unchanged lock hashes, and every declared direct package.
All twelve installations pass. The graph test passes after this correction.
No product dependency, package manifest, or release lock changes.

[native-dependencies.json](native-dependencies.json) retains every command,
package hash, lock hash, installed direct version, and result. The candidate for
fresh-store tests remains separate and retains its verified source manifest.
The runtime source uses the complete dependency installation only for tests.

## Complete regression sweep

All 219 test modules run in four isolated processes against product revision
`2710b37`. The source bindings and commands are retained. The sweep runs 2,089
tests with zero assertion failures, three errors, and 67 skips. Two groups pass;
two groups report errors. The complete sweep is not clean.

| Error case | Observed result | Serial rerun |
| --- | --- | --- |
| Originally inactive service during ownership setup | The service barrier refuses an unstable active/inactive state. | Passes. |
| Native tools after ownership restart and return | The service barrier refuses unreviewed runtime properties. | Passes. |
| Regenerable profile backup entries | The long temporary directory makes the Unix socket path exceed the operating system limit. | Passes with a shorter temporary directory. |

[remaining-regression.txt](remaining-regression.txt) retains all three passing
serial reruns. The two original service rejections remain unresolved under
concurrent regression activity. No service admission rule changes. Stable service
acceptance remains a combined-release requirement. The socket-path error is a
fixture path constraint; no backup code change is required.

[summary.json](summary.json) gives the aggregate counts. Each `suite-N.txt` keeps
the actual test output, errors, and skips. Each `suite-N.json` gives test counts and
error case identifiers. The retained completion markers preserve nonzero exits.
These records do not convert the sweep into a passing full gate.

## Final evidence gate

The final checker review reproduces an attempted external artifact read in the
new functional-control path. The checker now verifies that path before opening
its result. A negative regression test rejects the controlled external artifact.

The final evidence, classifier, and patch-bundle gate passes 21 tests without
skips. Its output is [final-gate.txt](final-gate.txt). The registration evidence
check passes. The `--require-complete` gate still refuses complete handler parity.
The live selected hook controls remain passing. Production remains unchanged.
