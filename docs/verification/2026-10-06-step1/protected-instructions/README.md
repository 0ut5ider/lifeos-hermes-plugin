# Protected instruction approval

Date: 2026-10-06. Target: isolated development accounts on `192.168.8.252`.

A real Hermes one-shot `write_file` request for synthetic `CLAUDE.md` content waits beyond the 120-second fixture bound. The live stack shows `file_tools_write_guards` calling the modal approval callback and waiting on its queue. The one-shot CLI has no active interactive UI to answer that prompt.

The compatibility patch checks the existing single-query approval context after gateway routing and before the CLI callback. It returns the existing no-human refusal. It does not accept the normal unattended auto-approve policy for protected instruction files. Interactive and gateway operations still require their per-operation decision.

The actual corrected CLI returns a blocked tool result and final response in about six seconds. No file mutation or evaluation hook occurs. The retained failed harness summary expects a successful evaluation and therefore cannot be counted as a passing paired case. The CLI result itself verifies the refusal.

Three guard controls pass. They verify that single-query context cannot call the approval callback, interactive one-operation approval still passes, and interactive denial still blocks. These controls exercise the actual guard with an injected decision callback. They are policy controls, not end-to-end transport tests.

The successful sentinel control uses the actual interactive Hermes CLI in a pseudo-terminal. The operator input selects Allow once on the real protected-file panel. The real file tool writes the synthetic target. The actual configuration runner publishes its model-backed evaluation. Separate paired evidence records the completed turn and CLI shutdown.
