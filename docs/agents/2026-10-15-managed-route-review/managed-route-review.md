2026-10-15
Role: Independent focused code reviewer
Question: Does the managed route child correction load the selected Hermes dependencies while retaining route isolation, exact configuration checks, and private output?
Model: gpt-6.1-sol, high reasoning effort

# Managed route review

Reviewed correction: `e813806fb30d87978148832c2692a425a64d5ce9`.

**No new finding is identified within the tested boundary. The local managed-store regression closes. Sixteen distinct controls pass. Installed browser and application replay remains primary-agent work.**

## Measured regression and correction

The previous owner-route review covers a dependency-equipped test interpreter. It does not cover a bare managed-store interpreter starting another direct child. The installed receipt records `route_child_missing_dotenv: true`. This review preserves that receipt and independently reproduces the dependency difference locally.

The actual local managed Python 3.14 store interpreter cannot import `dotenv` or `ruamel` without bootstrap. Under that same interpreter, the retained earlier route helper raises `MemoryUnavailable`. The corrected helper succeeds when it uses `hermes_cli._launchers.runtime_command`.

The corrected route command imports the actual Hermes bootstrap before the route code. Bootstrap selects the runtime dependency environment. The command keeps isolated Python execution, disables bytecode output, uses the exact selected profile, and retains configuration hash checks before and after route resolution. The correction does not change grant construction or owner authority.

## Independent verification

| Run | Result | Scope |
| --- | --- | --- |
| `review-managed-route-existing` | 13 PASS | Current owner-grant controls and the seven independent route/isolation controls |
| `review-managed-route-bare` | 3 PASS | Bare interpreter dependency absence, actual bootstrap dependency selection, and old/new route comparison under that interpreter |
| `review-managed-route-observations` | 3 repeated PASS | The same managed controls rerun to retain safe child observations on disk |

The repeated run adds raw observations, not additional distinct coverage.

The managed controls use a real existing local runtime, its real store Python, its real sealed dependency environment, and a synthetic temporary account and profile. They do not replace the launcher or dependency loader with mocks. The bare interpreter has neither route dependency. Bootstrap then imports both dependencies from that runtime's `python-environment/lib/python3.14/site-packages`.

The old and corrected helpers run under the same bare interpreter. The old direct child refuses. The corrected helper resolves the configured synthetic endpoint and admits the exact local owner, profile, and reviewed route. Unknown accounts, profiles, and routes remain denied. The selected configuration stays byte-identical, and the synthetic credential does not appear in the disclosure.

A synthetic parent `sitecustomize.py` payload does not execute. Parent Python paths and virtual environment inputs do not select unrelated dependencies. Existing controls also retain selected-profile dotenv isolation, named-provider resolution, safe generic error output, and refusal of a configuration edit immediately before child startup.

## Bootstrap and source checks

`runtime-source-comparison.json` verifies that the local managed runtime's launcher, bootstrap, dependency activation, and launch preparation source bytes match the e813 candidate's corresponding files. It also verifies that the reviewed route helper matches the candidate package. The candidate build receipt identifies the full program commit above.

The normal bootstrap performs Hermes startup and dependency activation. The tested source is a sealed runtime, so it does not enter the self-managed Git update path. Temporary profile scratch state is permitted and cleaned with the fixture. The exact selected model configuration remains unchanged. This review does not test concurrent dependency-generation replacement or self-managed source-update recovery.

The source snapshot uses direct file hashes and candidate-file comparison. No Git command or remote access is used. `source-pin.json`, `source/`, and `final-source-check.json` preserve the inspected bytes and final identity check. `original-direct-helper.py` preserves the earlier implementation. `observations/` retains the safe actual child results. Raw test receipts, complete stdout, and complete stderr are included.

## Verification limits

This is real local runtime and component integration evidence. It is not installed guest browser acceptance or a complete installation replay. The test runtime uses the sealed payload dependency selection path. The installed guest can additionally use its committed dependency-generation state, which remains part of the primary replay.

No control sends a model request. A successful route result establishes configuration and admission, not model authentication or inference. Installed native FlashNext turns, full removal, reboot, and release qualification remain outside this review.

The review does not change product code, remote hosts, personal data, memory stores, credentials, staging, or commits. It creates only review artifacts and synthetic local test state.
