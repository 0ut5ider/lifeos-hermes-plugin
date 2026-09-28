# SessionEnd through a real Hermes CLI boundary

Date: 2026-09-27. Target: isolated `lifeos-hermes@192.168.8.212` account.

The installed bridge previously ran all six native LifeOS `SessionEnd` hooks only in a synthetic boundary probe. A real one-shot Hermes CLI run now tested the event path. A temporary `UserPromptSubmit` hook blocked a unique synthetic prompt, and a temporary `SessionEnd` hook wrote its received session ID and reason to a marker. Hermes returned the prompt-block reason with exit code zero. The `SessionEnd` hook ran at CLI shutdown with the same session ID and `reason: other` in its native payload.

The probe restored the original Claude hook settings bytes. It did not call a model. This verifies the real CLI lifecycle path; Discord gateway session teardown remains untested in the isolated account because it has no Discord channel.
