# Nested execute_code tool session identity

On 2026-09-28, a direct probe of Hermes's `execute_code` RPC dispatcher on the isolated `.212` account recorded only `task_id` in the call to `handle_function_call`. The outer `session_id` was absent. The inner tool hooks therefore ran under the bridge's empty session and could write to a separate transcript or select the wrong project hook settings.

I added `session_id` to the `execute_code` handler, the local `CellAuthority`, the remote session kernel poller, and the remote per-call poller. Each new test failed against the old call path before the change. The local kernel regression runs two cells with different session IDs in one persistent kernel. The file RPC test checks every inner call, while remote kernel and fallback tests check the identity passed into those routes.

The isolated Hermes fork at commit `5ffe49067` passed 100 broader `execute_code` tests, with four skips and five environment-dependent tests deselected. The five deselected tests launched child interpreters that could not import `ruamel.yaml` outside the isolated Hermes runtime. Two test mocks also needed the new `session_id` parameter; their affected tests passed after the mock signatures were updated. The regenerated public patch applied cleanly to public Hermes commit `bac0c45d`, and 49 focused tests passed in that disposable checkout.

A real local probe used the enabled LifeOS bridge with disposable hook settings. An outer `execute_code` call invoked `read_file`. The hook received `PreToolUse` and `PostToolUse` for Read with `session_id: nested-real-hook-probe`. The bridge transcript had four rows: the inner Read call and result, then the outer `execute_code` call and result. The probe used a temporary file and removed its hook settings and marker when it ended.

The remote kernel and remote per-call paths have automated identity checks. A real remote host executing nested calls has not been exercised. The dashboard restart and health result are recorded in the parity record.
