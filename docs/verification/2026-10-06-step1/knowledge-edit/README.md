# Real Edit knowledge warning delivery

Date: 2026-10-06. The native Claude Code CLI and Hermes each apply the requested Edit to the synthetic knowledge note. The actual KnowledgeWriteGuard emits its off-schema warning, and the next real private FlashNext request contains that warning. Both clients deliver the final response. Five successful inference requests have verified request and response hashes in `wire-proof.json`.

The native CLI uses its actual Edit event. Hermes uses its actual file dispatcher and Edit mapping. The retained source-bound results, hook payloads, output text, fixture events, and frozen runners make those claims reviewable. This case covers Edit. The earlier paired knowledge case covers Write. Batch model delivery has a separate control.
