# 2026-09-27: Native LifeOS write hooks through the bridge

Eight isolated probes used the installed LifeOS hook scripts on `.212`. Each probe supplied a temporary LifeOS root or home directory and a settings file containing only the relevant native registrations.

1. A `Write` PostToolUse event for a Research note without valid frontmatter returned KnowledgeWriteGuard's off-schema advisory through the bridge's tool result context.
2. A `Write` PostToolUse event with 250 synthetic lines returned ComplexityRatchet's net-lines advisory through the same context path.
3. A `Read` PostToolUse event recorded the hash of a synthetic ISA. After an external edit, a `Write` PreToolUse event reached PreToolGuard and blocked the stale replacement. A second `Read` recorded the new hash, and the same `Write` was allowed.
4. A `Write` PostToolUse event for a synthetic ISA reached ISASync. The temporary work registry gained the expected `synthetic-isa` entry, and the hook returned context.
5. Three identical `Read` PostToolUse events reached LoopDetector. Its private session state recorded `seq: 3`; the third result contained `[LOOP DETECTED]` with the Read input. The first two returned no advisory.
6. A `Write` PostToolUse event for a synthetic `CLAUDE.md` reached ConfigEvalFire. A harmless replacement runner wrote a marker, and the native hook created its debounce state. The probe did not run the real configuration evaluation.
7. A `Bash` PostToolUse event containing a synthetic `systemctl --user enable` command reached AtlasEventCapture. The hook appended one `systemd` hint to a temporary home's Atlas events file. The command was not executed.
8. A `Write` PostToolUse event for a synthetic `~/.claude/CLAUDE.md` reached PostToolObserver. Its SystemChangeSurface component wrote a per-session ledger entry and returned a `SYSTEM: CLAUDE.md` line in the tool result context.

These probes verify native hook decisions, state effects, and the bridge return path. They do not verify all Write and Edit handlers, or a real model consuming the advisory text. CheckpointPerISC was inspected but not executed with an opted-in repository: its native commit command uses `--no-verify`, which would bypass repository pre-commit hooks.

The installed LifeOS settings register LoopDetector directly on PostToolUse and also register PostToolObserver, which calls LoopDetector internally. A two-event probe with both registrations still left session state at `seq: 2`; each pair of concurrent calls can overwrite one another's state. An observer-only control probe also left `seq: 2`. This duplicate native registration is present in LifeOS's `hooks.json`, so the bridge must not silently remove it as a Hermes-specific parity fix.
