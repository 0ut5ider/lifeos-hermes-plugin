Date: 2026-10-15
Role: Independent focused code reviewer, delegated by the primary Cerebo agent
Question: Does removal prepare the exact environment bytes that pinned stock Hermes preserves at startup without losing unrelated credentials or weakening publication checks?
Model: gpt-6.1-sol, high reasoning effort

## Disposition

CLEAR within the bounded environment-preparation scope. I found no new actionable defect in the correction. Fifteen independent and existing tests pass with clean output. The review covers the captured working source below. Source hashes identify the exact reviewed correction; no new archive qualification is implied.

The previous source-selection review at `f8e0d25b` remains clear with its limits. Normal installed first apply with both corrections remains pending. The old guest operation needs the separately authorized narrow repair because its exact applied-byte check correctly refuses its startup-modified environment. This report does not claim unaided recovery of that operation.

## Failure and correction

The primary measured that stock startup adds LF to an unterminated prepared `.env`. ProgramTransaction subsequently refuses its exact applied identity. The supplied installed diagnosis identifies one target, expected 23 bytes and current 24 bytes, with the same keys and values. I did not access the guest or inspect real environment contents.

I independently reproduce the underlying boundary using an isolated synthetic profile and the contained stock interpreter. The previous preparation result `API_TOKEN=synthetic-token` becomes that exact byte sequence plus LF when actual stock `sanitize_env_file()` runs. It reports one correction. `baseline-startup-red.json` records that direct observation.

The correction removes the existing exact owned block, decodes remaining content with strict UTF-8 and BOM tolerance, translates universal newlines, and calls the actual pinned `_sanitize_env_lines`. It prepares the normalized bytes before owner review. It does not ignore an applied identity mismatch or alter verification, restore, or source admission.

The qualified Hermes, upstream fixture, and constructed stock `hermes_cli/config.py` files are byte-identical. All three have SHA-256 `a469923872fc1e4d905089bb4cc4af5c8cc4104f9f72a159656205c07cdb80ef`. Their captured sanitizer and startup migration excerpts also match. This closes the concern that preparation could use a different sanitizer from the stock destination in this pinned combination.

## Independent verification

Command:

```text
python3 docs/verification/2026-10-15-memory-portability/run_tests.py review-removal-environment-current test_removal_configuration docs.agents.2026-10-15-removal-environment-review.environment_probes test_removal_preparation.RemovalSoftwarePlanTests
```

Result: 15 tests pass in 33.089 seconds. Runner duration is 33.263 seconds. Process and runner exit codes are zero; `unhandled_diagnostics` is false. I read the complete stderr output. No actual system service changes were needed.

The independent matrix includes 15 inputs. Each prepares real bytes and then launches the actual contained stock interpreter twice: once for `sanitize_env_file()` and once for `migrate_config(interactive=False, quiet=True)`. These are 30 real child processes using the stock source and environment, with bytecode writes disabled. Each child uses a private synthetic profile and no model. The prepared environment stays byte-identical through both calls, and the actual stock environment parser returns the expected synthetic values.

| Input case | Verified behavior |
|---|---|
| Missing final LF | Preparation adds LF; stock does not rewrite again. |
| CRLF and CR-only endings | Preparation selects LF; values remain exact. |
| Leading UTF-8 BOM | Preparation removes the BOM; the first key remains correct. |
| Comments and blank lines | Comment and blank-line whitespace remain; endings become LF. |
| Embedded variable name, equals characters, and hash in an opaque value | The value remains one value. No extra assignment appears. |
| Quoted leading/trailing spaces | Spaces inside the value remain exact. |
| Quoted hash and trailing comment | The actual parser retains the intended value. |
| Escaped backslash and quote | The actual parser retains the intended value. |
| Export prefix and assignment whitespace | The actual parser returns the same key and value. |
| Duplicate unrelated keys | Both lines remain; native last-value behavior remains. |
| Empty value | The empty value remains. |
| Non-ASCII UTF-8 | The synthetic accented value remains. |
| Blank-only and empty input | Output is stable and parses to no values. |

Separate refusal controls check two exact owned blocks and four malformed UTF-8 sequences, including a BOM followed by an invalid byte, an incomplete sequence, and an encoded surrogate. All refuse before preparation returns output. A custom safe-root value remains present. Owned-block removal remains exact, as before this correction; this change does not broaden which owner content it deletes.

## Actual transaction and later-edit protection

The independent transaction control uses the real software-plan function and ProgramTransaction:

1. Prepare a synthetic profile containing an unterminated retained credential followed by the exact owned block.
2. Prepare and apply the real software transaction.
3. Run the actual contained stock sanitizer. It leaves the prepared environment unchanged.
4. Run `check_applied()`. It succeeds with the original strict identity checks.
5. Publish a later synthetic owner edit to `.env`.
6. Confirm `check_applied()` and `restore()` both refuse and preserve that later edit.
7. Re-establish the exact reviewed applied bytes, then restore.
8. Confirm the original byte sequence, including its original owned block, is restored exactly.

`transaction-environment.json` records these outcomes. This control demonstrates that normalizing before owner review does not relax later-edit protection. The software-plan function still captures and validates the original input identity before transformation and passes it as `expected_before` to transaction preparation.

## Preserved primary evidence

The primary `environment-startup-red` run contains six tests and four assertion failures: malformed UTF-8 was accepted, and three prepared cases still required stock normalization. I preserved this output.

The first primary run named `environment-startup-green` is not a clean passing run. Its six configuration controls pass, but a nonexistent `test_removal_software_plan` module causes one import error. I preserved that result without reclassifying it. The subsequent `environment-startup-fixed` run uses the correct module and passes 25 tests cleanly. Those results are supplied primary evidence, separate from the independently executed 15-test run.

## Exact captured source

SHA-256:

| File | SHA-256 |
|---|---|
| `optional/lifeos_release_manager/removal_configuration.py` | `19677f2513c8041b0957ba251787c6dbc759b091b6ab4ed2a737ea22b8f1dfc6` |
| `optional/lifeos_release_manager/removal_preparation.py` | `28bfb409a1a8be07d8f41afc219e5f490985949888975564643f8496d4865863` |
| `optional/lifeos_release_manager/release_programs.py` | `d78e487bc92dcaaaf3299b6de1ee0c307bae9a1065ecf56467407e26d925b45c` |
| `tests/test_removal_configuration.py` | `871707e1f8f3c4c5b53291c6456a3fdb406bd4d3ade063bad79fc24823f6415d` |

`source-hashes.json` also records all three actual Hermes configuration module hashes and sanitizer excerpt hashes. `source/` contains the exact reviewed product and test bytes. `environment_probes.py` contains the independently reproducible commands and controls; `environment_probes.sha256` pins that file.

## Scope and remaining acceptance

This is component and actual stock startup-migration evidence. It is not a live dashboard restart, a browser owner apply, a model turn, a reboot, or a complete installed removal acceptance. No product code, private records, remote systems, or Git state were changed by this review.

The installed package must include both the source-selection and environment corrections. The normal owner workflow must then complete first apply and its actual retained recovery and rollback tests. Earlier `033`, `4db`, and `bb947` archive runs do not qualify the current correction. The old operation's repair remains an explicit operator action, not evidence that the pre-correction recovery path succeeds unaided.
