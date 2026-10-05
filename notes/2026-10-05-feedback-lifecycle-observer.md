# A blocking observer hides the feedback hook

Date: 2026-10-05. The first paired feedback fixture assumes a blocking UserPromptSubmit observer can stop model generation while another hook group captures a rating. Claude Code 2.1.272 records two observer events, SessionStart and UserPromptSubmit, then exits. It invokes zero SatisfactionCapture hooks and emits no SessionEnd observer event. Its result reports the observer's block reason and zero model usage.

The selected feedback hook occupies a later group in the same event. Blocking the earlier group prevents the native control from reaching the selected hook. The fixture fails its complete-lifecycle assertion before it can produce a paired result. This run does not establish a Hermes compatibility defect.

The next fixture permits each synthetic feedback prompt to finish through private FlashNext. It requires one successful generation, final client output, the selected hook exactly once, and the actual startup, prompt, and session-end boundaries. It keeps the seeded response cache unchanged because this fixture selects SatisfactionCapture only. Full production hook groups remain a separate acceptance requirement.
