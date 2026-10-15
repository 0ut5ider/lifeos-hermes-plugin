2026-10-15
Role: Independent focused code reviewer
Question: Do the terminal cycle archives, backup failure recovery, exact plugin selection, and detached worker changes preserve current state and authority?
Model: gpt-6.1-sol, high reasoning effort

# Portability cycle review

Reviewed commits: `735ad565` and `6f92a0484731b9971ae8e2537f0cf166bc162c40` (full reviewed tip in `source-pin.json`). Base: `89f26d06`. The checkout also contains a later documentation-only commit. The reviewed product files match the selected source snapshots.

**No additional defect is identified in the two cycle commits. One pre-existing owner-admission gap is independently measured in the expanded review scope. It remains a first-use acceptance blocker.**

## P2: Fresh dashboard claim activation has no admitted owner conversation

Locations: `lifeos_hook_bridge/memory_preferences.py:131-132`, `lifeos_hook_bridge/memory_ownership.py:196-198`, and `lifeos_hook_bridge/memory_policy.py:80-96`.

The dashboard claim creates one authenticated dashboard account binding and an empty destination map. Activation enables ownership without adding a terminal account binding, the selected profile destination grant, or a model route grant. Normal CLI metadata maps to `terminal:<operating-system UID>` and the selected profile path. The policy therefore rejects the first owner conversation even when activation reports `configured`.

The independent reproduction replaces the fixture's pre-injected accounts and destinations with the exact fresh dashboard claim shape. It captures and publishes a new synthetic import, prepares activation, and applies activation through actual backups and isolated services. Activation returns `configured`. Resolving host-bound CLI metadata then returns `The current account has no approved identity binding`. The desired-admission assertion fails at that reason. The failure does not depend on the synthetic model route because identity binding fails first. No model call runs in this reproduction.

Exact control: `docs.agents.2026-10-15-portability-cycle-review.cycle_controls.ClaimedOwnerAdmission.test_fresh_dashboard_claim_activation_has_usable_local_owner_admission`.

This gap predates the two reviewed cycle commits. Existing successful ownership tests inject conversation grants into their fixtures. The normal claim and activation UI paths do not enroll these grants. I find no account, destination, or model-route enrollment endpoint in the inspected preference API. External explicit policy setup is currently required.

The correction needs an explicit owner-reviewed account, selected profile destination, and actual model route binding, or a clear prerequisite refusal before activation. Unknown accounts and unreviewed routes must continue to fail. The primary agent separately confirms the same refusal in its installed CLI observation. That installed result is reported by the primary agent and is not counted as this review's independent evidence.

## Verification of the cycle changes

75 controls pass:

| Run | Result | Boundary |
| --- | --- | --- |
| `review-cycle-existing` | 70 PASS | Lifecycle, activation, ownership, setup, and profile backup regressions |
| `review-cycle-aliases` | 3 PASS | YAML leaf aliases, merged selection refusal, and cache link handling |
| `review-cycle-connector-preservation` | 2 PASS | Both original connector edits during the actual writer check |
| `review-cycle-owner-admission` | 1 measured FAIL | The fresh claim gap above |

The lifecycle controls exercise a repeated activation after a verified current-state return, an actual process exit during terminal journal moves, resume without historical file restoration, a later terminal journal edit, and wrong-owner refusal before effects. The current file bytes, native data, original plans, and retained proof remain covered.

The additional alias control shares enabled and disabled plugin lists, a LifeOS entry with a foreign entry, and an external skill directory list. Activation changes only the selected values. Foreign alias values remain unchanged. A merged plugin mapping refuses without modifying configuration. A symlink named `__pycache__` is not excluded as regenerable, and a workspace cache directory remains covered.

The existing preparation failure control uses an unsafe synthetic directory to cause a real backup refusal. It verifies that original active services resume, the setup becomes cancelled, and profile contents remain unchanged. Existing real process interruption controls remain passing. The worker changes select `-B`, set `PYTHONDONTWRITEBYTECODE`, set the process bytecode flag before relative worker imports, and use a user service with `UMask=0077`. Those new launch arguments receive source inspection here; this review does not claim a separate installed detached worker replay.

## Evidence and limits

`source-pin.json` records the selected commit and hashes. `source/` retains the reviewed source files. `reviewed.patch` records the product and test changes. `results.json` and the raw receipts retain exact commands, exit codes, runtime source paths, elapsed times, and full output. `cycle_controls.py` contains the independent controls.

Tests use synthetic records, actual files, SQLite, real child exits, and isolated user services under the shared service fixture lock. The lifecycle return proof uses a fresh Hermes constructor and explicitly reports `model_turn_executed: false`. One older ownership host control also sends an actual HTTP conversation to a scripted local response service. That proves request integration, not a real model's behavior or the installed private model route.

This review does not qualify the entire feature, installed browser activation, real private model turns, removal, reboot, or production release. It does not change product source, remotes, personal data, memory stores, credentials, staging, or commits. The upcoming owner-admission correction requires a separate focused review.
