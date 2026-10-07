# Native completion and source admission controls

Date: 2026-10-07. Development target: `192.168.8.252`. This record covers complete source preparation with eleven Hermes patches and twenty-two LifeOS patches. The independent installer candidate has zero file differences from the prepared native source. [Source identity](native-completion-source-identity.json) retains both manifests.

The [current gate](native-completion-current.txt) passes 84 tests without skips. The [neighboring gate](native-completion-neighbors.txt) passes 76 tests without skips. Both use the release Bun version, 1.3.14. Native command controls execute actual Bun programs. Memory controls use the real local governed memory service and synthetic data.

## Measured failures and corrections

- Killing a process during a destination write leaves an empty response, nudge, integrity, spend marker, or memory-injection state file. The existing atomic publication helper now preserves the previous destination until rename.
- Eight concurrent reviews collide on their shared temporary file. Eight concurrent spend updates lose session markers. Eight concurrent feedback captures lose ISA pulses. Existing bridge locks now coordinate each shared native state file. The passing controls retain one global review fire, eight spend markers, and eight feedback pulses.
- Eight concurrent ISA renders produce seven rename failures. Separate temporary files preserve complete pages. An unavailable render executable previously produces a misleading scheduled-render record. The handler now records the actual spawn failure.
- A real model returns a valid documentation correction array. The JSON parser selects its inner object, and the documentation handler resolves targets from the wrong root. Complete JSON parsing now comes first. The handler binds edits to its reviewed documentation inventory and publishes applied changes atomically.
- Managed startup rejects a legitimate ISA with Markdown frontmatter. Source reads now use the native document validator. Fact writes retain their separate validator. Current caller authority, private markup, and retired claims remain enforced.
- Managed feedback copies previous response text without current authority. The feedback preview and drift measurement now require admitted sources. Code and quoted instructions do not create standing directives.
- A missing `gh` executable records a delivered reminder before any issue exists. The asynchronous worker now waits for successful command exit before publishing that marker. Failed attempts remain eligible for retry.

The retained `*-before.txt` records preserve these failures. Some preliminary failures came from missing fixture dependencies or incomplete source-variable bindings. The current passing gates bind the complete source and dependencies.

## Actual inference and limits

The [inference results](inference/result.json) retain actual model requests and responses for low-rating FailureCapture, documentation correction, capability audit, and governed memory review. Those preliminary remote runs use Bun 1.4.2. The separate pinned-version run repeats all four controls with Bun 1.3.14 before release acceptance.

The memory review parses an actual result and publishes pending proposals. Its create/review grant does not permit automatic application. The reviewer reports that refused automatic application with exit code 1. The control requires the pending queue, an unchanged target, and zero automatically applied proposals. It does not report the whole review command as successful.

SpendAuditor checks capability use against prompt length. It does not audit monetary cost. ReminderRouter creates private GitHub issues for explicit reminders, research requests, and queued work. It does not implement a due-time scheduler. Enabled issue delivery still requires an authorized private destination. A lost acknowledgement after server-side creation has an unknown external outcome; the marker does not guarantee exactly-once network delivery.

The desktop voice control receives actual HTTP notifications. It verifies channel policy, repeated Stop behavior, failed delivery, and interruption. It does not establish Discord transcription or spoken replies. The writing detector control verifies the missing-detector policy and an explicit availability refusal. It does not claim successful detection through an unavailable external service.

Production `.212` and the final model-tier mapping remain unchanged.

The [final installed acceptance controls](../installed-release-controls/README.md) extend this historical 22-patch gate with the 23-patch candidate, actual pinned-version inference, concurrent admitted review, complete installed sessions, and full-tree update and restore. The final regression sweep reports zero failures and zero errors. Enabled private GitHub reminder delivery and actual Discord release acceptance remain open.
