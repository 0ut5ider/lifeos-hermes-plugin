# SessionEnd UpdateCounts on the local-model account

On 2026-09-28, the parity record showed that all six installed SessionEnd handlers exited successfully, but it had no state-effect check for `UpdateCounts.hook.ts`. I inspected the installed handler on the isolated `.212` account. Its former settings counts write was removed upstream. The handler now reads Claude Code OAuth credentials and, when present, refreshes `LIFEOS/MEMORY/STATE/usage-cache.json` from the Anthropic usage API.

The `.212` account has no `~/.claude/.credentials.json` and no usage cache. I dispatched the installed hook through the bridge with a disposable home and LifeOS root. It exited zero and did not create `usage-cache.json`. No network request was made because the credential file was absent. This is the expected native local-model path, not a missed bridge callback.

If Claude OAuth credentials are later added to an installation, this native hook can contact Anthropic for usage metadata. The isolated test account also has LAN-only outbound rules. The probe did not exercise a credentialed refresh, and the public plugin does not alter this LifeOS behavior.
