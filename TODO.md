# Project todos

- [ ] Install and update the complete LifeOS integration from Hermes. Deferred from the first daily-use release. See the [installation and update assessment](notes/2026-10-03-hermes-managed-install-update.md).
- [ ] Complete Discord voice input and spoken replies after the first daily-use text release.
- [ ] Add native Content audio and video processing with the later voice release. Verify extraction, transcription, runner control, and actual media outputs before enabling the runner.
- [ ] Complete personal-data import and reverse migration when Adrian resumes that work.
- [ ] Distinguish cancelled clarification results from timeout results. A cancelled waiter currently returns an empty timeout result. The live stop and recovery behavior passes, but the next model reply can misdescribe cancellation. See the [live cancellation evidence](docs/verification/2026-10-07-discord-cutover/cancellation.json).
