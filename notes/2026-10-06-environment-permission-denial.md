# Environment prefixes hid a denied command

Date: 2026-10-06. The installed dispatcher rejected a compound command and a timeout wrapper, but executed `env PAIR=1 touch target` despite a matching `Bash(touch target)` deny rule. The disposable marker file existed afterward. The parser returned only the complete env expression and marked it safe for an allow rule. Its wrapper list omitted env. A leading assignment also kept the executable inside an unmatched complete expression.

The correction exposes literal assignment prefixes and supported env options as command aliases. It follows nested supported wrappers for denial and review. File-target parsing follows wrapped readers too. Unknown env options remain uncertain. Environment-changing aliases do not create an automatic inner allow. An assigned directory change marks subsequent target resolution uncertain rather than resolving against the wrong directory.

The failing installed operation and parser assertions precede the correction. Six parser controls pass after the correction. The installed policy matrix verifies 13 actual file and shell outcomes, including changed policy, managed precedence, malformed review, project trust, wrappers, redirects, directory changes, and symlink aliases. Broader parser and bridge regression checks remain required.
