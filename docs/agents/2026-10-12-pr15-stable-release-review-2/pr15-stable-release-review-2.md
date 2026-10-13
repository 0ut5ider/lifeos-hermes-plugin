Date: 2026-10-12
Agent role: Independent read-only qualification closure reviewer, Cerebo
Question: Does commit 2a9c4a76 close PR15's qualification receipt binding finding without changing the sealed program archive or public installation behavior?
Model: gpt-6.1-sol, high reasoning effort.

Adrian, the prior P2 finding is closed in the reviewed code. This focused review has no unresolved actionable finding. Qualification still requires the actual identity-bound native repeat, whole-guest restore, normal rollback, and public asset verification. The synthetic regression fixtures do not complete those gates.

The reviewed head is 2a9c4a76f35fb516747d7898ff0c6baded113ae4. The PR15 base remains be215380dcbda35c92e6f28b23b4a1d7bc15004e. The closure diff compares the generator and native runner to original reviewed head 8e804cc8e1b8727e0517ccdfa91b261c5d91f062. The immutable program commit remains a87e7ae94894dabc3651454d1334cb23c4fae27e.

The generator now requires the integration receipt's package_commit to equal the build head. It requires the fresh preparation version, commit, and package_sha256 to equal the build identity. The native receipt must identify the package commit, archive hash, source manifest hash, source tree hash, unchanged archived source files, Bun version, and Bun binary hash. The generator reads the native source manifest directly from the verified immutable archive and compares the native receipt with that manifest. The certificate also contains SHA-256 values for all twelve qualification receipt and test-output files.

I independently run the thirteen-case regression against both generators. The corrected generator passes: its synthetic complete baseline emits a certificate, and all twelve incomplete or mismatched cases refuse. The original generator fails the regression with AssertionError: Certificate accepts mismatched qualification evidence. The original output shows the stale integration and mismatched fresh/native cases accepted. Both raw results and exit codes are retained. The original failure is the expected characterization of the fixed defect, not an unresolved test failure.

I also repeat the original measured reproduction against the correction. To reach the individual binding checks, this probe supplies explicitly labeled synthetic future gates and native identity fields only inside temporary directories. Replacing the current integration receipt and stderr with the actual historical passing 4644f90c receipts now exits one and writes no certificate. Setting fresh.preparation.package_sha256 to zeroes also exits one and writes no certificate. The synthetic complete baseline exits zero. Its twelve published receipt digests equal the actual copied receipt and output bytes. Untouched current evidence refuses certification because its native receipt lacks the newly required package_commit. All probe certificates remain temporary and are removed with their fixture directories.

The native runner records identity from a new extraction of the verified immutable archive rather than the previously contaminated cached extraction. It validates the native source before the official runner starts. It captures the source manifest and all original file hashes before testing, uses a new private HOME, supplies UTC, disables file retries, and places the qualified Bun directory first on PATH. It checks the actual executable version and fixed binary digest before the run. After the official runner returns, it verifies that every original source file still exists with the same bytes before it publishes the identity-bound receipt. The program archive and original cached package are read-only inputs to this path. Expected runtime additions do not alter the recorded original-file preservation claim.

The selected official test files and runner invocation remain the same 38-file gate. I do not run the native runner because that would invoke the live SSH fixture and repeat the complete native gate. The primary agent must execute this revised runner against the real fixture and preserve the original evidence according to the release record. The existing native receipt deliberately cannot satisfy the updated generator. The public RELEASE-CERTIFICATE.json is absent at the reviewed head.

The correction changes qualification scripts and regression evidence. It does not change the product archive, version declarations, native locks, Bun asset metadata, public catalog binding, or install/update coordinator. The previous independent archive/source/lock/Bun checks remain applicable. The primary agent separately repeats the earlier sixteen focused tests and asset validator. This reviewer does not claim to repeat those checks in this closure round.

Raw evidence in this directory:

- closure-diff.patch: exact generator and native runner changes reviewed.
- current-binding.stdout, current-binding.stderr, current-binding.exit: thirteen-case corrected regression, exit zero and empty stderr.
- original-binding.stdout, original-binding.stderr, original-binding.exit: regression against the original generator, expected assertion failure and exit one.
- original-certify-release.py: original generator retrieved with git show, used only as a read-only regression input.
- probe_certificate_binding.py and certificate-binding-results.json: actual historical-receipt and wrong-fresh-digest closure reproduction, including explicit synthetic fixture labels and verified receipt digests.
- Separate per-case stdout/stderr and historical-probe output: exact negative-case refusal evidence.
- commands.txt and reviewed-state.txt: commands and reviewed Git state.

Only reviewer report directories are authored. I update the first report's model metadata to the precise inherited model confirmed by the primary agent. No product file, original receipt, sealed asset, live service, credential, personal data, memory store, or journal changes. Every Python command that reads the archive uses PYTHONDONTWRITEBYTECODE=1 and -B. No push, merge, publication, or delegation occurs.

The code review is clear for this correction. Adrian's remaining review concerns are the actual identity-bound native receipt and the outstanding live recovery/rollback results. This report does not qualify the release, complete a live gate, or authorize publication.

Follow-up working-tree review requested by the primary agent:

At the same reviewed head, the native runner gains a bounded readiness wait for the actual .252 SSH fixture after the independent stop-mode backup. I inspect this additional diff. It starts the existing official runner only after an actual SSH true command returns zero. Failure or timeout prevents native qualification. native-readiness-followup.patch preserves the exact reviewed delta.

I also inspect the unrun qualify_public_install.py driver. It creates a new synthetic HOME and profile, installs the standalone manager from the public GitHub version tag through stock Hermes, enables the plugin, and uses actual public CLI prepare and start. It verifies the prepared commit and archive hash, compares the downloaded certificate with the local qualified certificate, waits for actual applied state, and reads installed identity from lifeos-version's active object. The fresh release plan uses services=None, so this synthetic first installation does not control the account's existing application services. The driver does not run a model call or connect to either server. Its public preparation downloads and validates the complete package through the existing catalog path. The archive/source and metadata checks remain within the synthetic workspace.

The public driver remains unrun because there is no public release yet. I establish no additional actionable finding in this static review. qualify-public-install-reviewed.py and followup-file-hashes.txt preserve its exact reviewed bytes and the final native runner bytes. A passing public driver receipt still belongs to the remaining actual acceptance work. The final code-review recommendation remains clear, with the release gates explicitly incomplete.
