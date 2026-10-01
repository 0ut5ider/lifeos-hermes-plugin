# Selecting a provider does not disable the built-in stores

Date: 2026-09-30. The tests use a temporary profile and the real Hermes agent constructor.

Hermes permits an external provider alongside its built-in stores. Selecting `lifeos-hook-bridge` alone still injects both synthetic `MEMORY.md` and `USER.md` markers. Fresh LifeOS ownership must also set `memory.memory_enabled` and `memory.user_profile_enabled` to false. No additional host patch is needed for these flags.

With both flags disabled, the real prompt excludes the two markers and the tool surface excludes `memory`. Both direct and freshly loaded disabled-store writes fail. The files retain their exact bytes. LifeOS explicit tools and `skill_manage` remain available. An unavailable LifeOS provider does not reactivate either built-in store.

Three separate agent processes establish the restore sequence: built-in configuration, LifeOS configuration, then built-in configuration again. The last process reads the preserved markers and exposes the built-in memory tool. This proves a configuration target for a future ownership transaction. It does not prove transactional rollback, a live session switch, full history or compression behavior, or successful automatic skill learning.

The constructor sends local model capability probes to `/api/show`. They contain only the synthetic model name. The first fixture incorrectly required zero requests; the corrected assertion distinguishes these probes from model prompt requests. Another fixture expected an unavailable-provider warning on stderr. The host sends that warning to its logger. The child now captures the actual logger and asserts the expected reason without ignoring other test output.

Disabled tools do not prevent a process with the same operating-system identity from directly reading or editing the preserved files. This configuration behavior is not a filesystem isolation boundary. Ownership remains disabled on running systems, and the preferences page still has no activation action.
