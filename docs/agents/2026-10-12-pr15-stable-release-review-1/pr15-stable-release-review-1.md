Date: 2026-10-12
Agent role: Independent read-only stable release reviewer, Cerebo
Question: Does PR15 correctly identify the stable assets, preserve public installation compatibility, and refuse incomplete or mismatched release qualification?
Model: gpt-6.1-sol, high reasoning effort. The primary agent confirms this inherited harness configuration.

Adrian, this review has one actionable P2 finding in the new certificate generator. The stable product metadata and immutable program archive pass the independent checks described below. The public release must remain unqualified until the finding and outstanding acceptance gates are complete.

The reviewed PR is https://github.com/0ut5ider/lifeos-hermes-plugin/pull/15. The reviewed head is 8e804cc8e1b8727e0517ccdfa91b261c5d91f062. The base is origin/main at be215380dcbda35c92e6f28b23b4a1d7bc15004e. The exact program commit is a87e7ae94894dabc3651454d1334cb23c4fae27e. The primary agent may append later acceptance receipts. This report does not claim to review those future changes.

1. P2: Certificate generation does not bind all qualification receipts to the archive it certifies.

   Location: docs/verification/2026-10-12-release-0.4.0/certify_release.py:12. Related identity checks are at lines 16 and 21.

   The generator verifies the archive hash and size, then checks the integration receipt's exit code and passing test text. It does not compare the receipt's package_commit with build.head. Native qualification similarly trusts a filename and passing count, without recorded source or package identity. Fresh qualification compares its top-level package_commit, but ignores the prepared operation's package_sha256 and commit.

   The isolated reproduction copies the exact generator and public evidence into temporary directories. The untouched incomplete current evidence refuses certification and writes no certificate, because development-bunfixed-rollback.json does not exist. For the receipt-binding negative tests only, the probe supplies explicitly labeled synthetic future rollback and whole-guest receipts. These are test fixtures, never acceptance evidence.

   The passing baseline emits a QUALIFIED certificate for a87e7ae9. Replacing only the current integration JSON and stderr with the actual historical passing integration-sealed-4644f90c files still emits a QUALIFIED certificate for a87e7ae9. The input JSON records package_commit 4644f90c10d301a943f9ca2a47c9725b136ac5d4. The output certificate records a87e7ae94894dabc3651454d1334cb23c4fae27e and SHA-256 82acd3da141ef5aad322b49f30a8306305c298fa6706d44cc320de54f76442da. The older archive is explicitly superseded for its Bun extraction failure.

   A second negative case keeps the current integration evidence but changes fresh.preparation.package_sha256 to 64 zeroes. The generator again exits zero and emits the same QUALIFIED certificate. No live service, operation, profile, sealed source, or original receipt changes in these probes.

   This can certify a release with stale or mismatched test evidence after an evidence-copy or naming error. The actual current integration receipt is correctly bound by its package_commit. The finding concerns the generator's missing enforcement, not a claim that the completed current test run used the wrong source.

   Minimal correction: require full.package_commit == build.head. Require the fresh preparation version, commit, and package_sha256 to equal the build identity. Have the native runner record its package commit, archive hash, source identity, and actual Bun identity, then require those fields before certification. Add negative checks for stale integration evidence and mismatched native/fresh identities. Keep incomplete-gate refusal. Recording receipt digests in the certificate also makes the published qualification evidence auditable.

   Reproduction: run PYTHONDONTWRITEBYTECODE=1 and the native test Python with -B on probe_certificate_binding.py in this report directory. certificate-binding-results.json records all four cases. Each case has separate stdout and stderr. The probe writes any generated certificates only inside temporary directories that it removes afterward.

Independent verification:

- All sixteen version and native dependency checks pass in 6.171 seconds, with isolated HOME, TZ=UTC, the corrected Bun first on PATH, and the required source variables. focused-tests.stderr contains the complete clean result. No test skips.
- The exact immutable program archive is 119,131,156 bytes and hashes to 82acd3da141ef5aad322b49f30a8306305c298fa6706d44cc320de54f76442da.
- A fresh temporary extraction passes the existing actual validate_package function, bridge and manager file maps, frozen Python closure validation, all five version declarations, and both native source manifests. No source validation bypass is used.
- All twelve native lockfiles are byte-for-byte identical between origin/main, the current branch, and the immutable archive. Their measured hashes are in asset-identity-results.json.
- The official Bun baseline zip is 42,015,103 bytes and hashes to 1fc2edac843102909e3a1be1d8d9802cc6071cf074e67e88231f4ffe0f8b397b. Its selected member equals the available executable, whose SHA-256 is 7ce7d6b654eddeec20afddf2396317fba6dc19ab52788a27e894e1806bf8f24b. The actual executable reports 1.4.3.
- The product diff is exactly VERSION, both plugin.yaml files, both dashboard manifests, the dependency catalog runtime pin, and release-tools.json. No native patch, release-manager logic, build script, or test implementation changes from the merged PR14 base. Patch counts remain ten Hermes and twenty-five LifeOS.

An initial validation of the cached extracted package refuses because Hermes source hashing includes extra bytecode files and .bytecode-fingerprint. The subsequent archive-to-directory comparison proves that all 18,292 archived Hermes files still have identical bytes. Every difference is an extra runtime artifact. The immutable archive itself contains none of these extra files and passes fresh extraction validation. asset-directory-contamination.stderr and sealed-directory-comparison.json preserve this observation. No cache cleanup or sealed package modification occurs.

The review inspects public catalog asset binding, bounded extraction, Bun acquisition and executable verification, candidate validation, the unchanged package builder, documented installation and update paths, historical private certificates, the integration/native qualification runners, fresh actual interruption qualification, development observation and reboot verification, and the whole-guest controller and synthetic history/program verification. PR15's public installation instructions explicitly require a qualified tag and preserve 0.3.1 assets as historical rollback inputs. The documented old-coordinator refusal is consistent with the frozen closure requirement. No additional actionable public compatibility or inherited release-manager blocker is established.

Release limitations: the existing 625 integration result and official 716 native test result are inspected but not repeated by this reviewer. The live development acceptance, whole-guest backup/restore, normal rollback, publication, and public post-publication preparation path belong to the primary agent. The untouched certificate generator correctly refuses the missing acceptance receipts. Private fixture certificates remain separate from the public release certificate. Daily .253 remains outside this review's mutation scope.

Only this report directory is authored. No product file, service, personal data, credential, memory store, or journal is changed or read by this reviewer. Every Python command that reads sealed source uses -B and PYTHONDONTWRITEBYTECODE=1. No push, merge, publication, dependency installation into a live account, or delegation occurs.

Adrian's review should focus on the qualification binding correction and the remaining whole-guest/normal rollback gates. This report does not qualify a release or authorize publication. The primary owns the final receipts, Git changes, and public asset verification.
