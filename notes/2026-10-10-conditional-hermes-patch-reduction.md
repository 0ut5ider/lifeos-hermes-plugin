# Conditional reduction from 36 to 35 patches

Date: 2026-10-10. Status: qualification task, not an approved source upgrade.

The current bundle contains 11 Hermes patches and 25 LifeOS patches. Keep all 36 patches on the current source pins. One later Hermes revision can potentially replace `hermes-protected-instruction-approval.patch` with upstream behavior. This would leave 10 Hermes patches and 25 LifeOS patches.

The installed Hermes base is `758ad514eb0e800547e015edf05aa18f78b78d82`. The assessment inspected upstream revision `f925b01791fe052e7d55dc975750c0bd985aff91`. Its [protected instruction guard](https://github.com/NousResearch/hermes-agent/blob/f925b01791fe052e7d55dc975750c0bd985aff91/tools/file_tools_write_guards.py#L322) refuses approval when `_no_user_can_answer()` returns true. The [approval context](https://github.com/NousResearch/hermes-agent/blob/f925b01791fe052e7d55dc975750c0bd985aff91/tools/approval_context.py#L158) covers single-query, scheduled, and unattended platform execution. This is the boundary that the local patch supplies.

The independent assessment compared three boundary cases against the patched pin: unattended execution with automatic approval and an approving callback, interactive approval, and interactive denial. The primary agent repeats all six executions and confirms matching responses without errors. The unattended case refuses before it calls the callback. The [primary control record](../docs/verification/2026-10-10-publication-review-fixes/approval-controls.json) retains the commands and results. These results do not qualify the complete newer Hermes tree. The initial mixed-version imports fail because private helper APIs differ. Copying one newer file into the pinned installation is not a supported upgrade.

## Qualification sequence

1. Select a complete immutable Hermes revision and retain the current release for rollback.
2. Prepare the complete source tree with the other 10 Hermes patches in their declared order.
3. Rebase any incompatible patch against that tree and verify the source manifest and packaged copies.
4. Test protected instruction refusal in single-query, scheduled, and unattended platform contexts, including automatic approval and approving callbacks.
5. Test interactive approval and denial through the actual native execution path.
6. Run the complete plugin and Hermes integration checks, including required middleware, prompt admission, command policy, lifecycle, delivery, child routing, strict inference, and scheduled workers.
7. Verify the installed candidate, its update path, and rollback with the same release package.
8. Change the pin and both ordered patch registries together only after all checks pass. Remove the canonical patch and its packaged copy in that change.

The result must retain full behavior and pass the complete release checks. A count of 35 is a conditional outcome, not a promise. No LifeOS patch removal follows from this evidence. Separating generated frontend output and generating duplicate distribution copies reduce maintenance bytes while leaving the functional patch count unchanged.

The [assessment report](../docs/agents/2026-10-10-patch-reduction-assessment/patch-reduction-assessment.md), [inventory](../docs/agents/2026-10-10-patch-reduction-assessment/patch-inventory.csv), and saved experiment logs contain the source identities, measurements, and qualification limits.
