# ABOUTME: Probes pinned Claude Code hook decisions in an isolated reference account.
# ABOUTME: Writes synthetic hook inputs and summarized outputs without credentials.

import json
import os
import pwd
import subprocess
import sys
import tempfile
from pathlib import Path


HOME_DIR = Path(pwd.getpwuid(os.getuid()).pw_dir)
ROOT = HOME_DIR / ".claude"
LAUNCHER = HOME_DIR / ".local/bin/lifeos-reference"


def run_probe(name, event, matcher, hook_output, prompt, *, tools="Bash", effect_name=""):
    with tempfile.TemporaryDirectory(prefix="parity-contract-", dir=ROOT) as temporary:
        directory = Path(temporary)
        log = directory / "events.jsonl"
        hook = directory / "hook.py"
        hook.write_text(
            "import json,sys\n"
            "from pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            f"with Path({str(log)!r}).open('a') as stream: stream.write(json.dumps(data)+'\\n')\n"
            f"print(json.dumps({hook_output!r}))\n"
        )
        settings = directory / "settings.json"
        settings.write_text(json.dumps({"hooks": {
            event: [{"matcher": matcher, "hooks": [{"type": "command", "command": f"python3 {hook}"}]}],
        }}))
        effect = directory / effect_name if effect_name else None
        if effect is not None:
            prompt = prompt.format(effect=effect)
        command = [str(LAUNCHER), "-p", prompt, "--output-format", "json", "--settings", str(settings),
                   "--permission-mode", "default", "--max-turns", "3" if effect else "1"]
        if tools:
            command.extend(["--tools", tools])
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=180)
        try:
            response = json.loads(result.stdout)
        except json.JSONDecodeError:
            response = {"stdout_tail": result.stdout[-1000:]}
        events = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        return {
            "name": name,
            "returncode": result.returncode,
            "event_count": len(events),
            "events": [{key: event.get(key) for key in ("hook_event_name", "source", "reason", "tool_name", "tool_input")}
                       for event in events],
            "permission_denials": response.get("permission_denials"),
            "is_error": response.get("is_error"),
            "effect_exists": effect.exists() if effect else None,
            "effect_content": effect.read_text() if effect and effect.exists() else None,
            "result_excerpt": str(response.get("result", ""))[-500:],
            "stderr_tail": result.stderr[-1000:],
        }


def main():
    ask = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                    "permissionDecisionReason": "Synthetic review request"}}
    for name, output in (("pretool-allow", {"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "allow",
    }}), ("pretool-ask", ask)):
        if len(sys.argv) > 1 and name not in sys.argv[1:]:
            continue
        marker = f"PARITY-{name.upper()}"
        prompt = f"Use Bash once with the exact command 'printf {marker} > {{effect}}'. Report the tool result."
        print(json.dumps(run_probe(name, "PreToolUse", "Bash", output, prompt,
                                   effect_name="effect.txt")), flush=True)
    for name, matcher in (("start-startup", "startup"), ("start-resume", "resume"),
                          ("start-star", "*")):
        if len(sys.argv) > 1 and name not in sys.argv[1:]:
            continue
        output = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "PARITY-START"}}
        print(json.dumps(run_probe(name, "SessionStart", matcher, output,
                                   "Reply with the word READY without tools.", tools="")), flush=True)
    for name, matcher in (("end-other", "other"), ("end-star", "*")):
        if len(sys.argv) > 1 and name not in sys.argv[1:]:
            continue
        print(json.dumps(run_probe(name, "SessionEnd", matcher, {},
                                   "Reply with the word READY without tools.", tools="")), flush=True)
    for name, matcher in (("pretool-matcher-comma", "Bash, Read"),
                          ("pretool-matcher-regex", "^Ba"),
                          ("pretool-matcher-star", "*")):
        if len(sys.argv) > 1 and name not in sys.argv[1:]:
            continue
        output = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}
        prompt = "Use Bash once with the exact command 'printf PARITY-MATCHER'. Report the tool result."
        print(json.dumps(run_probe(name, "PreToolUse", matcher, output, prompt)), flush=True)


if __name__ == "__main__":
    main()
