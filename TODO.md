# Project todos

- [ ] Install and update the complete LifeOS integration from Hermes. Deferred until hook compatibility evidence is complete. See the [installation and update assessment](notes/2026-10-03-hermes-managed-install-update.md).
- [ ] Distinguish cancelled clarification results from timeout results. A cancelled waiter currently returns an empty timeout result. The live stop and recovery behavior passes, but the next model reply can misdescribe cancellation. See the [live cancellation evidence](docs/verification/2026-10-07-discord-cutover/cancellation.json).
