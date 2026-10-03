# Background skill review with lasting-memory ownership

Date: 2026-09-30. Role: primary implementation. Model: GPT-6.1-Sol.

The real foreground Hermes turn completes and sends one HTTP request. Its actual background review fork sends zero requests. Observational tracing captures its failed result: `Memory history cannot verify the current user input`. The generated review prompt differs from the human input proof inherited from the foreground turn. The host describes this admission error as a temporarily unavailable provider.

The initial scratch probe failed because its fixture path stopped one object too early. That is a probe error, not an admission result. After the fixture correction, the isolated child exits successfully and captures the actual background result. No live Hermes installation is imported or changed.

The proposed fix uses the host-owned `tools.skill_provenance` context marker. It applies the generated-content checks to background reviews. It does not use prompt text, messaging app names, or user-supplied arguments to identify a review. Skill writes retain the configured Hermes approval gate. A fresh profile defaults to direct skill writes; a profile with `skills.write_approval: true` stages the write. Both paths need actual tool and filesystem evidence.

The preceding conversation-repair full regression executes 612 tests. Of these, 535 pass and 77 skip. No test fails. This run predates the background review tests and fix. It does not close the release gate.

The independent review exercises a subsequent foreground turn. The first turn and background skill write succeed with three HTTP requests. The next turn sends zero requests and fails admission. A control without background review also fails its second turn. The review origin remains `assistant_tool`; it does not leak from the worker thread. The reviewer compares the two stamps: scope, generation, rendered prompt, and context agree. Only the user-input proof differs. The prompt-admission worker updates the persisted proof, while the parent retains the previous proof in its ContextVar. This is an ordinary continuation defect, separate from resume reconstruction. The primary reruns the reviewer probe and confirms the failure.

The correction now rebinds the worker's input proof under the cooperating native transaction lock. It requires unchanged scope, generation, rendered prompt, and context. The actual current user message must match the proof during primary projection. Auxiliary calls and direct final admission cannot rebind. All 26 review and history tests pass, including both actual two-turn cases and three direct worker-handoff cases. The primary runs the reviewer's unchanged archived child: four HTTP requests, a real saved skill, clean stderr, a successful human-quote follow-up, and the foreground origin still `assistant_tool`. Independent closure is pending.

The closure reviewer passes 81 cases in 195.043 seconds. The primary passes the same 81 cases in 199.815 seconds. Ten independent handoff checks verify refusal of wrong input, unapproved model, changed author, changed policy, changed SOUL, lost admission state, and disabled ownership. They also verify a newer concurrent input supersedes an older proof and a combined proof handoff with native forgetting still projects the retired claim. The final review finds no further material defect in this bounded unit. No host or native patch is added. No running installation changes.

The committed implementation completes the broader regression: 622 cases in 284.041 seconds, with 545 passes, 77 skips, and no failures or errors. The skip-dependent release gate is still open. The next read-only audit traces the 132 native-source candidates before further native changes. Ownership remains disabled.
