# 2026-09-27: Native LifeOS write hooks through the bridge

Three isolated probes used the installed LifeOS hook scripts on `.212`. Each probe supplied a temporary LifeOS root and a settings file containing only the relevant native registrations.

1. A `Write` PostToolUse event for a Research note without valid frontmatter returned KnowledgeWriteGuard's off-schema advisory through the bridge's tool result context.
2. A `Write` PostToolUse event with 250 synthetic lines returned ComplexityRatchet's net-lines advisory through the same context path.
3. A `Read` PostToolUse event recorded the hash of a synthetic ISA. After an external edit, a `Write` PreToolUse event reached PreToolGuard and blocked the stale replacement. A second `Read` recorded the new hash, and the same `Write` was allowed.

These probes verify the native hook decisions and bridge return path. They do not verify all Write and Edit handlers, or a real model consuming the advisory text.
