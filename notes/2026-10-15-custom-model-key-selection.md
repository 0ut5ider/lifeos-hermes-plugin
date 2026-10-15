# Select the custom endpoint credential explicitly

Date: 2026-10-15.

The disposable `.244` profile has a valid custom endpoint key in its private environment file. The first real built-in-memory model turn returns HTTP 401. The native runtime resolver selects its direct-alias branch and the `no-key-required` placeholder. Its resolved key does not match the environment file, although the process environment does contain that file's key.

The pinned Hermes runtime selects direct-alias keys from an explicit key, `model.key_env`, or host-gated provider variables. The arbitrary custom endpoint does not select `CUSTOM_API_KEY` automatically on that branch. A successful model-list request therefore does not prove that the actual agent uses the same credential.

The fixture now sets `model.key_env: CUSTOM_API_KEY`. It preserves the selected model, endpoint, and four effort levels. The next fresh real Hermes CLI turn returns the exported synthetic memory marker without tools or earlier chat history. The safe receipt records a model turn and PASS. The original HTTP 401 receipt remains retained. No development or daily server configuration changes.
