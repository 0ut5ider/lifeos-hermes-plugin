# Local model rung observation

Date: 2026-09-27

The isolated `.212` Claude settings have no model pin. A temporary bridge transcript contained an assistant message from `flashnext-w4a16-fp8ple`. The bridge ran the installed `ModelRungGuard.hook.ts` at the next UserPromptSubmit. The native observability row recorded `model: flashnext-w4a16-fp8ple`, `live: null`, `pin: null`, and `event: on-pin`.

This proves that the bridge supplied the actual model name and that the native hook cannot classify it as a Claude tier. The `on-pin` label in this case does not establish rung compliance. Model-tier policy needs an explicit local mapping or separate tier models before the hook can enforce it.
