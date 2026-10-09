# Activity cache survives an equal-length log replacement

2026-10-08, native operational reader investigation. The current TELOS candidate still uses the original ambient activity cache for its algorithm board. The independent five-route field comparison passes before any operational reader change.

An actual native HTTP fixture first reads a tool event whose tool_name is Write. The fixture replaces tool-activity.jsonl with a different file whose tool_name is Agent. Both files contain 217 bytes. The inode changes from 1537031 to 1537073. The actual source parses as Agent. The next /api/algorithm response still reports Write. The retained observation is in docs/verification/2026-10-08-operational-views/rotation-observation.txt.

The native getActivityData function returns its saved map when the file size equals its consumed offset. That condition does not test file identity or current bytes. Replacing a log without changing its length therefore skips the fold. The governed reader will fold the current admitted snapshot into a local map. It must not reuse a map populated from an earlier source or permission state. The unmanaged native cache remains outside this scoped change until its own correction has acceptance evidence.

The initial operational baseline reports 21 failed assertions across seven tests. Anonymous reads, private and retired text, revoked owner requests, and the initial stream bypass managed admission. The rotation finding is separate from that missing route boundary. No operational implementation change exists at the time of this note.

The governed reader subsequently folds current admitted events into a local map. The expanded gate now reports Agent after the same 217-byte replacement. Its observation records inode 1576815 changing to 1576822. All 26 focused reader, stream, and frontend checks pass. The unmanaged cache behavior remains unchanged. Current-package installation and combined release acceptance remain open.
