Date: 2026-10-12
Agent role: Independent read-only exact-version compatibility reviewer, Cerebo
Question: Does PR16 correctly separate the LifeOS release selection from the latest stock Hermes global version flag while preserving release defaults, metadata, and public bootstrap compatibility?
Model: gpt-6.1-sol, high reasoning effort.

Adrian, this bounded PR16 review is clear. I establish no actionable finding in the parser correction, namespace use, default selection, metadata, or public bootstrap dispatch.

The reviewed PR is https://github.com/0ut5ider/lifeos-hermes-plugin/pull/16. The candidate is 223cbfc1681f0b4d3a7bad668d40822a9267137e on feature/release-0-4-1. The base is origin/main at de2172241a545b901188deab21461dac4c136700. Tracked state is clean during the reviewed implementation checks. Later qualification evidence added by the primary is outside this report's claims.

The current official latest Hermes release page resolves to v0.21.7 at commit prefix 71d34ba: https://github.com/NousResearch/hermes-agent/releases/tag/v0.21.7. This matches the project's supported full commit 71d34bad1045610252eda02ee79549436896e784 and the actual stock source used below. The native global-version probe reports v0.21.7 and upstream 71d34bad. Public source observations and URLs are retained on disk.

The product behavior change has two lines in optional/lifeos_release_manager/cli.py. configure assigns the prepare option --version to release_version. run reads args.release_version when it calls prepare. The external separated and equals forms remain available. Other operation handlers do not require the new field. No remaining manager reader expects args.version. The existing catalog receives None for omitted selection and chooses its latest endpoint; an exact string chooses the corresponding release tag. The catalog, candidate planner, admission, worker, recovery, rollback, and dashboard implementation are unchanged.

This addresses the actual host ordering. Stock Hermes main.py checks args.version before it dispatches the plugin handler. The previous string selection makes that condition true. The corrected option leaves the host's boolean field false and supplies the selected string in release_version. The root global --version flag retains its independent meaning.

Independent focused verification:

- All twenty-six command, dashboard, version, and native dependency tests pass without skips. The unittest runtime is 22.146 seconds. The outer driver reports 22.826 seconds. The full result is in focused.stderr and focused.json.
- The run uses a private synthetic HOME, UTC, the corrected Bun first on PATH, a copy of the prepared Hermes source, and the required read-only native and managed-fresh fixtures. Copying the Hermes host prevents native bootstrap bytecode activity from affecting the sealed extraction.
- The added regression exercises an actual argparse parent flag and plugin subparser. Existing dashboard checks verify actual authenticated request boundaries and owner revocation. This reviewer does not treat the focused component gate as a full release qualification result.

Independent actual stock CLI verification:

- A copied stock Hermes source installs the standalone manager through the public GitHub URL pinned to full commit 223cbfc1681f0b4d3a7bad668d40822a9267137e. Install, enable, and manager status all exit zero. Status reports no operations before the probes.
- Actual lifeos-release prepare --version not-a-version and --version=not-a-version both exit one with the manager's rejected JSON. Neither prints the Hermes version. Invalid selections refuse before any release asset download, and their synthetic operations end preparation_failed.
- The actual native parser returns global_version false and release_version '0.4.0' for both valid separated and equals forms. Omitted selection returns release_version null and global_version false. This checks real native plugin discovery and parser construction rather than only a reconstructed parser.
- Actual hermes --version still exits zero and reports Hermes v0.21.7. The synthetic native installation remains absent. No operation applies, and no existing profile or server participates in these checks.

stock-cli-results.json records each command, exit code, timing, and namespace. Per-case stdout/stderr and probe_stock_cli.py preserve the complete raw evidence. The completed stock probe exits zero. The invalid-selection and namespace checks have empty stderr.

The first reviewer stock probe reaches the correct manager rejection but then fails its own assertion because it expects an error field. The existing CLI intentionally emits its generic message field. I correct the probe to assert that actual contract and repeat it in a new synthetic workspace. initial-harness-key-error.stderr, initial-harness-key-error.exit, initial-separated-invalid-exact.stdout, and initial-public-commit-install output preserve that reviewer harness error. It is not a product failure. The corrected public probe completes all checks above.

Metadata and immutable candidate verification:

All five version declarations are 0.4.1. The patch directories, twelve dependency locks, catalog, and Bun release tools metadata are unchanged from the merged base. The patch counts remain ten Hermes and twenty-five LifeOS. The README correctly distinguishes the qualified immutable 0.4.0 release from the unqualified 0.4.1 correction, identifies the explicit-version limitation, and uses a full commit for native plugin --ref.

The new immutable archive is 119,131,524 bytes with SHA-256 5727d5035e416ed665ecfd19ee48a585428e1edd0466ac8bcb5dabfb9e0c11d5. Its build receipt names the exact reviewed commit. I independently verify the hash and size, all five archived version declarations, and archived cli.py equality with reviewed code. metadata-results.json records these checks. This reads the archive without extraction or source modification and does not qualify it for publication.

The review authors only this report directory and temporary synthetic test workspaces. Native plugin installation and dependency preparation occur only inside the disposable stock workspace through the requested public bootstrap test. No existing service or account configuration changes. Every Python command reading sealed source or archive uses PYTHONDONTWRITEBYTECODE=1 and -B. There is no live SSH, credential access, personal-data read, memory/journal call, product edit, primary repository Git mutation, push, merge, or delegation.

The full frozen 626 integration gate, official 716 native gate, installed update/recovery/reboot/rollback, whole-guest recovery, public exact-version full preparation, and publication belong to the primary's pending 0.4.1 qualification. This report verifies argument dispatch and safe refusal, not a successful valid release download or installation. Development and daily remain on accepted 0.3.1 according to the supplied state, and the ready public 0.4.0 operation is not treated as applied.

The code review recommendation is clear for the exact-version correction. Adrian's remaining review concerns are the complete new archive qualification and actual post-publication valid exact selection. Published 0.4.0 and 0.3.1 assets remain immutable. This report does not qualify a release or authorize publication.
