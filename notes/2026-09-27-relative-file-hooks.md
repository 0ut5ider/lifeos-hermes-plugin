# Relative file hook paths

Date: 2026-09-27

Hermes file tools accept paths relative to the active task workspace. The bridge had passed those paths unchanged to native LifeOS hooks. Some LifeOS guards compare `file_path` with an absolute LifeOS directory, so a relative path to the same file bypassed them.

A local regression test first showed that a relative Write path reached a hook unchanged. The bridge now makes Read, Write, and Edit paths absolute against the task workspace. The V4A adapter does the same for each file named in a multi-file patch. It normalizes the path without reading the target file or dereferencing a symlink.

On `.212`, a temporary LifeOS root held an invalid `MEMORY/KNOWLEDGE/Research/note.md`. A synthetic V4A patch used the relative path `LIFEOS/MEMORY/KNOWLEDGE/Research/note.md`. Before the bridge change, the installed native `KnowledgeWriteGuard` returned no advisory. After the change, it returned an off-schema advisory for `Research/note.md`. The probe invoked PostToolUse with a synthetic result; it did not modify the note.

This verifies local workspace resolution. A remote or container backend can use a different filesystem namespace, and a symlinked workspace can resolve differently from the path Hermes ultimately patches. Those cases need their own probes.
