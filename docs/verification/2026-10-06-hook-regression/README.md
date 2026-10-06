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

The complete regression sweep and any unresolved failures are recorded below
when execution finishes. These focused results do not establish full hook parity
or authorize production deployment.
