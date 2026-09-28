# ReminderRouter prompt egress

Date: 2026-09-28. LifeOS base: `5e2f2e8`.

LifeOS `ReminderRouter.hook.ts` runs at UserPromptSubmit. When a prompt matches one of its explicit reminder, research, or queue phrases and `WORK.REPO` is configured, `buildIssue()` includes the original prompt verbatim in the issue body. `createIssueDetached()` starts `gh issue create` against that repository. The hook does not send a prompt for nonmatching text or when `WORK.REPO` is unset.

This matters for the private local-model setup: model traffic can stay on the LAN while this hook still sends a matching conversation prompt to GitHub. The isolated `.212` fixture has no `WORK.REPO`, so the route is inactive there. No GitHub issue was created during this investigation. A deployment policy is pending: local reminder storage, explicit GitHub issue routing, or disabling this one route. The other LifeOS hooks remain enabled in the test fixture.

The SessionEnd `UpdateCounts` hook also contains an Anthropic OAuth usage-cache request. It reads a Claude Code OAuth credential from the account before making that request and sends no conversation text. The isolated `.212` account has no such credential or admin key, so this route is inactive there too. The fixture's outbound rule would block it if a credential appeared.
