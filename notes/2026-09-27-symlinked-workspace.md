# Symlinked workspace file hooks

Date: 2026-09-27

Hypothesis: A local workspace symlink lets Hermes write the real target while the bridge sends the alias path to LifeOS. The installed `KnowledgeWriteGuard` compares the path with the LifeOS root as a string, so this would skip its advisory.

On `.212`, a disposable `alias` directory pointed to `real`. The same relative note path resolved to `alias/LIFEOS/MEMORY/KNOWLEDGE/Research/note.md` in the bridge and `real/LIFEOS/MEMORY/KNOWLEDGE/Research/note.md` in Hermes. A local regression test reproduced the mismatch and failed with the alias path.

The bridge now uses Hermes's task file path resolver when it is available. That resolver follows local symlinks and keeps remote and container paths in their own namespaces. When Hermes's module is unavailable, the bridge resolves the local path itself. On `.212`, the same disposable path resolved to `real` in both components, and the installed native `KnowledgeWriteGuard` returned its off-schema advisory for a temporary invalid note. The probe invoked the PostToolUse hook with a synthetic result and did not write the note. The full local suite passed 78 tests, with five optional native tests skipped.

This verifies local symlinked workspaces. Remote and container namespace fidelity still needs separate probes.
