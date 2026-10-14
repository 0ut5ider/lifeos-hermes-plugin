# Active editor revocation

The 28 backend editor checks pass, but a fresh full pull request review finds one remaining browser path. An open identity row keeps its cached body after the real 60-second overview request returns 403. A separate same-session file request also returns 403. The backend refuses the account correctly. The parent component ignores the overview error and keeps rendering cached rows.

The fix makes any failed overview read withhold the governed surface and disables overview retries. Unmounting the rows discards their draft and review state. This intentionally hides the editor during a temporary overview failure too. Recovery requires a successful current overview and a fresh file read. The regression check keeps the row open across the real timer, instead of closing and reopening it.

The previous archive remains a historical acceptance checkpoint. It does not contain this browser fix. The next complete release package needs new qualification. Production stays on 0.4.3.

The second independent round confirms the timer fix and fresh source recovery, then finds a related Save path. A real PUT returns 403 while the browser retains all 24 rows and the full draft. The file stays unchanged. The fix retains typed HTTP status and sends all core owner denials to one parent refusal state. Only 401 and 403 trigger this path; 409 preserves the draft. A denial revision prevents a response started before the denial from clearing that state. A real local HTTP test characterizes successful replies and checks denial callbacks for 401, 403, 409, and 503. It fails before the status change and passes afterward.
