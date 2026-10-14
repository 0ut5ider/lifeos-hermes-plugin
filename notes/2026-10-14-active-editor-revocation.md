# Active editor revocation

The 28 backend editor checks pass, but a fresh full pull request review finds one remaining browser path. An open identity row keeps its cached body after the real 60-second overview request returns 403. A separate same-session file request also returns 403. The backend refuses the account correctly. The parent component ignores the overview error and keeps rendering cached rows.

The fix makes any failed overview read withhold the governed surface and disables overview retries. Unmounting the rows discards their draft and review state. This intentionally hides the editor during a temporary overview failure too. Recovery requires a successful current overview and a fresh file read. The regression check keeps the row open across the real timer, instead of closing and reopening it.

The previous archive remains a historical acceptance checkpoint. It does not contain this browser fix. The next complete release package needs new qualification. Production stays on 0.4.3.
